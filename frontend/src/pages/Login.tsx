import { Form, Input, Button, Card, Typography, message } from 'antd';
import { LockOutlined, MailOutlined, RobotOutlined, ApiOutlined, ThunderboltOutlined, SafetyOutlined, CloudOutlined, TeamOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { useLogin } from '../features/auth/authHooks';
import type { LoginRequest } from '../types/auth';

const { Title, Text, Paragraph } = Typography;

const features = [
  {
    icon: <RobotOutlined style={{ fontSize: 28, color: '#c7d2fe' }} />,
    title: 'Visual Agent Builder',
    description: 'Design complex AI agents with an intuitive drag-and-drop canvas. No coding required.',
  },
  {
    icon: <ApiOutlined style={{ fontSize: 28, color: '#c7d2fe' }} />,
    title: 'LangGraph Orchestration',
    description: 'Enterprise-grade workflow orchestration with built-in state management and checkpointing.',
  },
  {
    icon: <CloudOutlined style={{ fontSize: 28, color: '#c7d2fe' }} />,
    title: 'RAG Integration',
    description: 'Connect to your knowledge bases via REST or GraphQL for context-aware AI responses.',
  },
  {
    icon: <ThunderboltOutlined style={{ fontSize: 28, color: '#c7d2fe' }} />,
    title: 'One-Click Deployment',
    description: 'Deploy agents instantly with auto-generated API endpoints and versioning.',
  },
  {
    icon: <SafetyOutlined style={{ fontSize: 28, color: '#c7d2fe' }} />,
    title: 'Enterprise Security',
    description: 'Role-based access control, encrypted credentials, and comprehensive audit logs.',
  },
  {
    icon: <TeamOutlined style={{ fontSize: 28, color: '#c7d2fe' }} />,
    title: 'Team Collaboration',
    description: 'Multi-tenant workspace with organization management and shared agent templates.',
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
    <div className="login-container" style={{
      display: 'flex',
      minHeight: '100vh',
      width: '100%',
    }}>
      {/* Left Panel - Branding & Features */}
      <div
        style={{
          width: '55%',
          minHeight: '100vh',
          background: 'linear-gradient(145deg, #1e1b4b 0%, #312e81 40%, #4338ca 100%)',
          padding: '48px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Background decoration */}
        <div style={{
          position: 'absolute',
          top: '-20%',
          right: '-10%',
          width: '400px',
          height: '400px',
          background: 'radial-gradient(circle, rgba(99,102,241,0.3) 0%, transparent 70%)',
          borderRadius: '50%',
        }} />
        <div style={{
          position: 'absolute',
          bottom: '-10%',
          left: '-5%',
          width: '300px',
          height: '300px',
          background: 'radial-gradient(circle, rgba(139,92,246,0.2) 0%, transparent 70%)',
          borderRadius: '50%',
        }} />

        {/* Logo Section */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <div style={{
              background: 'rgba(255,255,255,0.15)',
              borderRadius: '12px',
              padding: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <RobotOutlined style={{ fontSize: 32, color: '#fff' }} />
            </div>
            <div>
              <Title level={2} style={{ color: '#fff', margin: 0, fontWeight: 700 }}>
                AgentStudio
              </Title>
              <Text style={{ color: 'rgba(255,255,255,0.6)', fontSize: 14 }}>
                by AI Demyst
              </Text>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div style={{ position: 'relative', zIndex: 1, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', paddingTop: '20px', paddingBottom: '20px' }}>
          <div style={{ marginBottom: '40px' }}>
            <Title style={{ color: '#fff', marginBottom: '16px', fontSize: '36px', fontWeight: 700, lineHeight: 1.2 }}>
              Build AI Agents<br />Without Code
            </Title>
            <Paragraph style={{ color: 'rgba(255,255,255,0.8)', fontSize: '17px', lineHeight: 1.7, maxWidth: '500px', margin: 0 }}>
              AgentStudio is your complete platform for creating, testing, and deploying
              intelligent AI agents. Transform complex workflows into powerful automations
              with our visual builder powered by LangGraph.
            </Paragraph>
          </div>

          {/* Features Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '16px',
            maxWidth: '600px',
          }}>
            {features.map((feature, index) => (
              <div
                key={index}
                style={{
                  background: 'rgba(255,255,255,0.08)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: '12px',
                  padding: '20px',
                  border: '1px solid rgba(255,255,255,0.1)',
                  transition: 'all 0.3s ease',
                }}
              >
                <div style={{ marginBottom: '12px' }}>{feature.icon}</div>
                <Text strong style={{ color: '#fff', fontSize: '15px', display: 'block', marginBottom: '6px' }}>
                  {feature.title}
                </Text>
                <Text style={{ color: 'rgba(255,255,255,0.65)', fontSize: '13px', lineHeight: 1.5 }}>
                  {feature.description}
                </Text>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderTop: '1px solid rgba(255,255,255,0.1)',
            paddingTop: '24px',
          }}>
            <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>
              2024 AI Demyst. All rights reserved.
            </Text>
            <div style={{ display: 'flex', gap: '24px' }}>
              <a href="https://www.aidemyst.com" target="_blank" rel="noopener noreferrer" style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', textDecoration: 'none' }}>
                About Us
              </a>
              <a href="mailto:support@aidemyst.com" style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', textDecoration: 'none' }}>
                Contact
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div style={{
        width: '45%',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px',
        background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
      }}>
        <Card
          style={{
            width: '100%',
            maxWidth: '420px',
            borderRadius: '16px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
            border: 'none',
          }}
          styles={{ body: { padding: '40px' } }}
        >
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <Title level={2} style={{ marginBottom: '8px', color: '#1e293b' }}>
              Welcome back
            </Title>
            <Text type="secondary" style={{ fontSize: '15px' }}>
              Sign in to continue to AgentStudio
            </Text>
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
                prefix={<MailOutlined style={{ color: '#94a3b8' }} />}
                placeholder="Email address"
                autoComplete="email"
                style={{
                  borderRadius: '10px',
                  height: '48px',
                  fontSize: '15px',
                }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: 'Please input your password!' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#94a3b8' }} />}
                placeholder="Password"
                autoComplete="current-password"
                style={{
                  borderRadius: '10px',
                  height: '48px',
                  fontSize: '15px',
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: '16px', marginTop: '24px' }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={isPending}
                block
                style={{
                  height: '48px',
                  borderRadius: '10px',
                  fontWeight: 600,
                  fontSize: '16px',
                  background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                  border: 'none',
                  boxShadow: '0 4px 14px 0 rgba(99, 102, 241, 0.4)',
                }}
              >
                Sign In
              </Button>
            </Form.Item>
          </Form>

          <div style={{
            textAlign: 'center',
            marginTop: '24px',
            paddingTop: '24px',
            borderTop: '1px solid #e2e8f0'
          }}>
            <Text type="secondary" style={{ fontSize: '14px' }}>
              Don't have an account?{' '}
              <Link to="/register" style={{ color: '#6366f1', fontWeight: 600 }}>
                Create one
              </Link>
            </Text>
          </div>
        </Card>
      </div>

      {/* Mobile Styles - Override for small screens */}
      <style>{`
        @media (max-width: 1024px) {
          .login-container > div:first-child {
            display: none !important;
          }
          .login-container > div:last-child {
            width: 100% !important;
          }
        }
      `}</style>
    </div>
  );
};
