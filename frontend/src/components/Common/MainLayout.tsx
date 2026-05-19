import { useEffect, useState } from 'react';
import { Layout, Menu, Avatar, Dropdown, Typography, Tag, Button } from 'antd';
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
  CloudServerOutlined,
  BarChartOutlined,
  CrownOutlined,
  TeamOutlined,
  MailOutlined,
  AuditOutlined,
  HistoryOutlined,
  BankOutlined,
  CreditCardOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
  ApiOutlined,
  FileTextOutlined,
  ExportOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore, usePermissions, useOrganizationSwitcher, useImpersonation } from '../../features/auth/authStore';
import { ImpersonationBanner } from './ImpersonationBanner';
import { useLogout, useInitializeOrganization } from '../../features/auth/authHooks';
import type { MenuProps } from 'antd';

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

export const MainLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, organization, isAuthenticated } = useAuthStore();
  const { isPlatformAdmin, canAccess, hasProduct } = usePermissions();
  const { mutate: logout } = useLogout();
  const { mutate: initializeOrganization } = useInitializeOrganization();
  const {
    effectiveOrganization,
  } = useOrganizationSwitcher();
  const { isImpersonating } = useImpersonation();

  // Sidebar collapsed state - persisted in localStorage
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    return saved ? JSON.parse(saved) : false;
  });

  // Save collapsed state to localStorage
  const toggleCollapsed = () => {
    const newState = !collapsed;
    setCollapsed(newState);
    localStorage.setItem('sidebarCollapsed', JSON.stringify(newState));
  };

  // Initialize organization data on mount (for page refresh scenarios)
  useEffect(() => {
    if (isAuthenticated && !organization) {
      initializeOrganization();
    }
  }, [isAuthenticated, organization, initializeOrganization]);

  // Platform admins get a focused admin-only menu; regular users get the full org menu
  const menuItems: MenuProps['items'] = isPlatformAdmin
    ? [
        // Platform Admin nav — each section is its own page
        {
          key: '/admin',
          icon: <DashboardOutlined />,
          label: 'Dashboard',
          onClick: () => navigate('/admin'),
        },
        { type: 'divider' as const },
        {
          key: '/admin/organizations',
          icon: <BankOutlined />,
          label: 'Organisations',
          onClick: () => navigate('/admin/organizations'),
        },
        {
          key: '/admin/users',
          icon: <TeamOutlined />,
          label: 'Users',
          onClick: () => navigate('/admin/users'),
        },
        {
          key: '/admin/plans',
          icon: <CrownOutlined />,
          label: 'Plans',
          onClick: () => navigate('/admin/plans'),
        },
        { type: 'divider' as const },
        {
          key: '/audit-logs',
          icon: <AuditOutlined />,
          label: 'Audit Logs',
          onClick: () => navigate('/audit-logs'),
        },
        {
          key: '/admin/system-logs',
          icon: <FileTextOutlined />,
          label: 'System Logs',
          onClick: () => navigate('/admin/system-logs'),
        },
      ]
    : [
        // Regular org-user menu
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
          key: '/mcp-servers',
          icon: <CloudServerOutlined />,
          label: 'MCP Servers',
          onClick: () => navigate('/mcp-servers'),
        },
        {
          key: '/mcp-tools',
          icon: <ApiOutlined />,
          label: 'Dynamic Tools',
          onClick: () => navigate('/mcp-tools'),
        },
        {
          key: '/hosted-mcp-servers',
          icon: <CloudServerOutlined />,
          label: 'Hosted MCP',
          onClick: () => navigate('/hosted-mcp-servers'),
        },
        ...(canAccess('credentials-access')
          ? [
              {
                key: '/credentials',
                icon: <KeyOutlined />,
                label: 'Credentials',
                onClick: () => navigate('/credentials'),
              },
            ]
          : []),
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
        // Organization Settings
        ...(canAccess('user-management')
          ? [
              {
                key: '/settings',
                icon: <SettingOutlined />,
                label: 'Settings',
                onClick: () => navigate('/settings'),
              },
              {
                key: '/billing',
                icon: <CreditCardOutlined />,
                label: 'Billing',
                onClick: () => navigate('/billing'),
              },
            ]
          : []),
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
        // Product links — shown only when the org's plan includes the product
        ...(hasProduct('demystrag') || hasProduct('mock_api')
          ? [{ type: 'divider' as const }]
          : []),
        ...(hasProduct('demystrag')
          ? [
              {
                key: 'product-demystrag',
                icon: <DatabaseOutlined />,
                label: 'DemystRAG',
                onClick: () => {
                  const base = import.meta.env.VITE_DEMYSTRAG_URL || 'http://localhost:8001';
                  const token = useAuthStore.getState().tokens?.accessToken;
                  window.open(token ? `${base}/#token=${token}` : base, '_blank');
                },
              },
            ]
          : []),
        ...(hasProduct('mock_api')
          ? [
              {
                key: 'product-mock-api',
                icon: <ExportOutlined />,
                label: 'Mock API',
                onClick: () => {
                  const base = import.meta.env.VITE_MOCK_API_URL || 'http://localhost:5183';
                  const token = useAuthStore.getState().tokens?.accessToken;
                  window.open(token ? `${base}/#token=${token}` : base, '_blank');
                },
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

  // For admin sub-routes (/admin/organizations, /admin/users, etc.) use full path as key
  const selectedKey = location.pathname.startsWith('/admin/')
    ? location.pathname
    : '/' + location.pathname.split('/')[1];

  return (
    <>
      <ImpersonationBanner />
      <Layout style={{ minHeight: '100vh', paddingTop: isImpersonating ? 44 : 0 }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={220}
        collapsedWidth={80}
        theme={isPlatformAdmin ? 'dark' : 'light'}
        style={{
          borderRight: isPlatformAdmin ? 'none' : '1px solid #f0f0f0',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          overflow: 'auto',
          background: isPlatformAdmin ? '#1a1a2e' : undefined,
        }}
      >
        <div
          style={{
            padding: collapsed ? '16px 8px' : '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: '10px',
            height: '64px',
            borderBottom: isPlatformAdmin ? '1px solid rgba(255,255,255,0.1)' : '1px solid #f0f0f0',
          }}
        >
          <RobotOutlined style={{ fontSize: 24, color: isPlatformAdmin ? '#f59e0b' : '#6366f1' }} />
          {!collapsed && (
            <Typography.Title level={4} style={{ margin: 0, color: isPlatformAdmin ? '#fff' : '#312e81' }}>
              AgentStudio
            </Typography.Title>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          theme={isPlatformAdmin ? 'dark' : 'light'}
          style={{ borderRight: 0, background: isPlatformAdmin ? '#1a1a2e' : undefined }}
          inlineCollapsed={collapsed}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 220, transition: 'margin-left 0.2s' }}>
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
          {/* Toggle Button and Organization Info */}
          <div className="flex items-center gap-3">
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={toggleCollapsed}
              style={{
                fontSize: '18px',
                width: 40,
                height: 40,
              }}
            />
            {isPlatformAdmin ? (
              // Platform Admin: show console badge instead of org switcher
              <Tag
                color="gold"
                icon={<CrownOutlined />}
                style={{ fontSize: 13, padding: '4px 12px', margin: 0 }}
              >
                Platform Admin Console
              </Tag>
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
                  {(() => {
                    const r = user?.roles?.length ? user.roles[0] : user?.role || 'Member';
                    return r === 'Agent Admin' ? 'Team Lead' : r;
                  })()}
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
    </>
  );
};
