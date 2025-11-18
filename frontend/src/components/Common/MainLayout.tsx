import { Layout, Menu, Avatar, Dropdown, Typography } from 'antd';
import {
  DashboardOutlined,
  RocketOutlined,
  ToolOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  FolderOutlined,
  CloudOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../features/auth/authStore';
import { useLogout } from '../../features/auth/authHooks';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

export const MainLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
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
      label: 'Agents',
      onClick: () => navigate('/agents'),
    },
    {
      key: '/tools',
      icon: <ToolOutlined />,
      label: 'Tools',
      onClick: () => navigate('/tools'),
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
    ...(user?.role === 'admin'
      ? [
          {
            key: '/users',
            icon: <UserOutlined />,
            label: 'Users',
            onClick: () => navigate('/users'),
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
          }}
        >
          <div />
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div className="flex items-center cursor-pointer">
              <Avatar icon={<UserOutlined />} />
              <div className="ml-2">
                <Text strong>{user?.email}</Text>
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {user?.role}
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
