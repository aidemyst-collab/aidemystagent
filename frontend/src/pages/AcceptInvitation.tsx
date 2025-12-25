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
  Alert,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
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

const AcceptInvitation: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [verificationData, setVerificationData] = useState<VerificationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

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
      const result = await invitationService.accept(token, {
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

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: '#f0f2f5',
        }}
      >
        <Card style={{ width: 400, textAlign: 'center' }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: 16 }}>Verifying invitation...</Paragraph>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: '#f0f2f5',
        }}
      >
        <Card style={{ width: 500 }}>
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

  if (success) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: '#f0f2f5',
        }}
      >
        <Card style={{ width: 500 }}>
          <Result
            status="success"
            title="Account Created!"
            subTitle="Your account has been created successfully. Redirecting to login..."
          />
        </Card>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: '#f0f2f5',
        padding: 24,
      }}
    >
      <Card style={{ width: 450 }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={3} style={{ margin: 0 }}>
            Accept Invitation
          </Title>
          <Text type="secondary">Complete your account setup</Text>
        </div>

        {verificationData && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
            message={
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <TeamOutlined />
                  <Text strong>Organization:</Text>
                  <Text>{verificationData.organization_name}</Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <UserOutlined />
                  <Text strong>Role:</Text>
                  <Text>{verificationData.role_name}</Text>
                </div>
              </div>
            }
          />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          autoComplete="off"
        >
          <Form.Item name="email" label="Email">
            <Input
              prefix={<MailOutlined />}
              disabled
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="fullName"
            label="Full Name"
            rules={[
              { required: true, message: 'Please enter your full name' },
              { min: 2, message: 'Name must be at least 2 characters' },
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Enter your full name"
              size="large"
            />
          </Form.Item>

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
              prefix={<LockOutlined />}
              placeholder="Create a password"
              size="large"
            />
          </Form.Item>

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
              prefix={<LockOutlined />}
              placeholder="Confirm your password"
              size="large"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={submitting}
              block
              size="large"
            >
              Create Account
            </Button>
          </Form.Item>

          <div style={{ textAlign: 'center' }}>
            <Text type="secondary">
              Already have an account?{' '}
              <a onClick={() => navigate('/login')}>Sign in</a>
            </Text>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default AcceptInvitation;
