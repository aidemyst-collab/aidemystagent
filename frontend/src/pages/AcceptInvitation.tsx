import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Typography,
  message,
  Spin,
  Result,
  Progress,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  RobotOutlined,
  BankOutlined,
  SafetyOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  CloudOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { invitationService } from '../features/invitations/invitationService';

const { Title, Text, Paragraph } = Typography;

interface VerificationData {
  email: string;
  organization_name: string;
  role_name: string;
  expires_at: string;
  message?: string;
}

function getPasswordStrength(password: string): {
  percent: number;
  strokeColor: string;
  status: 'exception' | 'normal' | 'active' | 'success';
  label: string;
} {
  const len = password.length;
  if (len === 0) return { percent: 0, strokeColor: '#ff4d4f', status: 'exception', label: '' };
  if (len <= 2) return { percent: 10, strokeColor: '#ff4d4f', status: 'exception', label: 'Very weak' };
  if (len <= 5) return { percent: 33, strokeColor: '#fa8c16', status: 'normal', label: 'Weak' };
  if (len <= 9) return { percent: 66, strokeColor: '#faad14', status: 'normal', label: 'Moderate' };
  return { percent: 100, strokeColor: '#52c41a', status: 'success', label: 'Strong' };
}

const AcceptInvitation: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [verificationData, setVerificationData] = useState<VerificationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [passwordValue, setPasswordValue] = useState('');

  useEffect(() => {
    if (token) {
      verifyInvitation();
    }
  }, [token]);

  const verifyInvitation = async () => {
    if (!token) {
      setError('Invalid invitation link');
      setLoading(false);
      return;
    }

    try {
      const data = await invitationService.verify(token);
      setVerificationData(data);
      form.setFieldValue('email', data.email);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Invalid or expired invitation';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: { fullName: string; password: string; confirmPassword: string }) => {
    if (!token) return;

    if (values.password !== values.confirmPassword) {
      message.error('Passwords do not match');
      return;
    }

    setSubmitting(true);
    try {
      await invitationService.accept(token, {
        fullName: values.fullName,
        password: values.password,
      });

      setSuccess(true);
      message.success('Account created successfully!');

      // Redirect to login after a short delay
      setTimeout(() => {
        navigate('/login', { state: { email: verificationData?.email } });
      }, 2000);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to accept invitation';
      message.error(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const passwordStrength = getPasswordStrength(passwordValue);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
        }}
      >
        <Card
          style={{
            width: 400,
            textAlign: 'center',
            borderRadius: '16px',
            border: 'none',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
          }}
          styles={{ body: { padding: '40px' } }}
        >
          <Spin size="large" />
          <Paragraph style={{ marginTop: 16, color: '#64748b' }}>Verifying invitation...</Paragraph>
        </Card>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
        }}
      >
        <Card
          style={{
            width: 500,
            borderRadius: '16px',
            border: 'none',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
          }}
        >
          <Result
            status="error"
            title="Invalid Invitation"
            subTitle={error}
            extra={[
              <Button type="primary" key="login" onClick={() => navigate('/login')}>
                Go to Login
              </Button>,
              <Button key="home" onClick={() => navigate('/')}>
                Go to Home
              </Button>,
            ]}
          />
        </Card>
      </div>
    );
  }

  // ── Success state ──────────────────────────────────────────────────────────
  if (success) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
        }}
      >
        <Card
          style={{
            width: 500,
            borderRadius: '16px',
            border: 'none',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
          }}
        >
          <Result
            status="success"
            title={`Welcome to ${verificationData?.organization_name ?? 'the team'}!`}
            subTitle="Your account is ready. Redirecting to login..."
            extra={[
              <Button type="primary" key="login" onClick={() => navigate('/login')}>
                Go to Login
              </Button>,
            ]}
          />
        </Card>
      </div>
    );
  }

  // ── Main split-screen layout ───────────────────────────────────────────────
  return (
    <div
      className="accept-invitation-container"
      style={{
        display: 'flex',
        minHeight: '100vh',
        width: '100%',
      }}
    >
      {/* Left Panel — Branding & Invitation Info */}
      <div
        style={{
          width: '45%',
          minHeight: '100vh',
          background: 'linear-gradient(135deg, #4338ca 0%, #6366f1 100%)',
          padding: '48px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Background decoration */}
        <div
          style={{
            position: 'absolute',
            top: '-20%',
            right: '-10%',
            width: '400px',
            height: '400px',
            background: 'radial-gradient(circle, rgba(99,102,241,0.3) 0%, transparent 70%)',
            borderRadius: '50%',
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: '-10%',
            left: '-5%',
            width: '300px',
            height: '300px',
            background: 'radial-gradient(circle, rgba(139,92,246,0.2) 0%, transparent 70%)',
            borderRadius: '50%',
          }}
        />

        {/* Logo Section */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <div
              style={{
                background: 'rgba(255,255,255,0.15)',
                borderRadius: '12px',
                padding: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
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
        <div
          style={{
            position: 'relative',
            zIndex: 1,
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            paddingTop: '20px',
            paddingBottom: '20px',
          }}
        >
          <div style={{ marginBottom: '32px' }}>
            <Title
              style={{
                color: '#fff',
                marginBottom: '12px',
                fontSize: '32px',
                fontWeight: 700,
                lineHeight: 1.2,
              }}
            >
              You've been invited<br />to join a team
            </Title>
            <Paragraph
              style={{
                color: 'rgba(255,255,255,0.8)',
                fontSize: '16px',
                lineHeight: 1.7,
                maxWidth: '400px',
                margin: 0,
              }}
            >
              Complete your account setup to access AgentStudio and start building
              intelligent AI agents with your team.
            </Paragraph>
          </div>

          {/* Invitation Details Box */}
          {verificationData && (
            <div
              style={{
                background: 'rgba(255,255,255,0.15)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                padding: '24px',
                border: '1px solid rgba(255,255,255,0.2)',
                maxWidth: '400px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginBottom: '12px',
                }}
              >
                <BankOutlined style={{ fontSize: 18, color: '#c7d2fe' }} />
                <Text strong style={{ color: '#fff', fontSize: '15px' }}>
                  {verificationData.organization_name}
                </Text>
              </div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginBottom: '12px',
                }}
              >
                <SafetyOutlined style={{ fontSize: 18, color: '#c7d2fe' }} />
                <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: '14px' }}>
                  Role: <span style={{ color: '#fff', fontWeight: 600 }}>{verificationData.role_name}</span>
                </Text>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <MailOutlined style={{ fontSize: 18, color: '#c7d2fe' }} />
                <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: '14px' }}>
                  {verificationData.email}
                </Text>
              </div>

              {verificationData.message && (
                <div
                  style={{
                    marginTop: '16px',
                    paddingTop: '16px',
                    borderTop: '1px solid rgba(255,255,255,0.15)',
                  }}
                >
                  <Text
                    style={{
                      color: 'rgba(255,255,255,0.7)',
                      fontSize: '13px',
                      fontStyle: 'italic',
                    }}
                  >
                    "{verificationData.message}"
                  </Text>
                </div>
              )}
            </div>
          )}

          {/* Feature hints */}
          <div style={{ marginTop: '32px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {[
              { icon: <ApiOutlined style={{ fontSize: 18, color: '#c7d2fe' }} />, text: 'Visual drag-and-drop agent builder' },
              { icon: <ThunderboltOutlined style={{ fontSize: 18, color: '#c7d2fe' }} />, text: 'One-click deployment with versioning' },
              { icon: <CloudOutlined style={{ fontSize: 18, color: '#c7d2fe' }} />, text: 'Enterprise-grade RAG integrations' },
              { icon: <TeamOutlined style={{ fontSize: 18, color: '#c7d2fe' }} />, text: 'Shared workspace & team templates' },
            ].map((item, index) => (
              <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {item.icon}
                <Text style={{ color: 'rgba(255,255,255,0.75)', fontSize: '14px' }}>
                  {item.text}
                </Text>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderTop: '1px solid rgba(255,255,255,0.1)',
              paddingTop: '24px',
            }}
          >
            <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>
              2024 AI Demyst. All rights reserved.
            </Text>
            <div style={{ display: 'flex', gap: '24px' }}>
              <a
                href="https://www.aidemyst.com"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', textDecoration: 'none' }}
              >
                About Us
              </a>
              <a
                href="mailto:support@aidemyst.com"
                style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', textDecoration: 'none' }}
              >
                Contact
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel — Account Setup Form */}
      <div
        style={{
          width: '55%',
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '48px',
          background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
        }}
      >
        <Card
          style={{
            width: '100%',
            maxWidth: '440px',
            borderRadius: '16px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
            border: 'none',
          }}
          styles={{ body: { padding: '40px' } }}
        >
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <Title level={2} style={{ marginBottom: '8px', color: '#1e293b' }}>
              Complete your account
            </Title>
            <Text type="secondary" style={{ fontSize: '15px' }}>
              Set up your credentials to get started
            </Text>
          </div>

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            autoComplete="off"
            size="large"
          >
            {/* Email — disabled, pre-filled */}
            <Form.Item name="email" label="Email">
              <Input
                prefix={<MailOutlined style={{ color: '#94a3b8' }} />}
                disabled
                style={{ borderRadius: '10px', height: '48px', fontSize: '15px' }}
              />
            </Form.Item>

            {/* Full Name */}
            <Form.Item
              name="fullName"
              label="Full Name"
              rules={[
                { required: true, message: 'Please enter your full name' },
                { min: 2, message: 'Name must be at least 2 characters' },
              ]}
            >
              <Input
                prefix={<UserOutlined style={{ color: '#94a3b8' }} />}
                placeholder="Enter your full name"
                style={{ borderRadius: '10px', height: '48px', fontSize: '15px' }}
              />
            </Form.Item>

            {/* Password */}
            <Form.Item
              name="password"
              label="Password"
              rules={[
                { required: true, message: 'Please enter a password' },
                { min: 8, message: 'Password must be at least 8 characters' },
                {
                  pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                  message: 'Password must contain uppercase, lowercase, and number',
                },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#94a3b8' }} />}
                placeholder="Create a password"
                style={{ borderRadius: '10px', height: '48px', fontSize: '15px' }}
                onChange={(e) => setPasswordValue(e.target.value)}
              />
            </Form.Item>

            {/* Password strength indicator */}
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
                  {passwordStrength.label}
                </Text>
              </div>
            )}

            {/* Confirm Password */}
            <Form.Item
              name="confirmPassword"
              label="Confirm Password"
              dependencies={['password']}
              rules={[
                { required: true, message: 'Please confirm your password' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('Passwords do not match'));
                  },
                }),
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#94a3b8' }} />}
                placeholder="Confirm your password"
                style={{ borderRadius: '10px', height: '48px', fontSize: '15px' }}
              />
            </Form.Item>

            {/* Submit */}
            <Form.Item style={{ marginBottom: '16px', marginTop: '8px' }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={submitting}
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
                {verificationData?.organization_name
                  ? `Create Account & Join ${verificationData.organization_name}`
                  : 'Create Account'}
              </Button>
            </Form.Item>
          </Form>

          <div
            style={{
              textAlign: 'center',
              marginTop: '24px',
              paddingTop: '24px',
              borderTop: '1px solid #e2e8f0',
            }}
          >
            <Text type="secondary" style={{ fontSize: '14px' }}>
              Already have an account?{' '}
              <a onClick={() => navigate('/login')} style={{ cursor: 'pointer' }}>
                Sign in
              </a>
            </Text>
          </div>
        </Card>
      </div>

      {/* Responsive: hide left panel on mobile */}
      <style>{`
        @media (max-width: 768px) {
          .accept-invitation-container > div:first-child {
            display: none !important;
          }
          .accept-invitation-container > div:last-child {
            width: 100% !important;
            padding: 24px !important;
          }
        }
      `}</style>
    </div>
  );
};

export default AcceptInvitation;
