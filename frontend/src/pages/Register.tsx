import { Form, Input, Button, Card, Typography, message, Select, Radio, Space } from 'antd';
import { LockOutlined, MailOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useRegister } from '../features/auth/authHooks';
import type { RegisterRequest } from '../types/auth';
import { apiClient } from '../services/api';
import { useAuthStore } from '../features/auth/authStore';

const { Title, Text } = Typography;
const { Option } = Select;

interface Organization {
  id: string;
  name: string;
  slug?: string;
}

export const Register = () => {
  const { mutate: register, isPending } = useRegister();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [orgMode, setOrgMode] = useState<'create' | 'join'>('create');
  const [form] = Form.useForm();

  // Check if accessed from within the app (e.g., /users/create)
  const isInternalCreate = location.pathname === '/users/create';

  useEffect(() => {
    fetchOrganizations();
  }, []);

  const fetchOrganizations = async () => {
    setLoadingOrgs(true);
    try {
      // Use public endpoint for unauthenticated users
      const endpoint = isAuthenticated ? '/organizations' : '/organizations/public';
      const response = await apiClient.get(endpoint, isAuthenticated ? {} : { skipAuth: true });
      setOrganizations(response.organizations || []);
      // If there are existing organizations, default to join mode
      if (response.organizations?.length > 0) {
        setOrgMode('join');
      }
    } catch (error) {
      console.error('Error fetching organizations:', error);
      // Don't show error - orgs might just be empty
    } finally {
      setLoadingOrgs(false);
    }
  };

  const onFinish = (values: any) => {
    // Build the registration request
    const registerData: RegisterRequest = {
      email: values.email,
      password: values.password,
      fullName: values.fullName,
    };

    if (orgMode === 'create') {
      registerData.organizationName = values.organizationName;
    } else if (values.organizationId) {
      registerData.organizationId = values.organizationId;
    }

    if (isInternalCreate && values.role) {
      registerData.role = values.role;
    }

    register(registerData, {
      onSuccess: () => {
        if (isInternalCreate) {
          message.success('User created successfully');
          navigate('/users');
        }
      },
      onError: (error) => {
        message.error(error.message || (isInternalCreate ? 'Failed to create user' : 'Registration failed'));
      },
    });
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <Card className="w-full max-w-md">
        <div className="text-center mb-8">
          <Title level={2}>{isInternalCreate ? 'Create New User' : 'AgentStudio'}</Title>
          <Text type="secondary">{isInternalCreate ? 'Add a new user to your organization' : 'Create your account'}</Text>
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
            rules={[
              { required: true, message: 'Please enter your name!' },
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Full Name"
              autoComplete="name"
            />
          </Form.Item>

          <Form.Item
            name="email"
            rules={[
              { required: true, message: 'Please input your email!' },
              { type: 'email', message: 'Please enter a valid email!' },
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="Email"
              autoComplete="email"
            />
          </Form.Item>

          {isInternalCreate && (
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
          )}

          {!isInternalCreate && (
            <>
              <Form.Item label="Organization">
                <Radio.Group
                  value={orgMode}
                  onChange={(e) => setOrgMode(e.target.value)}
                  style={{ marginBottom: 12 }}
                >
                  <Radio.Button value="create">Create New</Radio.Button>
                  <Radio.Button value="join" disabled={organizations.length === 0}>
                    Join Existing
                  </Radio.Button>
                </Radio.Group>
              </Form.Item>

              {orgMode === 'create' ? (
                <Form.Item
                  name="organizationName"
                  rules={[{ required: true, message: 'Please enter organization name!' }]}
                >
                  <Input
                    prefix={<TeamOutlined />}
                    placeholder="Organization Name (e.g., Acme Corp)"
                  />
                </Form.Item>
              ) : (
                <Form.Item
                  name="organizationId"
                  rules={[{ required: true, message: 'Please select an organization!' }]}
                >
                  <Select
                    placeholder="Select an organization to join"
                    loading={loadingOrgs}
                  >
                    {organizations.map((org) => (
                      <Option key={org.id} value={org.id}>
                        {org.name}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              )}
            </>
          )}

          {isInternalCreate && (
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
          )}

          <Form.Item
            name="password"
            rules={[
              { required: true, message: 'Please input your password!' },
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
            />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            dependencies={['password']}
            rules={[
              { required: true, message: 'Please confirm your password!' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Passwords do not match!'));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Confirm Password"
              autoComplete="new-password"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={isPending}
              block
            >
              {isInternalCreate ? 'Create User' : 'Sign Up'}
            </Button>
          </Form.Item>

          {!isInternalCreate && (
            <div className="text-center">
              <Text type="secondary">
                Already have an account?{' '}
                <Link to="/login">Sign in</Link>
              </Text>
            </div>
          )}

          {isInternalCreate && (
            <div className="text-center">
              <Button type="link" onClick={() => navigate('/users')}>
                Cancel
              </Button>
            </div>
          )}
        </Form>
      </Card>
    </div>
  );
};
