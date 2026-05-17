import React from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Button, Typography, Space } from 'antd';
import {
  ApartmentOutlined,
  TeamOutlined,
  RobotOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  ArrowRightOutlined,
  CrownOutlined,
  FileTextOutlined,
  AuditOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { adminService } from '../features/admin/adminService';
import type { OrganizationAdmin } from '../types/auth';
import { usePermissions } from '../features/auth/authStore';
import { Navigate, useNavigate } from 'react-router-dom';

const { Text } = Typography;

function statusColor(status: string) {
  switch (status) {
    case 'active': return 'green';
    case 'trial': return 'blue';
    case 'suspended': return 'red';
    case 'cancelled': return 'orange';
    default: return 'default';
  }
}

const AdminDashboard: React.FC = () => {
  const { isPlatformAdmin } = usePermissions();
  const navigate = useNavigate();

  if (!isPlatformAdmin) return <Navigate to="/dashboard" replace />;

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: adminService.getStats,
    refetchInterval: 60000,
  });

  const { data: recentOrgs, isLoading: orgsLoading } = useQuery({
    queryKey: ['admin', 'organizations-recent'],
    queryFn: () => adminService.listOrganizations({ limit: 8 }),
  });

  const statCards = [
    {
      title: 'Organisations',
      value: stats?.totalOrganizations || 0,
      suffix: stats ? `(${stats.activeOrganizations} active)` : '',
      icon: <ApartmentOutlined style={{ fontSize: 28, color: '#6366f1' }} />,
      bg: '#f0f0ff',
      onClick: () => navigate('/admin/organizations'),
    },
    {
      title: 'Users',
      value: stats?.totalUsers || 0,
      suffix: stats ? `(${stats.activeUsers} active)` : '',
      icon: <TeamOutlined style={{ fontSize: 28, color: '#0ea5e9' }} />,
      bg: '#f0f9ff',
      onClick: () => navigate('/admin/users'),
    },
    {
      title: 'Agents',
      value: stats?.totalAgents || 0,
      suffix: '',
      icon: <RobotOutlined style={{ fontSize: 28, color: '#10b981' }} />,
      bg: '#f0fdf4',
      onClick: undefined,
    },
    {
      title: 'Deployments',
      value: stats?.totalDeployments || 0,
      suffix: stats ? `(${stats.activeDeployments} active)` : '',
      icon: <CloudServerOutlined style={{ fontSize: 28, color: '#f59e0b' }} />,
      bg: '#fffbeb',
      onClick: undefined,
    },
    {
      title: 'Executions',
      value: stats?.totalExecutions || 0,
      suffix: '',
      icon: <ThunderboltOutlined style={{ fontSize: 28, color: '#8b5cf6' }} />,
      bg: '#faf5ff',
      onClick: undefined,
    },
    {
      title: 'Tools',
      value: stats?.totalTools || 0,
      suffix: '',
      icon: <ToolOutlined style={{ fontSize: 28, color: '#ec4899' }} />,
      bg: '#fdf2f8',
      onClick: undefined,
    },
  ];

  const quickLinks = [
    {
      title: 'Organisations',
      desc: 'Approve, suspend, assign plans',
      icon: <ApartmentOutlined style={{ fontSize: 24, color: '#6366f1' }} />,
      path: '/admin/organizations',
    },
    {
      title: 'Users',
      desc: 'Manage users, roles, impersonation',
      icon: <TeamOutlined style={{ fontSize: 24, color: '#0ea5e9' }} />,
      path: '/admin/users',
    },
    {
      title: 'Plans',
      desc: 'Subscription plans and pricing',
      icon: <CrownOutlined style={{ fontSize: 24, color: '#f59e0b' }} />,
      path: '/admin/plans',
    },
    {
      title: 'Audit Logs',
      desc: 'User actions and security events',
      icon: <AuditOutlined style={{ fontSize: 24, color: '#10b981' }} />,
      path: '/audit-logs',
    },
    {
      title: 'System Logs',
      desc: 'Platform events, errors, cleanup',
      icon: <FileTextOutlined style={{ fontSize: 24, color: '#8b5cf6' }} />,
      path: '/admin/system-logs',
    },
  ];

  const orgColumns = [
    {
      title: 'Organisation',
      key: 'name',
      render: (_: unknown, r: OrganizationAdmin) => (
        <div>
          <div style={{ fontWeight: 500 }}>{r.name}</div>
          {r.slug && <Text type="secondary" style={{ fontSize: 11 }}>/{r.slug}</Text>}
        </div>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      render: (_: unknown, r: OrganizationAdmin) => {
        if (!r.isActive) return <Tag color="red">Inactive</Tag>;
        return <Tag color={statusColor(r.subscriptionStatus)}>
          {r.subscriptionStatus?.charAt(0).toUpperCase() + r.subscriptionStatus?.slice(1)}
        </Tag>;
      },
    },
    {
      title: 'Plan',
      key: 'plan',
      width: 120,
      render: (_: unknown, r: OrganizationAdmin) =>
        r.subscriptionPlanName
          ? <Tag color="blue">{r.subscriptionPlanName}</Tag>
          : <Tag color="orange">No plan</Tag>,
    },
    { title: 'Users', dataIndex: 'userCount', key: 'users', width: 65 },
    { title: 'Agents', dataIndex: 'agentCount', key: 'agents', width: 65 },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'created',
      width: 110,
      render: (v: string) => v ? new Date(v).toLocaleDateString() : '—',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>Platform Overview</h1>
        <Text type="secondary">AgentStudio platform health and activity at a glance</Text>
      </div>

      {/* Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {statCards.map((c) => (
          <Col xs={12} sm={8} md={8} lg={4} key={c.title}>
            <Card
              loading={statsLoading}
              style={{ background: c.bg, border: 'none', cursor: c.onClick ? 'pointer' : 'default' }}
              styles={{ body: { padding: '16px 20px' } }}
              onClick={c.onClick}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ background: '#fff', borderRadius: 10, padding: 8, display: 'flex' }}>
                  {c.icon}
                </div>
                <div>
                  <Statistic
                    title={<span style={{ fontSize: 12 }}>{c.title}</span>}
                    value={c.value}
                    valueStyle={{ fontSize: 22, fontWeight: 700 }}
                  />
                  {c.suffix && <Text type="secondary" style={{ fontSize: 11 }}>{c.suffix}</Text>}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Quick Navigation */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {quickLinks.map((q) => (
          <Col xs={12} sm={8} md={8} lg={4} key={q.title} style={{ flex: '1 1 0' }}>
            <Card
              hoverable
              style={{ cursor: 'pointer', height: '100%' }}
              styles={{ body: { padding: '16px 20px' } }}
              onClick={() => navigate(q.path)}
            >
              <Space direction="vertical" size={4}>
                {q.icon}
                <Text strong style={{ fontSize: 14 }}>{q.title}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>{q.desc}</Text>
              </Space>
              <div style={{ marginTop: 12 }}>
                <Button type="link" size="small" style={{ padding: 0 }} icon={<ArrowRightOutlined />}>
                  Open
                </Button>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Recent Organisations */}
      <Card
        title="Recent Organisations"
        extra={
          <Button type="link" icon={<ArrowRightOutlined />} onClick={() => navigate('/admin/organizations')}>
            View all
          </Button>
        }
      >
        <Table
          dataSource={recentOrgs?.organizations || []}
          columns={orgColumns}
          loading={orgsLoading}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
};

export default AdminDashboard;
