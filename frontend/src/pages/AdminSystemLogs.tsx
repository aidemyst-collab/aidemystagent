import React, { useState } from 'react';
import { Card, Table, Tag, Input, Select, Typography, Space } from 'antd';
import {
  SearchOutlined, InfoCircleOutlined, WarningOutlined, CloseCircleOutlined, CheckCircleOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { usePermissions } from '../features/auth/authStore';
import { Navigate } from 'react-router-dom';

const { Text } = Typography;
const { Option } = Select;

interface SystemLogEntry {
  id: string;
  level: string;
  category: string;
  message: string;
  details?: Record<string, unknown>;
  source?: string;
  created_at: string;
}

const levelConfig: Record<string, { color: string; icon: React.ReactNode }> = {
  INFO: { color: 'blue', icon: <InfoCircleOutlined /> },
  WARNING: { color: 'orange', icon: <WarningOutlined /> },
  ERROR: { color: 'red', icon: <CloseCircleOutlined /> },
  CRITICAL: { color: 'volcano', icon: <CloseCircleOutlined /> },
};

const AdminSystemLogs: React.FC = () => {
  const { isPlatformAdmin } = usePermissions();
  const [level, setLevel] = useState<string | undefined>();
  const [category, setCategory] = useState<string | undefined>();
  const [search, setSearch] = useState('');

  if (!isPlatformAdmin) return <Navigate to="/dashboard" replace />;

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'system-logs', level, category, search],
    queryFn: () => {
      const p = new URLSearchParams();
      if (level) p.set('level', level);
      if (category) p.set('category', category);
      if (search) p.set('search', search);
      return apiClient.get(`/admin/system-logs?${p.toString()}`) as Promise<{
        logs: SystemLogEntry[];
        total: number;
      }>;
    },
    refetchInterval: 30000,
  });

  const columns = [
    {
      title: 'Time',
      dataIndex: 'created_at',
      key: 'time',
      width: 165,
      render: (v: string) => v ? new Date(v).toLocaleString() : '—',
    },
    {
      title: 'Level',
      dataIndex: 'level',
      key: 'level',
      width: 100,
      render: (lv: string) => {
        const c = levelConfig[lv] || { color: 'default', icon: <CheckCircleOutlined /> };
        return <Tag color={c.color} icon={c.icon}>{lv}</Tag>;
      },
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (cat: string) => <Tag>{cat}</Tag>,
    },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
    },
    {
      title: 'Source',
      dataIndex: 'source',
      key: 'source',
      width: 180,
      render: (src: string) => src
        ? <Text type="secondary" style={{ fontSize: 11 }}>{src}</Text>
        : '—',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>System Logs</h1>
        <Text type="secondary">Platform event log — auto-refreshes every 30 seconds. Entries older than 30 days are removed automatically.</Text>
      </div>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Input
            placeholder="Search message..."
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 260 }}
            allowClear
          />
          <Select placeholder="Level" value={level} onChange={setLevel} style={{ width: 130 }} allowClear>
            <Option value="INFO">INFO</Option>
            <Option value="WARNING">WARNING</Option>
            <Option value="ERROR">ERROR</Option>
            <Option value="CRITICAL">CRITICAL</Option>
          </Select>
          <Select placeholder="Category" value={category} onChange={setCategory} style={{ width: 160 }} allowClear>
            <Option value="auth">auth</Option>
            <Option value="system">system</Option>
            <Option value="admin">admin</Option>
            <Option value="deployment">deployment</Option>
          </Select>
          {data && (
            <Text type="secondary" style={{ lineHeight: '32px', fontSize: 13 }}>
              {data.total} entries
            </Text>
          )}
        </div>

        <Table
          dataSource={data?.logs || []}
          columns={columns}
          loading={isLoading}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `${t} logs` }}
        />
      </Card>
    </div>
  );
};

export default AdminSystemLogs;
