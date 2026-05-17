import { Card, Typography, Steps, Button, Space } from 'antd';
import { ClockCircleOutlined } from '@ant-design/icons';
import { useAuthStore } from '../features/auth/authStore';
import { useLogout } from '../features/auth/authHooks';

const { Title, Text, Paragraph } = Typography;

export const PendingApproval = () => {
  const user = useAuthStore((state) => state.user);
  const { mutate: logout, isPending: isLoggingOut } = useLogout();

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
      padding: '24px',
    }}>
      <Card
        style={{
          width: '100%',
          maxWidth: '480px',
          borderRadius: '16px',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          border: 'none',
        }}
        styles={{ body: { padding: '48px 40px' } }}
      >
        {/* Icon */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <ClockCircleOutlined style={{ fontSize: 48, color: '#f59e0b' }} />
        </div>

        {/* Heading */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <Title level={3} style={{ marginBottom: '12px', color: '#1e293b' }}>
            Your account is under review
          </Title>
          <Paragraph style={{ color: '#64748b', fontSize: '15px', margin: 0 }}>
            We're reviewing your organisation. You'll receive an email at{' '}
            <Text strong>{user?.email || 'your email address'}</Text>{' '}
            once approved. This usually takes 24–48 hours.
          </Paragraph>
        </div>

        {/* Steps */}
        <div style={{ marginBottom: '32px' }}>
          <Steps
            direction="vertical"
            size="small"
            items={[
              {
                title: 'Account Created',
                status: 'finish',
                description: 'Your account has been successfully created.',
              },
              {
                title: 'Under Review',
                status: 'process',
                description: 'Our team is reviewing your organisation details.',
              },
              {
                title: 'Access Granted',
                status: 'wait',
                description: 'Full platform access will be enabled after approval.',
              },
            ]}
          />
        </div>

        {/* Support link */}
        <div style={{
          textAlign: 'center',
          marginBottom: '24px',
          paddingTop: '16px',
          borderTop: '1px solid #e2e8f0',
        }}>
          <Text type="secondary" style={{ fontSize: '14px' }}>
            Need help?{' '}
            <a href="mailto:support@aidemyst.com" style={{ color: '#6366f1' }}>
              Contact support@aidemyst.com
            </a>
          </Text>
        </div>

        {/* Logout button */}
        <div style={{ textAlign: 'center' }}>
          <Space>
            <Button
              onClick={() => logout()}
              loading={isLoggingOut}
              style={{ borderRadius: '8px' }}
            >
              Logout
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  );
};
