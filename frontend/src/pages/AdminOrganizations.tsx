import React, { useState } from 'react';
import {
  Card, Table, Tag, Input, Select, Button, Space, message, Modal, Form, Typography
} from 'antd';
import {
  SearchOutlined, PlusOutlined, ReloadOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminService } from '../features/admin/adminService';
import { apiClient } from '../services/api';
import type { OrganizationAdmin, SubscriptionPlan } from '../types/auth';
import { usePermissions } from '../features/auth/authStore';
import { Navigate } from 'react-router-dom';

const { Text } = Typography;
const { Option } = Select;

function statusColor(status: string) {
  switch (status) {
    case 'active': return 'green';
    case 'trial': return 'blue';
    case 'suspended': return 'red';
    case 'cancelled': return 'orange';
    case 'past_due': return 'volcano';
    default: return 'default';
  }
}

function approvalColor(status: string) {
  switch (status) {
    case 'active': return 'green';
    case 'pending': return 'orange';
    case 'rejected': return 'red';
    case 'suspended': return 'volcano';
    default: return 'default';
  }
}

const AdminOrganizations: React.FC = () => {
  const { isPlatformAdmin } = usePermissions();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [approvalFilter, setApprovalFilter] = useState<string | undefined>();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();

  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assignTarget, setAssignTarget] = useState<OrganizationAdmin | null>(null);
  const [assignPlanId, setAssignPlanId] = useState<string | undefined>();

  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectTargetId, setRejectTargetId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  if (!isPlatformAdmin) return <Navigate to="/dashboard" replace />;

  const { data: orgsData, isLoading, refetch } = useQuery({
    queryKey: ['admin', 'organizations', search, statusFilter, approvalFilter],
    queryFn: () => adminService.listOrganizations({
      search: search || undefined,
      subscriptionStatus: statusFilter,
    }),
  });

  const { data: plansData } = useQuery({
    queryKey: ['admin', 'subscription-plans'],
    queryFn: () => adminService.listSubscriptionPlans({ includeInactive: false }),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'organizations'] });
    queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
  };

  const approveOrg = useMutation({
    mutationFn: (id: string) => apiClient.post(`/admin/organizations/${id}/approve`, {}),
    onSuccess: () => { invalidate(); message.success('Organisation approved'); },
    onError: () => message.error('Failed to approve'),
  });

  const rejectOrg = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      apiClient.post(`/admin/organizations/${id}/reject`, { reason }),
    onSuccess: () => {
      invalidate();
      message.success('Organisation rejected');
      setRejectModalOpen(false);
      setRejectTargetId(null);
      setRejectReason('');
    },
    onError: () => message.error('Failed to reject'),
  });

  const suspendOrg = useMutation({
    mutationFn: (id: string) => apiClient.post(`/admin/organizations/${id}/suspend`, {}),
    onSuccess: () => { invalidate(); message.success('Organisation suspended'); },
    onError: () => message.error('Failed to suspend'),
  });

  const reactivateOrg = useMutation({
    mutationFn: (id: string) => apiClient.post(`/admin/organizations/${id}/reactivate`, {}),
    onSuccess: () => { invalidate(); message.success('Organisation reactivated'); },
    onError: () => message.error('Failed to reactivate'),
  });

  const updateOrg = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { isActive?: boolean; subscriptionPlanId?: string; subscriptionStatus?: string } }) =>
      adminService.updateOrganizationStatus(id, data),
    onSuccess: () => { invalidate(); message.success('Organisation updated'); },
    onError: () => message.error('Failed to update'),
  });

  const createOrg = useMutation({
    mutationFn: adminService.createOrganization,
    onSuccess: () => {
      invalidate();
      message.success('Organisation created');
      setCreateModalOpen(false);
      createForm.resetFields();
    },
    onError: (e: Error) => message.error(e.message || 'Failed to create'),
  });

  const assignPlan = useMutation({
    mutationFn: ({ id, planId }: { id: string; planId: string }) =>
      adminService.updateOrganizationStatus(id, { subscriptionPlanId: planId, subscriptionStatus: 'active' }),
    onSuccess: () => {
      invalidate();
      message.success('Plan assigned');
      setAssignModalOpen(false);
      setAssignTarget(null);
      setAssignPlanId(undefined);
    },
    onError: () => message.error('Failed to assign plan'),
  });

  const columns = [
    {
      title: 'Organisation',
      key: 'name',
      render: (_: unknown, r: OrganizationAdmin) => (
        <div>
          <div style={{ fontWeight: 500 }}>{r.name}</div>
          {r.slug && <Text type="secondary" style={{ fontSize: 12 }}>/{r.slug}</Text>}
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
      width: 160,
      render: (_: unknown, r: OrganizationAdmin) => (
        <Space size={4}>
          {r.subscriptionPlanName
            ? <Tag color="blue">{r.subscriptionPlanName}</Tag>
            : <Tag color="orange">No plan</Tag>}
          <Button size="small" type="link" style={{ padding: 0 }}
            onClick={() => { setAssignTarget(r); setAssignPlanId(undefined); setAssignModalOpen(true); }}>
            Change
          </Button>
        </Space>
      ),
    },
    { title: 'Users', dataIndex: 'userCount', key: 'userCount', width: 70 },
    { title: 'Agents', dataIndex: 'agentCount', key: 'agentCount', width: 70 },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 110,
      render: (v: string) => v ? new Date(v).toLocaleDateString() : '—',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 220,
      render: (_: unknown, r: OrganizationAdmin) => (
        <Space size={4} wrap>
          {r.isActive ? (
            <Button size="small" danger onClick={() => suspendOrg.mutate(r.id)}>Suspend</Button>
          ) : (
            <Button size="small" type="primary" onClick={() => reactivateOrg.mutate(r.id)}>Reactivate</Button>
          )}
          <Button size="small"
            onClick={() => updateOrg.mutate({ id: r.id, data: { isActive: !r.isActive } })}>
            {r.isActive ? 'Deactivate' : 'Activate'}
          </Button>
          {!r.isActive && (
            <Button size="small" type="primary"
              loading={approveOrg.isPending && approveOrg.variables === r.id}
              onClick={() => approveOrg.mutate(r.id)}>
              Approve
            </Button>
          )}
          <Button size="small" danger
            onClick={() => { setRejectTargetId(r.id); setRejectReason(''); setRejectModalOpen(true); }}>
            Reject
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ margin: 0 }}>Organisations</h1>
          <Text type="secondary">Manage all organisations across the platform</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { createForm.resetFields(); setCreateModalOpen(true); }}>
          New Organisation
        </Button>
      </div>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Input
            placeholder="Search by name..."
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 240 }}
            allowClear
          />
          <Select placeholder="Subscription status" value={statusFilter} onChange={setStatusFilter} style={{ width: 180 }} allowClear>
            <Option value="active">Active</Option>
            <Option value="trial">Trial</Option>
            <Option value="suspended">Suspended</Option>
            <Option value="cancelled">Cancelled</Option>
            <Option value="past_due">Past Due</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Refresh</Button>
        </div>

        <Table
          dataSource={orgsData?.organizations || []}
          columns={columns}
          loading={isLoading}
          rowKey="id"
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `${t} organisations` }}
        />
      </Card>

      {/* Create Org Modal */}
      <Modal title="Create Organisation" open={createModalOpen}
        onCancel={() => { setCreateModalOpen(false); createForm.resetFields(); }}
        footer={null} width={480}>
        <Form form={createForm} layout="vertical" onFinish={(v) => createOrg.mutate(v)}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="Acme Corporation" />
          </Form.Item>
          <Form.Item name="slug" label="Slug" extra="Leave empty to auto-generate">
            <Input placeholder="acme-corp" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={createOrg.isPending}>Create</Button>
              <Button onClick={() => setCreateModalOpen(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Assign Plan Modal */}
      <Modal title={`Assign Plan — ${assignTarget?.name}`} open={assignModalOpen}
        onCancel={() => { setAssignModalOpen(false); setAssignTarget(null); setAssignPlanId(undefined); }}
        onOk={() => { if (assignTarget && assignPlanId) assignPlan.mutate({ id: assignTarget.id, planId: assignPlanId }); }}
        okText="Assign" okButtonProps={{ disabled: !assignPlanId, loading: assignPlan.isPending }}>
        <p style={{ marginBottom: 8 }}>Current: <strong>{assignTarget?.subscriptionPlanName || 'None'}</strong></p>
        <Select placeholder="Choose plan" value={assignPlanId} onChange={setAssignPlanId} style={{ width: '100%' }}>
          {plansData?.plans.filter(p => p.isActive).map(p => (
            <Option key={p.id} value={p.id}>
              {p.displayName} — {p.priceMonthyCents === 0 ? 'Free' : `$${(p.priceMonthyCents / 100).toFixed(0)}/mo`}
            </Option>
          ))}
        </Select>
      </Modal>

      {/* Reject Modal */}
      <Modal title="Reject Organisation" open={rejectModalOpen}
        onCancel={() => { setRejectModalOpen(false); setRejectTargetId(null); setRejectReason(''); }}
        onOk={() => {
          if (!rejectReason.trim()) { message.warning('Please provide a reason'); return; }
          if (rejectTargetId) rejectOrg.mutate({ id: rejectTargetId, reason: rejectReason });
        }}
        okText="Reject" okButtonProps={{ danger: true, loading: rejectOrg.isPending, disabled: !rejectReason.trim() }}>
        <Form layout="vertical">
          <Form.Item label="Reason" required extra="Communicated to the organisation owner.">
            <Input.TextArea rows={3} value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Provide a reason for rejection..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminOrganizations;
