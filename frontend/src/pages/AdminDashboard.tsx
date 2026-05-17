import React, { useState } from 'react';
import { Badge, Card, Row, Col, Statistic, Table, Tag, Input, Select, Button, Tabs, Space, message, Modal, Form, InputNumber, Switch, Typography } from 'antd';
import {
  TeamOutlined,
  ApartmentOutlined,
  RobotOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  SearchOutlined,
  ReloadOutlined,
  CrownOutlined,
  PlusOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminService } from '../features/admin/adminService';
import type { OrganizationAdmin, UserAdmin, SubscriptionPlan } from '../types/auth';
import { usePermissions, useImpersonation } from '../features/auth/authStore';
import { Navigate, useNavigate } from 'react-router-dom';
import { apiClient } from '../services/api';

const { TabPane } = Tabs;
const { Option } = Select;
const { Text } = Typography;

interface OrgApprovalRecord {
  id: string;
  name: string;
  slug?: string;
  approvalStatus: string;
  ownerEmail: string;
  userCount: number;
  createdAt: string;
}

const AdminDashboard: React.FC = () => {
  const { isPlatformAdmin } = usePermissions();
  const navigate = useNavigate();
  const { startImpersonation } = useImpersonation();
  const queryClient = useQueryClient();

  const [orgSearch, setOrgSearch] = useState('');
  const [orgStatusFilter, setOrgStatusFilter] = useState<string | undefined>();
  const [userSearch, setUserSearch] = useState('');
  const [planModalVisible, setPlanModalVisible] = useState(false);
  const [editingPlan, setEditingPlan] = useState<SubscriptionPlan | null>(null);
  const [planForm] = Form.useForm();
  const [orgModalVisible, setOrgModalVisible] = useState(false);
  const [orgForm] = Form.useForm();
  const [userModalVisible, setUserModalVisible] = useState(false);
  const [userForm] = Form.useForm();
  const [assignPlanModalVisible, setAssignPlanModalVisible] = useState(false);
  const [selectedOrgForPlan, setSelectedOrgForPlan] = useState<OrganizationAdmin | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<string | undefined>();

  // Org approval panel state
  const [approvalTab, setApprovalTab] = useState<'pending' | 'active' | 'suspended' | 'all'>('pending');
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [rejectingOrgId, setRejectingOrgId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // Redirect non-platform admins
  if (!isPlatformAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  // Queries
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: adminService.getStats,
  });

  const { data: orgsData, isLoading: orgsLoading } = useQuery({
    queryKey: ['admin', 'organizations', orgSearch, orgStatusFilter],
    queryFn: () => adminService.listOrganizations({
      search: orgSearch || undefined,
      subscriptionStatus: orgStatusFilter,
    }),
  });

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['admin', 'users', userSearch],
    queryFn: () => adminService.listAllUsers({
      search: userSearch || undefined,
    }),
  });

  const { data: plansData, isLoading: plansLoading } = useQuery({
    queryKey: ['admin', 'subscription-plans'],
    queryFn: () => adminService.listSubscriptionPlans({ includeInactive: true }),
  });

  // Org approval queries — one per tab
  const { data: pendingOrgsData, isLoading: pendingOrgsLoading } = useQuery({
    queryKey: ['admin-organizations', 'pending'],
    queryFn: () => apiClient.get('/admin/organizations?status=pending') as Promise<{ organizations: OrgApprovalRecord[]; total: number }>,
  });

  const { data: activeApprovalOrgsData, isLoading: activeApprovalOrgsLoading } = useQuery({
    queryKey: ['admin-organizations', 'active'],
    queryFn: () => apiClient.get('/admin/organizations?status=active') as Promise<{ organizations: OrgApprovalRecord[]; total: number }>,
    enabled: approvalTab === 'active',
  });

  const { data: suspendedApprovalOrgsData, isLoading: suspendedApprovalOrgsLoading } = useQuery({
    queryKey: ['admin-organizations', 'suspended'],
    queryFn: () => apiClient.get('/admin/organizations?status=suspended') as Promise<{ organizations: OrgApprovalRecord[]; total: number }>,
    enabled: approvalTab === 'suspended',
  });

  const { data: allApprovalOrgsData, isLoading: allApprovalOrgsLoading } = useQuery({
    queryKey: ['admin-organizations', 'all'],
    queryFn: () => apiClient.get('/admin/organizations') as Promise<{ organizations: OrgApprovalRecord[]; total: number }>,
    enabled: approvalTab === 'all',
  });

  const approveOrg = useMutation({
    mutationFn: (orgId: string) => apiClient.post(`/admin/organizations/${orgId}/approve`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-organizations'] });
      message.success('Organisation approved');
    },
    onError: () => {
      message.error('Failed to approve organisation');
    },
  });

  const rejectOrg = useMutation({
    mutationFn: ({ orgId, reason }: { orgId: string; reason: string }) =>
      apiClient.post(`/admin/organizations/${orgId}/reject`, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-organizations'] });
      message.success('Organisation rejected');
      setRejectModalVisible(false);
      setRejectingOrgId(null);
      setRejectReason('');
    },
    onError: () => {
      message.error('Failed to reject organisation');
    },
  });

  const suspendOrg = useMutation({
    mutationFn: (orgId: string) => apiClient.post(`/admin/organizations/${orgId}/suspend`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-organizations'] });
      message.success('Organisation suspended');
    },
    onError: () => {
      message.error('Failed to suspend organisation');
    },
  });

  const reactivateOrg = useMutation({
    mutationFn: (orgId: string) => apiClient.post(`/admin/organizations/${orgId}/reactivate`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-organizations'] });
      message.success('Organisation reactivated');
    },
    onError: () => {
      message.error('Failed to reactivate organisation');
    },
  });

  // Mutations
  const updateOrgStatus = useMutation({
    mutationFn: ({ orgId, data }: { orgId: string; data: { isActive?: boolean; subscriptionStatus?: string; subscriptionPlanId?: string } }) =>
      adminService.updateOrganizationStatus(orgId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'organizations'] });
      message.success('Organization updated');
    },
    onError: () => {
      message.error('Failed to update organization');
    },
  });

  const assignPlanToOrg = useMutation({
    mutationFn: ({ orgId, planId }: { orgId: string; planId: string }) =>
      adminService.updateOrganizationStatus(orgId, { subscriptionPlanId: planId, subscriptionStatus: 'active' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'organizations'] });
      message.success('Plan assigned successfully');
      setAssignPlanModalVisible(false);
      setSelectedOrgForPlan(null);
      setSelectedPlanId(undefined);
    },
    onError: () => {
      message.error('Failed to assign plan');
    },
  });

  const togglePlatformAdmin = useMutation({
    mutationFn: ({ userId, isAdmin }: { userId: string; isAdmin: boolean }) =>
      adminService.togglePlatformAdmin(userId, isAdmin),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      message.success('User updated');
    },
    onError: () => {
      message.error('Failed to update user');
    },
  });

  const updateUserStatus = useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      adminService.updateUserStatus(userId, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      message.success('User status updated');
    },
    onError: () => {
      message.error('Failed to update user status');
    },
  });

  const createOrganization = useMutation({
    mutationFn: adminService.createOrganization,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'organizations'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
      message.success('Organization created successfully');
      setOrgModalVisible(false);
      orgForm.resetFields();
    },
    onError: (error: Error) => {
      message.error(error.message || 'Failed to create organization');
    },
  });

  const createUser = useMutation({
    mutationFn: adminService.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
      message.success('User created successfully');
      setUserModalVisible(false);
      userForm.resetFields();
    },
    onError: (error: Error) => {
      message.error(error.message || 'Failed to create user');
    },
  });

  const createPlan = useMutation({
    mutationFn: adminService.createSubscriptionPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'subscription-plans'] });
      message.success('Plan created');
      setPlanModalVisible(false);
      planForm.resetFields();
    },
    onError: () => {
      message.error('Failed to create plan');
    },
  });

  const updatePlan = useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: Parameters<typeof adminService.updateSubscriptionPlan>[1] }) =>
      adminService.updateSubscriptionPlan(planId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'subscription-plans'] });
      message.success('Plan updated');
      setPlanModalVisible(false);
      setEditingPlan(null);
      planForm.resetFields();
    },
    onError: () => {
      message.error('Failed to update plan');
    },
  });

  const impersonateUser = useMutation({
    mutationFn: (userId: string) =>
      apiClient.post(`/auth/impersonate/${userId}`, {}) as Promise<{
        accessToken: string;
        targetUser: UserAdmin;
      }>,
    onSuccess: (data) => {
      startImpersonation(data.targetUser as any, data.accessToken);
      navigate('/dashboard');
      message.success(`Now viewing as ${data.targetUser.email}`);
    },
    onError: (error: Error) => {
      message.error(error.message || 'Failed to start impersonation session');
    },
  });

  // Organization columns
  const orgColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: OrganizationAdmin) => (
        <div>
          <div style={{ fontWeight: 500 }}>{name}</div>
          {record.slug && <div style={{ fontSize: 12, color: '#888' }}>/{record.slug}</div>}
        </div>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_: unknown, record: OrganizationAdmin) => (
        <Space direction="vertical" size={0}>
          <Tag color={record.isActive ? 'green' : 'red'}>
            {record.isActive ? 'Active' : 'Inactive'}
          </Tag>
          <Tag color={getStatusColor(record.subscriptionStatus)}>
            {record.subscriptionStatus}
          </Tag>
        </Space>
      ),
    },
    {
      title: 'Plan',
      dataIndex: 'subscriptionPlanName',
      key: 'plan',
      render: (plan: string, record: OrganizationAdmin) => (
        <Space>
          {plan ? (
            <Tag color="blue">{plan}</Tag>
          ) : (
            <Tag color="orange">No plan</Tag>
          )}
          <Button
            size="small"
            type="link"
            onClick={() => {
              setSelectedOrgForPlan(record);
              setSelectedPlanId(undefined);
              setAssignPlanModalVisible(true);
            }}
          >
            Change
          </Button>
        </Space>
      ),
    },
    {
      title: 'Users',
      dataIndex: 'userCount',
      key: 'userCount',
    },
    {
      title: 'Agents',
      dataIndex: 'agentCount',
      key: 'agentCount',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: OrganizationAdmin) => (
        <Space>
          <Button
            size="small"
            onClick={() => updateOrgStatus.mutate({
              orgId: record.id,
              data: { isActive: !record.isActive },
            })}
          >
            {record.isActive ? 'Deactivate' : 'Activate'}
          </Button>
        </Space>
      ),
    },
  ];

  // User columns
  const userColumns = [
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (email: string, record: UserAdmin) => (
        <div>
          <div style={{ fontWeight: 500 }}>{email}</div>
          {record.fullName && <div style={{ fontSize: 12, color: '#888' }}>{record.fullName}</div>}
        </div>
      ),
    },
    {
      title: 'Organization',
      dataIndex: 'organizationName',
      key: 'organizationName',
    },
    {
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role: string, record: UserAdmin) => (
        <Space>
          <Tag>{role}</Tag>
          {record.isPlatformAdmin && <Tag color="gold" icon={<CrownOutlined />}>Platform Admin</Tag>}
        </Space>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_: unknown, record: UserAdmin) => (
        <Space>
          <Tag color={record.isActive ? 'green' : 'red'}>
            {record.isActive ? 'Active' : 'Inactive'}
          </Tag>
          {record.emailVerified && <Tag color="blue">Verified</Tag>}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: UserAdmin) => (
        <Space>
          <Button
            size="small"
            onClick={() => updateUserStatus.mutate({
              userId: record.id,
              isActive: !record.isActive,
            })}
          >
            {record.isActive ? 'Deactivate' : 'Activate'}
          </Button>
          <Button
            size="small"
            type={record.isPlatformAdmin ? 'default' : 'primary'}
            onClick={() => togglePlatformAdmin.mutate({
              userId: record.id,
              isAdmin: !record.isPlatformAdmin,
            })}
          >
            {record.isPlatformAdmin ? 'Remove Admin' : 'Make Admin'}
          </Button>
          {!record.isPlatformAdmin && (
            <Button
              size="small"
              icon={<EyeOutlined />}
              title="Impersonate user for troubleshooting"
              loading={impersonateUser.isPending && impersonateUser.variables === record.id}
              onClick={() => impersonateUser.mutate(record.id)}
            >
              Impersonate
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // Plan columns
  const planColumns = [
    {
      title: 'Name',
      dataIndex: 'displayName',
      key: 'displayName',
      render: (name: string, record: SubscriptionPlan) => (
        <div>
          <div style={{ fontWeight: 500 }}>{name}</div>
          <div style={{ fontSize: 12, color: '#888' }}>{record.name}</div>
        </div>
      ),
    },
    {
      title: 'Limits',
      key: 'limits',
      render: (_: unknown, record: SubscriptionPlan) => (
        <Space direction="vertical" size={0} style={{ fontSize: 12 }}>
          <span>Users: {record.maxUsers === -1 ? '∞' : record.maxUsers}</span>
          <span>Agents: {record.maxAgents === -1 ? '∞' : record.maxAgents}</span>
          <span>Executions: {record.maxExecutionsPerMonth === -1 ? '∞' : record.maxExecutionsPerMonth}/mo</span>
        </Space>
      ),
    },
    {
      title: 'Price',
      key: 'price',
      render: (_: unknown, record: SubscriptionPlan) => (
        <Space direction="vertical" size={0}>
          <span>${(record.priceMonthyCents / 100).toFixed(2)}/mo</span>
          <span style={{ fontSize: 12, color: '#888' }}>${(record.priceYearlyCents / 100).toFixed(2)}/yr</span>
        </Space>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_: unknown, record: SubscriptionPlan) => (
        <Space>
          <Tag color={record.isActive ? 'green' : 'red'}>
            {record.isActive ? 'Active' : 'Inactive'}
          </Tag>
          {record.isPublic && <Tag color="blue">Public</Tag>}
        </Space>
      ),
    },
    {
      title: 'Organizations',
      dataIndex: 'organizationCount',
      key: 'organizationCount',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: SubscriptionPlan) => (
        <Button
          size="small"
          onClick={() => {
            setEditingPlan(record);
            planForm.setFieldsValue({
              displayName: record.displayName,
              description: record.description,
              maxUsers: record.maxUsers,
              maxAgents: record.maxAgents,
              maxDeployments: record.maxDeployments,
              maxExecutionsPerMonth: record.maxExecutionsPerMonth,
              maxTools: record.maxTools,
              maxCredentials: record.maxCredentials,
              priceMonthyCents: record.priceMonthyCents,
              priceYearlyCents: record.priceYearlyCents,
              isActive: record.isActive,
              isPublic: record.isPublic,
            });
            setPlanModalVisible(true);
          }}
        >
          Edit
        </Button>
      ),
    },
  ];

  const handlePlanSubmit = async (values: Record<string, unknown>) => {
    if (editingPlan) {
      updatePlan.mutate({ planId: editingPlan.id, data: values });
    } else {
      createPlan.mutate(values as Parameters<typeof createPlan.mutate>[0]);
    }
  };

  // Build org approval columns based on which sub-tab is active
  const buildApprovalColumns = (tab: typeof approvalTab) => [
    {
      title: 'Organisation Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: OrgApprovalRecord) => (
        <div>
          <div style={{ fontWeight: 500 }}>{name}</div>
          {record.slug && <Text type="secondary" style={{ fontSize: 12 }}>/{record.slug}</Text>}
        </div>
      ),
    },
    {
      title: 'Owner Email',
      dataIndex: 'ownerEmail',
      key: 'ownerEmail',
    },
    {
      title: 'Users',
      dataIndex: 'userCount',
      key: 'userCount',
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => date ? new Date(date).toLocaleDateString() : '—',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: OrgApprovalRecord) => (
        <Space>
          {tab === 'pending' && (
            <>
              <Button
                size="small"
                type="primary"
                loading={approveOrg.isPending && approveOrg.variables === record.id}
                onClick={() => approveOrg.mutate(record.id)}
              >
                Approve
              </Button>
              <Button
                size="small"
                danger
                onClick={() => {
                  setRejectingOrgId(record.id);
                  setRejectReason('');
                  setRejectModalVisible(true);
                }}
              >
                Reject
              </Button>
            </>
          )}
          {tab === 'active' && (
            <Button
              size="small"
              danger
              loading={suspendOrg.isPending && suspendOrg.variables === record.id}
              onClick={() => suspendOrg.mutate(record.id)}
            >
              Suspend
            </Button>
          )}
          {tab === 'suspended' && (
            <Button
              size="small"
              type="primary"
              loading={reactivateOrg.isPending && reactivateOrg.variables === record.id}
              onClick={() => reactivateOrg.mutate(record.id)}
            >
              Reactivate
            </Button>
          )}
          {tab === 'all' && (
            <Tag color={getApprovalStatusColor(record.approvalStatus)}>
              {record.approvalStatus}
            </Tag>
          )}
        </Space>
      ),
    },
  ];

  const approvalTableData = (): { data: OrgApprovalRecord[]; loading: boolean } => {
    switch (approvalTab) {
      case 'pending':
        return { data: pendingOrgsData?.organizations || [], loading: pendingOrgsLoading };
      case 'active':
        return { data: activeApprovalOrgsData?.organizations || [], loading: activeApprovalOrgsLoading };
      case 'suspended':
        return { data: suspendedApprovalOrgsData?.organizations || [], loading: suspendedApprovalOrgsLoading };
      case 'all':
        return { data: allApprovalOrgsData?.organizations || [], loading: allApprovalOrgsLoading };
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>Platform Administration</h1>
        <p style={{ color: '#888' }}>Manage organizations, users, and subscription plans</p>
      </div>

      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card loading={statsLoading}>
            <Statistic
              title="Organizations"
              value={stats?.totalOrganizations || 0}
              prefix={<ApartmentOutlined />}
              suffix={<span style={{ fontSize: 12, color: '#52c41a' }}>({stats?.activeOrganizations || 0} active)</span>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card loading={statsLoading}>
            <Statistic
              title="Users"
              value={stats?.totalUsers || 0}
              prefix={<TeamOutlined />}
              suffix={<span style={{ fontSize: 12, color: '#52c41a' }}>({stats?.activeUsers || 0} active)</span>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card loading={statsLoading}>
            <Statistic
              title="Agents"
              value={stats?.totalAgents || 0}
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card loading={statsLoading}>
            <Statistic
              title="Deployments"
              value={stats?.totalDeployments || 0}
              prefix={<CloudServerOutlined />}
              suffix={<span style={{ fontSize: 12, color: '#52c41a' }}>({stats?.activeDeployments || 0} active)</span>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card loading={statsLoading}>
            <Statistic
              title="Executions"
              value={stats?.totalExecutions || 0}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card loading={statsLoading}>
            <Statistic
              title="Tools"
              value={stats?.totalTools || 0}
              prefix={<ToolOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Org Approval Panel */}
      <Card style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>Organisations</h2>
          <Text type="secondary">Review and manage organisation approvals</Text>
        </div>
        <Tabs
          activeKey={approvalTab}
          onChange={(key) => setApprovalTab(key as typeof approvalTab)}
          items={[
            {
              key: 'pending',
              label: (
                <Badge count={pendingOrgsData?.total ?? pendingOrgsData?.organizations?.length ?? 0} offset={[8, 0]}>
                  Pending
                </Badge>
              ),
            },
            { key: 'active', label: 'Active' },
            { key: 'suspended', label: 'Suspended' },
            { key: 'all', label: 'All' },
          ]}
        />
        <Table
          dataSource={approvalTableData().data}
          columns={buildApprovalColumns(approvalTab)}
          loading={approvalTableData().loading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Reject Modal */}
      <Modal
        title="Reject Organisation"
        open={rejectModalVisible}
        onCancel={() => {
          setRejectModalVisible(false);
          setRejectingOrgId(null);
          setRejectReason('');
        }}
        onOk={() => {
          if (!rejectReason.trim()) {
            message.warning('Please provide a rejection reason');
            return;
          }
          if (rejectingOrgId) {
            rejectOrg.mutate({ orgId: rejectingOrgId, reason: rejectReason });
          }
        }}
        okText="Reject Organisation"
        okButtonProps={{ danger: true, loading: rejectOrg.isPending, disabled: !rejectReason.trim() }}
      >
        <Form layout="vertical">
          <Form.Item
            label="Rejection Reason"
            required
            extra="This reason will be communicated to the organisation owner."
          >
            <Input.TextArea
              rows={4}
              placeholder="Please provide a reason for rejection..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Tabs */}
      <Card>
        <Tabs defaultActiveKey="organizations">
          <TabPane tab="Organizations" key="organizations">
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <Input
                  placeholder="Search organizations..."
                  prefix={<SearchOutlined />}
                  value={orgSearch}
                  onChange={(e) => setOrgSearch(e.target.value)}
                  style={{ width: 250 }}
                  allowClear
                />
                <Select
                  placeholder="Filter by status"
                  value={orgStatusFilter}
                  onChange={setOrgStatusFilter}
                  style={{ width: 150 }}
                  allowClear
                >
                  <Option value="active">Active</Option>
                  <Option value="trial">Trial</Option>
                  <Option value="suspended">Suspended</Option>
                  <Option value="cancelled">Cancelled</Option>
                </Select>
                <Button icon={<ReloadOutlined />} onClick={() => refetchStats()}>
                  Refresh
                </Button>
              </Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  orgForm.resetFields();
                  setOrgModalVisible(true);
                }}
              >
                Create Organization
              </Button>
            </div>
            <Table
              dataSource={orgsData?.organizations || []}
              columns={orgColumns}
              loading={orgsLoading}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </TabPane>

          <TabPane tab="Users" key="users">
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <Input
                  placeholder="Search users..."
                  prefix={<SearchOutlined />}
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  style={{ width: 250 }}
                  allowClear
                />
              </Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  userForm.resetFields();
                  setUserModalVisible(true);
                }}
              >
                Create User
              </Button>
            </div>
            <Table
              dataSource={usersData?.users || []}
              columns={userColumns}
              loading={usersLoading}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </TabPane>

          <TabPane tab="Subscription Plans" key="plans">
            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingPlan(null);
                  planForm.resetFields();
                  setPlanModalVisible(true);
                }}
              >
                Create Plan
              </Button>
            </div>
            <Table
              dataSource={plansData?.plans || []}
              columns={planColumns}
              loading={plansLoading}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* Organization Modal */}
      <Modal
        title="Create Organization"
        open={orgModalVisible}
        onCancel={() => {
          setOrgModalVisible(false);
          orgForm.resetFields();
        }}
        footer={null}
        width={500}
      >
        <Form
          form={orgForm}
          layout="vertical"
          onFinish={(values) => createOrganization.mutate(values)}
        >
          <Form.Item
            name="name"
            label="Organization Name"
            rules={[{ required: true, message: 'Please enter organization name' }]}
          >
            <Input placeholder="e.g., Acme Corporation" />
          </Form.Item>
          <Form.Item
            name="slug"
            label="Slug (URL-friendly identifier)"
            extra="Leave empty to auto-generate from name"
          >
            <Input placeholder="e.g., acme-corp" />
          </Form.Item>
          <Form.Item
            name="description"
            label="Description"
          >
            <Input.TextArea rows={3} placeholder="Brief description of the organization" />
          </Form.Item>
          <Form.Item
            name="logoUrl"
            label="Logo URL"
          >
            <Input placeholder="https://example.com/logo.png" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={createOrganization.isPending}>
                Create Organization
              </Button>
              <Button onClick={() => setOrgModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Assign Plan Modal */}
      <Modal
        title={`Assign Plan to ${selectedOrgForPlan?.name || 'Organization'}`}
        open={assignPlanModalVisible}
        onCancel={() => {
          setAssignPlanModalVisible(false);
          setSelectedOrgForPlan(null);
          setSelectedPlanId(undefined);
        }}
        onOk={() => {
          if (selectedOrgForPlan && selectedPlanId) {
            assignPlanToOrg.mutate({ orgId: selectedOrgForPlan.id, planId: selectedPlanId });
          }
        }}
        okText="Assign Plan"
        okButtonProps={{ disabled: !selectedPlanId, loading: assignPlanToOrg.isPending }}
        width={500}
      >
        <div style={{ marginBottom: 16 }}>
          <p>Current Plan: <strong>{selectedOrgForPlan?.subscriptionPlanName || 'None'}</strong></p>
          <p>Current Status: <Tag color={getStatusColor(selectedOrgForPlan?.subscriptionStatus || '')}>{selectedOrgForPlan?.subscriptionStatus}</Tag></p>
        </div>
        <Form layout="vertical">
          <Form.Item label="Select New Plan" required>
            <Select
              placeholder="Choose a subscription plan"
              value={selectedPlanId}
              onChange={setSelectedPlanId}
              loading={plansLoading}
              style={{ width: '100%' }}
            >
              {plansData?.plans.filter(p => p.isActive).map((plan) => (
                <Option key={plan.id} value={plan.id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>{plan.displayName}</span>
                    <span style={{ color: '#888' }}>
                      {plan.priceMonthyCents === 0 ? 'Free' : `$${(plan.priceMonthyCents / 100).toFixed(2)}/mo`}
                    </span>
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>
          {selectedPlanId && plansData?.plans.find(p => p.id === selectedPlanId) && (
            <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
              <strong>Plan Details:</strong>
              <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
                <li>Users: {plansData.plans.find(p => p.id === selectedPlanId)?.maxUsers === -1 ? 'Unlimited' : plansData.plans.find(p => p.id === selectedPlanId)?.maxUsers}</li>
                <li>Agents: {plansData.plans.find(p => p.id === selectedPlanId)?.maxAgents === -1 ? 'Unlimited' : plansData.plans.find(p => p.id === selectedPlanId)?.maxAgents}</li>
                <li>Executions/mo: {plansData.plans.find(p => p.id === selectedPlanId)?.maxExecutionsPerMonth === -1 ? 'Unlimited' : plansData.plans.find(p => p.id === selectedPlanId)?.maxExecutionsPerMonth}</li>
              </ul>
            </div>
          )}
        </Form>
      </Modal>

      {/* User Modal */}
      <Modal
        title="Create User"
        open={userModalVisible}
        onCancel={() => {
          setUserModalVisible(false);
          userForm.resetFields();
        }}
        footer={null}
        width={500}
      >
        <Form
          form={userForm}
          layout="vertical"
          onFinish={(values) => createUser.mutate(values)}
          initialValues={{ role: 'developer', isActive: true, isPlatformAdmin: false }}
        >
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Please enter email' },
              { type: 'email', message: 'Please enter a valid email' },
            ]}
          >
            <Input placeholder="user@example.com" />
          </Form.Item>
          <Form.Item
            name="password"
            label="Password"
            rules={[
              { required: true, message: 'Please enter password' },
              { min: 8, message: 'Password must be at least 8 characters' },
            ]}
          >
            <Input.Password placeholder="Minimum 8 characters" />
          </Form.Item>
          <Form.Item
            name="fullName"
            label="Full Name"
          >
            <Input placeholder="John Doe" />
          </Form.Item>
          <Form.Item
            name="organizationId"
            label="Organization"
            rules={[{ required: true, message: 'Please select an organization' }]}
          >
            <Select placeholder="Select organization" loading={orgsLoading}>
              {orgsData?.organizations.map((org) => (
                <Option key={org.id} value={org.id}>
                  {org.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="role"
            label="Role"
            extra="Select the user's role within the organization"
          >
            <Select>
              <Option value="org_owner">
                <div>
                  <strong>Organization Owner</strong>
                  <div style={{ fontSize: 11, color: '#888' }}>Full control including billing and deletion</div>
                </div>
              </Option>
              <Option value="org_admin">
                <div>
                  <strong>Organization Admin</strong>
                  <div style={{ fontSize: 11, color: '#888' }}>Organization management without billing</div>
                </div>
              </Option>
              <Option value="team_lead">
                <div>
                  <strong>Team Lead</strong>
                  <div style={{ fontSize: 11, color: '#888' }}>Manage all agents regardless of creator</div>
                </div>
              </Option>
              <Option value="developer">
                <div>
                  <strong>Developer</strong>
                  <div style={{ fontSize: 11, color: '#888' }}>Create and edit own agents and tools</div>
                </div>
              </Option>
              <Option value="operator">
                <div>
                  <strong>Operator</strong>
                  <div style={{ fontSize: 11, color: '#888' }}>Execute and deploy agents</div>
                </div>
              </Option>
              <Option value="viewer">
                <div>
                  <strong>Viewer</strong>
                  <div style={{ fontSize: 11, color: '#888' }}>Read-only access to resources</div>
                </div>
              </Option>
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="isActive" label="Active" valuePropName="checked">
                <Switch defaultChecked />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="isPlatformAdmin" label="Platform Admin" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={createUser.isPending}>
                Create User
              </Button>
              <Button onClick={() => setUserModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Plan Modal */}
      <Modal
        title={editingPlan ? 'Edit Plan' : 'Create Plan'}
        open={planModalVisible}
        onCancel={() => {
          setPlanModalVisible(false);
          setEditingPlan(null);
          planForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={planForm}
          layout="vertical"
          onFinish={handlePlanSubmit}
          initialValues={{
            maxUsers: 5,
            maxAgents: 10,
            maxDeployments: 5,
            maxExecutionsPerMonth: 1000,
            maxTools: 20,
            maxCredentials: 10,
            priceMonthyCents: 0,
            priceYearlyCents: 0,
            isActive: true,
            isPublic: true,
          }}
        >
          {!editingPlan && (
            <Form.Item name="name" label="Plan Name (slug)" rules={[{ required: true }]}>
              <Input placeholder="e.g., professional" />
            </Form.Item>
          )}
          <Form.Item name="displayName" label="Display Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Professional" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="maxUsers" label="Max Users">
                <InputNumber style={{ width: '100%' }} min={-1} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="maxAgents" label="Max Agents">
                <InputNumber style={{ width: '100%' }} min={-1} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="maxDeployments" label="Max Deployments">
                <InputNumber style={{ width: '100%' }} min={-1} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="maxExecutionsPerMonth" label="Max Executions/mo">
                <InputNumber style={{ width: '100%' }} min={-1} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="maxTools" label="Max Tools">
                <InputNumber style={{ width: '100%' }} min={-1} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="maxCredentials" label="Max Credentials">
                <InputNumber style={{ width: '100%' }} min={-1} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="priceMonthyCents" label="Monthly Price (cents)">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="priceYearlyCents" label="Yearly Price (cents)">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="isActive" label="Active" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="isPublic" label="Public" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={createPlan.isPending || updatePlan.isPending}>
                {editingPlan ? 'Update' : 'Create'}
              </Button>
              <Button onClick={() => setPlanModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

function getStatusColor(status: string): string {
  switch (status) {
    case 'active':
      return 'green';
    case 'trial':
      return 'blue';
    case 'suspended':
      return 'red';
    case 'cancelled':
      return 'gray';
    case 'past_due':
      return 'orange';
    default:
      return 'default';
  }
}

function getApprovalStatusColor(status: string): string {
  switch (status) {
    case 'approved':
    case 'active':
      return 'green';
    case 'pending':
      return 'orange';
    case 'rejected':
      return 'red';
    case 'suspended':
      return 'volcano';
    default:
      return 'default';
  }
}

export default AdminDashboard;
