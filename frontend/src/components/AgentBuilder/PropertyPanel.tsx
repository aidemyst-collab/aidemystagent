import { Form, Input, Card, Typography, Empty, InputNumber, Select, Button, Space, Checkbox } from 'antd';
import { useEffect, useState } from 'react';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import type { Edge } from '@xyflow/react';
import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';
import { credentialService, type Credential } from '../../features/credentials/credentialService';
import { toolService, type Tool } from '../../features/tools/toolService';
import { ragService, type Collection } from '../../features/rag/ragService';
import { NodeInputPanel } from './NodeInputPanel';
import { NodeOutputPanel } from './NodeOutputPanel';
import { TemplateHelper } from './TemplateHelper';

const { Title } = Typography;
const { TextArea } = Input;

interface PropertyPanelProps {
  selectedNode: WorkflowNode | null;
  onUpdate: (nodeId: string, data: any) => void;
  allNodes?: WorkflowNode[];
  allEdges?: WorkflowEdge[];
}

export const PropertyPanel = ({ selectedNode, onUpdate, allNodes = [], allEdges = [] }: PropertyPanelProps) => {
  const [form] = Form.useForm();
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedToolType, setSelectedToolType] = useState<string>('built-in');
  const [builtInTools, setBuiltInTools] = useState<any[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);

  // Helper function to get upstream nodes
  const getUpstreamNodes = (currentNode: WorkflowNode): WorkflowNode[] => {
    // Find all edges that point to the current node
    const incomingEdges = allEdges.filter(edge => edge.target === currentNode.id);

    // Get the source nodes
    return incomingEdges
      .map(edge => allNodes.find(node => node.id === edge.source))
      .filter((node): node is WorkflowNode => node !== undefined);
  };

  useEffect(() => {
    // Fetch credentials, tools, and collections when component mounts
    fetchCredentials();
    fetchTools('built-in'); // Default to built-in tools
    fetchCollections();
  }, []);

  useEffect(() => {
    if (selectedNode) {
      form.setFieldsValue(selectedNode.data);

      // If TOOL node is selected, fetch tools based on configured type
      if (selectedNode.data.type === 'TOOL') {
        const configuredToolType = selectedNode.data.config?.toolType || 'built-in';
        setSelectedToolType(configuredToolType);
        fetchTools(configuredToolType);
      }
    } else {
      form.resetFields();
    }
  }, [selectedNode, form]);

  const fetchCredentials = async () => {
    try {
      const data = await credentialService.getCredentials();
      setCredentials(data.credentials || []);
    } catch (error) {
      console.error('Error fetching credentials:', error);
    }
  };

  const fetchTools = async (toolType?: string) => {
    try {
      if (toolType === 'built-in') {
        const data = await toolService.getBuiltInTools();
        setBuiltInTools(data.tools || []);
        setTools([]);
      } else {
        const data = await toolService.getTools(0, 100, toolType);
        setTools(data.tools || []);
        setBuiltInTools([]);
      }
    } catch (error) {
      console.error('Error fetching tools:', error);
    }
  };

  const fetchCollections = async () => {
    try {
      const data = await ragService.getCollections();
      setCollections(data.collections || []);
    } catch (error) {
      console.error('Error fetching collections:', error);
    }
  };

  const handleToolTypeChange = (value: string) => {
    setSelectedToolType(value);
    fetchTools(value);
    // Clear the toolId when type changes
    form.setFieldValue(['config', 'toolId'], undefined);
  };

  if (!selectedNode) {
    return (
      <div className="p-4 h-full flex items-center justify-center">
        <Empty description="Select a node to edit properties" />
      </div>
    );
  }

  const handleValueChange = (changedValues: any) => {
    if (selectedNode) {
      // Deep merge function to handle nested config objects
      const deepMerge = (target: any, source: any): any => {
        const output = { ...target };
        for (const key in source) {
          if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
            output[key] = deepMerge(target[key] || {}, source[key]);
          } else {
            output[key] = source[key];
          }
        }
        return output;
      };

      const updatedData = deepMerge(selectedNode.data, changedValues);
      onUpdate(selectedNode.id, updatedData);
    }
  };

  return (
    <div className="p-4 bg-gray-50 h-full overflow-auto">
      <Title level={5}>Properties</Title>
      <Card size="small" className="mb-4">
        <div className="text-sm text-gray-600">Node ID: {selectedNode.id}</div>
        <div className="text-sm text-gray-600">Type: {selectedNode.data.type}</div>
      </Card>

      {/* Input Data Panel - shows what data is available from upstream nodes */}
      <NodeInputPanel
        currentNode={selectedNode}
        upstreamNodes={getUpstreamNodes(selectedNode)}
        onInsertTemplate={(template) => {
          // Template will be inserted when user clicks a field
          console.log('Template ready to insert:', template);
        }}
      />

      {/* Output Data Panel - shows what data this node produces */}
      <NodeOutputPanel
        currentNode={selectedNode}
        onUpdateCustomFields={(fields) => {
          onUpdate(selectedNode.id, {
            ...selectedNode.data,
            config: {
              ...selectedNode.data.config,
              customOutputFields: fields
            }
          });
        }}
      />

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
            <Form.Item
              name={['config', 'credentialId']}
              label="API Credential"
              tooltip="Select the API credential to use for this LLM node"
              rules={[{ required: true, message: 'Please select a credential' }]}
            >
              <Select
                placeholder="Select credential"
                options={credentials.map(cred => ({
                  label: `${cred.name} (${cred.provider})`,
                  value: cred.id,
                }))}
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
              />
            </Form.Item>

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
              <TemplateHelper
                value={form.getFieldValue(['config', 'systemPrompt']) || ''}
                onChange={(value) => form.setFieldValue(['config', 'systemPrompt'], value)}
                availableNodes={getUpstreamNodes(selectedNode)}
                placeholder="Enter system prompt with templates like {{input-1.message}}"
                rows={4}
              />
            </Form.Item>

            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
              💡 <strong>Tip:</strong> Connect TOOL nodes to this LLM to give it access to tools (Calculator, Web Search, etc.)
            </Typography.Text>
          </>
        )}

        {selectedNode.data.type === 'RAG_RETRIEVER' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Configure pgvector retrieval for Retrieval-Augmented Generation
            </Typography.Text>

            <Card size="small" title="Collection" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'collectionId']}
                label="Document Collection"
                rules={[{ required: true, message: 'Please select a collection' }]}
              >
                <Select
                  placeholder="Select collection"
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={collections.map(c => ({
                    label: `${c.name} ${c.description ? `- ${c.description}` : ''}`,
                    value: c.id
                  }))}
                />
              </Form.Item>

              <Form.Item name={['config', 'includeMetadata']} valuePropName="checked" initialValue={true}>
                <Checkbox>Include document metadata in context</Checkbox>
              </Form.Item>
            </Card>

            <Card size="small" title="Embedding Configuration" style={{ marginBottom: 16 }}>
              <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
                Note: Use the same embedding model that was used to create the collection
              </Typography.Text>

              <Form.Item name={['config', 'embeddingProvider']} label="Provider" initialValue="openai">
                <Select
                  options={[
                    { label: 'OpenAI', value: 'openai' },
                    { label: 'Google', value: 'google' },
                    { label: 'Voyage AI (Anthropic recommended)', value: 'voyage' },
                  ]}
                />
              </Form.Item>

              <Form.Item name={['config', 'embeddingModel']} label="Model" initialValue="text-embedding-ada-002">
                <Select
                  options={[
                    { label: 'text-embedding-ada-002 (1536d)', value: 'text-embedding-ada-002' },
                    { label: 'text-embedding-3-small (1536d)', value: 'text-embedding-3-small' },
                    { label: 'text-embedding-3-large (3072d)', value: 'text-embedding-3-large' },
                  ]}
                />
              </Form.Item>
            </Card>

            <Card size="small" title="Retrieval Settings">
              <Form.Item name={['config', 'searchMethod']} label="Search Method" initialValue="cosine">
                <Select
                  options={[
                    { label: 'Cosine Similarity (recommended)', value: 'cosine' },
                    { label: 'L2 Distance', value: 'l2' },
                  ]}
                />
              </Form.Item>

              <Form.Item name={['config', 'topK']} label="Top K Results" initialValue={5}>
                <InputNumber
                  min={1}
                  max={20}
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item name={['config', 'scoreThreshold']} label="Score Threshold" initialValue={0.7}>
                <InputNumber
                  min={0}
                  max={1}
                  step={0.1}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Card>
          </>
        )}

        {selectedNode.data.type === 'TOOL' && (
          <>
            <Form.Item name={['config', 'toolType']} label="Tool Type" initialValue="built-in">
              <Select
                placeholder="Select tool type"
                onChange={handleToolTypeChange}
                options={[
                  { label: 'Built-in Tools', value: 'built-in' },
                  { label: 'API Integration', value: 'api' },
                  { label: 'Custom Code', value: 'custom' },
                  { label: 'MCP Tools', value: 'mcp' },
                ]}
              />
            </Form.Item>

            <Form.Item name={['config', 'toolId']} label="Tool" rules={[{ required: true, message: 'Please select a tool' }]}>
              <Select
                placeholder="Select tool"
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={
                  selectedToolType === 'built-in'
                    ? builtInTools.map(tool => ({
                        label: `${tool.name} - ${tool.description}`,
                        value: tool.name,
                      }))
                    : tools.map(tool => ({
                        label: `${tool.name} - ${tool.description}`,
                        value: tool.id,
                      }))
                }
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

        {selectedNode.data.type === 'FILE_READER' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Read files from the server filesystem with configurable options
            </Typography.Text>

            <Form.Item
              name={['config', 'filePath']}
              label="File Path"
              rules={[{ required: true, message: 'Please enter file path' }]}
              tooltip="Absolute or relative path to the file. Supports templates like {{input-1.path}}"
            >
              <TemplateHelper
                value={form.getFieldValue(['config', 'filePath']) || ''}
                onChange={(value) => form.setFieldValue(['config', 'filePath'], value)}
                availableNodes={getUpstreamNodes(selectedNode)}
                placeholder="/var/data/file.txt or {{input-1.file_path}}"
                rows={2}
              />
            </Form.Item>

            <Form.Item
              name={['config', 'operation']}
              label="File Operation"
              initialValue="read_text"
              rules={[{ required: true, message: 'Please select operation' }]}
            >
              <Select
                options={[
                  { label: 'Read as Text', value: 'read_text' },
                  { label: 'Read as Binary (Base64)', value: 'read_binary' },
                  { label: 'Read & Parse JSON', value: 'read_json' },
                  { label: 'Read & Parse CSV', value: 'read_csv' },
                  { label: 'Read as Lines', value: 'read_lines' },
                  { label: 'Get Metadata Only', value: 'get_metadata' },
                ]}
              />
            </Form.Item>

            <Form.Item noStyle shouldUpdate>
              {() => {
                const operation = form.getFieldValue(['config', 'operation']) || 'read_text';
                const isTextOperation = ['read_text', 'read_json', 'read_csv', 'read_lines'].includes(operation);

                return (
                  <>
                    {isTextOperation && (
                      <Form.Item name={['config', 'encoding']} label="Encoding" initialValue="utf-8">
                        <Select
                          options={[
                            { label: 'UTF-8', value: 'utf-8' },
                            { label: 'UTF-16', value: 'utf-16' },
                            { label: 'ASCII', value: 'ascii' },
                            { label: 'Latin1', value: 'latin1' },
                          ]}
                        />
                      </Form.Item>
                    )}

                    {operation === 'read_csv' && (
                      <Card size="small" title="CSV Options" className="mb-3">
                        <Form.Item name={['config', 'csvDelimiter']} label="Delimiter" initialValue=",">
                          <Input placeholder="," />
                        </Form.Item>
                        <Form.Item name={['config', 'csvHasHeader']} valuePropName="checked" initialValue={true}>
                          <Checkbox>First row is header</Checkbox>
                        </Form.Item>
                        <Form.Item name={['config', 'csvSkipEmpty']} valuePropName="checked" initialValue={true}>
                          <Checkbox>Skip empty lines</Checkbox>
                        </Form.Item>
                        <Form.Item name={['config', 'csvTrimFields']} valuePropName="checked" initialValue={true}>
                          <Checkbox>Trim field whitespace</Checkbox>
                        </Form.Item>
                      </Card>
                    )}

                    {operation === 'read_json' && (
                      <Card size="small" title="JSON Options" className="mb-3">
                        <Form.Item name={['config', 'validateSchema']} valuePropName="checked" initialValue={false}>
                          <Checkbox>Validate against JSON schema</Checkbox>
                        </Form.Item>
                        {form.getFieldValue(['config', 'validateSchema']) && (
                          <Form.Item name={['config', 'jsonSchema']} label="JSON Schema">
                            <TextArea rows={6} placeholder="Enter JSON schema..." />
                          </Form.Item>
                        )}
                      </Card>
                    )}

                    {operation === 'read_lines' && (
                      <Card size="small" title="Line Options" className="mb-3">
                        <Form.Item name={['config', 'linesSkipEmpty']} valuePropName="checked" initialValue={true}>
                          <Checkbox>Skip empty lines</Checkbox>
                        </Form.Item>
                        <Form.Item name={['config', 'linesTrim']} valuePropName="checked" initialValue={true}>
                          <Checkbox>Trim line whitespace</Checkbox>
                        </Form.Item>
                        <Form.Item name={['config', 'linesStart']} label="Start Line (optional)">
                          <InputNumber min={1} style={{ width: '100%' }} placeholder="1" />
                        </Form.Item>
                        <Form.Item name={['config', 'linesEnd']} label="End Line (optional)">
                          <InputNumber min={1} style={{ width: '100%' }} placeholder="100" />
                        </Form.Item>
                      </Card>
                    )}
                  </>
                );
              }}
            </Form.Item>

            <Card size="small" title="Error Handling" className="mb-3">
              <Form.Item
                name={['config', 'errorHandling']}
                label="On Error"
                initialValue="fail"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    { label: 'Fail Workflow', value: 'fail' },
                    { label: 'Continue with Empty Result', value: 'continue' },
                    { label: 'Use Default Value', value: 'default_value' },
                  ]}
                />
              </Form.Item>

              {form.getFieldValue(['config', 'errorHandling']) === 'default_value' && (
                <Form.Item name={['config', 'defaultValue']} label="Default Value">
                  <TextArea rows={3} placeholder="Value to use if file cannot be read..." />
                </Form.Item>
              )}
            </Card>

            <Form.Item name={['config', 'maxFileSizeMB']} label="Max File Size (MB)" initialValue={10}>
              <InputNumber min={1} max={100} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item
              name={['config', 'outputVarName']}
              label="Output Variable Name"
              initialValue="file_content"
              tooltip="Custom name for the output field in node outputs"
            >
              <Input placeholder="file_content" />
            </Form.Item>
          </>
        )}

        {selectedNode.data.type === 'STRUCTURED_OUTPUT_PARSER' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Parse LLM outputs into structured, validated JSON format
            </Typography.Text>

            <Card size="small" title="Parser Configuration" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'parserType']}
                label="Parser Type"
                initialValue="json_schema"
              >
                <Select>
                  <Select.Option value="json_schema">JSON Schema</Select.Option>
                  <Select.Option value="field_extractor">Field Extractor</Select.Option>
                  <Select.Option value="key_value">Key-Value Pairs</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item
                name={['config', 'strategy']}
                label="Parsing Strategy"
                initialValue="lenient"
              >
                <Select>
                  <Select.Option value="strict">Strict - Fail if mismatch</Select.Option>
                  <Select.Option value="lenient">Lenient - Best effort</Select.Option>
                  <Select.Option value="auto_fix">Auto-fix - Attempt repairs</Select.Option>
                </Select>
              </Form.Item>
            </Card>

            <Card size="small" title="Schema Definition" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'schema']}
                label="JSON Schema"
                tooltip="Define the expected output structure"
              >
                <TextArea
                  rows={8}
                  placeholder={`{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "price": { "type": "number" }
  },
  "required": ["name"]
}`}
                  style={{ fontFamily: 'monospace', fontSize: 12 }}
                />
              </Form.Item>
            </Card>

            <Card size="small" title="Error Handling" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'errorHandling']}
                label="On Parse Error"
                initialValue="fail"
              >
                <Select>
                  <Select.Option value="fail">Fail execution</Select.Option>
                  <Select.Option value="pass_through">Pass original text</Select.Option>
                  <Select.Option value="default_values">Use default values</Select.Option>
                  <Select.Option value="retry_llm">Retry with LLM</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item
                name={['config', 'typeCoercion']}
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>Enable type coercion (e.g., "123" → 123)</Checkbox>
              </Form.Item>

              <Form.Item
                name={['config', 'llmGuidance']}
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>Add schema instructions to LLM prompt</Checkbox>
              </Form.Item>
            </Card>
          </>
        )}

        {selectedNode.data.type === 'INPUT' && (
          <>
            <Form.Item name={['config', 'mode']} label="Input Mode" initialValue="chat">
              <Select
                options={[
                  { label: 'Chat', value: 'chat', description: 'Conversational text input' },
                  { label: 'JSON', value: 'json', description: 'Structured JSON data' },
                  { label: 'Form', value: 'form', description: 'Form fields with validation' },
                ]}
                placeholder="Select input mode"
              />
            </Form.Item>

            <Form.Item noStyle shouldUpdate>
              {() => {
                const mode = form.getFieldValue(['config', 'mode']) || 'chat';

                if (mode === 'chat') {
                  return (
                    <Card size="small" title="Chat Configuration" className="mb-3">
                      <Form.Item
                        name={['config', 'chatConfig', 'systemMessage']}
                        label="System Message"
                        tooltip="Optional system message to set context for the conversation"
                      >
                        <TextArea rows={3} placeholder="You are a helpful assistant..." />
                      </Form.Item>

                      <Form.Item
                        name={['config', 'chatConfig', 'includeHistory']}
                        valuePropName="checked"
                      >
                        <Checkbox>Include chat history</Checkbox>
                      </Form.Item>

                      {form.getFieldValue(['config', 'chatConfig', 'includeHistory']) && (
                        <Form.Item
                          name={['config', 'chatConfig', 'maxHistoryMessages']}
                          label="Max History Messages"
                        >
                          <InputNumber min={1} max={50} style={{ width: '100%' }} placeholder="10" />
                        </Form.Item>
                      )}

                      <Form.Item label="Metadata Collection">
                        <Form.Item
                          name={['config', 'chatConfig', 'metadata', 'collectTimestamp']}
                          valuePropName="checked"
                          noStyle
                        >
                          <Checkbox>Collect timestamp</Checkbox>
                        </Form.Item>
                        <Form.Item
                          name={['config', 'chatConfig', 'metadata', 'collectUserId']}
                          valuePropName="checked"
                          noStyle
                          style={{ marginTop: 8 }}
                        >
                          <Checkbox>Collect user ID</Checkbox>
                        </Form.Item>
                      </Form.Item>
                    </Card>
                  );
                }

                if (mode === 'json') {
                  return (
                    <Card size="small" title="JSON Configuration" className="mb-3">
                      <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
                        Define JSON schema for validation (JSON Schema format)
                      </Typography.Text>
                      <Form.Item
                        name={['config', 'jsonConfig', 'schema']}
                        label="JSON Schema"
                        tooltip="Define the expected JSON structure"
                      >
                        <TextArea
                          rows={10}
                          placeholder={`{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "age": { "type": "number" }
  },
  "required": ["name"]
}`}
                          onChange={(e) => {
                            try {
                              const schema = JSON.parse(e.target.value);
                              form.setFieldValue(['config', 'jsonConfig', 'schema'], schema);
                            } catch (err) {
                              // Invalid JSON, keep as string
                            }
                          }}
                        />
                      </Form.Item>

                      <Form.Item
                        name={['config', 'jsonConfig', 'validateOnInput']}
                        valuePropName="checked"
                        initialValue={true}
                      >
                        <Checkbox>Validate on input</Checkbox>
                      </Form.Item>

                      <Form.Item
                        name={['config', 'jsonConfig', 'coerceTypes']}
                        valuePropName="checked"
                      >
                        <Checkbox>Coerce types automatically</Checkbox>
                      </Form.Item>
                    </Card>
                  );
                }

                if (mode === 'form') {
                  return (
                    <Card size="small" title="Form Configuration" className="mb-3">
                      <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
                        Define form fields with validation rules
                      </Typography.Text>
                      <Form.List name={['config', 'formConfig', 'fields']}>
                        {(fields, { add, remove }) => (
                          <>
                            {fields.map(({ key, name, ...restField }) => (
                              <Card key={key} size="small" className="mb-2" style={{ background: '#f9f9f9' }}>
                                <Form.Item
                                  {...restField}
                                  name={[name, 'key']}
                                  label="Field Key"
                                  rules={[{ required: true, message: 'Key is required' }]}
                                >
                                  <Input placeholder="e.g., email" />
                                </Form.Item>

                                <Form.Item
                                  {...restField}
                                  name={[name, 'label']}
                                  label="Label"
                                  rules={[{ required: true, message: 'Label is required' }]}
                                >
                                  <Input placeholder="e.g., Email Address" />
                                </Form.Item>

                                <Form.Item
                                  {...restField}
                                  name={[name, 'type']}
                                  label="Type"
                                  rules={[{ required: true, message: 'Type is required' }]}
                                  initialValue="text"
                                >
                                  <Select
                                    options={[
                                      { label: 'Text', value: 'text' },
                                      { label: 'Text Area', value: 'textarea' },
                                      { label: 'Number', value: 'number' },
                                      { label: 'Select', value: 'select' },
                                      { label: 'Checkbox', value: 'checkbox' },
                                      { label: 'Date', value: 'date' },
                                    ]}
                                  />
                                </Form.Item>

                                <Form.Item
                                  {...restField}
                                  name={[name, 'required']}
                                  valuePropName="checked"
                                >
                                  <Checkbox>Required</Checkbox>
                                </Form.Item>

                                <Form.Item
                                  {...restField}
                                  name={[name, 'placeholder']}
                                  label="Placeholder"
                                >
                                  <Input placeholder="Enter placeholder text" />
                                </Form.Item>

                                <Form.Item
                                  {...restField}
                                  name={[name, 'default']}
                                  label="Default Value"
                                >
                                  <Input placeholder="Default value" />
                                </Form.Item>

                                <Button
                                  type="link"
                                  danger
                                  icon={<DeleteOutlined />}
                                  onClick={() => remove(name)}
                                  size="small"
                                >
                                  Remove Field
                                </Button>
                              </Card>
                            ))}
                            <Button
                              type="dashed"
                              onClick={() => add()}
                              block
                              icon={<PlusOutlined />}
                            >
                              Add Field
                            </Button>
                          </>
                        )}
                      </Form.List>
                    </Card>
                  );
                }

                return null;
              }}
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
              <TemplateHelper
                value={form.getFieldValue(['config', 'template']) || ''}
                onChange={(value) => form.setFieldValue(['config', 'template'], value)}
                availableNodes={getUpstreamNodes(selectedNode)}
                placeholder="Use {{node_id.field}} syntax for dynamic values"
                rows={4}
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

        {selectedNode.data.type === 'MEMORY' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Configure conversation history management for multi-turn interactions
            </Typography.Text>

            <Form.Item name={['config', 'type']} label="Memory Type" initialValue="buffer-window">
              <Select
                options={[
                  { label: 'Buffer', value: 'buffer', description: 'Store all conversation history' },
                  { label: 'Buffer Window', value: 'buffer-window', description: 'Store last N messages' },
                  { label: 'Summary', value: 'summary', description: 'Summarize old messages' },
                  { label: 'Vector', value: 'vector', description: 'Semantic search over history' },
                  { label: 'Entity', value: 'entity', description: 'Extract and track entities' },
                ]}
                placeholder="Select memory type"
              />
            </Form.Item>

            <Form.Item noStyle shouldUpdate>
              {() => {
                const memoryType = form.getFieldValue(['config', 'type']) || 'buffer-window';

                return (
                  <>
                    {(memoryType === 'buffer-window' || memoryType === 'buffer') && (
                      <Form.Item
                        name={['config', 'windowSize']}
                        label="Window Size"
                        tooltip="Number of recent messages to keep in memory"
                        initialValue={10}
                      >
                        <InputNumber
                          min={1}
                          max={100}
                          style={{ width: '100%' }}
                          placeholder="10"
                        />
                      </Form.Item>
                    )}

                    <Card size="small" title="Persistence" className="mb-3">
                      <Form.Item
                        name={['config', 'persistence', 'enabled']}
                        valuePropName="checked"
                        initialValue={true}
                      >
                        <Checkbox>Enable persistent storage</Checkbox>
                      </Form.Item>

                      {form.getFieldValue(['config', 'persistence', 'enabled']) && (
                        <>
                          <Form.Item
                            name={['config', 'persistence', 'backend']}
                            label="Storage Backend"
                            initialValue="redis"
                          >
                            <Select
                              options={[
                                { label: 'Redis', value: 'redis' },
                                { label: 'PostgreSQL', value: 'postgres' },
                                { label: 'MongoDB', value: 'mongodb' },
                              ]}
                              placeholder="Select storage backend"
                            />
                          </Form.Item>

                          <Form.Item
                            name={['config', 'persistence', 'credentialId']}
                            label="Storage Credential"
                            tooltip="Select the credential for connecting to your storage backend"
                            rules={[{ required: true, message: 'Please select a credential' }]}
                          >
                            <Select
                              placeholder="Select credential"
                              options={credentials
                                .filter(cred => {
                                  const backend = form.getFieldValue(['config', 'persistence', 'backend']) || 'redis';
                                  // Filter credentials based on backend type
                                  if (backend === 'redis') return cred.type === 'redis' || cred.provider === 'redis';
                                  if (backend === 'postgres') return cred.type === 'database' || cred.provider === 'postgresql';
                                  if (backend === 'mongodb') return cred.type === 'database' || cred.provider === 'mongodb';
                                  return false;
                                })
                                .map(cred => ({
                                  label: `${cred.name}${cred.provider ? ` (${cred.provider})` : ''}`,
                                  value: cred.id,
                                }))}
                              showSearch
                              filterOption={(input, option) =>
                                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                              }
                              notFoundContent={
                                <div style={{ padding: '8px', textAlign: 'center', color: '#999' }}>
                                  No credentials found. Create one in the Credentials page.
                                </div>
                              }
                            />
                          </Form.Item>

                          <Form.Item
                            name={['config', 'persistence', 'ttlDays']}
                            label="TTL (Days)"
                            tooltip="How long to retain conversation history"
                            initialValue={30}
                          >
                            <InputNumber
                              min={1}
                              max={365}
                              style={{ width: '100%' }}
                              placeholder="30"
                            />
                          </Form.Item>
                        </>
                      )}
                    </Card>
                  </>
                );
              }}
            </Form.Item>
          </>
        )}
      </Form>
    </div>
  );
};
