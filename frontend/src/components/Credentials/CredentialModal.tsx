import { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Button, message, Space, Alert } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import {
  credentialService,
  type Credential,
  type CredentialProvider,
} from '../../features/credentials/credentialService';

const { Option } = Select;

interface CredentialModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialData?: Credential | null;
}

export const CredentialModal = ({
  visible,
  onClose,
  onSuccess,
  initialData,
}: CredentialModalProps) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<CredentialProvider>('openai');
  const [credentialType, setCredentialType] = useState<'llm' | 'database' | 'voice' | 'whatsapp'>('llm');

  useEffect(() => {
    if (initialData) {
      // Determine credential type from provider
      const isDatabaseProvider = ['redis', 'postgresql', 'mongodb'].includes(initialData.provider);
      const isVoiceProvider = ['twilio', 'etisalat'].includes(initialData.provider);
      const isWhatsAppProvider = initialData.provider === 'whatsapp_meta';
      const credType = isDatabaseProvider ? 'database' : isVoiceProvider ? 'voice' : isWhatsAppProvider ? 'whatsapp' : 'llm';

      form.setFieldsValue({
        credential_type: credType,
        name: initialData.name,
        provider: initialData.provider,
        api_base: initialData.api_base,
        api_version: initialData.api_version,
        organization_key: initialData.organization_key,
      });
      setSelectedProvider(initialData.provider);
      setCredentialType(credType);
    } else {
      form.resetFields();
      setSelectedProvider('openai');
      setCredentialType('llm');
    }
    setTestResult(null);
  }, [initialData, form, visible]);

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      const isDatabase = ['redis', 'postgresql', 'mongodb'].includes(values.provider);
      const isVoice = ['twilio', 'etisalat'].includes(values.provider);
      const isWhatsApp = values.provider === 'whatsapp_meta';

      if (initialData) {
        // Update existing credential
        const updateData: any = {
          name: values.name,
        };

        if (isWhatsApp) {
          // Build connection config for WhatsApp credentials
          const connectionConfig: Record<string, any> = {};
          connectionConfig.phone_number_id = values.phone_number_id;
          connectionConfig.access_token = values.whatsapp_access_token;
          if (values.business_account_id) connectionConfig.business_account_id = values.business_account_id;
          if (values.app_secret) connectionConfig.app_secret = values.app_secret;

          updateData.connection_config = connectionConfig;
        } else if (isVoice) {
          // Build connection config for voice credentials
          const connectionConfig: Record<string, any> = {};

          if (values.provider === 'twilio') {
            connectionConfig.account_sid = values.account_sid;
            connectionConfig.auth_token = values.auth_token;
            if (values.phone_number) connectionConfig.phone_number = values.phone_number;
          } else if (values.provider === 'etisalat') {
            connectionConfig.api_key = values.etisalat_api_key;
            connectionConfig.account_id = values.account_id;
            if (values.api_secret) connectionConfig.api_secret = values.api_secret;
            if (values.sender_id) connectionConfig.sender_id = values.sender_id;
            if (values.webhook_secret) connectionConfig.webhook_secret = values.webhook_secret;
          }

          updateData.connection_config = connectionConfig;
        } else if (isDatabase) {
          // Build connection config for database credentials
          const connectionConfig: Record<string, any> = {};

          if (values.provider === 'redis') {
            connectionConfig.host = values.host;
            connectionConfig.port = values.port;
            if (values.password) connectionConfig.password = values.password;
            connectionConfig.database = values.database || 0;
          } else if (values.provider === 'postgresql') {
            if (values.connection_string) {
              connectionConfig.connection_string = values.connection_string;
            } else {
              if (values.host) connectionConfig.host = values.host;
              if (values.port) connectionConfig.port = values.port;
              if (values.database) connectionConfig.database = values.database;
              if (values.username) connectionConfig.username = values.username;
              if (values.password) connectionConfig.password = values.password;
            }
          } else if (values.provider === 'mongodb') {
            connectionConfig.connection_uri = values.connection_uri;
            connectionConfig.database = values.database;
            if (values.collection) connectionConfig.collection = values.collection;
          }

          updateData.connection_config = connectionConfig;
        } else {
          // LLM credential
          if (values.api_key) updateData.api_key = values.api_key;
          updateData.api_base = values.api_base;
          updateData.api_version = values.api_version;
          updateData.organization_key = values.organization_key;
        }

        await credentialService.updateCredential(initialData.id, updateData);
        message.success('Credential updated successfully');
      } else {
        // Create new credential
        const createData: any = {
          name: values.name,
          provider: values.provider,
        };

        if (isWhatsApp) {
          // Build connection config for WhatsApp credentials
          const connectionConfig: Record<string, any> = {};
          connectionConfig.phone_number_id = values.phone_number_id;
          connectionConfig.access_token = values.whatsapp_access_token;
          if (values.business_account_id) connectionConfig.business_account_id = values.business_account_id;
          if (values.app_secret) connectionConfig.app_secret = values.app_secret;

          createData.connection_config = connectionConfig;
        } else if (isVoice) {
          // Build connection config for voice credentials
          const connectionConfig: Record<string, any> = {};

          if (values.provider === 'twilio') {
            connectionConfig.account_sid = values.account_sid;
            connectionConfig.auth_token = values.auth_token;
            if (values.phone_number) connectionConfig.phone_number = values.phone_number;
          } else if (values.provider === 'etisalat') {
            connectionConfig.api_key = values.etisalat_api_key;
            connectionConfig.account_id = values.account_id;
            if (values.api_secret) connectionConfig.api_secret = values.api_secret;
            if (values.sender_id) connectionConfig.sender_id = values.sender_id;
            if (values.webhook_secret) connectionConfig.webhook_secret = values.webhook_secret;
          }

          createData.connection_config = connectionConfig;
        } else if (isDatabase) {
          // Build connection config for database credentials
          const connectionConfig: Record<string, any> = {};

          if (values.provider === 'redis') {
            connectionConfig.host = values.host;
            connectionConfig.port = values.port;
            if (values.password) connectionConfig.password = values.password;
            connectionConfig.database = values.database || 0;
          } else if (values.provider === 'postgresql') {
            if (values.connection_string) {
              connectionConfig.connection_string = values.connection_string;
            } else {
              connectionConfig.host = values.host;
              connectionConfig.port = values.port;
              connectionConfig.database = values.database;
              connectionConfig.username = values.username;
              connectionConfig.password = values.password;
            }
          } else if (values.provider === 'mongodb') {
            connectionConfig.connection_uri = values.connection_uri;
            connectionConfig.database = values.database;
            if (values.collection) connectionConfig.collection = values.collection;
          }

          createData.connection_config = connectionConfig;
        } else {
          // LLM credential
          createData.api_key = values.api_key;
          createData.api_base = values.api_base;
          createData.api_version = values.api_version;
          createData.organization_key = values.organization_key;
        }

        await credentialService.createCredential(createData);
        message.success('Credential created successfully');
      }

      form.resetFields();
      setTestResult(null);
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Error saving credential:', error);
      message.error(error.response?.data?.detail || 'Failed to save credential');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    try {
      const values = form.getFieldsValue();
      const isDatabase = ['redis', 'postgresql', 'mongodb'].includes(values.provider);

      setTesting(true);
      setTestResult(null);

      const testData: any = {
        provider: values.provider,
      };

      // If editing an existing credential and no new values provided, use stored credential
      if (initialData && !values.api_key && !isDatabase) {
        testData.credential_id = initialData.id;
      } else if (initialData && isDatabase && !values.host && !values.connection_string && !values.connection_uri) {
        testData.credential_id = initialData.id;
      } else {
        // Validate required fields for new credentials or when values are provided
        if (isDatabase) {
          await form.validateFields(['provider']);
        } else {
          // For LLM credentials, API key is required for testing
          if (!values.api_key) {
            message.error('Please enter the API key to test the connection');
            setTesting(false);
            return;
          }
          await form.validateFields(['provider', 'api_key']);
        }
      }

      // Only build config if not using stored credential
      if (!testData.credential_id) {
        if (isDatabase) {
          // Build connection config for database credentials
          const connectionConfig: Record<string, any> = {};

          if (values.provider === 'redis') {
            connectionConfig.host = values.host;
            connectionConfig.port = values.port;
            if (values.password) connectionConfig.password = values.password;
            connectionConfig.database = values.database || 0;
          } else if (values.provider === 'postgresql') {
            if (values.connection_string) {
              connectionConfig.connection_string = values.connection_string;
            } else {
              connectionConfig.host = values.host;
              connectionConfig.port = values.port;
              connectionConfig.database = values.database;
              connectionConfig.username = values.username;
              connectionConfig.password = values.password;
            }
          } else if (values.provider === 'mongodb') {
            connectionConfig.connection_uri = values.connection_uri;
            connectionConfig.database = values.database;
            if (values.collection) connectionConfig.collection = values.collection;
          }

          testData.connection_config = connectionConfig;
        } else {
          // LLM credential
          testData.api_key = values.api_key;
          testData.api_base = values.api_base;
          testData.api_version = values.api_version;
        }
      }

      const result = await credentialService.testCredential(testData);

      setTestResult(result);

      if (result.success) {
        message.success('Credential test successful');
      } else {
        message.error('Credential test failed');
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.error('Please fill in required fields first');
      } else {
        console.error('Error testing credential:', error);
        message.error('Failed to test credential');
        setTestResult({ success: false, message: 'Failed to test credential' });
      }
    } finally {
      setTesting(false);
    }
  };

  const showApiBaseField = () => {
    return selectedProvider === 'azure_openai' || selectedProvider === 'custom';
  };

  const showApiVersionField = () => {
    return selectedProvider === 'azure_openai';
  };

  const showOrganizationKeyField = () => {
    return selectedProvider === 'openai';
  };

  return (
    <Modal
      title={initialData ? 'Edit Credential' : 'Add New Credential'}
      open={visible}
      onCancel={onClose}
      width={600}
      footer={null}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{ provider: 'openai' }}
      >
        <Form.Item
          label="Credential Type"
          name="credential_type"
          rules={[{ required: true, message: 'Please select credential type' }]}
          initialValue="llm"
        >
          <Select
            placeholder="Select credential type"
            onChange={(value) => setCredentialType(value as 'llm' | 'database' | 'voice')}
            disabled={!!initialData}
          >
            <Option value="llm">LLM Provider (OpenAI, Anthropic, etc.)</Option>
            <Option value="database">Storage/Database (Redis, PostgreSQL, MongoDB)</Option>
            <Option value="voice">Voice Provider (Twilio, Etisalat)</Option>
            <Option value="whatsapp">WhatsApp (Meta Cloud API)</Option>
          </Select>
        </Form.Item>

        <Form.Item
          label="Credential Name"
          name="name"
          rules={[
            { required: true, message: 'Please enter a name for this credential' },
          ]}
        >
          <Input placeholder={
            credentialType === 'llm' ? 'e.g., My OpenAI Key' :
            credentialType === 'voice' ? 'e.g., Production Twilio' :
            credentialType === 'whatsapp' ? 'e.g., Production WhatsApp' :
            'e.g., Production Redis'
          } />
        </Form.Item>

        <Form.Item
          label={
            credentialType === 'llm' ? 'LLM Provider' :
            credentialType === 'voice' ? 'Voice Provider' :
            credentialType === 'whatsapp' ? 'WhatsApp Provider' :
            'Storage Type'
          }
          name="provider"
          rules={[{ required: true, message: 'Please select a provider' }]}
        >
          <Select
            placeholder={
              credentialType === 'llm' ? 'Select LLM provider' :
              credentialType === 'voice' ? 'Select voice provider' :
              credentialType === 'whatsapp' ? 'Select WhatsApp provider' :
              'Select storage type'
            }
            onChange={(value) => setSelectedProvider(value as CredentialProvider)}
            disabled={!!initialData}
          >
            {credentialType === 'llm' ? (
              <>
                <Option value="openai">OpenAI</Option>
                <Option value="anthropic">Anthropic</Option>
                <Option value="google">Google (Gemini)</Option>
                <Option value="azure_openai">Azure OpenAI</Option>
                <Option value="custom">Custom</Option>
              </>
            ) : credentialType === 'voice' ? (
              <>
                <Option value="twilio">Twilio</Option>
                <Option value="etisalat">Etisalat CPaaS (e&)</Option>
              </>
            ) : credentialType === 'whatsapp' ? (
              <>
                <Option value="whatsapp_meta">Meta Cloud API</Option>
              </>
            ) : (
              <>
                <Option value="redis">Redis</Option>
                <Option value="postgresql">PostgreSQL</Option>
                <Option value="mongodb">MongoDB</Option>
              </>
            )}
          </Select>
        </Form.Item>

        {credentialType === 'llm' ? (
          <Form.Item
            label="API Key"
            name="api_key"
            rules={[
              { required: !initialData, message: 'Please enter your API key' },
              { min: 10, message: 'API key must be at least 10 characters' },
            ]}
            tooltip={initialData ? 'Leave empty to keep existing key' : undefined}
            help={initialData ? 'You can test with the stored key or enter a new one' : undefined}
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>
        ) : credentialType === 'voice' ? (
          <>
            {/* Voice Provider Fields */}
            {selectedProvider === 'twilio' && (
              <>
                <Alert
                  message="Find your Twilio credentials in the Twilio Console under Account > API Keys & Tokens"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Form.Item
                  label="Account SID"
                  name="account_sid"
                  rules={[{ required: true, message: 'Please enter your Twilio Account SID' }]}
                  tooltip="Found on your Twilio Console dashboard"
                >
                  <Input placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
                </Form.Item>
                <Form.Item
                  label="Auth Token"
                  name="auth_token"
                  rules={[{ required: true, message: 'Please enter your Twilio Auth Token' }]}
                  tooltip="Found on your Twilio Console dashboard"
                >
                  <Input.Password placeholder="Your Twilio Auth Token" />
                </Form.Item>
                <Form.Item
                  label="Phone Number (Optional)"
                  name="phone_number"
                  tooltip="Your Twilio phone number for outbound calls"
                >
                  <Input placeholder="+1234567890" />
                </Form.Item>
              </>
            )}

            {selectedProvider === 'etisalat' && (
              <>
                <Alert
                  message="Get your Etisalat CPaaS credentials from the e& enterprise engageX Nexus portal"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Form.Item
                  label="API Key"
                  name="etisalat_api_key"
                  rules={[{ required: true, message: 'Please enter your Etisalat API Key' }]}
                  tooltip="Your Etisalat CPaaS API key"
                >
                  <Input.Password placeholder="Your Etisalat API Key" />
                </Form.Item>
                <Form.Item
                  label="Account ID"
                  name="account_id"
                  rules={[{ required: true, message: 'Please enter your Etisalat Account ID' }]}
                  tooltip="Your Etisalat CPaaS account identifier"
                >
                  <Input placeholder="Your Account ID" />
                </Form.Item>
                <Form.Item
                  label="API Secret (Optional)"
                  name="api_secret"
                  tooltip="Used for webhook signature validation"
                >
                  <Input.Password placeholder="Your API Secret" />
                </Form.Item>
                <Form.Item
                  label="Sender ID (Optional)"
                  name="sender_id"
                  tooltip="Your registered sender ID for outbound calls"
                >
                  <Input placeholder="Your Sender ID" />
                </Form.Item>
                <Form.Item
                  label="Webhook Secret (Optional)"
                  name="webhook_secret"
                  tooltip="Secret for validating incoming webhooks"
                >
                  <Input.Password placeholder="Webhook validation secret" />
                </Form.Item>
              </>
            )}
          </>
        ) : credentialType === 'whatsapp' ? (
          <>
            {/* WhatsApp Provider Fields */}
            {selectedProvider === 'whatsapp_meta' && (
              <>
                <Alert
                  message="Get your credentials from the Meta Developer Dashboard under WhatsApp > Getting Started"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Form.Item
                  label="Phone Number ID"
                  name="phone_number_id"
                  rules={[{ required: true, message: 'Please enter your WhatsApp Phone Number ID' }]}
                  tooltip="Found in Meta Developer Dashboard under WhatsApp > Getting Started"
                >
                  <Input placeholder="1234567890123456" />
                </Form.Item>
                <Form.Item
                  label="Access Token"
                  name="whatsapp_access_token"
                  rules={[{ required: true, message: 'Please enter your Access Token' }]}
                  tooltip="Permanent token from System User or temporary token from dashboard"
                >
                  <Input.Password placeholder="EAAxxxxxxx..." />
                </Form.Item>
                <Form.Item
                  label="Business Account ID (Optional)"
                  name="business_account_id"
                  tooltip="Required for template management"
                >
                  <Input placeholder="1234567890123456" />
                </Form.Item>
                <Form.Item
                  label="App Secret (Optional)"
                  name="app_secret"
                  tooltip="Used for webhook signature validation - found in App Settings > Basic"
                >
                  <Input.Password placeholder="Your App Secret" />
                </Form.Item>
              </>
            )}
          </>
        ) : (
          <>
            {/* Database Connection Fields */}
            {selectedProvider === 'redis' && (
              <>
                <Form.Item
                  label="Host"
                  name="host"
                  rules={[{ required: true, message: 'Please enter Redis host' }]}
                >
                  <Input placeholder="localhost or redis.example.com" />
                </Form.Item>
                <Form.Item
                  label="Port"
                  name="port"
                  rules={[{ required: true, message: 'Please enter Redis port' }]}
                  initialValue={6379}
                >
                  <Input placeholder="6379" type="number" />
                </Form.Item>
                <Form.Item label="Password" name="password">
                  <Input.Password placeholder="Optional Redis password" />
                </Form.Item>
                <Form.Item
                  label="Database"
                  name="database"
                  initialValue={0}
                  tooltip="Redis database number (0-15)"
                >
                  <Input placeholder="0" type="number" />
                </Form.Item>
              </>
            )}

            {selectedProvider === 'postgresql' && (
              <>
                <Form.Item
                  label="Connection String"
                  name="connection_string"
                  rules={[{ required: true, message: 'Please enter PostgreSQL connection string' }]}
                  tooltip="Full PostgreSQL connection string"
                >
                  <Input.Password placeholder="postgresql://user:pass@host:5432/dbname" />
                </Form.Item>
                <Alert
                  message="Alternative: Enter individual fields below instead of connection string"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Form.Item label="Host" name="host">
                  <Input placeholder="localhost" />
                </Form.Item>
                <Form.Item label="Port" name="port" initialValue={5432}>
                  <Input placeholder="5432" type="number" />
                </Form.Item>
                <Form.Item label="Database" name="database">
                  <Input placeholder="conversations" />
                </Form.Item>
                <Form.Item label="Username" name="username">
                  <Input placeholder="postgres" />
                </Form.Item>
                <Form.Item label="Password" name="password">
                  <Input.Password placeholder="password" />
                </Form.Item>
              </>
            )}

            {selectedProvider === 'mongodb' && (
              <>
                <Form.Item
                  label="Connection URI"
                  name="connection_uri"
                  rules={[{ required: true, message: 'Please enter MongoDB connection URI' }]}
                  tooltip="Full MongoDB connection string"
                >
                  <Input.Password placeholder="mongodb://user:pass@host:27017/dbname" />
                </Form.Item>
                <Form.Item
                  label="Database"
                  name="database"
                  rules={[{ required: true, message: 'Please enter database name' }]}
                >
                  <Input placeholder="conversations" />
                </Form.Item>
                <Form.Item label="Collection" name="collection" initialValue="memory">
                  <Input placeholder="memory" />
                </Form.Item>
              </>
            )}
          </>
        )}

        {showApiBaseField() && (
          <Form.Item
            label="API Base URL"
            name="api_base"
            rules={[
              {
                required: selectedProvider === 'azure_openai',
                message: 'Please enter the API base URL',
              },
            ]}
          >
            <Input placeholder="https://your-resource.openai.azure.com" />
          </Form.Item>
        )}

        {showApiVersionField() && (
          <Form.Item
            label="API Version"
            name="api_version"
            rules={[{ required: true, message: 'Please enter the API version' }]}
          >
            <Input placeholder="2023-05-15" />
          </Form.Item>
        )}

        {showOrganizationKeyField() && (
          <Form.Item
            label="Organization ID (Optional)"
            name="organization_key"
            tooltip="Optional OpenAI organization ID"
          >
            <Input placeholder="org-..." />
          </Form.Item>
        )}

        {testResult && (
          <Alert
            message={testResult.success ? 'Test Successful' : 'Test Failed'}
            description={testResult.message}
            type={testResult.success ? 'success' : 'error'}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
            >
              {initialData ? 'Update' : 'Create'}
            </Button>
            <Button
              onClick={handleTest}
              loading={testing}
              icon={testing ? <LoadingOutlined /> : null}
            >
              Test Connection
            </Button>
            <Button onClick={onClose}>Cancel</Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};
