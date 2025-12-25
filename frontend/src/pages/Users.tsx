import React, { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Card,
  Tooltip,
  Typography,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LockOutlined,
  UnlockOutlined,
  UserDeleteOutlined,
  MailOutlined,
  CrownOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userService } from '../features/users/userService';
import type { OrgUser, OrgRole } from '../features/users/userService';
import { usePermissions } from '../features/auth/authStore';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Option } = Select;
const { Text } = Typography;

export const Users: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { canAccess } = usePermissions();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<boolean | undefined>();
  const [roleModalVisible, setRoleModalVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState<OrgUser | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<string>('');

  // Redirect if user doesn't have permission
  if (!canAccess('user-management')) {
    return <Navigate to="/dashboard" replace />;
  }

  // Queries
  const { data: usersData, isLoading, refetch } = useQuery({
    queryKey: ['users', search, statusFilter],
    queryFn: () => userService.list({
      search: search || undefined,
      isActive: statusFilter,
    }),
  });

  const { data: roles } = useQuery({
    queryKey: ['user-roles'],
    queryFn: userService.getRoles,
  });

  // Mutations
  const activateUser = useMutation({
    mutationFn: userService.activate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      message.success('User activated');
    },
    onError: () => {
      message.error('Failed to activate user');
    },
  });

  const deactivateUser = useMutation({
    mutationFn: userService.deactivate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      message.success('User deactivated');
    },
    onError: () => {
      message.error('Failed to deactivate user');
    },
  });

  const unlockUser = useMutation({
    mutationFn: userService.unlock,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      message.success('User account unlocked');
    },
    onError: () => {
      message.error('Failed to unlock user');
    },
  });

  const deleteUser = useMutation({
    mutationFn: userService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      message.success('User removed');
    },
    onError: () => {
      message.error('Failed to remove user');
    },
  });

  const assignRole = useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      userService.assignRole(userId, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      message.success('Role assigned');
      setRoleModalVisible(false);
      setSelectedUser(null);
      setSelectedRoleId('');
    },
    onError: () => {
      message.error('Failed to assign role');
    },
  });

  const removeRole = useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      userService.removeRole(userId, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      message.success('Role removed');
    },
    onError: () => {
      message.error('Failed to remove role');
    },
  });

  const getRoleColor = (roleName: string) => {
    const colorMap: Record<string, string> = {
      'Super Admin': 'gold',
      'Organization Owner': 'purple',
      'Organization Admin': 'red',
      'Agent Admin': 'blue',
      'Developer': 'green',
      'Operator': 'cyan',
      'Viewer': 'default',
    };
    return colorMap[roleName] || 'default';
  };

  const openRoleModal = (user: OrgUser) => {
    setSelectedUser(user);
    setRoleModalVisible(true);
  };

  const handleAssignRole = () => {
    if (selectedUser && selectedRoleId) {
      assignRole.mutate({ userId: selectedUser.id, roleId: selectedRoleId });
    }
  };

  const filteredUsers = usersData?.users || [];

  const columns = [
    {
      title: 'User',
      key: 'user',
      render: (_: unknown, record: OrgUser) => (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Text strong>{record.fullName || record.email}</Text>
            {record.isPlatformAdmin && (
              <Tooltip title="Platform Administrator">
                <CrownOutlined style={{ color: '#faad14' }} />
              </Tooltip>
            )}
          </div>
          {record.fullName && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.email}
            </Text>
          )}
        </div>
      ),
    },
    {
      title: 'Roles',
      key: 'roles',
      render: (_: unknown, record: OrgUser) => (
        <Space wrap>
          {record.roles.map((role) => (
            <Tag
              key={role.id}
              color={getRoleColor(role.displayName)}
              closable={record.roles.length > 1}
              onClose={(e) => {
                e.preventDefault();
                removeRole.mutate({ userId: record.id, roleId: role.id });
              }}
            >
              {role.displayName}
            </Tag>
          ))}
          <Button
            size="small"
            type="dashed"
            icon={<PlusOutlined />}
            onClick={() => openRoleModal(record)}
          >
            Add
          </Button>
        </Space>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      render: (_: unknown, record: OrgUser) => (
        <Space direction="vertical" size={0}>
          <Badge
            status={record.isActive ? 'success' : 'error'}
            text={record.isActive ? 'Active' : 'Inactive'}
          />
          {record.emailVerified ? (
            <Text type="secondary" style={{ fontSize: 11 }}>
              <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 4 }} />
              Verified
            </Text>
          ) : (
            <Text type="secondary" style={{ fontSize: 11 }}>
              <CloseCircleOutlined style={{ color: '#f5222d', marginRight: 4 }} />
              Not verified
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Last Login',
      key: 'lastLogin',
      width: 150,
      render: (_: unknown, record: OrgUser) => (
        record.lastLoginAt ? (
          <Tooltip title={dayjs(record.lastLoginAt).format('YYYY-MM-DD HH:mm:ss')}>
            {dayjs(record.lastLoginAt).fromNow()}
          </Tooltip>
        ) : (
          <Text type="secondary">Never</Text>
        )
      ),
    },
    {
      title: 'Joined',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      render: (date: string) => (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          {dayjs(date).fromNow()}
        </Tooltip>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: OrgUser) => (
        <Space>
          {record.isActive ? (
            <Popconfirm
              title="Deactivate user?"
              description="User will lose access to the organization."
              onConfirm={() => deactivateUser.mutate(record.id)}
            >
              <Tooltip title="Deactivate">
                <Button
                  size="small"
                  icon={<LockOutlined />}
                  loading={deactivateUser.isPending}
                />
              </Tooltip>
            </Popconfirm>
          ) : (
            <Tooltip title="Activate">
              <Button
                size="small"
                icon={<UnlockOutlined />}
                onClick={() => activateUser.mutate(record.id)}
                loading={activateUser.isPending}
              />
            </Tooltip>
          )}
          <Tooltip title="Unlock Account">
            <Button
              size="small"
              icon={<UnlockOutlined />}
              onClick={() => unlockUser.mutate(record.id)}
              loading={unlockUser.isPending}
            />
          </Tooltip>
          <Popconfirm
            title="Remove user?"
            description="This will remove the user from the organization."
            onConfirm={() => deleteUser.mutate(record.id)}
          >
            <Tooltip title="Remove User">
              <Button
                size="small"
                danger
                icon={<UserDeleteOutlined />}
                loading={deleteUser.isPending}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>User Management</h1>
        <p style={{ color: '#888' }}>Manage users in your organization</p>
      </div>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Space>
            <Input
              placeholder="Search users..."
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
              <Option value={true}>Active</Option>
              <Option value={false}>Inactive</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              Refresh
            </Button>
          </Space>
          <Button
            type="primary"
            icon={<MailOutlined />}
            onClick={() => navigate('/invitations')}
          >
            Invite User
          </Button>
        </div>

        <Table
          dataSource={filteredUsers}
          columns={columns}
          loading={isLoading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Assign Role Modal */}
      <Modal
        title={`Assign Role to ${selectedUser?.fullName || selectedUser?.email}`}
        open={roleModalVisible}
        onCancel={() => {
          setRoleModalVisible(false);
          setSelectedUser(null);
          setSelectedRoleId('');
        }}
        onOk={handleAssignRole}
        okText="Assign Role"
        okButtonProps={{ disabled: !selectedRoleId, loading: assignRole.isPending }}
      >
        <Form layout="vertical">
          <Form.Item label="Select Role">
            <Select
              placeholder="Choose a role to assign"
              value={selectedRoleId}
              onChange={setSelectedRoleId}
              style={{ width: '100%' }}
            >
              {roles
                ?.filter(
                  (role: OrgRole) =>
                    !selectedUser?.roles.some((ur) => ur.id === role.id)
                )
                .map((role: OrgRole) => (
                  <Option key={role.id} value={role.id}>
                    <div>
                      <Text strong>{role.displayName}</Text>
                      {role.description && (
                        <div>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {role.description}
                          </Text>
                        </div>
                      )}
                    </div>
                  </Option>
                ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
