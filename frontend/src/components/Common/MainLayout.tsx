import { useEffect } from 'react';
import { Layout, Menu, Avatar, Dropdown, Typography, Tag, Select, Tooltip, Space } from 'antd';
import {
  DashboardOutlined,
  RocketOutlined,
  ToolOutlined,
  KeyOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  FolderOutlined,
  CloudOutlined,
  BarChartOutlined,
  CrownOutlined,
  TeamOutlined,
  MailOutlined,
  AuditOutlined,
  HistoryOutlined,
  BankOutlined,
  SwapOutlined,
  EyeOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore, usePermissions, useOrganizationSwitcher } from '../../features/auth/authStore';
import { useLogout, useInitializeOrganization } from '../../features/auth/authHooks';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import type { MenuProps } from 'antd';
import type { Organization } from '../../types/auth';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

// Subscription status tag colors
const subscriptionStatusColors: Record<string, string> = {
  trial: 'blue',
  active: 'green',
  suspended: 'red',
  cancelled: 'orange',
  expired: 'default',
};

// Fetch all organizations for platform admin switcher
const fetchAllOrganizations = async (): Promise<{ organizations: Organization[]; total: number }> => {
  return apiClient.get('/organizations/');
};

export const MainLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, organization, isAuthenticated } = useAuthStore();
  const { isPlatformAdmin, canAccess } = usePermissions();
  const { mutate: logout } = useLogout();
  const { mutate: initializeOrganization } = useInitializeOrganization();
  const {
    switchedOrganization,
    effectiveOrganization,
    isSwitched,
    canSwitch,
    switchOrganization,
    clearSwitch,
  } = useOrganizationSwitcher();
  const queryClient = useQueryClient();

  // Fetch organizations for platform admin switcher
  const { data: orgsData } = useQuery({
    queryKey: ['all-organizations'],
    queryFn: fetchAllOrganizations,
    enabled: canSwitch, // Only fetch if user can switch (platform admin)
  });

  // Initialize organization data on mount (for page refresh scenarios)
  useEffect(() => {
    if (isAuthenticated && !organization) {
      initializeOrganization();
    }
  }, [isAuthenticated, organization, initializeOrganization]);

  // Handle organization switch
  const handleOrgSwitch = (orgId: string) => {
    if (orgId === 'self') {
      clearSwitch();
    } else {
      const selectedOrg = orgsData?.organizations.find(o => o.id === orgId);
      if (selectedOrg) {
        switchOrganization(selectedOrg);
      }
    }
    // Invalidate all queries to refetch data for the new organization
    // Exclude the 'all-organizations' query as it's not org-specific
    queryClient.invalidateQueries({
      predicate: (query) => query.queryKey[0] !== 'all-organizations',
    });
  };

  const menuItems: MenuProps['items'] = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
      onClick: () => navigate('/dashboard'),
    },
    {
      key: '/agents',
      icon: <RocketOutlined />,
      label: 'Workflows',
      onClick: () => navigate('/agents'),
    },
    {
      key: '/tools',
      icon: <ToolOutlined />,
      label: 'Tools',
      onClick: () => navigate('/tools'),
    },
    {
      key: '/credentials',
      icon: <KeyOutlined />,
      label: 'Credentials',
      onClick: () => navigate('/credentials'),
    },
    {
      key: '/templates',
      icon: <FolderOutlined />,
      label: 'Templates',
      onClick: () => navigate('/templates'),
    },
    {
      key: '/deployments',
      icon: <CloudOutlined />,
      label: 'Deployments',
      onClick: () => navigate('/deployments'),
    },
    {
      key: '/analytics',
      icon: <BarChartOutlined />,
      label: 'Analytics',
      onClick: () => navigate('/analytics'),
    },
    // Organization admin section
    ...(canAccess('user-management')
      ? [
          { type: 'divider' as const },
          {
            key: '/users',
            icon: <TeamOutlined />,
            label: 'Users',
            onClick: () => navigate('/users'),
          },
        ]
      : []),
    ...(canAccess('invite-users')
      ? [
          {
            key: '/invitations',
            icon: <MailOutlined />,
            label: 'Invitations',
            onClick: () => navigate('/invitations'),
          },
        ]
      : []),
    ...(canAccess('audit-logs')
      ? [
          {
            key: '/audit-logs',
            icon: <AuditOutlined />,
            label: 'User Audit',
            onClick: () => navigate('/audit-logs'),
          },
          {
            key: '/execution-logs',
            icon: <HistoryOutlined />,
            label: 'Execution Logs',
            onClick: () => navigate('/execution-logs'),
          },
        ]
      : []),
    // Platform admin section
    ...(isPlatformAdmin
      ? [
          { type: 'divider' as const },
          {
            key: '/admin',
            icon: <CrownOutlined />,
            label: 'Platform Admin',
            onClick: () => navigate('/admin'),
          },
        ]
      : []),
  ];

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: () => logout(),
    },
  ];

  const selectedKey = '/' + location.pathname.split('/')[1];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        breakpoint="lg"
        collapsedWidth="0"
        theme="light"
        style={{
          borderRight: '1px solid #f0f0f0',
        }}
      >
        <div className="p-4 text-center border-b border-gray-200">
          <Typography.Title level={4} style={{ margin: 0 }}>
            AgentStudio
          </Typography.Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            height: '64px',
          }}
        >
          {/* Organization Info with Switcher for Platform Admins */}
          <div className="flex items-center gap-3">
            {canSwitch ? (
              // Platform Admin: Show organization switcher
              <Space size="middle">
                {isSwitched && (
                  <Tooltip title="Viewing as another organization">
                    <Tag color="orange" icon={<EyeOutlined />} style={{ margin: 0 }}>
                      Viewing As
                    </Tag>
                  </Tooltip>
                )}
                <Select
                  value={switchedOrganization?.id || 'self'}
                  onChange={handleOrgSwitch}
                  style={{ minWidth: 220 }}
                  popupMatchSelectWidth={false}
                  optionLabelProp="label"
                >
                  <Select.Option value="self" label={organization?.name || 'My Organization'}>
                    <div className="flex items-center gap-2">
                      <BankOutlined style={{ color: '#1890ff' }} />
                      <span>{organization?.name || 'My Organization'}</span>
                      <Tag color="green" style={{ margin: 0, marginLeft: 'auto' }}>You</Tag>
                    </div>
                  </Select.Option>
                  <Select.OptGroup label="Switch to Organization">
                    {orgsData?.organizations
                      .filter(org => org.id !== organization?.id)
                      .map(org => (
                        <Select.Option key={org.id} value={org.id} label={org.name}>
                          <div className="flex items-center gap-2">
                            <SwapOutlined style={{ color: '#888' }} />
                            <span>{org.name}</span>
                            {org.userCount && (
                              <Text type="secondary" style={{ marginLeft: 'auto', fontSize: 11 }}>
                                {org.userCount} users
                              </Text>
                            )}
                          </div>
                        </Select.Option>
                      ))}
                  </Select.OptGroup>
                </Select>
                {isSwitched && (
                  <Tooltip title="Return to your organization">
                    <CloseCircleOutlined
                      onClick={() => handleOrgSwitch('self')}
                      style={{ color: '#ff4d4f', fontSize: 16, cursor: 'pointer' }}
                    />
                  </Tooltip>
                )}
              </Space>
            ) : (
              // Regular User: Show organization info
              <>
                {effectiveOrganization?.logoUrl ? (
                  <Avatar size={36} src={effectiveOrganization.logoUrl} shape="square" />
                ) : (
                  <BankOutlined style={{ fontSize: 20, color: '#1890ff' }} />
                )}
                <div className="flex flex-col justify-center">
                  <div className="flex items-center gap-2">
                    <Text strong style={{ fontSize: 14, lineHeight: 1.2 }}>
                      {effectiveOrganization?.name || user?.organizationName || 'My Organization'}
                    </Text>
                    {effectiveOrganization?.subscriptionStatus && (
                      <Tag
                        color={subscriptionStatusColors[effectiveOrganization.subscriptionStatus] || 'default'}
                        style={{ margin: 0, fontSize: 10, lineHeight: 1.4, padding: '0 4px' }}
                      >
                        {effectiveOrganization.subscriptionStatus.charAt(0).toUpperCase() + effectiveOrganization.subscriptionStatus.slice(1)}
                      </Tag>
                    )}
                  </div>
                  <Text type="secondary" style={{ fontSize: 11, lineHeight: 1.2 }}>
                    {effectiveOrganization?.userCount ? `${effectiveOrganization.userCount} members` : 'Organization'}
                  </Text>
                </div>
              </>
            )}
          </div>

          {/* User Info */}
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div className="flex items-center gap-3 cursor-pointer">
              <Avatar size={40} icon={<UserOutlined />} src={user?.avatarUrl} />
              <div className="flex flex-col justify-center">
                <div className="flex items-center gap-2">
                  <Text strong className="leading-tight">{user?.fullName || user?.email}</Text>
                  {isPlatformAdmin && <Tag color="gold" style={{ margin: 0 }}>Admin</Tag>}
                </div>
                <Text type="secondary" className="text-xs leading-tight">
                  {user?.roles?.length ? user.roles[0] : user?.role || 'Member'}
                </Text>
              </div>
            </div>
          </Dropdown>
        </Header>
        <Content
          style={{
            margin: '24px',
            padding: 24,
            background: '#fff',
            borderRadius: 8,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};
