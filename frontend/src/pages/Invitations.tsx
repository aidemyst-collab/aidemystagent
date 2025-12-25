import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Input,
  Select,
  Modal,
  Form,
  message,
  Tooltip,
  Typography,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  SendOutlined,
  DeleteOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { invitationService } from '../features/invitations/invitationService';
import { usePermissions } from '../features/auth/authStore';
import { Navigate } from 'react-router-dom';
import type { Invitation, Role } from '../types/auth';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Option } = Select;
const { Text } = Typography;

const Invitations: React.FC = () => {
  const { canAccess } = usePermissions();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  // Redirect if user doesn't have permission
  if (!canAccess('invite-users')) {
    return <Navigate to="/dashboard" replace />;
  }

  // Queries
  const { data: invitationsData, isLoading, refetch } = useQuery({
    queryKey: ['invitations', search, statusFilter],
    queryFn: () => invitationService.list({
      status: statusFilter,
    }),
  });

  const { data: roles } = useQuery({
    queryKey: ['invitation-roles'],
    queryFn: invitationService.getAvailableRoles,
  });

  // Mutations
  const createInvitation = useMutation({
    mutationFn: invitationService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
      message.success('Invitation sent successfully');
      setModalVisible(false);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(error.message || 'Failed to send invitation');
    },
  });

  const resendInvitation = useMutation({
    mutationFn: invitationService.resend,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
      message.success('Invitation resent');
    },
    onError: () => {
      message.error('Failed to resend invitation');
    },
  });

  const revokeInvitation = useMutation({
    mutationFn: invitationService.revoke,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
      message.success('Invitation revoked');
    },
    onError: () => {
      message.error('Failed to revoke invitation');
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'blue';
      case 'accepted':
        return 'green';
      case 'expired':
        return 'orange';
      case 'revoked':
        return 'red';
      default:
        return 'default';
    }
  };

  const copyInviteLink = (token: string) => {
    const url = `${window.location.origin}/invitations/accept/${token}`;
    navigator.clipboard.writeText(url);
    message.success('Invitation link copied to clipboard');
  };

  const columns = [
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (email: string) => <Text strong>{email}</Text>,
    },
    {
      title: 'Role',
      dataIndex: 'roleName',
      key: 'roleName',
      render: (role: string) => <Tag>{role}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </Tag>
      ),
    },
    {
      title: 'Invited By',
      dataIndex: 'invitedByEmail',
      key: 'invitedByEmail',
    },
    {
      title: 'Sent',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          {dayjs(date).fromNow()}
        </Tooltip>
      ),
    },
    {
      title: 'Expires',
      dataIndex: 'expiresAt',
      key: 'expiresAt',
      render: (date: string, record: Invitation) => {
        if (record.status !== 'pending') return '-';
        const isExpired = dayjs(date).isBefore(dayjs());
        return (
          <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
            <Text type={isExpired ? 'danger' : undefined}>
              {isExpired ? 'Expired' : dayjs(date).fromNow()}
            </Text>
          </Tooltip>
        );
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: Invitation) => (
        <Space>
          {record.status === 'pending' && (
            <>
              <Tooltip title="Copy invite link">
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() => copyInviteLink(record.token)}
                />
              </Tooltip>
              <Tooltip title="Resend invitation">
                <Button
                  size="small"
                  icon={<SendOutlined />}
                  onClick={() => resendInvitation.mutate(record.id)}
                  loading={resendInvitation.isPending}
                />
              </Tooltip>
              <Popconfirm
                title="Revoke invitation?"
                description="This will invalidate the invitation link."
                onConfirm={() => revokeInvitation.mutate(record.id)}
                okText="Yes"
                cancelText="No"
              >
                <Tooltip title="Revoke invitation">
                  <Button
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    loading={revokeInvitation.isPending}
                  />
                </Tooltip>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  const filteredInvitations = invitationsData?.invitations?.filter(
    (inv) => !search || inv.email.toLowerCase().includes(search.toLowerCase())
  ) || [];

  const handleCreateInvitation = async (values: {
    email: string;
    roleId: string;
    message?: string;
    expiresInDays?: number;
  }) => {
    createInvitation.mutate(values);
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>Invitations</h1>
        <p style={{ color: '#888' }}>Invite users to join your organization</p>
      </div>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Space>
            <Input
              placeholder="Search by email..."
              prefix={<SearchOutlined />}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: 250 }}
              allowClear
            />
            <Select
              placeholder="Filter by status"
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 150 }}
              allowClear
            >
              <Option value="pending">Pending</Option>
              <Option value="accepted">Accepted</Option>
              <Option value="expired">Expired</Option>
              <Option value="revoked">Revoked</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              Refresh
            </Button>
          </Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalVisible(true)}
          >
            Invite User
          </Button>
        </div>

        <Table
          dataSource={filteredInvitations}
          columns={columns}
          loading={isLoading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Invite User Modal */}
      <Modal
        title="Invite User"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateInvitation}
          initialValues={{ expiresInDays: 7 }}
        >
          <Form.Item
            name="email"
            label="Email Address"
            rules={[
              { required: true, message: 'Please enter email address' },
              { type: 'email', message: 'Please enter a valid email' },
            ]}
          >
            <Input placeholder="user@example.com" />
          </Form.Item>

          <Form.Item
            name="roleId"
            label="Role"
            rules={[{ required: true, message: 'Please select a role' }]}
          >
            <Select placeholder="Select role">
              {roles?.map((role: Role) => (
                <Option key={role.id} value={role.id}>
                  {role.displayName || role.name}
                  {role.description && (
                    <span style={{ color: '#888', marginLeft: 8, fontSize: 12 }}>
                      - {role.description}
                    </span>
                  )}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="message" label="Personal Message (Optional)">
            <Input.TextArea
              rows={3}
              placeholder="Add a personal message to the invitation email..."
            />
          </Form.Item>

          <Form.Item name="expiresInDays" label="Expires In (Days)">
            <Select>
              <Option value={1}>1 day</Option>
              <Option value={3}>3 days</Option>
              <Option value={7}>7 days</Option>
              <Option value={14}>14 days</Option>
              <Option value={30}>30 days</Option>
            </Select>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={createInvitation.isPending}
              >
                Send Invitation
              </Button>
              <Button onClick={() => setModalVisible(false)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Invitations;
