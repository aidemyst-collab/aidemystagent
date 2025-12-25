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
  message,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  DownloadOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { auditService } from '../features/audit/auditService';
import { usePermissions } from '../features/auth/authStore';
import { Navigate } from 'react-router-dom';
import type { AuditLog } from '../types/auth';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Text, Title } = Typography;

const AuditLogs: React.FC = () => {
  const { canAccess } = usePermissions();

  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState<string | undefined>();
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Redirect if user doesn't have permission
  if (!canAccess('audit-logs')) {
    return <Navigate to="/dashboard" replace />;
  }

  // Queries
  const { data: logsData, isLoading, refetch } = useQuery({
    queryKey: ['audit-logs', search, actionFilter, resourceTypeFilter, statusFilter, dateRange, page, pageSize],
    queryFn: () => auditService.list({
      skip: (page - 1) * pageSize,
      limit: pageSize,
      action: actionFilter,
      resourceType: resourceTypeFilter,
      status: statusFilter,
      startDate: dateRange?.[0]?.toISOString(),
      endDate: dateRange?.[1]?.toISOString(),
      search: search || undefined,
    }),
  });

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['audit-summary', dateRange],
    queryFn: () => auditService.getSummary({
      startDate: dateRange?.[0]?.toISOString(),
      endDate: dateRange?.[1]?.toISOString(),
    }),
  });

  const { data: actions } = useQuery({
    queryKey: ['audit-actions'],
    queryFn: auditService.getActions,
  });

  const { data: resourceTypes } = useQuery({
    queryKey: ['audit-resource-types'],
    queryFn: auditService.getResourceTypes,
  });

  const getActionColor = (action: string) => {
    if (action.startsWith('create')) return 'green';
    if (action.startsWith('update')) return 'blue';
    if (action.startsWith('delete')) return 'red';
    if (action.startsWith('login')) return 'cyan';
    if (action.startsWith('logout')) return 'orange';
    return 'default';
  };

  const getStatusIcon = (status: string) => {
    return status === 'success' ? (
      <CheckCircleOutlined style={{ color: '#52c41a' }} />
    ) : (
      <CloseCircleOutlined style={{ color: '#f5222d' }} />
    );
  };

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const blob = await auditService.exportLogs({
        format,
        action: actionFilter,
        resourceType: resourceTypeFilter,
        startDate: dateRange?.[0]?.toISOString(),
        endDate: dateRange?.[1]?.toISOString(),
        limit: 10000,
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${dayjs().format('YYYY-MM-DD')}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      message.success(`Exported audit logs as ${format.toUpperCase()}`);
    } catch {
      message.error('Failed to export audit logs');
    }
  };

  const viewLogDetails = (log: AuditLog) => {
    setSelectedLog(log);
    setDrawerVisible(true);
  };

  const columns = [
    {
      title: 'Timestamp',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
      render: (date: string) => (
        <Text style={{ fontSize: 12 }}>
          {dayjs(date).format('YYYY-MM-DD HH:mm:ss')}
        </Text>
      ),
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => (
        <Tag color={getActionColor(action)}>
          {action.replace(/_/g, ' ')}
        </Tag>
      ),
    },
    {
      title: 'Resource',
      key: 'resource',
      render: (_: unknown, record: AuditLog) => (
        <div>
          <div>{record.resourceType}</div>
          {record.resourceId && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              {record.resourceId.substring(0, 8)}...
            </Text>
          )}
        </div>
      ),
    },
    {
      title: 'User',
      dataIndex: 'userEmail',
      key: 'userEmail',
      render: (email: string) => email || <Text type="secondary">System</Text>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Space>
          {getStatusIcon(status)}
          <span>{status}</span>
        </Space>
      ),
    },
    {
      title: 'IP Address',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
      width: 130,
      render: (ip: string) => ip || '-',
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      render: (_: unknown, record: AuditLog) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => viewLogDetails(record)}
        />
      ),
    },
  ];

  // Flatten actions for select
  const actionOptions = actions
    ? Object.entries(actions).flatMap(([category, acts]) =>
        (acts as string[]).map((action) => ({
          value: action,
          label: `${category}: ${action.replace(/_/g, ' ')}`,
        }))
      )
    : [];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>Audit Logs</h1>
        <p style={{ color: '#888' }}>View system activity and security events</p>
      </div>

      {/* Summary Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} md={6}>
          <Card loading={summaryLoading}>
            <Statistic title="Total Events" value={summary?.totalLogs || 0} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6}>
          <Card loading={summaryLoading}>
            <Statistic
              title="Success Rate"
              value={
                summary?.logsByStatus
                  ? Math.round(
                      ((summary.logsByStatus['success'] || 0) /
                        Math.max(summary.totalLogs, 1)) *
                        100
                    )
                  : 0
              }
              suffix="%"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6}>
          <Card loading={summaryLoading}>
            <Statistic
              title="Failed Events"
              value={summary?.logsByStatus?.['failure'] || 0}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6}>
          <Card loading={summaryLoading}>
            <Statistic
              title="Active Users"
              value={summary?.recentUsers?.length || 0}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        {/* Filters */}
        <div style={{ marginBottom: 16 }}>
          <Row gutter={[8, 8]}>
            <Col xs={24} sm={12} md={6}>
              <Input
                placeholder="Search logs..."
                prefix={<SearchOutlined />}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                allowClear
              />
            </Col>
            <Col xs={24} sm={12} md={5}>
              <Select
                placeholder="Filter by action"
                value={actionFilter}
                onChange={setActionFilter}
                style={{ width: '100%' }}
                allowClear
                showSearch
                optionFilterProp="label"
                options={actionOptions}
              />
            </Col>
            <Col xs={24} sm={12} md={4}>
              <Select
                placeholder="Resource type"
                value={resourceTypeFilter}
                onChange={setResourceTypeFilter}
                style={{ width: '100%' }}
                allowClear
              >
                {resourceTypes?.map((type) => (
                  <Option key={type} value={type}>
                    {type}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col xs={24} sm={12} md={3}>
              <Select
                placeholder="Status"
                value={statusFilter}
                onChange={setStatusFilter}
                style={{ width: '100%' }}
                allowClear
              >
                <Option value="success">Success</Option>
                <Option value="failure">Failure</Option>
              </Select>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <RangePicker
                style={{ width: '100%' }}
                value={dateRange}
                onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
              />
            </Col>
          </Row>
          <Row style={{ marginTop: 8 }}>
            <Col>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
                  Refresh
                </Button>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={() => handleExport('csv')}
                >
                  Export CSV
                </Button>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={() => handleExport('json')}
                >
                  Export JSON
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        <Table
          dataSource={logsData?.audit_logs || []}
          columns={columns}
          loading={isLoading}
          rowKey="id"
          pagination={{
            current: page,
            pageSize: pageSize,
            total: logsData?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} events`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          size="small"
        />
      </Card>

      {/* Log Details Drawer */}
      <Drawer
        title="Audit Log Details"
        placement="right"
        width={500}
        open={drawerVisible}
        onClose={() => {
          setDrawerVisible(false);
          setSelectedLog(null);
        }}
      >
        {selectedLog && (
          <>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="ID">
                <Text copyable>{selectedLog.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Timestamp">
                {dayjs(selectedLog.createdAt).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Action">
                <Tag color={getActionColor(selectedLog.action)}>
                  {selectedLog.action.replace(/_/g, ' ')}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Space>
                  {getStatusIcon(selectedLog.status)}
                  {selectedLog.status}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Resource Type">
                {selectedLog.resourceType}
              </Descriptions.Item>
              <Descriptions.Item label="Resource ID">
                <Text copyable={!!selectedLog.resourceId}>
                  {selectedLog.resourceId || '-'}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="User">
                {selectedLog.userEmail || 'System'}
              </Descriptions.Item>
              <Descriptions.Item label="User ID">
                <Text copyable={!!selectedLog.userId}>
                  {selectedLog.userId || '-'}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="Organization ID">
                <Text copyable={!!selectedLog.organizationId}>
                  {selectedLog.organizationId || '-'}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="IP Address">
                {selectedLog.ipAddress || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="User Agent">
                <Text style={{ fontSize: 11 }}>
                  {selectedLog.userAgent || '-'}
                </Text>
              </Descriptions.Item>
            </Descriptions>

            {selectedLog.changes && Object.keys(selectedLog.changes).length > 0 && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>Changes</Title>
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    fontSize: 12,
                    overflow: 'auto',
                  }}
                >
                  {JSON.stringify(selectedLog.changes, null, 2)}
                </pre>
              </div>
            )}

            {selectedLog.metadata && Object.keys(selectedLog.metadata).length > 0 && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>Metadata</Title>
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    fontSize: 12,
                    overflow: 'auto',
                  }}
                >
                  {JSON.stringify(selectedLog.metadata, null, 2)}
                </pre>
              </div>
            )}

            {selectedLog.errorMessage && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>Error Message</Title>
                <Text type="danger">{selectedLog.errorMessage}</Text>
              </div>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default AuditLogs;
