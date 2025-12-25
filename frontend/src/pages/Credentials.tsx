import { useState, useEffect } from 'react';
import { Typography, Button, Table, Space, message, Popconfirm, Tag, Spin } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { credentialService, type Credential } from '../features/credentials/credentialService';
import { CredentialModal } from '../components/Credentials/CredentialModal';

const { Title } = Typography;

export const Credentials = () => {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingCredential, setEditingCredential] = useState<Credential | null>(null);

  useEffect(() => {
    fetchCredentials();
  }, []);

  const fetchCredentials = async () => {
    setLoading(true);
    try {
      const data = await credentialService.getCredentials();
      setCredentials(data.credentials || []);
    } catch (error) {
      console.error('Error fetching credentials:', error);
      message.error('Failed to load credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingCredential(null);
    setModalVisible(true);
  };

  const handleEdit = (credential: Credential) => {
    setEditingCredential(credential);
    setModalVisible(true);
  };

  const handleDelete = async (credentialId: string) => {
    try {
      await credentialService.deleteCredential(credentialId);
      message.success('Credential deleted successfully');
      fetchCredentials();
    } catch (error) {
      console.error('Error deleting credential:', error);
      message.error('Failed to delete credential');
    }
  };

  const handleModalSuccess = () => {
    fetchCredentials();
  };

  const getProviderColor = (provider: string): string => {
    const colors: Record<string, string> = {
      openai: 'green',
      anthropic: 'blue',
      google: 'orange',
      azure_openai: 'cyan',
      custom: 'purple',
    };
    return colors[provider] || 'default';
  };

  const getProviderLabel = (provider: string): string => {
    const labels: Record<string, string> = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      google: 'Google',
      azure_openai: 'Azure OpenAI',
      custom: 'Custom',
    };
    return labels[provider] || provider;
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      width: '25%',
    },
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
      width: '15%',
      render: (provider: string) => (
        <Tag color={getProviderColor(provider)}>
          {getProviderLabel(provider)}
        </Tag>
      ),
    },
    {
      title: 'API Key',
      dataIndex: 'api_key_preview',
      key: 'api_key_preview',
      width: '20%',
      render: (preview: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {preview}
        </span>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: '10%',
      render: (status: string) => (
        status === 'active' ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            Active
          </Tag>
        ) : (
          <Tag color="default">Inactive</Tag>
        )
      ),
    },
    {
      title: 'Last Used',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: '15%',
      render: (date: string | null) =>
        date ? new Date(date).toLocaleDateString() : 'Never',
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: '15%',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: '10%',
      render: (_: any, record: Credential) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="Delete Credential"
            description="Are you sure you want to delete this credential?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <Title level={2} className="mb-2">LLM Credentials</Title>
          <p className="text-gray-600">
            Manage your API keys for different LLM providers
          </p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
          size="large"
        >
          Add Credential
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={credentials}
        rowKey="id"
        pagination={{
          pageSize: 10,
          showTotal: (total) => `Total ${total} credentials`,
        }}
      />

      <CredentialModal
        visible={modalVisible}
        onClose={() => {
          setModalVisible(false);
          setEditingCredential(null);
        }}
        onSuccess={handleModalSuccess}
        initialData={editingCredential}
      />
    </div>
  );
};
