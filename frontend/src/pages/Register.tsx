import { Form, Input, Button, Card, Typography, message, Select, Progress, Alert } from 'antd';
import { LockOutlined, MailOutlined, TeamOutlined, UserOutlined, RobotOutlined, ApiOutlined, ThunderboltOutlined, SafetyOutlined, CloudOutlined } from '@ant-design/icons';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useRegister } from '../features/auth/authHooks';
import type { RegisterRequest } from '../types/auth';
import { apiClient } from '../services/api';
import { useAuthStore } from '../features/auth/authStore';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

interface Organization {
  id: string;
  name: string;
  slug?: string;
}

function getPasswordStrength(password: string): { percent: number; strokeColor: string; status: 'exception' | 'normal' | 'active' | 'success' } {
  const len = password.length;
  if (len === 0) return { percent: 0, strokeColor: '#ff4d4f', status: 'exception' };
  if (len <= 2) return { percent: 10, strokeColor: '#ff4d4f', status: 'exception' };
  if (len <= 5) return { percent: 33, strokeColor: '#fa8c16', status: 'normal' };
  if (len <= 9) return { percent: 66, strokeColor: '#faad14', status: 'normal' };
  return { percent: 100, strokeColor: '#52c41a', status: 'success' };
}

const brandingFeatures = [
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
];

export const Register = () => {
  const { mutate: register, isPending } = useRegister();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [passwordValue, setPasswordValue] = useState('');
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [form] = Form.useForm();

  // Check if accessed from within the app (e.g., /users/create)
  const isInternalCreate = location.pathname === '/users/create';

  // Fetch organizations for internal create mode only
  const fetchOrganizations = async () => {
    if (!isInternalCreate) return;
    setLoadingOrgs(true);
    try {
      const response = await apiClient.get('/organizations', {});
      setOrganizations(response.organizations || []);
    } catch (error) {
      console.error('Error fetching organizations:', error);
    } finally {
      setLoadingOrgs(false);
    }
  };

  // Only fetch orgs when in internal create mode
  if (isInternalCreate && organizations.length === 0 && !loadingOrgs) {
    fetchOrganizations();
  }

  const onFinish = (values: any) => {
    setRegisterError(null);
    const registerData: RegisterRequest = {
      email: values.email,
      password: values.password,
      fullName: values.fullName,
    };

    if (!isInternalCreate) {
      registerData.organizationName = values.organizationName;
    } else {
      if (values.organizationId) {
        registerData.organizationId = values.organizationId;
      }
      if (values.role) {
        registerData.role = values.role;
      }
    }

    register(registerData, {
      onSuccess: () => {
        if (isInternalCreate) {
          message.success('User created successfully');
          navigate('/users');
        }
      },
      onError: (error) => {
        const msg = error.message || (isInternalCreate ? 'Failed to create user' : 'Registration failed');
        if (isInternalCreate) {
          message.error(msg);
        } else {
          setRegisterError(msg);
        }
      },
    });
  };

  const passwordStrength = getPasswordStrength(passwordValue);

  // Internal create mode — keep the simple card layout
  if (isInternalCreate) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <Card className="w-full max-w-md">
          <div className="text-center mb-8">
            <Title level={2}>Create New User</Title>
            <Text type="secondary">Add a new user to your organization</Text>
          </div>

          <Form
            name="register-internal"
            form={form}
            onFinish={onFinish}
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="fullName"
              label="Full Name"
              rules={[{ required: true, message: 'Please enter the full name!' }]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="Full Name"
                autoComplete="name"
              />
            </Form.Item>

            <Form.Item
              name="email"
              label="Work Email"
              rules={[
                { required: true, message: 'Please input the email!' },
                { type: 'email', message: 'Please enter a valid email!' },
              ]}
            >
              <Input
                prefix={<MailOutlined />}
                placeholder="Email"
                autoComplete="email"
              />
            </Form.Item>

            <Form.Item
              name="role"
              label="User Role"
              rules={[{ required: true, message: 'Please select a role!' }]}
              initialValue="creator"
            >
              <Select placeholder="Select user role">
                <Option value="admin">Admin - Full access to organization</Option>
                <Option value="creator">Creator - Can create and manage workflows</Option>
                <Option value="viewer">Viewer - Read-only access</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="organizationId"
              label="Organization"
              rules={[{ required: true, message: 'Please select an organization!' }]}
            >
              <Select
                placeholder="Select organization"
                loading={loadingOrgs}
              >
                {organizations.map((org) => (
                  <Option key={org.id} value={org.id}>
                    {org.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="password"
              label="Password"
              rules={[
                { required: true, message: 'Please input a password!' },
                { min: 8, message: 'Password must be at least 8 characters!' },
                {
                  pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                  message: 'Password must contain uppercase, lowercase, and number!',
                },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Password"
                autoComplete="new-password"
                onChange={(e) => setPasswordValue(e.target.value)}
              />
            </Form.Item>

            {passwordValue.length > 0 && (
              <div style={{ marginTop: -16, marginBottom: 16 }}>
                <Progress
                  percent={passwordStrength.percent}
                  strokeColor={passwordStrength.strokeColor}
                  status={passwordStrength.status}
                  size="small"
                  showInfo={false}
                />
              </div>
            )}

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={isPending}
                block
              >
                Create User
              </Button>
            </Form.Item>

            <div className="text-center">
              <Button type="link" onClick={() => navigate('/users')}>
                Cancel
              </Button>
            </div>
          </Form>
        </Card>
      </div>
    );
  }

  // Public registration — split-screen layout matching Login.tsx
  return (
    <div className="register-container" style={{
      display: 'flex',
      minHeight: '100vh',
      width: '100%',
    }}>
      {/* Left Panel - Branding */}
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
              Start Building<br />AI Agents Today
            </Title>
            <Paragraph style={{ color: 'rgba(255,255,255,0.8)', fontSize: '17px', lineHeight: 1.7, maxWidth: '500px', margin: 0 }}>
              Join AgentStudio and create, test, and deploy intelligent AI agents.
              Transform complex workflows into powerful automations with our visual
              builder powered by LangGraph.
            </Paragraph>
          </div>

          {/* Features Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '16px',
            maxWidth: '600px',
          }}>
            {brandingFeatures.map((feature, index) => (
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

      {/* Right Panel - Register Form */}
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
              Create your account
            </Title>
            <Text type="secondary" style={{ fontSize: '15px' }}>
              Get started with AgentStudio
            </Text>
          </div>

          <Form
            name="register"
            form={form}
            onFinish={onFinish}
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="fullName"
              label="Full Name"
              rules={[{ required: true, message: 'Please enter your full name!' }]}
            >
              <Input
                prefix={<UserOutlined style={{ color: '#94a3b8' }} />}
                placeholder="Jane Smith"
                autoComplete="name"
                style={{ borderRadius: '10px', height: '48px', fontSize: '15px' }}
              />
            </Form.Item>

            <Form.Item
              name="email"
              label="Work Email"
              rules={[
                { required: true, message: 'Please input your email!' },
                { type: 'email', message: 'Please enter a valid email!' },
              ]}
            >
              <Input
                prefix={<MailOutlined style={{ color: '#94a3b8' }} />}
                placeholder="jane@company.com"
                autoComplete="email"
                style={{ borderRadius: '10px', height: '48px', fontSize: '15px' }}
              />
            </Form.Item>

            <Form.Item
              name="organizationName"
              label="Organisation Name"
              rules={[{ required: true, message: 'Please enter your organisation name!' }]}
            >
              <Input
                prefix={<TeamOutlined style={{ color: '#94a3b8' }} />}
                placeholder="Acme Corp"
                style={{ borderRadius: '10px', height: '48px', fontSize: '15px' }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              label="Password"
              rules={[
                { required: true, message: 'Please input a password!' },
                { min: 8, message: 'Password must be at least 8 characters!' },
                {
                  pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                  message: 'Password must contain uppercase, lowercase, and number!',
                },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#94a3b8' }} />}
                placeholder="Create a strong password"
                autoComplete="new-password"
                style={{ borderRadius: '10px', height: '48px', fontSize: '15px' }}
                onChange={(e) => setPasswordValue(e.target.value)}
              />
            </Form.Item>

            {/* Password strength bar */}
            {passwordValue.length > 0 && (
              <div style={{ marginTop: -16, marginBottom: 16 }}>
                <Progress
                  percent={passwordStrength.percent}
                  strokeColor={passwordStrength.strokeColor}
                  status={passwordStrength.status}
                  size="small"
                  showInfo={false}
                />
                <Text style={{ fontSize: 12, color: '#94a3b8' }}>
                  {passwordStrength.percent <= 10 && 'Very weak'}
                  {passwordStrength.percent === 33 && 'Weak'}
                  {passwordStrength.percent === 66 && 'Moderate'}
                  {passwordStrength.percent === 100 && 'Strong'}
                </Text>
              </div>
            )}

            {registerError && (
              <Alert
                message={registerError}
                type="error"
                showIcon
                style={{ marginBottom: 16, borderRadius: 10 }}
                closable
                onClose={() => setRegisterError(null)}
              />
            )}

            <Form.Item style={{ marginBottom: '16px', marginTop: '8px' }}>
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
                Create Account
              </Button>
            </Form.Item>
          </Form>

          <div style={{
            textAlign: 'center',
            marginTop: '24px',
            paddingTop: '24px',
            borderTop: '1px solid #e2e8f0',
          }}>
            <Text type="secondary" style={{ fontSize: '14px' }}>
              Already have an account?{' '}
              <Link to="/login">Sign in</Link>
            </Text>
          </div>
        </Card>
      </div>

      {/* Mobile Styles */}
      <style>{`
        @media (max-width: 1024px) {
          .register-container > div:first-child {
            display: none !important;
          }
          .register-container > div:last-child {
            width: 100% !important;
          }
        }
      `}</style>
    </div>
  );
};
