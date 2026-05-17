import { Alert, Button, Space, Typography } from 'antd';
import { EyeOutlined, CloseCircleOutlined, LoadingOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useImpersonation } from '../../features/auth/authStore';
import { apiClient } from '../../services/api';

const { Text } = Typography;

export const ImpersonationBanner = () => {
  const navigate = useNavigate();
  const { isImpersonating, impersonatedUser, endImpersonation } = useImpersonation();
  const [loading, setLoading] = useState(false);

  if (!isImpersonating || !impersonatedUser) return null;

  const handleExit = async () => {
    setLoading(true);
    try {
      await apiClient.post('/auth/impersonate/end', {});
    } catch {
      // Proceed with local cleanup even if server call fails
    } finally {
      endImpersonation();
      setLoading(false);
      navigate('/admin');
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 2000,
        background: '#fffbe6',
        borderBottom: '2px solid #faad14',
        padding: '8px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 44,
      }}
    >
      <Space size="small">
        <EyeOutlined style={{ color: '#d48806', fontSize: 16 }} />
        <Text style={{ color: '#614700' }}>
          Viewing as{' '}
          <Text strong style={{ color: '#614700' }}>
            {impersonatedUser.fullName || impersonatedUser.email}
          </Text>
          {' '}
          <Text style={{ color: '#8c6800', fontSize: 12 }}>
            ({impersonatedUser.email})
          </Text>
          {' — '}
          <Text style={{ color: '#8c6800', fontSize: 12 }}>
            Read-only troubleshooting session · 30 min limit
          </Text>
        </Text>
      </Space>
      <Button
        size="small"
        danger
        icon={loading ? <LoadingOutlined /> : <CloseCircleOutlined />}
        onClick={handleExit}
        loading={loading}
        style={{ borderColor: '#faad14', color: '#d48806', background: 'transparent' }}
      >
        Exit Impersonation
      </Button>
    </div>
  );
};
