import { Layout, Menu, Avatar, Dropdown, Typography, Tag } from 'antd';
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
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore, usePermissions } from '../../features/auth/authStore';
import { useLogout } from '../../features/auth/authHooks';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

export const MainLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  const { isPlatformAdmin, isOrgAdmin, canAccess } = usePermissions();
  const { mutate: logout } = useLogout();

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
            label: 'Audit Logs',
            onClick: () => navigate('/audit-logs'),
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
          <div />
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div className="flex items-center gap-3 cursor-pointer">
              <Avatar size={40} icon={<UserOutlined />} />
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
