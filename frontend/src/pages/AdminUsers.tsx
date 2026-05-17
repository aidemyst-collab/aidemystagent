import React, { useState } from 'react';
import {
  Card, Table, Tag, Input, Select, Button, Space, message, Modal, Form, Row, Col, Switch, Typography
} from 'antd';
import { SearchOutlined, PlusOutlined, EyeOutlined, CrownOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminService } from '../features/admin/adminService';
import { apiClient } from '../services/api';
import type { UserAdmin } from '../types/auth';
import { usePermissions, useImpersonation } from '../features/auth/authStore';
import { Navigate, useNavigate } from 'react-router-dom';

const { Text } = Typography;
const { Option } = Select;

const AdminUsers: React.FC = () => {
  const { isPlatformAdmin } = usePermissions();
  const { startImpersonation } = useImpersonation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [orgFilter, setOrgFilter] = useState<string | undefined>();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();

  if (!isPlatformAdmin) return <Navigate to="/dashboard" replace />;

  const { data: orgsData } = useQuery({
    queryKey: ['admin', 'organizations-all'],
    queryFn: () => adminService.listOrganizations({ limit: 200 }),
  });

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['admin', 'users', search, orgFilter],
    queryFn: () => adminService.listAllUsers({
      search: search || undefined,
      organizationId: orgFilter,
    }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });

  const updateStatus = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      adminService.updateUserStatus(id, isActive),
    onSuccess: () => { invalidate(); message.success('User updated'); },
    onError: () => message.error('Failed to update user'),
  });

  const toggleAdmin = useMutation({
    mutationFn: ({ id, isAdmin }: { id: string; isAdmin: boolean }) =>
      adminService.togglePlatformAdmin(id, isAdmin),
    onSuccess: () => { invalidate(); message.success('Admin status updated'); },
    onError: () => message.error('Failed to update admin status'),
  });

  const impersonateUser = useMutation({
    mutationFn: (id: string) =>
      apiClient.post(`/auth/impersonate/${id}`, {}) as Promise<{ accessToken: string; targetUser: UserAdmin }>,
    onSuccess: (data) => {
      startImpersonation(data.targetUser as any, data.accessToken);
      navigate('/dashboard');
      message.success(`Viewing as ${data.targetUser.email}`);
    },
    onError: (e: Error) => message.error(e.message || 'Failed to start session'),
  });

  const createUser = useMutation({
    mutationFn: adminService.createUser,
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
      message.success('User created');
      setCreateModalOpen(false);
      createForm.resetFields();
    },
    onError: (e: Error) => message.error(e.message || 'Failed to create user'),
  });

  const columns = [
    {
      title: 'User',
      key: 'user',
      render: (_: unknown, r: UserAdmin) => (
        <div>
          <div style={{ fontWeight: 500 }}>{r.email}</div>
          {r.fullName && <Text type="secondary" style={{ fontSize: 12 }}>{r.fullName}</Text>}
        </div>
      ),
    },
    {
      title: 'Organisation',
      dataIndex: 'organizationName',
      key: 'organizationName',
    },
    {
      title: 'Role',
      key: 'role',
      width: 160,
      render: (_: unknown, r: UserAdmin) => (
        <Space size={4}>
          <Tag>{r.role}</Tag>
          {r.isPlatformAdmin && <Tag color="gold" icon={<CrownOutlined />}>Admin</Tag>}
        </Space>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      render: (_: unknown, r: UserAdmin) => (
        <Space size={4}>
          <Tag color={r.isActive ? 'green' : 'red'}>{r.isActive ? 'Active' : 'Inactive'}</Tag>
          {r.emailVerified && <Tag color="blue" style={{ fontSize: 10 }}>Verified</Tag>}
        </Space>
      ),
    },
    {
      title: 'Last Login',
      key: 'lastLogin',
      width: 120,
      render: (_: unknown, r: UserAdmin) =>
        r.lastLoginAt ? new Date(r.lastLoginAt).toLocaleDateString() : <Text type="secondary">Never</Text>,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 240,
      render: (_: unknown, r: UserAdmin) => (
        <Space size={4} wrap>
          <Button size="small"
            onClick={() => updateStatus.mutate({ id: r.id, isActive: !r.isActive })}>
            {r.isActive ? 'Deactivate' : 'Activate'}
          </Button>
          <Button size="small"
            type={r.isPlatformAdmin ? 'default' : 'primary'}
            onClick={() => toggleAdmin.mutate({ id: r.id, isAdmin: !r.isPlatformAdmin })}>
            {r.isPlatformAdmin ? 'Remove Admin' : 'Make Admin'}
          </Button>
          {!r.isPlatformAdmin && (
            <Button size="small" icon={<EyeOutlined />}
              loading={impersonateUser.isPending && impersonateUser.variables === r.id}
              onClick={() => impersonateUser.mutate(r.id)}>
              View as
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ margin: 0 }}>Users</h1>
          <Text type="secondary">All users across the platform</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { createForm.resetFields(); setCreateModalOpen(true); }}>
          New User
        </Button>
      </div>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Input
            placeholder="Search by email or name..."
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 260 }}
            allowClear
          />
          <Select placeholder="Filter by organisation" value={orgFilter} onChange={setOrgFilter}
            style={{ width: 240 }} allowClear showSearch
            filterOption={(input, option) =>
              String(option?.children || '').toLowerCase().includes(input.toLowerCase())
            }>
            {orgsData?.organizations.map(o => (
              <Option key={o.id} value={o.id}>{o.name}</Option>
            ))}
          </Select>
        </div>

        <Table
          dataSource={usersData?.users || []}
          columns={columns}
          loading={isLoading}
          rowKey="id"
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `${t} users` }}
        />
      </Card>

      {/* Create User Modal */}
      <Modal title="Create User" open={createModalOpen}
        onCancel={() => { setCreateModalOpen(false); createForm.resetFields(); }}
        footer={null} width={520}>
        <Form form={createForm} layout="vertical" onFinish={(v) => createUser.mutate(v)}
          initialValues={{ role: 'developer', isActive: true, isPlatformAdmin: false }}>
          <Form.Item name="email" label="Email"
            rules={[{ required: true }, { type: 'email' }]}>
            <Input placeholder="user@example.com" />
          </Form.Item>
          <Form.Item name="password" label="Password"
            rules={[{ required: true }, { min: 8, message: 'Minimum 8 characters' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="fullName" label="Full Name">
            <Input placeholder="Jane Smith" />
          </Form.Item>
          <Form.Item name="organizationId" label="Organisation" rules={[{ required: true }]}>
            <Select placeholder="Select organisation" showSearch
              filterOption={(input, option) =>
                String(option?.children || '').toLowerCase().includes(input.toLowerCase())
              }>
              {orgsData?.organizations.map(o => <Option key={o.id} value={o.id}>{o.name}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="role" label="Role">
            <Select>
              <Option value="org_owner">Organisation Owner</Option>
              <Option value="org_admin">Organisation Admin</Option>
              <Option value="team_lead">Team Lead</Option>
              <Option value="developer">Developer</Option>
              <Option value="operator">Operator</Option>
              <Option value="viewer">Viewer</Option>
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
              <Button type="primary" htmlType="submit" loading={createUser.isPending}>Create</Button>
              <Button onClick={() => setCreateModalOpen(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminUsers;
