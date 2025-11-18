import { Form, Input, Button, Card, Typography, message, Result } from 'antd';
import { MailOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { useResetPassword } from '../features/auth/authHooks';
import { PasswordResetRequest } from '../types/auth';
import { useState } from 'react';

const { Title, Text } = Typography;

export const ForgotPassword = () => {
  const { mutate: resetPassword, isPending } = useResetPassword();
  const [emailSent, setEmailSent] = useState(false);

  const onFinish = (values: PasswordResetRequest) => {
    resetPassword(values, {
      onSuccess: () => {
        setEmailSent(true);
      },
      onError: (error) => {
        message.error(error.message || 'Failed to send reset email');
      },
    });
  };

  if (emailSent) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <Card className="w-full max-w-md">
          <Result
            status="success"
            title="Email Sent!"
            subTitle="Check your email for password reset instructions."
            extra={[
              <Link to="/login" key="login">
                <Button type="primary">Back to Login</Button>
              </Link>,
            ]}
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <Card className="w-full max-w-md">
        <div className="text-center mb-8">
          <Title level={2}>Reset Password</Title>
          <Text type="secondary">Enter your email to reset your password</Text>
        </div>

        <Form
          name="forgot-password"
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
              prefix={<MailOutlined />}
              placeholder="Email"
              autoComplete="email"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={isPending}
              block
            >
              Send Reset Link
            </Button>
          </Form.Item>

          <div className="text-center">
            <Link to="/login">
              <Text type="secondary">Back to login</Text>
            </Link>
          </div>
        </Form>
      </Card>
    </div>
  );
};
