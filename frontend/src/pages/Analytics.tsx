import React, { useState } from 'react';
import { Row, Col, Card, Statistic, Alert, Select, DatePicker, Tooltip, Typography, Button } from 'antd';
import {
  RocketOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ApiOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { Dayjs } from 'dayjs';
import { Progress } from 'antd';
import { apiClient } from '../services/api';
import { QuotaUsage } from '../components/Common/QuotaUsage';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Text } = Typography;

interface ExecutionByAgent {
  agent_name: string;
  count: number;
}

interface ExecutionOverTime {
  date: string;
  count: number;
}

interface ExecutionTrend {
  date: string;
  count: number;
}

interface Agent {
  id: string;
  name: string;
}

interface AgentsResponse {
  agents: Agent[];
}

interface AnalyticsData {
  total_agents: number;
  total_executions: number;
  avg_execution_time: number;
  success_rate: number;
  executions_by_agent: ExecutionByAgent[];
  executions_over_time: ExecutionOverTime[];
  executions_30d?: ExecutionTrend[];
  total_tokens_used?: number;
}

export const Analytics: React.FC = () => {
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  const { data, isLoading, error, refetch } = useQuery<AnalyticsData>({
    queryKey: ['analytics', selectedAgent, dateRange],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedAgent !== 'all') params.append('agent_id', selectedAgent);
      if (dateRange?.[0]) params.append('start_date', dateRange[0].toISOString());
      if (dateRange?.[1]) params.append('end_date', dateRange[1].toISOString());
      return apiClient.get<AnalyticsData>(`/analytics?${params}`);
    },
  });

  const { data: agentsData } = useQuery<AgentsResponse>({
    queryKey: ['agents-for-filter'],
    queryFn: () => apiClient.get<AgentsResponse>('/agents'),
  });

  if (error) {
    return (
      <div className="p-6">
        <Alert message="Error" description={(error as Error).message} type="error" showIcon />
      </div>
    );
  }

  const maxCount = Math.max(...(data?.executions_30d || []).map((d) => d.count), 1);

  return (
    <div className="p-6">
      <div className="mb-6" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="text-3xl font-bold mb-2">Analytics Dashboard</h1>
          <p className="text-gray-600">Monitor your agent performance and usage</p>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()} loading={isLoading}>
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-4">
        <Select
          value={selectedAgent}
          onChange={setSelectedAgent}
          style={{ width: 200 }}
          loading={isLoading}
        >
          <Option value="all">All Agents</Option>
          {(agentsData?.agents || []).map((agent) => (
            <Option key={agent.id} value={agent.id}>
              {agent.name}
            </Option>
          ))}
        </Select>

        <RangePicker
          onChange={(dates) => setDateRange(dates as [Dayjs | null, Dayjs | null] | null)}
          style={{ width: 300 }}
        />
      </div>

      {/* Stats Cards */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Agents"
              value={data?.total_agents || 0}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#1890ff' }}
              loading={isLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Executions"
              value={data?.total_executions || 0}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#52c41a' }}
              loading={isLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Avg Execution Time"
              value={data?.avg_execution_time || 0}
              suffix="ms"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
              loading={isLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Success Rate"
              value={data?.success_rate || 0}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
              loading={isLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Tokens Used"
              value={data?.total_tokens_used || 0}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#722ed1' }}
              formatter={(v) => Number(v).toLocaleString()}
              loading={isLoading}
            />
          </Card>
        </Col>
      </Row>

      {/* Executions by Agent + Over Time */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={12}>
          <Card title="Executions by Agent" className="h-full">
            {data?.executions_by_agent && data.executions_by_agent.length > 0 ? (
              <div>
                {data.executions_by_agent.map((item, i) => {
                  const maxAgentCount = Math.max(
                    ...data.executions_by_agent.map((a) => a.count),
                    1
                  );
                  return (
                    <div key={i} style={{ marginBottom: 12 }}>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          marginBottom: 4,
                        }}
                      >
                        <Text>{item.agent_name}</Text>
                        <Text strong>{item.count}</Text>
                      </div>
                      <Progress
                        percent={Math.round((item.count / maxAgentCount) * 100)}
                        showInfo={false}
                        strokeColor="#6366f1"
                        size="small"
                      />
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-500">No data available</p>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Executions Over Time" className="h-full">
            {data?.executions_over_time && data.executions_over_time.length > 0 ? (
              <div className="space-y-2">
                {data.executions_over_time.map((item, index) => (
                  <div key={index} className="flex justify-between items-center">
                    <span>{new Date(item.date).toLocaleDateString()}</span>
                    <span className="font-bold text-green-600">{item.count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No data available</p>
            )}
          </Card>
        </Col>
      </Row>

      {/* 30-Day Execution Trend */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24}>
          <Card title="Execution Trend (30 Days)">
            {data?.executions_30d && data.executions_30d.length > 0 ? (
              <>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-end',
                    gap: 3,
                    height: 120,
                    padding: '0 8px',
                  }}
                >
                  {data.executions_30d.map((item, i) => (
                    <Tooltip key={i} title={`${item.date}: ${item.count} executions`}>
                      <div
                        style={{
                          flex: 1,
                          height: `${Math.max((item.count / maxCount) * 100, 2)}%`,
                          background: '#6366f1',
                          borderRadius: '2px 2px 0 0',
                          cursor: 'pointer',
                          transition: 'opacity 0.2s',
                        }}
                      />
                    </Tooltip>
                  ))}
                </div>
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 8px 0' }}
                >
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {data.executions_30d[0]?.date}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {data.executions_30d[data.executions_30d.length - 1]?.date}
                  </Text>
                </div>
              </>
            ) : (
              <p className="text-gray-500">No trend data available</p>
            )}
          </Card>
        </Col>
      </Row>

      {/* Resource Limits */}
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <QuotaUsage />
        </Col>
      </Row>
    </div>
  );
};
