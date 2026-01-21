import React, { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Input,
  Select,
  Button,
  DatePicker,
  Drawer,
  Descriptions,
  Typography,
  Row,
  Col,
  Statistic,
  Collapse,
  Timeline,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { usePermissions } from '../features/auth/authStore';
import { Navigate } from 'react-router-dom';
import { apiClient } from '../services/api';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Text, Title } = Typography;
const { Panel } = Collapse;

interface WorkflowExecution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  user_id: string;
  session_id: string | null;
  input: {
    raw_input: string;
    mode: string;
    session_id?: string;
    processed_input?: string;
    node_inputs?: Record<string, unknown>;
  };
  output: {
    result: string;
    llm_usage?: Record<string, number>;
    llm_cost?: Record<string, number>;
    node_outputs?: Record<string, unknown>;
    execution_trace?: string[];
  };
  tokens_used: number;
  execution_time: number;
  created_at: string;
}

interface ExecutionListResponse {
  total: number;
  executions: WorkflowExecution[];
}

// Fetch executions from API
const fetchExecutions = async (params: {
  skip?: number;
  limit?: number;
  workflowId?: string;
  startDate?: string;
  endDate?: string;
}): Promise<ExecutionListResponse> => {
  const queryParams = new URLSearchParams();
  if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
  if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params.workflowId) queryParams.append('workflow_id', params.workflowId);
  if (params.startDate) queryParams.append('start_date', params.startDate);
  if (params.endDate) queryParams.append('end_date', params.endDate);

  const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
  return apiClient.get<ExecutionListResponse>(`/workflows/executions/all${query}`);
};

// Fetch workflows for filter dropdown
const fetchWorkflows = async (): Promise<{ workflows: { id: string; name: string }[] }> => {
  return apiClient.get('/workflows');
};

const ExecutionLogs: React.FC = () => {
  const { canAccess } = usePermissions();

  const [workflowFilter, setWorkflowFilter] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<WorkflowExecution | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Redirect if user doesn't have permission
  if (!canAccess('audit-logs')) {
    return <Navigate to="/dashboard" replace />;
  }

  // Queries
  const { data: executionsData, isLoading, refetch } = useQuery({
    queryKey: ['execution-logs', workflowFilter, dateRange, page, pageSize],
    queryFn: () => fetchExecutions({
      skip: (page - 1) * pageSize,
      limit: pageSize,
      workflowId: workflowFilter,
      startDate: dateRange?.[0]?.toISOString(),
      endDate: dateRange?.[1]?.toISOString(),
    }),
  });

  const { data: workflowsData } = useQuery({
    queryKey: ['workflows-list'],
    queryFn: fetchWorkflows,
  });

  // Calculate summary stats
  const totalTokens = executionsData?.executions?.reduce((sum, e) => sum + (e.tokens_used || 0), 0) || 0;
  const avgExecutionTime = executionsData?.executions?.length
    ? Math.round(
        executionsData.executions.reduce((sum, e) => sum + (e.execution_time || 0), 0) /
          executionsData.executions.length
      )
    : 0;

  const viewExecutionDetails = (execution: WorkflowExecution) => {
    setSelectedExecution(execution);
    setDrawerVisible(true);
  };

  const columns = [
    {
      title: 'Timestamp',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => (
        <Text style={{ fontSize: 12 }}>
          {dayjs(date).format('YYYY-MM-DD HH:mm:ss')}
        </Text>
      ),
    },
    {
      title: 'Workflow',
      dataIndex: 'workflow_name',
      key: 'workflow_name',
      render: (name: string) => <Tag color="blue">{name}</Tag>,
    },
    {
      title: 'Session',
      dataIndex: 'session_id',
      key: 'session_id',
      width: 150,
      render: (sessionId: string) =>
        sessionId ? (
          <Text code style={{ fontSize: 11 }}>
            {sessionId.substring(0, 16)}...
          </Text>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: 'Mode',
      key: 'mode',
      width: 100,
      render: (_: unknown, record: WorkflowExecution) => (
        <Tag>{record.input?.mode || 'chat'}</Tag>
      ),
    },
    {
      title: 'Tokens',
      dataIndex: 'tokens_used',
      key: 'tokens_used',
      width: 100,
      render: (tokens: number) => (
        <Text>{tokens?.toLocaleString() || 0}</Text>
      ),
    },
    {
      title: 'Duration',
      dataIndex: 'execution_time',
      key: 'execution_time',
      width: 100,
      render: (ms: number) => (
        <Text>{ms ? `${(ms / 1000).toFixed(2)}s` : '-'}</Text>
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      render: (_: unknown, record: WorkflowExecution) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => viewExecutionDetails(record)}
        />
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>Workflow Execution Logs</h1>
        <p style={{ color: '#888' }}>View detailed workflow execution history with node-level data</p>
      </div>

      {/* Summary Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} md={6}>
          <Card loading={isLoading}>
            <Statistic
              title="Total Executions"
              value={executionsData?.total || 0}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6}>
          <Card loading={isLoading}>
            <Statistic
              title="Total Tokens"
              value={totalTokens}
              suffix="tokens"
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6}>
          <Card loading={isLoading}>
            <Statistic
              title="Avg Duration"
              value={avgExecutionTime}
              suffix="ms"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6}>
          <Card loading={isLoading}>
            <Statistic
              title="Workflows"
              value={workflowsData?.workflows?.length || 0}
              prefix={<NodeIndexOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        {/* Filters */}
        <div style={{ marginBottom: 16 }}>
          <Row gutter={[8, 8]}>
            <Col xs={24} sm={12} md={6}>
              <Select
                placeholder="Filter by workflow"
                value={workflowFilter}
                onChange={setWorkflowFilter}
                style={{ width: '100%' }}
                allowClear
                showSearch
                optionFilterProp="children"
              >
                {workflowsData?.workflows?.map((w) => (
                  <Option key={w.id} value={w.id}>
                    {w.name}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <RangePicker
                style={{ width: '100%' }}
                value={dateRange}
                onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
              />
            </Col>
            <Col>
              <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
                Refresh
              </Button>
            </Col>
          </Row>
        </div>

        <Table
          dataSource={executionsData?.executions || []}
          columns={columns}
          loading={isLoading}
          rowKey="id"
          pagination={{
            current: page,
            pageSize: pageSize,
            total: executionsData?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} executions`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          size="small"
        />
      </Card>

      {/* Execution Details Drawer */}
      <Drawer
        title="Execution Details"
        placement="right"
        width={700}
        open={drawerVisible}
        onClose={() => {
          setDrawerVisible(false);
          setSelectedExecution(null);
        }}
      >
        {selectedExecution && (
          <>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="Execution ID" span={2}>
                <Text copyable>{selectedExecution.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Workflow">
                <Tag color="blue">{selectedExecution.workflow_name}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Timestamp">
                {dayjs(selectedExecution.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Session ID" span={2}>
                <Text copyable={!!selectedExecution.session_id}>
                  {selectedExecution.session_id || '-'}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="Mode">
                <Tag>{selectedExecution.input?.mode || 'chat'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Duration">
                {selectedExecution.execution_time
                  ? `${(selectedExecution.execution_time / 1000).toFixed(2)}s`
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Tokens Used">
                {selectedExecution.tokens_used?.toLocaleString() || 0}
              </Descriptions.Item>
              <Descriptions.Item label="LLM Cost">
                {selectedExecution.output?.llm_cost
                  ? `$${Object.values(selectedExecution.output.llm_cost).reduce((a: number, b: unknown) => a + (Number(b) || 0), 0).toFixed(6)}`
                  : '-'}
              </Descriptions.Item>
            </Descriptions>

            <Collapse style={{ marginTop: 24 }} defaultActiveKey={['input', 'output']}>
              <Panel header="Input" key="input">
                <div style={{ marginBottom: 12 }}>
                  <Text strong>Raw Input:</Text>
                  <pre
                    style={{
                      background: '#f5f5f5',
                      padding: 12,
                      borderRadius: 4,
                      fontSize: 12,
                      overflow: 'auto',
                      maxHeight: 200,
                    }}
                  >
                    {selectedExecution.input?.raw_input || '-'}
                  </pre>
                </div>
                {selectedExecution.input?.processed_input && (
                  <div>
                    <Text strong>Processed Input:</Text>
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 12,
                        borderRadius: 4,
                        fontSize: 12,
                        overflow: 'auto',
                        maxHeight: 200,
                      }}
                    >
                      {selectedExecution.input.processed_input}
                    </pre>
                  </div>
                )}
              </Panel>

              <Panel header="Output" key="output">
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    fontSize: 12,
                    overflow: 'auto',
                    maxHeight: 300,
                  }}
                >
                  {selectedExecution.output?.result || '-'}
                </pre>
              </Panel>

              {selectedExecution.output?.execution_trace &&
                selectedExecution.output.execution_trace.length > 0 && (
                  <Panel header="Execution Path" key="trace">
                    <Timeline>
                      {selectedExecution.output.execution_trace.map((node, index) => (
                        <Timeline.Item key={index} color="blue">
                          {node}
                        </Timeline.Item>
                      ))}
                    </Timeline>
                  </Panel>
                )}

              {selectedExecution.input?.node_inputs &&
                Object.keys(selectedExecution.input.node_inputs).length > 0 && (
                  <Panel header="Node Inputs" key="node_inputs">
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 12,
                        borderRadius: 4,
                        fontSize: 11,
                        overflow: 'auto',
                        maxHeight: 400,
                      }}
                    >
                      {JSON.stringify(selectedExecution.input.node_inputs, null, 2)}
                    </pre>
                  </Panel>
                )}

              {selectedExecution.output?.node_outputs &&
                Object.keys(selectedExecution.output.node_outputs).length > 0 && (
                  <Panel header="Node Outputs" key="node_outputs">
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 12,
                        borderRadius: 4,
                        fontSize: 11,
                        overflow: 'auto',
                        maxHeight: 400,
                      }}
                    >
                      {JSON.stringify(selectedExecution.output.node_outputs, null, 2)}
                    </pre>
                  </Panel>
                )}

              {selectedExecution.output?.llm_usage && (
                <Panel header="LLM Usage" key="llm_usage">
                  <Descriptions column={2} size="small">
                    {Object.entries(selectedExecution.output.llm_usage).map(([key, value]) => (
                      <Descriptions.Item key={key} label={key.replace(/_/g, ' ')}>
                        {typeof value === 'number' ? value.toLocaleString() : String(value)}
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                </Panel>
              )}
            </Collapse>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default ExecutionLogs;
