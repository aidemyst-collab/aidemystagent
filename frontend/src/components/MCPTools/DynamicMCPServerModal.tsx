import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Space,
  Card,
  Collapse,
  Table,
  Switch,
  InputNumber,
  message,
  Tooltip,
  Typography,
  Divider,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ApiOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  DynamicMCPServer,
  DynamicMCPTool,
  ServerCreateRequest,
  ServerUpdateRequest,
  ToolCreateRequest,
  ToolParameter,
  HTTPMethod,
  ParameterType,
  createEmptyTool,
  createEmptyParameter,
  dynamicMcpServerService,
} from '../../features/mcp-tools/dynamicMcpServerService';

const { TextArea } = Input;
const { Text, Title } = Typography;
const { Panel } = Collapse;

interface DynamicMCPServerModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  server?: DynamicMCPServer;  // If provided, edit mode
  credentials: { id: string; name: string }[];
}

const HTTP_METHODS: HTTPMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];
const PARAMETER_TYPES: ParameterType[] = ['string', 'number', 'integer', 'boolean', 'array', 'object'];

export const DynamicMCPServerModal: React.FC<DynamicMCPServerModalProps> = ({
  open,
  onClose,
  onSuccess,
  server,
  credentials,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [tools, setTools] = useState<ToolCreateRequest[]>([]);
  const [editingToolIndex, setEditingToolIndex] = useState<number | null>(null);
  const [activeKeys, setActiveKeys] = useState<string[]>([]);

  const isEditMode = !!server;

  // Initialize form with server data or defaults
  useEffect(() => {
    if (open) {
      if (server) {
        form.setFieldsValue({
          name: server.name,
          description: server.description || '',
          base_url: server.base_url,
          credential_id: server.credential_id,
          timeout_seconds: server.timeout_seconds,
          default_headers: server.default_headers
            ? JSON.stringify(server.default_headers, null, 2)
            : '{}',
        });
        // Convert existing tools to create request format
        setTools(server.tools.map(t => ({
          name: t.name,
          description: t.description,
          path: t.path,
          method: t.method,
          parameters: t.parameters || [],
          headers: t.headers || {},
          query_params: t.query_params || {},
          body_template: t.body_template || {},
          response_path: t.response_path,
        })));
      } else {
        form.resetFields();
        form.setFieldsValue({
          timeout_seconds: 30,
          default_headers: '{}',
        });
        setTools([]);
      }
      setEditingToolIndex(null);
      setActiveKeys([]);
    }
  }, [open, server, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // Parse headers JSON
      let defaultHeaders = {};
      try {
        defaultHeaders = JSON.parse(values.default_headers || '{}');
      } catch {
        message.error('Invalid JSON in default headers');
        setLoading(false);
        return;
      }

      if (isEditMode) {
        // Update server
        const updateData: ServerUpdateRequest = {
          name: values.name,
          description: values.description,
          base_url: values.base_url,
          credential_id: values.credential_id || undefined,
          default_headers: defaultHeaders,
          timeout_seconds: values.timeout_seconds,
        };
        await dynamicMcpServerService.updateServer(server!.id, updateData);

        // Note: Tools are managed separately in edit mode
        message.success('Provider updated successfully');
      } else {
        // Create server with tools
        const createData: ServerCreateRequest = {
          name: values.name,
          description: values.description,
          base_url: values.base_url,
          credential_id: values.credential_id || undefined,
          default_headers: defaultHeaders,
          timeout_seconds: values.timeout_seconds,
          tools: tools,
        };
        await dynamicMcpServerService.createServer(createData);
        message.success('Provider created successfully');
      }

      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Error saving provider:', error);
      message.error(error?.message || 'Failed to save provider');
    } finally {
      setLoading(false);
    }
  };

  // Tool management functions
  const addTool = () => {
    const newTool = createEmptyTool();
    setTools([...tools, newTool]);
    setEditingToolIndex(tools.length);
    setActiveKeys([...activeKeys, `tool-${tools.length}`]);
  };

  const updateTool = (index: number, updates: Partial<ToolCreateRequest>) => {
    const newTools = [...tools];
    newTools[index] = { ...newTools[index], ...updates };
    setTools(newTools);
  };

  const removeTool = (index: number) => {
    const newTools = tools.filter((_, i) => i !== index);
    setTools(newTools);
    if (editingToolIndex === index) {
      setEditingToolIndex(null);
    }
  };

  // Parameter management functions
  const addParameter = (toolIndex: number) => {
    const newTools = [...tools];
    const params = newTools[toolIndex].parameters || [];
    newTools[toolIndex].parameters = [...params, createEmptyParameter()];
    setTools(newTools);
  };

  const updateParameter = (
    toolIndex: number,
    paramIndex: number,
    updates: Partial<ToolParameter>
  ) => {
    const newTools = [...tools];
    const params = [...(newTools[toolIndex].parameters || [])];
    params[paramIndex] = { ...params[paramIndex], ...updates };
    newTools[toolIndex].parameters = params;
    setTools(newTools);
  };

  const removeParameter = (toolIndex: number, paramIndex: number) => {
    const newTools = [...tools];
    newTools[toolIndex].parameters = newTools[toolIndex].parameters?.filter(
      (_, i) => i !== paramIndex
    );
    setTools(newTools);
  };

  // Render tool editor
  const renderToolEditor = (tool: ToolCreateRequest, index: number) => {
    const paramColumns = [
      {
        title: 'Name',
        dataIndex: 'name',
        width: 120,
        render: (_: any, record: ToolParameter, paramIndex: number) => (
          <Input
            size="small"
            value={record.name}
            placeholder="param_name"
            onChange={(e) => updateParameter(index, paramIndex, { name: e.target.value })}
          />
        ),
      },
      {
        title: 'Type',
        dataIndex: 'type',
        width: 100,
        render: (_: any, record: ToolParameter, paramIndex: number) => (
          <Select
            size="small"
            value={record.type}
            style={{ width: '100%' }}
            onChange={(value) => updateParameter(index, paramIndex, { type: value })}
          >
            {PARAMETER_TYPES.map((t) => (
              <Select.Option key={t} value={t}>{t}</Select.Option>
            ))}
          </Select>
        ),
      },
      {
        title: 'Description',
        dataIndex: 'description',
        render: (_: any, record: ToolParameter, paramIndex: number) => (
          <Input
            size="small"
            value={record.description}
            placeholder="Parameter description"
            onChange={(e) => updateParameter(index, paramIndex, { description: e.target.value })}
          />
        ),
      },
      {
        title: 'Required',
        dataIndex: 'required',
        width: 80,
        render: (_: any, record: ToolParameter, paramIndex: number) => (
          <Switch
            size="small"
            checked={record.required}
            onChange={(checked) => updateParameter(index, paramIndex, { required: checked })}
          />
        ),
      },
      {
        title: '',
        width: 40,
        render: (_: any, __: any, paramIndex: number) => (
          <Button
            type="text"
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => removeParameter(index, paramIndex)}
          />
        ),
      },
    ];

    return (
      <div style={{ padding: '8px 0' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <Space style={{ width: '100%' }}>
            <Form.Item label="Name" style={{ marginBottom: 0, flex: 1 }}>
              <Input
                value={tool.name}
                placeholder="get_weather"
                onChange={(e) => updateTool(index, { name: e.target.value })}
              />
            </Form.Item>
            <Form.Item label="Method" style={{ marginBottom: 0, width: 100 }}>
              <Select
                value={tool.method}
                onChange={(value) => updateTool(index, { method: value })}
              >
                {HTTP_METHODS.map((m) => (
                  <Select.Option key={m} value={m}>{m}</Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item label="Path" style={{ marginBottom: 0, flex: 1 }}>
              <Input
                value={tool.path}
                placeholder="/endpoint or /users/{id}"
                onChange={(e) => updateTool(index, { path: e.target.value })}
              />
            </Form.Item>
          </Space>

          <Form.Item label="Description" style={{ marginBottom: 8 }}>
            <TextArea
              value={tool.description}
              placeholder="Describe what this tool does (used by LLM to decide when to use it)"
              rows={2}
              onChange={(e) => updateTool(index, { description: e.target.value })}
            />
          </Form.Item>

          <Divider orientation="left" plain style={{ margin: '8px 0' }}>
            Parameters
          </Divider>

          <Table
            size="small"
            dataSource={tool.parameters || []}
            columns={paramColumns}
            pagination={false}
            rowKey={(_, i) => `param-${i}`}
            locale={{ emptyText: 'No parameters defined' }}
          />

          <Button
            type="dashed"
            size="small"
            icon={<PlusOutlined />}
            onClick={() => addParameter(index)}
          >
            Add Parameter
          </Button>

          <Divider orientation="left" plain style={{ margin: '8px 0' }}>
            Response Path (Optional)
          </Divider>

          <Input
            value={tool.response_path}
            placeholder="data.items (JSON path to extract)"
            onChange={(e) => updateTool(index, { response_path: e.target.value })}
          />
        </Space>
      </div>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <ApiOutlined />
          {isEditMode ? 'Edit Tool Provider' : 'Create Tool Provider'}
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="cancel" onClick={onClose}>
          Cancel
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={loading}
          onClick={handleSubmit}
          icon={<ThunderboltOutlined />}
        >
          {isEditMode ? 'Update Provider' : 'Create Provider'}
        </Button>,
      ]}
    >
      <Form form={form} layout="vertical">
        {/* Provider Configuration */}
        <Card size="small" title="Provider Configuration" style={{ marginBottom: 16 }}>
          <Form.Item
            name="name"
            label="Provider Name"
            rules={[{ required: true, message: 'Please enter a provider name' }]}
          >
            <Input placeholder="Weather API" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={2} placeholder="API provider for weather data" />
          </Form.Item>

          <Form.Item
            name="base_url"
            label="Base URL"
            rules={[
              { required: true, message: 'Please enter the base URL' },
              { type: 'url', message: 'Please enter a valid URL' },
            ]}
            extra="All tool paths will be relative to this URL"
          >
            <Input placeholder="https://api.openweathermap.org/data/2.5" />
          </Form.Item>

          <Space style={{ width: '100%' }}>
            <Form.Item name="credential_id" label="Authentication" style={{ flex: 1 }}>
              <Select placeholder="Select credential (optional)" allowClear>
                {credentials.map((c) => (
                  <Select.Option key={c.id} value={c.id}>
                    {c.name}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="timeout_seconds"
              label="Timeout (seconds)"
              style={{ width: 150 }}
            >
              <InputNumber min={1} max={300} style={{ width: '100%' }} />
            </Form.Item>
          </Space>

          <Form.Item
            name="default_headers"
            label="Default Headers (JSON)"
          >
            <TextArea
              rows={2}
              placeholder='{"Content-Type": "application/json"}'
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
        </Card>

        {/* Tools Configuration */}
        <Card
          size="small"
          title={
            <Space>
              <span>Tools ({tools.length})</span>
            </Space>
          }
          extra={
            !isEditMode && (
              <Button type="primary" size="small" icon={<PlusOutlined />} onClick={addTool}>
                Add Tool
              </Button>
            )
          }
        >
          {isEditMode && (
            <Alert
              message="Tools are managed separately in edit mode. Use the provider page to add/edit/remove tools."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {!isEditMode && tools.length === 0 && (
            <div style={{ textAlign: 'center', padding: '24px', color: '#888' }}>
              <ApiOutlined style={{ fontSize: 32, marginBottom: 8 }} />
              <div>No tools defined yet</div>
              <div style={{ fontSize: 12 }}>Click "Add Tool" to create your first tool</div>
            </div>
          )}

          {!isEditMode && tools.length > 0 && (
            <Collapse
              activeKey={activeKeys}
              onChange={(keys) => setActiveKeys(keys as string[])}
            >
              {tools.map((tool, index) => (
                <Panel
                  key={`tool-${index}`}
                  header={
                    <Space>
                      <Text strong>{tool.name || `Tool ${index + 1}`}</Text>
                      <Text type="secondary">
                        {tool.method} {tool.path || '/'}
                      </Text>
                    </Space>
                  }
                  extra={
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        removeTool(index);
                      }}
                    />
                  }
                >
                  {renderToolEditor(tool, index)}
                </Panel>
              ))}
            </Collapse>
          )}

          {isEditMode && server?.tools && server.tools.length > 0 && (
            <Table
              size="small"
              dataSource={server.tools}
              columns={[
                { title: 'Name', dataIndex: 'name' },
                { title: 'Method', dataIndex: 'method', width: 80 },
                { title: 'Path', dataIndex: 'path' },
                {
                  title: 'Active',
                  dataIndex: 'is_active',
                  width: 70,
                  render: (active: boolean) => (
                    <Switch size="small" checked={active} disabled />
                  ),
                },
              ]}
              pagination={false}
              rowKey="id"
            />
          )}
        </Card>
      </Form>
    </Modal>
  );
};

export default DynamicMCPServerModal;
