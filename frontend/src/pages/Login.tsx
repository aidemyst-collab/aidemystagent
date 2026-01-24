import { Form, Input, Button, Card, Typography, message } from 'antd';
import { LockOutlined, MailOutlined, RobotOutlined, ApiOutlined, ThunderboltOutlined, SafetyOutlined } from '@ant-design/icons';
import { useLogin } from '../features/auth/authHooks';
import type { LoginRequest } from '../types/auth';

const { Title, Text, Paragraph } = Typography;

const features = [
  {
    icon: <RobotOutlined style={{ fontSize: 24, color: '#a5b4fc' }} />,
    title: 'Visual Agent Builder',
    description: 'Design AI agents with an intuitive drag-and-drop interface',
  },
  {
    icon: <ApiOutlined style={{ fontSize: 24, color: '#a5b4fc' }} />,
    title: 'LangGraph Powered',
    description: 'Enterprise-grade orchestration with state management',
  },
  {
    icon: <ThunderboltOutlined style={{ fontSize: 24, color: '#a5b4fc' }} />,
    title: 'One-Click Deploy',
    description: 'Deploy agents to production with API endpoints instantly',
  },
  {
    icon: <SafetyOutlined style={{ fontSize: 24, color: '#a5b4fc' }} />,
    title: 'Enterprise Ready',
    description: 'Role-based access, audit logs, and secure credentials',
  },
];

export const Login = () => {
  const { mutate: login, isPending } = useLogin();

  const onFinish = (values: LoginRequest) => {
    login(values, {
      onError: (error) => {
        message.error(error.message || 'Login failed');
      },
    });
  };

  return (
    <div className="flex min-h-screen">
      {/* Left Panel - Branding & Info */}
      <div
        className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12"
        style={{
          background: 'linear-gradient(135deg, #312e81 0%, #4338ca 50%, #6366f1 100%)',
        }}
      >
        <div>
          <div className="flex items-center gap-3 mb-2">
            <RobotOutlined style={{ fontSize: 36, color: '#fff' }} />
            <Title level={2} style={{ color: '#fff', margin: 0 }}>
              AgentStudio
            </Title>
          </div>
          <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 16 }}>
            by AI Demyst
          </Text>
        </div>

        <div className="space-y-8">
          <div>
            <Title level={3} style={{ color: '#fff', marginBottom: 16 }}>
              Build AI Agents Without Code
            </Title>
            <Paragraph style={{ color: 'rgba(255,255,255,0.85)', fontSize: 16, lineHeight: 1.7 }}>
              AgentStudio is your complete platform for creating, testing, and deploying
              intelligent AI agents. From simple chatbots to complex multi-step workflows,
              bring your AI vision to life with our visual builder.
            </Paragraph>
          </div>

          <div className="grid grid-cols-1 gap-6">
            {features.map((feature, index) => (
              <div
                key={index}
                className="flex items-start gap-4 p-4 rounded-lg"
                style={{ background: 'rgba(255,255,255,0.1)' }}
              >
                <div className="flex-shrink-0 mt-1">{feature.icon}</div>
                <div>
                  <Text strong style={{ color: '#fff', fontSize: 15 }}>
                    {feature.title}
                  </Text>
                  <Paragraph style={{ color: 'rgba(255,255,255,0.7)', margin: 0, fontSize: 13 }}>
                    {feature.description}
                  </Paragraph>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
            © 2024 AI Demyst. All rights reserved.
          </Text>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-gray-50">
        <Card
          className="w-full max-w-md shadow-lg"
          style={{ borderRadius: 12 }}
        >
          <div className="text-center mb-8">
            {/* Mobile logo - only visible on smaller screens */}
            <div className="lg:hidden flex items-center justify-center gap-2 mb-4">
              <RobotOutlined style={{ fontSize: 28, color: '#6366f1' }} />
              <Title level={3} style={{ margin: 0, color: '#312e81' }}>
                AgentStudio
              </Title>
            </div>
            <Title level={3} style={{ marginBottom: 4 }}>Welcome back</Title>
            <Text type="secondary">Sign in to continue to AgentStudio</Text>
          </div>

          <Form
            name="login"
            onFinish={onFinish}
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="email"
              rules={[
                { required: true, message: 'Please input your email!' },
                { type: 'email', message: 'Please enter a valid email!' },
              ]}
            >
              <Input
                prefix={<MailOutlined style={{ color: '#9ca3af' }} />}
                placeholder="Email address"
                autoComplete="email"
                style={{ borderRadius: 8 }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: 'Please input your password!' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#9ca3af' }} />}
                placeholder="Password"
                autoComplete="current-password"
                style={{ borderRadius: 8 }}
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={isPending}
                block
                style={{
                  height: 44,
                  borderRadius: 8,
                  fontWeight: 500,
                }}
              >
                Sign In
              </Button>
            </Form.Item>
          </Form>

          <div className="text-center mt-6 pt-6 border-t border-gray-100">
            <Text type="secondary" style={{ fontSize: 13 }}>
              Need access? Contact your administrator.
            </Text>
          </div>
        </Card>
      </div>
    </div>
  );
};
