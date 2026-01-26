import { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Button, message, Space, Tabs } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../features/auth/authStore';

const { TextArea } = Input;
const { Option } = Select;

interface ToolCreationModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialData?: any;
  preSelectedType?: string | null;
}

interface ParameterField {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default?: string;
}

interface KeyValuePair {
  key: string;
  value: string;
}

export const ToolCreationModal = ({ visible, onClose, onSuccess, initialData, preSelectedType }: ToolCreationModalProps) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [toolType, setToolType] = useState<string>(preSelectedType || 'custom');
  const [parameters, setParameters] = useState<ParameterField[]>([]);
  const [headers, setHeaders] = useState<KeyValuePair[]>([]);
  const [queryParams, setQueryParams] = useState<KeyValuePair[]>([]);

  // Update toolType when preSelectedType changes
  useEffect(() => {
    if (preSelectedType) {
      setToolType(preSelectedType);
      form.setFieldsValue({ tool_type: preSelectedType });
    }
  }, [preSelectedType, form]);

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      const config: any = {
        parameters: parameters.reduce((acc, param) => {
          acc[param.name] = {
            type: param.type,
            description: param.description,
            required: param.required,
          };
          if (param.default) {
            acc[param.name].default = param.default;
          }
          return acc;
        }, {} as any),
      };

      if (toolType === 'api') {
        const headersObj = headers.reduce((acc, h) => {
          if (h.key && h.value) acc[h.key] = h.value;
          return acc;
        }, {} as Record<string, string>);

        const queryParamsObj = queryParams.reduce((acc, p) => {
          if (p.key && p.value) acc[p.key] = p.value;
          return acc;
        }, {} as Record<string, string>);

        config.api = {
          endpoint: values.api_endpoint,
          method: values.api_method,
          auth_type: values.auth_type,
          token: values.auth_token || '',
          headers: headersObj,
          query_params: queryParamsObj,
          body: values.request_body ? JSON.parse(values.request_body) : undefined,
          timeout: values.timeout || 30,
        };
      } else if (toolType === 'custom') {
        config.language = values.language;
        config.code = values.code;
      }

      const payload = {
        name: values.name,
        description: values.description,
        type: toolType,
        config,
        visibility: values.visibility || 'private',
      };

      const { tokens } = useAuthStore.getState();
      const response = await fetch('/api/v1/tools', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${tokens?.accessToken}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Failed to create tool');
      }

      message.success('Tool created successfully');
      form.resetFields();
      setParameters([]);
      setHeaders([]);
      setQueryParams([]);
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Error creating tool:', error);
      message.error('Failed to create tool');
    } finally {
      setLoading(false);
    }
  };

  const addParameter = () => {
    setParameters([
      ...parameters,
      { name: '', type: 'string', description: '', required: false },
    ]);
  };

  const removeParameter = (index: number) => {
    setParameters(parameters.filter((_, i) => i !== index));
  };

  const updateParameter = (index: number, field: keyof ParameterField, value: any) => {
    const updated = [...parameters];
    updated[index] = { ...updated[index], [field]: value };
    setParameters(updated);
  };

  const addHeader = () => {
    setHeaders([...headers, { key: '', value: '' }]);
  };

  const removeHeader = (index: number) => {
    setHeaders(headers.filter((_, i) => i !== index));
  };

  const updateHeader = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...headers];
    updated[index] = { ...updated[index], [field]: value };
    setHeaders(updated);
  };

  const addQueryParam = () => {
    setQueryParams([...queryParams, { key: '', value: '' }]);
  };

  const removeQueryParam = (index: number) => {
    setQueryParams(queryParams.filter((_, i) => i !== index));
  };

  const updateQueryParam = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...queryParams];
    updated[index] = { ...updated[index], [field]: value };
    setQueryParams(updated);
  };

  const renderCustomToolForm = () => (
    <>
      <Form.Item
        label="Language"
        name="language"
        rules={[{ required: true, message: 'Please select a language' }]}
      >
        <Select placeholder="Select programming language">
          <Option value="python">Python</Option>
          <Option value="javascript">JavaScript</Option>
          <Option value="typescript">TypeScript</Option>
        </Select>
      </Form.Item>

      <Form.Item
        label="Code"
        name="code"
        rules={[{ required: true, message: 'Please enter the tool code' }]}
        tooltip="Write the function that will execute when this tool is called"
      >
        <TextArea
          rows={8}
          placeholder="def execute(params):&#10;    # Your tool logic here&#10;    return {'result': 'success'}"
          style={{ fontFamily: 'monospace' }}
        />
      </Form.Item>
    </>
  );

  const renderAPIToolForm = () => (
    <>
      <Form.Item
        label="API Endpoint"
        name="api_endpoint"
        rules={[{ required: true, message: 'Please enter the API endpoint' }]}
      >
        <Input placeholder="https://api.example.com/endpoint" />
      </Form.Item>

      <Form.Item
        label="HTTP Method"
        name="api_method"
        rules={[{ required: true, message: 'Please select HTTP method' }]}
        initialValue="GET"
      >
        <Select placeholder="Select HTTP method">
          <Option value="GET">GET</Option>
          <Option value="POST">POST</Option>
          <Option value="PUT">PUT</Option>
          <Option value="DELETE">DELETE</Option>
          <Option value="PATCH">PATCH</Option>
        </Select>
      </Form.Item>

      <Form.Item
        label="Authentication Type"
        name="auth_type"
        rules={[{ required: true, message: 'Please select authentication type' }]}
        initialValue="none"
      >
        <Select placeholder="Select authentication type">
          <Option value="none">None</Option>
          <Option value="api_key">API Key</Option>
          <Option value="bearer">Bearer Token</Option>
          <Option value="basic">Basic Auth</Option>
        </Select>
      </Form.Item>

      <Form.Item
        label="Authentication Token"
        name="auth_token"
        tooltip="API key, bearer token, or base64 encoded credentials for basic auth"
      >
        <Input.Password placeholder="Enter your token or credentials" />
      </Form.Item>

      <Form.Item label="Headers" tooltip="Add custom HTTP headers">
        <Space direction="vertical" style={{ width: '100%' }}>
          {headers.map((header, index) => (
            <div key={index} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Input
                placeholder="Header name (e.g., Content-Type)"
                value={header.key}
                onChange={(e) => updateHeader(index, 'key', e.target.value)}
                style={{ flex: 1 }}
              />
              <Input
                placeholder="Header value"
                value={header.value}
                onChange={(e) => updateHeader(index, 'value', e.target.value)}
                style={{ flex: 1 }}
              />
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => removeHeader(index)}
              />
            </div>
          ))}
          <Button type="dashed" onClick={addHeader} icon={<PlusOutlined />} block>
            Add Header
          </Button>
        </Space>
      </Form.Item>

      <Form.Item label="Query Parameters" tooltip="Add URL query parameters">
        <Space direction="vertical" style={{ width: '100%' }}>
          {queryParams.map((param, index) => (
            <div key={index} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Input
                placeholder="Parameter name"
                value={param.key}
                onChange={(e) => updateQueryParam(index, 'key', e.target.value)}
                style={{ flex: 1 }}
              />
              <Input
                placeholder="Parameter value"
                value={param.value}
                onChange={(e) => updateQueryParam(index, 'value', e.target.value)}
                style={{ flex: 1 }}
              />
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => removeQueryParam(index)}
              />
            </div>
          ))}
          <Button type="dashed" onClick={addQueryParam} icon={<PlusOutlined />} block>
            Add Query Parameter
          </Button>
        </Space>
      </Form.Item>

      <Form.Item
        label="Request Body (JSON)"
        name="request_body"
        tooltip="Request body for POST, PUT, PATCH methods"
      >
        <TextArea
          rows={6}
          placeholder='{"key": "value"}'
          style={{ fontFamily: 'monospace' }}
        />
      </Form.Item>

      <Form.Item
        label="Timeout (seconds)"
        name="timeout"
        initialValue={30}
        tooltip="Request timeout in seconds"
      >
        <Input type="number" min={1} max={300} placeholder="30" />
      </Form.Item>
    </>
  );

  const renderMCPToolForm = () => (
    <>
      <Form.Item
        label="MCP Type"
        name="mcp_type"
        rules={[{ required: true, message: 'Please select MCP type' }]}
      >
        <Select placeholder="Select MCP type">
          <Option value="resource">Resource</Option>
          <Option value="prompt">Prompt</Option>
          <Option value="tool">Tool</Option>
        </Select>
      </Form.Item>

      <Form.Item
        label="Resource URI"
        name="resource_uri"
        rules={[{ required: true, message: 'Please enter resource URI' }]}
        tooltip="The URI pattern for this resource (e.g., file:///, db://)"
      >
        <Input placeholder="file:///path/to/resource" />
      </Form.Item>

      <Form.Item
        label="MCP Server URL"
        name="mcp_server_url"
        tooltip="Optional custom MCP server URL"
      >
        <Input placeholder="http://localhost:3000/mcp" />
      </Form.Item>
    </>
  );

  const getModalTitle = () => {
    if (initialData) return 'Edit Tool';
    if (preSelectedType === 'custom') return 'Create Custom Code Tool';
    if (preSelectedType === 'api') return 'Create API Integration Tool';
    if (preSelectedType === 'mcp') return 'Create MCP Tool';
    return 'Create New Tool';
  };

  return (
    <Modal
      title={getModalTitle()}
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={initialData || { visibility: 'private' }}
      >
        <Form.Item
          label="Tool Name"
          name="name"
          rules={[
            { required: true, message: 'Please enter tool name' },
            { pattern: /^[a-z_][a-z0-9_]*$/, message: 'Use lowercase, numbers, and underscores only' },
          ]}
        >
          <Input placeholder="my_custom_tool" />
        </Form.Item>

        <Form.Item
          label="Description"
          name="description"
          rules={[{ required: true, message: 'Please enter tool description' }]}
        >
          <TextArea rows={2} placeholder="Describe what this tool does" />
        </Form.Item>

        {!preSelectedType && (
          <Form.Item
            label="Tool Type"
            name="tool_type"
            rules={[{ required: true, message: 'Please select tool type' }]}
          >
            <Select placeholder="Select tool type" onChange={setToolType} value={toolType}>
              <Option value="custom">Custom Code</Option>
              <Option value="api">API Integration</Option>
              <Option value="mcp">MCP (Model Context Protocol)</Option>
            </Select>
          </Form.Item>
        )}

        {toolType === 'custom' && renderCustomToolForm()}
        {toolType === 'api' && renderAPIToolForm()}
        {toolType === 'mcp' && renderMCPToolForm()}

        <Form.Item label="Parameters">
          <Space direction="vertical" style={{ width: '100%' }}>
            {parameters.map((param, index) => (
              <div key={index} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                <Input
                  placeholder="Parameter name"
                  value={param.name}
                  onChange={(e) => updateParameter(index, 'name', e.target.value)}
                  style={{ width: '150px' }}
                />
                <Select
                  value={param.type}
                  onChange={(value) => updateParameter(index, 'type', value)}
                  style={{ width: '120px' }}
                >
                  <Option value="string">String</Option>
                  <Option value="number">Number</Option>
                  <Option value="boolean">Boolean</Option>
                  <Option value="array">Array</Option>
                  <Option value="object">Object</Option>
                </Select>
                <Input
                  placeholder="Description"
                  value={param.description}
                  onChange={(e) => updateParameter(index, 'description', e.target.value)}
                  style={{ flex: 1 }}
                />
                <Select
                  value={param.required}
                  onChange={(value) => updateParameter(index, 'required', value)}
                  style={{ width: '100px' }}
                >
                  <Option value={true}>Required</Option>
                  <Option value={false}>Optional</Option>
                </Select>
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => removeParameter(index)}
                />
              </div>
            ))}
            <Button type="dashed" onClick={addParameter} icon={<PlusOutlined />} block>
              Add Parameter
            </Button>
          </Space>
        </Form.Item>

        <Form.Item
          label="Visibility"
          name="visibility"
          rules={[{ required: true, message: 'Please select visibility' }]}
        >
          <Select placeholder="Select visibility">
            <Option value="private">Private (Only you)</Option>
            <Option value="organization">Organization</Option>
            <Option value="public">Public</Option>
          </Select>
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              {initialData ? 'Update Tool' : 'Create Tool'}
            </Button>
            <Button onClick={onClose}>Cancel</Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};
