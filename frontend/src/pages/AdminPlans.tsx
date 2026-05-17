import React, { useState } from 'react';
import {
  Card, Table, Tag, Button, Space, message, Modal, Form, Input, InputNumber, Row, Col, Switch, Typography
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminService } from '../features/admin/adminService';
import type { SubscriptionPlan } from '../types/auth';
import { usePermissions } from '../features/auth/authStore';
import { Navigate } from 'react-router-dom';

const { Text } = Typography;

const AdminPlans: React.FC = () => {
  const { isPlatformAdmin } = usePermissions();
  const queryClient = useQueryClient();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<SubscriptionPlan | null>(null);
  const [form] = Form.useForm();

  if (!isPlatformAdmin) return <Navigate to="/dashboard" replace />;

  const { data: plansData, isLoading } = useQuery({
    queryKey: ['admin', 'subscription-plans'],
    queryFn: () => adminService.listSubscriptionPlans({ includeInactive: true }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['admin', 'subscription-plans'] });

  const createPlan = useMutation({
    mutationFn: adminService.createSubscriptionPlan,
    onSuccess: () => { invalidate(); message.success('Plan created'); setModalOpen(false); form.resetFields(); },
    onError: () => message.error('Failed to create plan'),
  });

  const updatePlan = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof adminService.updateSubscriptionPlan>[1] }) =>
      adminService.updateSubscriptionPlan(id, data),
    onSuccess: () => {
      invalidate(); message.success('Plan updated');
      setModalOpen(false); setEditingPlan(null); form.resetFields();
    },
    onError: () => message.error('Failed to update plan'),
  });

  const openEdit = (plan: SubscriptionPlan) => {
    setEditingPlan(plan);
    form.setFieldsValue({
      displayName: plan.displayName,
      description: plan.description,
      maxUsers: plan.maxUsers,
      maxAgents: plan.maxAgents,
      maxDeployments: plan.maxDeployments,
      maxExecutionsPerMonth: plan.maxExecutionsPerMonth,
      maxTools: plan.maxTools,
      maxCredentials: plan.maxCredentials,
      priceMonthyCents: plan.priceMonthyCents,
      priceYearlyCents: plan.priceYearlyCents,
      isActive: plan.isActive,
      isPublic: plan.isPublic,
    });
    setModalOpen(true);
  };

  const handleSubmit = (values: Record<string, unknown>) => {
    if (editingPlan) {
      updatePlan.mutate({ id: editingPlan.id, data: values });
    } else {
      createPlan.mutate(values as Parameters<typeof createPlan.mutate>[0]);
    }
  };

  const columns = [
    {
      title: 'Plan',
      key: 'plan',
      render: (_: unknown, r: SubscriptionPlan) => (
        <div>
          <div style={{ fontWeight: 500 }}>{r.displayName}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>{r.name}</Text>
        </div>
      ),
    },
    {
      title: 'Limits',
      key: 'limits',
      render: (_: unknown, r: SubscriptionPlan) => (
        <Space direction="vertical" size={0} style={{ fontSize: 12 }}>
          <span>Users: {r.maxUsers === -1 ? '∞' : r.maxUsers}</span>
          <span>Agents: {r.maxAgents === -1 ? '∞' : r.maxAgents}</span>
          <span>Executions: {r.maxExecutionsPerMonth === -1 ? '∞' : `${r.maxExecutionsPerMonth}/mo`}</span>
        </Space>
      ),
    },
    {
      title: 'Price',
      key: 'price',
      render: (_: unknown, r: SubscriptionPlan) => (
        <Space direction="vertical" size={0}>
          <span>{r.priceMonthyCents === 0 ? 'Free' : `$${(r.priceMonthyCents / 100).toFixed(2)}/mo`}</span>
          {r.priceYearlyCents > 0 && (
            <Text type="secondary" style={{ fontSize: 12 }}>${(r.priceYearlyCents / 100).toFixed(2)}/yr</Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Orgs',
      dataIndex: 'organizationCount',
      key: 'orgs',
      width: 70,
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      render: (_: unknown, r: SubscriptionPlan) => (
        <Space size={4}>
          <Tag color={r.isActive ? 'green' : 'red'}>{r.isActive ? 'Active' : 'Inactive'}</Tag>
          {r.isPublic && <Tag color="blue">Public</Tag>}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      render: (_: unknown, r: SubscriptionPlan) => (
        <Button size="small" onClick={() => openEdit(r)}>Edit</Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ margin: 0 }}>Subscription Plans</h1>
          <Text type="secondary">Manage plans and pricing</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />}
          onClick={() => { setEditingPlan(null); form.resetFields(); setModalOpen(true); }}>
          New Plan
        </Button>
      </div>

      <Card>
        <Table
          dataSource={plansData?.plans || []}
          columns={columns}
          loading={isLoading}
          rowKey="id"
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={editingPlan ? `Edit — ${editingPlan.displayName}` : 'Create Plan'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingPlan(null); form.resetFields(); }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}
          initialValues={{ maxUsers: 5, maxAgents: 10, maxDeployments: 5, maxExecutionsPerMonth: 1000, maxTools: 20, maxCredentials: 10, priceMonthyCents: 0, priceYearlyCents: 0, isActive: true, isPublic: true }}>
          {!editingPlan && (
            <Form.Item name="name" label="Slug (plan ID)" rules={[{ required: true }]}>
              <Input placeholder="professional" />
            </Form.Item>
          )}
          <Form.Item name="displayName" label="Display Name" rules={[{ required: true }]}>
            <Input placeholder="Professional" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="maxUsers" label="Max Users"><InputNumber style={{ width: '100%' }} min={-1} /></Form.Item></Col>
            <Col span={8}><Form.Item name="maxAgents" label="Max Agents"><InputNumber style={{ width: '100%' }} min={-1} /></Form.Item></Col>
            <Col span={8}><Form.Item name="maxDeployments" label="Max Deployments"><InputNumber style={{ width: '100%' }} min={-1} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="maxExecutionsPerMonth" label="Max Executions/mo"><InputNumber style={{ width: '100%' }} min={-1} /></Form.Item></Col>
            <Col span={8}><Form.Item name="maxTools" label="Max Tools"><InputNumber style={{ width: '100%' }} min={-1} /></Form.Item></Col>
            <Col span={8}><Form.Item name="maxCredentials" label="Max Credentials"><InputNumber style={{ width: '100%' }} min={-1} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="priceMonthyCents" label="Monthly Price (cents)"><InputNumber style={{ width: '100%' }} min={0} /></Form.Item></Col>
            <Col span={12}><Form.Item name="priceYearlyCents" label="Yearly Price (cents)"><InputNumber style={{ width: '100%' }} min={0} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="isActive" label="Active" valuePropName="checked"><Switch /></Form.Item></Col>
            <Col span={12}><Form.Item name="isPublic" label="Public" valuePropName="checked"><Switch /></Form.Item></Col>
          </Row>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={createPlan.isPending || updatePlan.isPending}>
                {editingPlan ? 'Update' : 'Create'}
              </Button>
              <Button onClick={() => setModalOpen(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminPlans;
