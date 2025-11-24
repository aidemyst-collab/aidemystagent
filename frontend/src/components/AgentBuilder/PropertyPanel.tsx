import { Form, Input, Card, Typography, Empty, InputNumber, Select, Button, Space } from 'antd';
import { useEffect } from 'react';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import type { Node } from '@xyflow/react';

const { Title } = Typography;
const { TextArea } = Input;

interface PropertyPanelProps {
  selectedNode: Node | null;
  onUpdate: (nodeId: string, data: any) => void;
}

export const PropertyPanel = ({ selectedNode, onUpdate }: PropertyPanelProps) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (selectedNode) {
      form.setFieldsValue(selectedNode.data);
    } else {
      form.resetFields();
    }
  }, [selectedNode, form]);

  if (!selectedNode) {
    return (
      <div className="p-4 h-full flex items-center justify-center">
        <Empty description="Select a node to edit properties" />
      </div>
    );
  }

  const handleValueChange = (changedValues: any) => {
    if (selectedNode) {
      onUpdate(selectedNode.id, { ...selectedNode.data, ...changedValues });
    }
  };

  return (
    <div className="p-4 bg-gray-50 h-full overflow-auto">
      <Title level={5}>Properties</Title>
      <Card size="small" className="mb-4">
        <div className="text-sm text-gray-600">Node ID: {selectedNode.id}</div>
        <div className="text-sm text-gray-600">Type: {selectedNode.data.type}</div>
      </Card>

      <Form
        form={form}
        layout="vertical"
        onValuesChange={handleValueChange}
        size="small"
      >
        <Form.Item name="label" label="Label">
          <Input placeholder="Node label" />
        </Form.Item>

        {selectedNode.data.type === 'LLM_AGENT' && (
          <>
            <Card size="small" title="Model Configuration" className="mb-3">
              <Form.Item name={['config', 'modelConfig', 'model']} label="Model">
                <Select
                  options={[
                    { label: 'GPT-4', value: 'gpt-4' },
                    { label: 'GPT-4 Turbo', value: 'gpt-4-turbo' },
                    { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
                    { label: 'Claude 3 Opus', value: 'claude-3-opus' },
                    { label: 'Claude 3 Sonnet', value: 'claude-3-sonnet' },
                    { label: 'Claude 3 Haiku', value: 'claude-3-haiku' },
                  ]}
                  placeholder="Select model"
                />
              </Form.Item>

              <Form.Item name={['config', 'modelConfig', 'temperature']} label="Temperature">
                <InputNumber
                  min={0}
                  max={2}
                  step={0.1}
                  style={{ width: '100%' }}
                  placeholder="0.7"
                />
              </Form.Item>

              <Form.Item name={['config', 'modelConfig', 'maxTokens']} label="Max Tokens">
                <InputNumber
                  min={1}
                  max={8192}
                  style={{ width: '100%' }}
                  placeholder="2048"
                />
              </Form.Item>
            </Card>

            <Form.Item name={['config', 'systemPrompt']} label="System Prompt">
              <TextArea rows={4} placeholder="Enter system prompt..." />
            </Form.Item>

            <Form.Item name={['config', 'tools']} label="Tools">
              <Select
                mode="multiple"
                placeholder="Select tools available to this LLM"
                options={[
                  { label: 'Web Search', value: 'web_search' },
                  { label: 'Calculator', value: 'calculator' },
                  { label: 'Date/Time', value: 'datetime' },
                  { label: 'File Reader', value: 'file_reader' },
                  { label: 'Code Executor', value: 'code_executor' },
                ]}
              />
            </Form.Item>
          </>
        )}

        {selectedNode.data.type === 'RAG_RETRIEVER' && (
          <>
            <Form.Item name={['config', 'endpoint']} label="Endpoint URL">
              <Input placeholder="https://api.example.com/search" />
            </Form.Item>

            <Form.Item name={['config', 'authType']} label="Authentication Type">
              <Select
                options={[
                  { label: 'API Key', value: 'api_key' },
                  { label: 'OAuth2', value: 'oauth2' },
                  { label: 'Basic Auth', value: 'basic' },
                ]}
                placeholder="Select auth type"
              />
            </Form.Item>

            <Form.Item name={['config', 'searchMethod']} label="Search Method">
              <Select
                options={[
                  { label: 'Semantic Search', value: 'semantic' },
                  { label: 'Hybrid Search', value: 'hybrid' },
                  { label: 'Keyword Search', value: 'keyword' },
                ]}
                placeholder="Select search method"
              />
            </Form.Item>

            <Form.Item name={['config', 'topK']} label="Top K Results">
              <InputNumber
                min={1}
                max={20}
                style={{ width: '100%' }}
                placeholder="5"
              />
            </Form.Item>

            <Form.Item name={['config', 'scoreThreshold']} label="Score Threshold">
              <InputNumber
                min={0}
                max={1}
                step={0.1}
                style={{ width: '100%' }}
                placeholder="0.7"
              />
            </Form.Item>
          </>
        )}

        {selectedNode.data.type === 'TOOL' && (
          <>
            <Form.Item name={['config', 'toolId']} label="Tool">
              <Select
                placeholder="Select tool"
                options={[
                  { label: 'Web Search', value: 'web_search' },
                  { label: 'Calculator', value: 'calculator' },
                  { label: 'Date/Time', value: 'datetime' },
                  { label: 'File Reader', value: 'file_reader' },
                  { label: 'Code Executor', value: 'code_executor' },
                ]}
              />
            </Form.Item>

            <Form.Item label="Parameters">
              <TextArea
                rows={4}
                placeholder='{"key": "value"}'
                defaultValue="{}"
                onChange={(e) => {
                  try {
                    const params = JSON.parse(e.target.value);
                    form.setFieldValue(['config', 'parameters'], params);
                  } catch (err) {
                    // Invalid JSON, don't update
                  }
                }}
              />
            </Form.Item>
          </>
        )}

        {selectedNode.data.type === 'DECISION' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Configure conditions that route to different nodes based on input data
            </Typography.Text>
            <Form.List name={['config', 'conditions']}>
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Card key={key} size="small" className="mb-2">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Form.Item
                          {...restField}
                          name={[name, 'field']}
                          label="Field"
                          rules={[{ required: true, message: 'Field is required' }]}
                        >
                          <Input placeholder="e.g., output.score" />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'operator']}
                          label="Operator"
                          rules={[{ required: true, message: 'Operator is required' }]}
                        >
                          <Select
                            options={[
                              { label: 'Equals (==)', value: '==' },
                              { label: 'Not Equals (!=)', value: '!=' },
                              { label: 'Greater Than (>)', value: '>' },
                              { label: 'Less Than (<)', value: '<' },
                              { label: 'Greater or Equal (>=)', value: '>=' },
                              { label: 'Less or Equal (<=)', value: '<=' },
                              { label: 'Contains', value: 'contains' },
                            ]}
                          />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'value']}
                          label="Value"
                          rules={[{ required: true, message: 'Value is required' }]}
                        >
                          <Input placeholder="e.g., 0.8" />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'targetNode']}
                          label="Target Node ID"
                          rules={[{ required: true, message: 'Target node is required' }]}
                        >
                          <Input placeholder="Node ID to route to" />
                        </Form.Item>

                        <Button
                          type="link"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(name)}
                        >
                          Remove Condition
                        </Button>
                      </Space>
                    </Card>
                  ))}
                  <Button
                    type="dashed"
                    onClick={() => add()}
                    block
                    icon={<PlusOutlined />}
                  >
                    Add Condition
                  </Button>
                </>
              )}
            </Form.List>
          </>
        )}

        {selectedNode.data.type === 'INPUT' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Define input validation schema (JSON Schema format)
            </Typography.Text>
            <Form.Item label="Schema">
              <TextArea
                rows={8}
                placeholder='{"type": "object", "properties": {"message": {"type": "string"}}}'
                defaultValue="{}"
                onChange={(e) => {
                  try {
                    const schema = JSON.parse(e.target.value);
                    form.setFieldValue(['config', 'schema'], schema);
                  } catch (err) {
                    // Invalid JSON, don't update
                  }
                }}
              />
            </Form.Item>
          </>
        )}

        {selectedNode.data.type === 'OUTPUT' && (
          <>
            <Form.Item name={['config', 'format']} label="Output Format">
              <Select
                options={[
                  { label: 'JSON', value: 'json' },
                  { label: 'Plain Text', value: 'text' },
                  { label: 'Markdown', value: 'markdown' },
                ]}
                placeholder="Select output format"
              />
            </Form.Item>

            <Form.Item name={['config', 'template']} label="Template (Optional)">
              <TextArea
                rows={4}
                placeholder="Use {{variable}} syntax for dynamic values"
              />
            </Form.Item>
          </>
        )}

        {selectedNode.data.type === 'SUBGRAPH' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Reference another workflow as a subgraph
            </Typography.Text>
            <Form.Item name={['config', 'workflowId']} label="Workflow ID">
              <Input placeholder="Enter workflow ID to embed" />
            </Form.Item>
          </>
        )}
      </Form>
    </div>
  );
};
