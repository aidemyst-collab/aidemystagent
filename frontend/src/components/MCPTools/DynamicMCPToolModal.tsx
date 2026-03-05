import { useEffect, useState } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  message,
  Space,
  Collapse,
  Switch,
  InputNumber,
  Divider,
  Typography,
} from 'antd';
import { PlusOutlined, DeleteOutlined, ApiOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import {
  mcpToolService,
  type DynamicMCPTool,
  type DynamicMCPToolCreateRequest,
  type ToolParameter,
} from '../../features/mcp-tools/mcpToolService';
import { apiClient } from '../../services/api';

const { TextArea } = Input;
const { Panel } = Collapse;
const { Text } = Typography;

interface DynamicMCPToolModalProps {
  visible: boolean;
  onClose: () => void;
  editingTool?: DynamicMCPTool | null;
}

interface Credential {
  id: string;
  name: string;
  provider: string;
}

interface KeyValuePair {
  key: string;
  value: string;
}

export const DynamicMCPToolModal = ({
  visible,
  onClose,
  editingTool,
}: DynamicMCPToolModalProps) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const isEditing = !!editingTool;

  // Local state for dynamic arrays
  const [parameters, setParameters] = useState<ToolParameter[]>([]);
  const [headers, setHeaders] = useState<KeyValuePair[]>([]);
  const [queryParams, setQueryParams] = useState<KeyValuePair[]>([]);

  // Fetch credentials for dropdown
  const { data: credentialsData } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => apiClient.get<{ credentials: Credential[] }>('/credentials'),
    enabled: visible,
  });

  // Reset form when modal opens/closes or editingTool changes
  useEffect(() => {
    if (visible) {
      if (editingTool) {
        form.setFieldsValue({
          name: editingTool.name,
          description: editingTool.description,
          api_endpoint: editingTool.api_endpoint,
          method: editingTool.method,
          credential_id: editingTool.credential_id || undefined,
          response_path: editingTool.response_path || '',
          response_template: editingTool.response_template || '',
          timeout_seconds: editingTool.timeout_seconds,
          body_template: editingTool.body_template
            ? JSON.stringify(editingTool.body_template, null, 2)
            : '',
        });

        // Set parameters
        setParameters(editingTool.parameters || []);

        // Set headers
        if (editingTool.headers && Object.keys(editingTool.headers).length > 0) {
          setHeaders(
            Object.entries(editingTool.headers).map(([key, value]) => ({
              key,
              value,
            }))
          );
        } else {
          setHeaders([]);
        }

        // Set query params
        if (editingTool.query_params && Object.keys(editingTool.query_params).length > 0) {
          setQueryParams(
            Object.entries(editingTool.query_params).map(([key, value]) => ({
              key,
              value,
            }))
          );
        } else {
          setQueryParams([]);
        }
      } else {
        form.resetFields();
        form.setFieldsValue({
          method: 'GET',
          timeout_seconds: 30,
        });
        setParameters([]);
        setHeaders([]);
        setQueryParams([]);
      }
    }
  }, [visible, editingTool, form]);

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: DynamicMCPToolCreateRequest) => mcpToolService.createTool(data),
    onSuccess: () => {
      message.success('Dynamic MCP tool created successfully');
      queryClient.invalidateQueries({ queryKey: ['dynamic-mcp-tools'] });
      onClose();
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to create tool');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      mcpToolService.updateTool(id, data),
    onSuccess: () => {
      message.success('Dynamic MCP tool updated successfully');
      queryClient.invalidateQueries({ queryKey: ['dynamic-mcp-tools'] });
      onClose();
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to update tool');
    },
  });

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Build headers object
      const headersObj = headers.reduce((acc, h) => {
        if (h.key && h.value) acc[h.key] = h.value;
        return acc;
      }, {} as Record<string, string>);

      // Build query params object
      const queryParamsObj = queryParams.reduce((acc, p) => {
        if (p.key && p.value) acc[p.key] = p.value;
        return acc;
      }, {} as Record<string, string>);

      // Parse body template
      let bodyTemplate = undefined;
      if (values.body_template) {
        try {
          bodyTemplate = JSON.parse(values.body_template);
        } catch (e) {
          message.error('Invalid JSON in body template');
          return;
        }
      }

      const data: DynamicMCPToolCreateRequest = {
        name: values.name,
        description: values.description,
        api_endpoint: values.api_endpoint,
        method: values.method,
        parameters: parameters,
        headers: Object.keys(headersObj).length > 0 ? headersObj : undefined,
        query_params: Object.keys(queryParamsObj).length > 0 ? queryParamsObj : undefined,
        body_template: bodyTemplate,
        credential_id: values.credential_id || undefined,
        response_path: values.response_path || undefined,
        response_template: values.response_template || undefined,
        timeout_seconds: values.timeout_seconds,
      };

      if (isEditing && editingTool) {
        updateMutation.mutate({ id: editingTool.id, data });
      } else {
        createMutation.mutate(data);
      }
    } catch (error) {
      // Form validation error
    }
  };

  // Parameter management
  const addParameter = () => {
    setParameters([
      ...parameters,
      { name: '', type: 'string', description: '', required: false },
    ]);
  };

  const removeParameter = (index: number) => {
    setParameters(parameters.filter((_, i) => i !== index));
  };

  const updateParameter = (index: number, field: keyof ToolParameter, value: any) => {
    const updated = [...parameters];
    updated[index] = { ...updated[index], [field]: value };
    setParameters(updated);
  };

  // Headers management
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

  // Query params management
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

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      title={
        <Space>
          <ApiOutlined />
          {isEditing ? 'Edit Dynamic MCP Tool' : 'Create Dynamic MCP Tool'}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      okText={isEditing ? 'Save Changes' : 'Create Tool'}
      confirmLoading={isLoading}
      width={800}
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        {/* Basic Info */}
        <Form.Item
          name="name"
          label="Tool Name"
          rules={[
            { required: true, message: 'Please enter a tool name' },
            {
              pattern: /^[a-z_][a-z0-9_-]*$/,
              message: 'Use lowercase letters, numbers, underscores, and hyphens only',
            },
          ]}
          extra="This name will be used by agents to call this tool"
        >
          <Input placeholder="e.g., get_weather, search_products" />
        </Form.Item>

        <Form.Item
          name="description"
          label="Description"
          rules={[{ required: true, message: 'Please enter a description' }]}
          extra="Describe what this tool does - this helps the LLM understand when to use it"
        >
          <TextArea
            rows={2}
            placeholder="e.g., Retrieves current weather data for a given city"
          />
        </Form.Item>

        <Divider>API Configuration</Divider>

        <Form.Item
          name="api_endpoint"
          label="API Endpoint"
          rules={[
            { required: true, message: 'Please enter the API endpoint' },
            {
              pattern: /^https?:\/\/.+/,
              message: 'URL must start with http:// or https://',
            },
          ]}
          extra="Use {parameter_name} for path parameters (e.g., /users/{user_id})"
        >
          <Input placeholder="https://api.example.com/v1/endpoint" />
        </Form.Item>

        <Space size="large" style={{ display: 'flex' }}>
          <Form.Item
            name="method"
            label="HTTP Method"
            rules={[{ required: true }]}
            style={{ width: 150 }}
          >
            <Select>
              <Select.Option value="GET">GET</Select.Option>
              <Select.Option value="POST">POST</Select.Option>
              <Select.Option value="PUT">PUT</Select.Option>
              <Select.Option value="PATCH">PATCH</Select.Option>
              <Select.Option value="DELETE">DELETE</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="timeout_seconds"
            label="Timeout (seconds)"
            style={{ width: 150 }}
          >
            <InputNumber min={1} max={300} />
          </Form.Item>

          <Form.Item
            name="credential_id"
            label="Authentication"
            style={{ flex: 1 }}
            extra="Select a credential for API authentication"
          >
            <Select allowClear placeholder="No authentication">
              {(credentialsData?.credentials || []).map((cred) => (
                <Select.Option key={cred.id} value={cred.id}>
                  {cred.name} ({cred.provider})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Space>

        <Divider>Tool Parameters</Divider>
        <Text type="secondary" className="mb-4 block">
          Define the parameters that agents can provide when calling this tool
        </Text>

        <Space direction="vertical" style={{ width: '100%' }} className="mb-4">
          {parameters.map((param, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                gap: '8px',
                alignItems: 'flex-start',
                background: '#f5f5f5',
                padding: '8px',
                borderRadius: '4px',
              }}
            >
              <Input
                placeholder="Name"
                value={param.name}
                onChange={(e) => updateParameter(index, 'name', e.target.value)}
                style={{ width: '120px' }}
              />
              <Select
                value={param.type}
                onChange={(value) => updateParameter(index, 'type', value)}
                style={{ width: '100px' }}
              >
                <Select.Option value="string">String</Select.Option>
                <Select.Option value="number">Number</Select.Option>
                <Select.Option value="integer">Integer</Select.Option>
                <Select.Option value="boolean">Boolean</Select.Option>
                <Select.Option value="array">Array</Select.Option>
                <Select.Option value="object">Object</Select.Option>
              </Select>
              <Input
                placeholder="Description"
                value={param.description}
                onChange={(e) => updateParameter(index, 'description', e.target.value)}
                style={{ flex: 1 }}
              />
              <Switch
                checkedChildren="Required"
                unCheckedChildren="Optional"
                checked={param.required}
                onChange={(checked) => updateParameter(index, 'required', checked)}
              />
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

        <Collapse ghost>
          <Panel header="Advanced Configuration" key="advanced">
            {/* Headers */}
            <Form.Item label="Custom Headers">
              <Space direction="vertical" style={{ width: '100%' }}>
                {headers.map((header, index) => (
                  <div key={index} style={{ display: 'flex', gap: '8px' }}>
                    <Input
                      placeholder="Header name"
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

            {/* Query Params */}
            <Form.Item label="Static Query Parameters">
              <Space direction="vertical" style={{ width: '100%' }}>
                {queryParams.map((param, index) => (
                  <div key={index} style={{ display: 'flex', gap: '8px' }}>
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

            {/* Body Template */}
            <Form.Item
              name="body_template"
              label="Request Body Template (JSON)"
              extra="Template for POST/PUT/PATCH requests. Use parameter names as placeholders."
            >
              <TextArea
                rows={4}
                placeholder='{"query": "{search_term}", "limit": 10}'
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>

            {/* Response Path */}
            <Form.Item
              name="response_path"
              label="Response JSON Path"
              extra="Extract specific data from response (e.g., 'data.items')"
            >
              <Input placeholder="data.items" />
            </Form.Item>
          </Panel>
        </Collapse>
      </Form>
    </Modal>
  );
};
