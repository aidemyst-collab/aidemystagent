import { Form, Input, Card, Typography, Empty, InputNumber, Select, Button, Space, Checkbox, message, Spin } from 'antd';
import { useEffect, useState } from 'react';
import { PlusOutlined, DeleteOutlined, ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import type { Edge } from '@xyflow/react';
import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';
import { credentialService, type Credential } from '../../features/credentials/credentialService';
import { toolService, type Tool } from '../../features/tools/toolService';
import { ragService, type Collection } from '../../features/rag/ragService';
import { NodeInputPanel } from './NodeInputPanel';
import { NodeOutputPanel } from './NodeOutputPanel';
import { TemplateHelper } from './TemplateHelper';
import { apiClient } from '../../services/api';

const { Title } = Typography;
const { TextArea } = Input;

interface PropertyPanelProps {
  selectedNode: WorkflowNode | null;
  onUpdate: (nodeId: string, data: any) => void;
  allNodes?: WorkflowNode[];
  allEdges?: WorkflowEdge[];
}

// External RAG collection type
interface ExternalCollection {
  id: number;
  name: string;
  description?: string;
  document_count?: number;
  embedding_provider?: string;
  embedding_model?: string;
}

export const PropertyPanel = ({ selectedNode, onUpdate, allNodes = [], allEdges = [] }: PropertyPanelProps) => {
  const [form] = Form.useForm();
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedToolType, setSelectedToolType] = useState<string>('built-in');
  const [builtInTools, setBuiltInTools] = useState<any[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);

  // External RAG state
  const [ragSource, setRagSource] = useState<string>('internal');
  const [externalCollections, setExternalCollections] = useState<ExternalCollection[]>([]);
  const [loadingExternalCollections, setLoadingExternalCollections] = useState(false);
  const [externalConnectionStatus, setExternalConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Execute Workflow state
  const [workflows, setWorkflows] = useState<{ id: string; name: string; description: string; status: string }[]>([]);
  const [loadingWorkflows, setLoadingWorkflows] = useState(false);

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

      // If EXECUTE_WORKFLOW node is selected, fetch available workflows
      if (selectedNode.data.type === 'EXECUTE_WORKFLOW') {
        // Get the current workflow ID from URL or context to exclude it
        const urlParams = new URLSearchParams(window.location.search);
        const currentWorkflowId = urlParams.get('id') || undefined;
        fetchWorkflows(currentWorkflowId);
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

  const fetchWorkflows = async (excludeId?: string) => {
    setLoadingWorkflows(true);
    try {
      const params = new URLSearchParams();
      if (excludeId) params.append('exclude_id', excludeId);
      const response = await apiClient.get<{ workflows: { id: string; name: string; description: string; status: string }[] }>(
        `/workflows/list?${params.toString()}`
      );
      setWorkflows(response.workflows || []);
    } catch (error) {
      console.error('Error fetching workflows:', error);
      // Fallback: try to get regular workflow list
      try {
        const response = await apiClient.get<{ workflows: { id: string; name: string; description: string; status: string }[] }>('/workflows');
        setWorkflows(response.workflows || []);
      } catch {
        setWorkflows([]);
      }
    } finally {
      setLoadingWorkflows(false);
    }
  };

  // External RAG functions
  const testExternalConnection = async () => {
    const url = form.getFieldValue(['config', 'externalUrl']);
    const apiKey = form.getFieldValue(['config', 'externalApiKey']);

    if (!url || !apiKey) {
      message.warning('Please enter both URL and API Key');
      return;
    }

    try {
      const response = await apiClient.post<{ success: boolean; message: string }>('/rag/external/test', { url, api_key: apiKey });
      if (response.success) {
        setExternalConnectionStatus('success');
        message.success(response.message);
      } else {
        setExternalConnectionStatus('error');
        message.error(response.message || 'Connection failed');
      }
    } catch (error: any) {
      setExternalConnectionStatus('error');
      message.error(error.message || 'Connection failed');
    }
  };

  const fetchExternalCollections = async () => {
    const url = form.getFieldValue(['config', 'externalUrl']);
    const apiKey = form.getFieldValue(['config', 'externalApiKey']);

    if (!url || !apiKey) {
      message.warning('Please enter both URL and API Key');
      return;
    }

    setLoadingExternalCollections(true);
    try {
      const response = await apiClient.post<{ success: boolean; collections: ExternalCollection[] }>('/rag/external/collections', { url, api_key: apiKey });
      if (response.success) {
        setExternalCollections(response.collections || []);
        setExternalConnectionStatus('success');
        message.success(`Loaded ${response.collections?.length || 0} collections`);
      } else {
        message.error('Failed to load collections');
      }
    } catch (error: any) {
      setExternalConnectionStatus('error');
      message.error(error.message || 'Failed to load collections');
    } finally {
      setLoadingExternalCollections(false);
    }
  };

  const handleRagSourceChange = (value: string) => {
    setRagSource(value);
    setExternalCollections([]);
    setExternalConnectionStatus('idle');
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
              Configure Retrieval-Augmented Generation (RAG) source
            </Typography.Text>

            {/* RAG Source Selection */}
            <Card size="small" title="RAG Source" style={{ marginBottom: 16 }}>
              <Form.Item name={['config', 'ragSource']} label="Source Type" initialValue="internal">
                <Select
                  onChange={handleRagSourceChange}
                  options={[
                    { label: 'Internal (pgvector)', value: 'internal' },
                    { label: 'External (DemystRAG)', value: 'external' },
                  ]}
                />
              </Form.Item>
            </Card>

            {/* External RAG Configuration */}
            {(ragSource === 'external' || form.getFieldValue(['config', 'ragSource']) === 'external') && (
              <Card size="small" title="DemystRAG Connection" style={{ marginBottom: 16 }}>
                <Form.Item
                  name={['config', 'externalUrl']}
                  label="DemystRAG URL"
                  rules={[{ required: true, message: 'Please enter the DemystRAG URL' }]}
                  initialValue="http://localhost:8003"
                >
                  <Input placeholder="http://localhost:8003" />
                </Form.Item>

                <Form.Item
                  name={['config', 'externalApiKey']}
                  label="API Key"
                  rules={[{ required: true, message: 'Please enter the API key' }]}
                >
                  <Input.Password placeholder="dmr_xxxxxxxxxxxxxxxx" />
                </Form.Item>

                <Space style={{ marginBottom: 16 }}>
                  <Button
                    icon={<CheckCircleOutlined />}
                    onClick={testExternalConnection}
                  >
                    Test Connection
                  </Button>
                  <Button
                    type="primary"
                    icon={<ReloadOutlined />}
                    onClick={fetchExternalCollections}
                    loading={loadingExternalCollections}
                  >
                    Load Collections
                  </Button>
                  {externalConnectionStatus === 'success' && (
                    <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
                  )}
                  {externalConnectionStatus === 'error' && (
                    <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 18 }} />
                  )}
                </Space>

                <Form.Item
                  name={['config', 'collectionId']}
                  label="Collection"
                  rules={[{ required: true, message: 'Please select a collection' }]}
                >
                  <Select
                    placeholder={loadingExternalCollections ? "Loading..." : "Select collection (load first)"}
                    showSearch
                    disabled={externalCollections.length === 0}
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                    options={externalCollections.map(c => ({
                      label: `${c.name}${c.document_count ? ` (${c.document_count} docs)` : ''}`,
                      value: c.id
                    }))}
                  />
                </Form.Item>

                <Form.Item name={['config', 'includeMetadata']} valuePropName="checked" initialValue={true}>
                  <Checkbox>Include document metadata in context</Checkbox>
                </Form.Item>
              </Card>
            )}

            {/* Internal RAG Configuration */}
            {(ragSource === 'internal' || form.getFieldValue(['config', 'ragSource']) !== 'external') && form.getFieldValue(['config', 'ragSource']) !== 'external' && (
              <>
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
              </>
            )}

            <Card size="small" title="Retrieval Settings">
              {(ragSource === 'internal' || form.getFieldValue(['config', 'ragSource']) !== 'external') && form.getFieldValue(['config', 'ragSource']) !== 'external' && (
                <Form.Item name={['config', 'searchMethod']} label="Search Method" initialValue="cosine">
                  <Select
                    options={[
                      { label: 'Cosine Similarity (recommended)', value: 'cosine' },
                      { label: 'L2 Distance', value: 'l2' },
                    ]}
                  />
                </Form.Item>
              )}

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
                  { label: 'Audio', value: 'audio', description: 'Voice/audio input with transcription' },
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

                if (mode === 'audio') {
                  return (
                    <Card size="small" title="Audio Input Configuration" className="mb-3">
                      <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
                        Receive and normalize audio input. Use AUDIO_TO_TEXT node for transcription.
                      </Typography.Text>

                      <Form.Item
                        name={['config', 'audioConfig', 'source']}
                        label="Audio Source"
                        initialValue="microphone"
                        tooltip="Where the audio input comes from"
                      >
                        <Select
                          options={[
                            { label: 'Twilio (Voice Call)', value: 'twilio' },
                            { label: 'Microphone (Record)', value: 'microphone' },
                            { label: 'Upload File', value: 'upload' },
                            { label: 'Audio URL', value: 'url' },
                          ]}
                        />
                      </Form.Item>

                      <Form.Item
                        noStyle
                        shouldUpdate={(prev, curr) =>
                          prev?.config?.audioConfig?.source !== curr?.config?.audioConfig?.source
                        }
                      >
                        {() => {
                          const source = form.getFieldValue(['config', 'audioConfig', 'source']);
                          if (source === 'twilio') {
                            return (
                              <>
                                <Form.Item
                                  name={['config', 'audioConfig', 'twilioConfig', 'format']}
                                  label="Twilio Audio Format"
                                  initialValue="mulaw"
                                >
                                  <Select
                                    options={[
                                      { label: 'μ-law (mulaw)', value: 'mulaw' },
                                      { label: 'PCM', value: 'pcm' },
                                    ]}
                                  />
                                </Form.Item>
                                <Form.Item
                                  name={['config', 'audioConfig', 'twilioConfig', 'sampleRate']}
                                  label="Sample Rate"
                                  initialValue={8000}
                                >
                                  <InputNumber min={8000} max={48000} style={{ width: '100%' }} />
                                </Form.Item>
                              </>
                            );
                          }
                          if (source === 'url') {
                            return (
                              <Form.Item
                                name={['config', 'audioConfig', 'audioUrl']}
                                label="Audio URL"
                                tooltip="URL to fetch audio from"
                              >
                                <Input placeholder="https://example.com/audio.mp3" />
                              </Form.Item>
                            );
                          }
                          return null;
                        }}
                      </Form.Item>

                      <Form.Item
                        name={['config', 'audioConfig', 'outputFormat']}
                        label="Normalized Output Format"
                        initialValue="wav"
                        tooltip="Format for passing to AUDIO_TO_TEXT node"
                      >
                        <Select
                          options={[
                            { label: 'WAV', value: 'wav' },
                            { label: 'MP3', value: 'mp3' },
                            { label: 'WebM', value: 'webm' },
                          ]}
                        />
                      </Form.Item>
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
                  { label: 'Audio (TTS)', value: 'audio' },
                ]}
                placeholder="Select output format"
              />
            </Form.Item>

            <Form.Item noStyle shouldUpdate>
              {() => {
                const format = form.getFieldValue(['config', 'format']);

                if (format === 'audio') {
                  return (
                    <Card size="small" title="Audio Output Configuration" className="mb-3">
                      <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
                        Receive audio from TEXT_TO_AUDIO node and send to target provider.
                      </Typography.Text>

                      <Form.Item
                        name={['config', 'audioConfig', 'targetProvider']}
                        label="Target Provider"
                        initialValue="auto"
                        tooltip="Where to send the audio response"
                      >
                        <Select
                          options={[
                            { label: 'Auto-detect (from INPUT)', value: 'auto' },
                            { label: 'Twilio (Voice Call)', value: 'twilio' },
                            { label: 'Browser (Playground)', value: 'browser' },
                            { label: 'API Response', value: 'api' },
                          ]}
                        />
                      </Form.Item>

                      <Form.Item
                        noStyle
                        shouldUpdate={(prev, curr) =>
                          prev?.config?.audioConfig?.targetProvider !== curr?.config?.audioConfig?.targetProvider
                        }
                      >
                        {() => {
                          const target = form.getFieldValue(['config', 'audioConfig', 'targetProvider']);
                          if (target === 'twilio') {
                            return (
                              <>
                                <Form.Item
                                  name={['config', 'audioConfig', 'twilioConfig', 'responseType']}
                                  label="Twilio Response Type"
                                  initialValue="twiml_play"
                                >
                                  <Select
                                    options={[
                                      { label: 'Play Custom Audio (<Play>)', value: 'twiml_play' },
                                      { label: 'Use Twilio TTS (<Say>)', value: 'twiml_say' },
                                    ]}
                                  />
                                </Form.Item>

                                <Form.Item
                                  noStyle
                                  shouldUpdate={(prev, curr) =>
                                    prev?.config?.audioConfig?.twilioConfig?.responseType !== curr?.config?.audioConfig?.twilioConfig?.responseType
                                  }
                                >
                                  {() => {
                                    const responseType = form.getFieldValue(['config', 'audioConfig', 'twilioConfig', 'responseType']);
                                    if (responseType === 'twiml_say') {
                                      return (
                                        <>
                                          <Form.Item
                                            name={['config', 'audioConfig', 'twilioConfig', 'sayVoice']}
                                            label="Twilio Voice"
                                            initialValue="alice"
                                          >
                                            <Select
                                              options={[
                                                { label: 'Alice (Female)', value: 'alice' },
                                                { label: 'Polly.Amy (Female)', value: 'Polly.Amy' },
                                                { label: 'Polly.Brian (Male)', value: 'Polly.Brian' },
                                                { label: 'Polly.Joanna (Female)', value: 'Polly.Joanna' },
                                                { label: 'Polly.Matthew (Male)', value: 'Polly.Matthew' },
                                              ]}
                                            />
                                          </Form.Item>
                                          <Form.Item
                                            name={['config', 'audioConfig', 'twilioConfig', 'sayLanguage']}
                                            label="Language"
                                            initialValue="en-US"
                                          >
                                            <Select
                                              options={[
                                                { label: 'English (US)', value: 'en-US' },
                                                { label: 'English (UK)', value: 'en-GB' },
                                                { label: 'Spanish', value: 'es-ES' },
                                                { label: 'French', value: 'fr-FR' },
                                                { label: 'German', value: 'de-DE' },
                                              ]}
                                            />
                                          </Form.Item>
                                        </>
                                      );
                                    }
                                    return (
                                      <Form.Item
                                        name={['config', 'audioConfig', 'twilioConfig', 'playUrl']}
                                        label="Audio URL (Optional)"
                                        tooltip="URL where audio will be served. Leave empty to use auto-generated URL."
                                      >
                                        <Input placeholder="https://your-api.com/audio/{execution_id}.mp3" />
                                      </Form.Item>
                                    );
                                  }}
                                </Form.Item>
                              </>
                            );
                          }
                          return null;
                        }}
                      </Form.Item>

                      <Form.Item
                        name={['config', 'audioConfig', 'includeTranscript']}
                        valuePropName="checked"
                        initialValue={true}
                      >
                        <Checkbox>Include text transcript with audio</Checkbox>
                      </Form.Item>

                      <Form.Item
                        name={['config', 'audioConfig', 'autoPlay']}
                        valuePropName="checked"
                        initialValue={true}
                      >
                        <Checkbox>Auto-play audio in playground</Checkbox>
                      </Form.Item>
                    </Card>
                  );
                }

                return null;
              }}
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

        {selectedNode.data.type === 'EXECUTE_WORKFLOW' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Call and execute another workflow. Map data between parent and child workflows.
            </Typography.Text>

            <Card size="small" title="Workflow Selection" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'workflowId']}
                label="Workflow"
                rules={[{ required: true, message: 'Please select a workflow to execute' }]}
              >
                <Select
                  placeholder={loadingWorkflows ? 'Loading workflows...' : 'Select a workflow'}
                  loading={loadingWorkflows}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={workflows.map(wf => ({
                    label: `${wf.name}${wf.status === 'deployed' ? ' (deployed)' : ''}`,
                    value: wf.id,
                  }))}
                  onChange={(value) => {
                    // Set the workflow name for display
                    const selectedWf = workflows.find(wf => wf.id === value);
                    if (selectedWf) {
                      form.setFieldValue(['config', 'workflowName'], selectedWf.name);
                    }
                  }}
                  notFoundContent={
                    loadingWorkflows ? (
                      <div style={{ textAlign: 'center', padding: 8 }}>
                        <Spin size="small" /> Loading...
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: 8 }}>
                        No workflows found.
                        <br />
                        <a href="/workflows" target="_blank" rel="noopener noreferrer">
                          Create one in Workflows
                        </a>
                      </div>
                    )
                  }
                />
              </Form.Item>
              <Form.Item name={['config', 'workflowName']} hidden>
                <Input />
              </Form.Item>

              <Button
                type="link"
                icon={<ReloadOutlined />}
                onClick={() => {
                  const urlParams = new URLSearchParams(window.location.search);
                  const currentWorkflowId = urlParams.get('id') || undefined;
                  fetchWorkflows(currentWorkflowId);
                }}
                size="small"
              >
                Refresh list
              </Button>
            </Card>

            <Card size="small" title="Execution Settings" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'executionMode']}
                label="Execution Mode"
                initialValue="sync"
                tooltip="How to execute the child workflow"
              >
                <Select
                  options={[
                    { label: 'Wait for completion (Sync)', value: 'sync' },
                    { label: 'Run in background (Async)', value: 'async' },
                    { label: 'Async with callback', value: 'async_callback' },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name={['config', 'timeout']}
                label="Timeout (ms)"
                initialValue={30000}
                tooltip="Maximum time to wait for workflow completion (sync mode)"
              >
                <InputNumber
                  min={1000}
                  max={300000}
                  step={1000}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Card>

            <Card size="small" title="Input Mapping" style={{ marginBottom: 16 }}>
              <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
                Map data from the current workflow to the child workflow's inputs.
              </Typography.Text>

              <Form.List name={['config', 'inputMapping']}>
                {(fields, { add, remove }) => (
                  <>
                    {fields.map(({ key, name, ...restField }) => (
                      <Card key={key} size="small" className="mb-2" style={{ background: '#f9f9f9' }}>
                        <Form.Item
                          {...restField}
                          name={[name, 'id']}
                          hidden
                          initialValue={`input-${Date.now()}-${key}`}
                        >
                          <Input />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'sourceField']}
                          label="Parent Field"
                          rules={[{ required: true, message: 'Source field is required' }]}
                          tooltip="Field from the current workflow state"
                        >
                          <Input placeholder="e.g., user_query, context.data" />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'targetField']}
                          label="Child Input"
                          rules={[{ required: true, message: 'Target field is required' }]}
                          tooltip="Field name in child workflow's input"
                        >
                          <Input placeholder="e.g., input, query, data" />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'transform']}
                          label="Transform (Optional)"
                          tooltip="JSONPath expression or simple transformation"
                        >
                          <Input placeholder="e.g., $.items[0], trim()" />
                        </Form.Item>

                        <Button
                          type="link"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(name)}
                          size="small"
                        >
                          Remove
                        </Button>
                      </Card>
                    ))}
                    <Button
                      type="dashed"
                      onClick={() => add({ id: `input-${Date.now()}` })}
                      block
                      icon={<PlusOutlined />}
                    >
                      Add Input Mapping
                    </Button>
                  </>
                )}
              </Form.List>
            </Card>

            <Card size="small" title="Output Mapping" style={{ marginBottom: 16 }}>
              <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
                Map data from the child workflow's outputs back to the parent workflow.
              </Typography.Text>

              <Form.List name={['config', 'outputMapping']}>
                {(fields, { add, remove }) => (
                  <>
                    {fields.map(({ key, name, ...restField }) => (
                      <Card key={key} size="small" className="mb-2" style={{ background: '#f9f9f9' }}>
                        <Form.Item
                          {...restField}
                          name={[name, 'id']}
                          hidden
                          initialValue={`output-${Date.now()}-${key}`}
                        >
                          <Input />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'sourceField']}
                          label="Child Output"
                          rules={[{ required: true, message: 'Source field is required' }]}
                          tooltip="Field from child workflow's output"
                        >
                          <Input placeholder="e.g., result, response, data" />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'targetField']}
                          label="Parent Field"
                          rules={[{ required: true, message: 'Target field is required' }]}
                          tooltip="Field name to set in parent workflow"
                        >
                          <Input placeholder="e.g., workflow_result, output" />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'transform']}
                          label="Transform (Optional)"
                          tooltip="JSONPath expression or simple transformation"
                        >
                          <Input placeholder="e.g., $.items[0], trim()" />
                        </Form.Item>

                        <Button
                          type="link"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(name)}
                          size="small"
                        >
                          Remove
                        </Button>
                      </Card>
                    ))}
                    <Button
                      type="dashed"
                      onClick={() => add({ id: `output-${Date.now()}` })}
                      block
                      icon={<PlusOutlined />}
                    >
                      Add Output Mapping
                    </Button>
                  </>
                )}
              </Form.List>
            </Card>

            <Card size="small" title="Error Handling" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'onError']}
                label="On Error"
                initialValue="stop"
                tooltip="What to do if the child workflow fails"
              >
                <Select
                  options={[
                    { label: 'Stop parent workflow', value: 'stop' },
                    { label: 'Continue with error in state', value: 'continue' },
                    { label: 'Use fallback value', value: 'fallback' },
                  ]}
                />
              </Form.Item>

              <Form.Item noStyle shouldUpdate>
                {() => {
                  const onError = form.getFieldValue(['config', 'onError']);
                  if (onError === 'fallback') {
                    return (
                      <Form.Item
                        name={['config', 'fallbackValue']}
                        label="Fallback Value"
                        tooltip="Value to use if child workflow fails (JSON)"
                      >
                        <TextArea
                          rows={3}
                          placeholder='{"error": "Workflow failed", "result": null}'
                          style={{ fontFamily: 'monospace', fontSize: 12 }}
                        />
                      </Form.Item>
                    );
                  }
                  return null;
                }}
              </Form.Item>
            </Card>

            <Card size="small" title="Advanced Options" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'passFullState']}
                valuePropName="checked"
                initialValue={false}
              >
                <Checkbox>Pass full parent state (ignores input mapping)</Checkbox>
              </Form.Item>

              <Form.Item
                name={['config', 'inheritCredentials']}
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>Inherit parent credentials</Checkbox>
              </Form.Item>
            </Card>

            <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
              <strong>Output:</strong> Child workflow results available as{' '}
              <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: 2 }}>
                {'{{node_id.result}}'}
              </code>
              {' '}or through output mapping.
            </Typography.Text>
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
                                  if (backend === 'redis') return cred.provider === 'redis';
                                  if (backend === 'postgres') return cred.provider === 'postgresql' || (cred.provider as string) === 'postgres';
                                  if (backend === 'mongodb') return cred.provider === 'mongodb';
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

        {selectedNode.data.type === 'AUDIO_TO_TEXT' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Transcribe audio to text using speech-to-text providers. Can read audio from INPUT node or external sources.
            </Typography.Text>

            <Card size="small" title="Audio Source" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'audioSource']}
                label="Source Type"
                initialValue="previous_node"
                rules={[{ required: true, message: 'Please select audio source' }]}
              >
                <Select
                  options={[
                    { label: 'Previous Node (INPUT)', value: 'previous_node' },
                    { label: 'Audio URL', value: 'url' },
                    { label: 'Base64 Encoded', value: 'base64' },
                    { label: 'Twilio Media Stream', value: 'twilio_stream' },
                  ]}
                />
              </Form.Item>

              <Form.Item noStyle shouldUpdate>
                {() => {
                  const audioSource = form.getFieldValue(['config', 'audioSource']) || 'previous_node';

                  if (audioSource === 'previous_node') {
                    return (
                      <>
                        <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
                          Audio will be automatically read from INPUT node. Make sure INPUT is in audio mode.
                        </Typography.Text>
                        <Form.Item
                          name={['config', 'sourceNodeId']}
                          label="Source Node ID (Optional)"
                          tooltip="Leave empty to auto-detect INPUT node with audio data"
                        >
                          <Select
                            allowClear
                            placeholder="Auto-detect"
                            options={getUpstreamNodes(selectedNode).map(node => ({
                              label: `${node.data.label} (${node.id})`,
                              value: node.id,
                            }))}
                          />
                        </Form.Item>
                      </>
                    );
                  }

                  if (audioSource === 'url') {
                    return (
                      <Form.Item
                        name={['config', 'audioUrl']}
                        label="Audio URL"
                        tooltip="URL to the audio file (e.g., Twilio recording URL)"
                      >
                        <TemplateHelper
                          value={form.getFieldValue(['config', 'audioUrl']) || ''}
                          onChange={(value) => form.setFieldValue(['config', 'audioUrl'], value)}
                          availableNodes={getUpstreamNodes(selectedNode)}
                          placeholder="https://api.twilio.com/... or {{input-1.recording_url}}"
                          rows={2}
                        />
                      </Form.Item>
                    );
                  }

                  if (audioSource === 'base64') {
                    return (
                      <>
                        <Form.Item
                          name={['config', 'audioData']}
                          label="Base64 Audio Data"
                          tooltip="Base64 encoded audio data (use template from upstream node)"
                        >
                          <TemplateHelper
                            value={form.getFieldValue(['config', 'audioData']) || ''}
                            onChange={(value) => form.setFieldValue(['config', 'audioData'], value)}
                            availableNodes={getUpstreamNodes(selectedNode)}
                            placeholder="{{input-1.audio_base64}}"
                            rows={2}
                          />
                        </Form.Item>

                        <Form.Item
                          name={['config', 'audioFormat']}
                          label="Audio Format"
                          initialValue="wav"
                        >
                          <Select
                            options={[
                              { label: 'WAV', value: 'wav' },
                              { label: 'MP3', value: 'mp3' },
                              { label: 'OGG', value: 'ogg' },
                              { label: 'WebM', value: 'webm' },
                              { label: 'FLAC', value: 'flac' },
                              { label: 'Mulaw (Twilio)', value: 'mulaw' },
                            ]}
                          />
                        </Form.Item>
                      </>
                    );
                  }

                  if (audioSource === 'twilio_stream') {
                    return (
                      <>
                        <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
                          Twilio media streams use mulaw audio at 8kHz. Audio data will be collected from WebSocket.
                        </Typography.Text>

                        <Form.Item
                          name={['config', 'audioData']}
                          label="Twilio Audio Data (Base64)"
                          tooltip="Base64 encoded mulaw audio from Twilio media stream"
                        >
                          <TemplateHelper
                            value={form.getFieldValue(['config', 'audioData']) || ''}
                            onChange={(value) => form.setFieldValue(['config', 'audioData'], value)}
                            availableNodes={getUpstreamNodes(selectedNode)}
                            placeholder="{{input-1.twilio_audio}}"
                            rows={2}
                          />
                        </Form.Item>

                        <Form.Item
                          name={['config', 'twilioFormat']}
                          valuePropName="checked"
                          initialValue={true}
                        >
                          <Checkbox>Twilio mulaw format (8kHz)</Checkbox>
                        </Form.Item>
                      </>
                    );
                  }

                  return null;
                }}
              </Form.Item>

              <Form.Item
                name={['config', 'sampleRate']}
                label="Sample Rate (Hz)"
                initialValue={8000}
                tooltip="Audio sample rate. Twilio uses 8000 Hz."
              >
                <Select
                  options={[
                    { label: '8000 Hz (Twilio)', value: 8000 },
                    { label: '16000 Hz', value: 16000 },
                    { label: '22050 Hz', value: 22050 },
                    { label: '44100 Hz (CD Quality)', value: 44100 },
                    { label: '48000 Hz', value: 48000 },
                  ]}
                />
              </Form.Item>
            </Card>

            <Card size="small" title="Transcription Provider" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'provider']}
                label="Provider"
                initialValue="openai_whisper"
                rules={[{ required: true, message: 'Please select a provider' }]}
              >
                <Select
                  options={[
                    { label: 'OpenAI Whisper', value: 'openai_whisper' },
                    { label: 'Deepgram', value: 'deepgram' },
                    { label: 'AssemblyAI', value: 'assemblyai' },
                    { label: 'Google Speech-to-Text', value: 'google_stt' },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name={['config', 'credentialId']}
                label="API Credential"
                tooltip="Select the API credential for the transcription provider"
                rules={[{ required: true, message: 'Please select a credential' }]}
              >
                <Select
                  placeholder="Select credential"
                  options={credentials
                    .filter(cred => {
                      const provider = form.getFieldValue(['config', 'provider']) || 'openai_whisper';
                      // Filter credentials based on provider - allow all credentials for transcription providers
                      // since user may have custom named credentials
                      if (provider === 'openai_whisper') return cred.provider === 'openai';
                      if (provider === 'google_stt') return cred.provider === 'google';
                      // For deepgram, assemblyai, and others - show all API key type credentials
                      return true;
                    })
                    .map(cred => ({
                      label: `${cred.name} (${cred.provider})`,
                      value: cred.id,
                    }))}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>

              <Form.Item noStyle shouldUpdate>
                {() => {
                  const provider = form.getFieldValue(['config', 'provider']) || 'openai_whisper';

                  return (
                    <Form.Item
                      name={['config', 'model']}
                      label="Model"
                      tooltip="Optional: Specific model to use for transcription"
                    >
                      <Select
                        allowClear
                        placeholder="Default model"
                        options={
                          provider === 'openai_whisper'
                            ? [{ label: 'whisper-1', value: 'whisper-1' }]
                            : provider === 'deepgram'
                            ? [
                                { label: 'nova-2 (recommended)', value: 'nova-2' },
                                { label: 'nova', value: 'nova' },
                                { label: 'enhanced', value: 'enhanced' },
                                { label: 'base', value: 'base' },
                              ]
                            : provider === 'google_stt'
                            ? [
                                { label: 'Default', value: '' },
                                { label: 'Phone call', value: 'phone_call' },
                                { label: 'Video', value: 'video' },
                              ]
                            : []
                        }
                      />
                    </Form.Item>
                  );
                }}
              </Form.Item>

              <Form.Item
                name={['config', 'language']}
                label="Language"
                tooltip="Language code for transcription (e.g., 'en', 'es', 'fr')"
              >
                <Select
                  allowClear
                  placeholder="Auto-detect"
                  showSearch
                  options={[
                    { label: 'Auto-detect', value: '' },
                    { label: 'English (en)', value: 'en' },
                    { label: 'Spanish (es)', value: 'es' },
                    { label: 'French (fr)', value: 'fr' },
                    { label: 'German (de)', value: 'de' },
                    { label: 'Italian (it)', value: 'it' },
                    { label: 'Portuguese (pt)', value: 'pt' },
                    { label: 'Dutch (nl)', value: 'nl' },
                    { label: 'Japanese (ja)', value: 'ja' },
                    { label: 'Korean (ko)', value: 'ko' },
                    { label: 'Chinese (zh)', value: 'zh' },
                    { label: 'Russian (ru)', value: 'ru' },
                    { label: 'Arabic (ar)', value: 'ar' },
                    { label: 'Hindi (hi)', value: 'hi' },
                  ]}
                />
              </Form.Item>
            </Card>

            <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
              <strong>Output:</strong> The transcribed text will be available as{' '}
              <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: 2 }}>
                {'{{node_id.text}}'}
              </code>
            </Typography.Text>
          </>
        )}

        {selectedNode.data.type === 'CODE' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Execute custom JavaScript or Python code. Access data from upstream nodes and return results.
            </Typography.Text>

            <Card size="small" title="Language & Code" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'language']}
                label="Language"
                initialValue="javascript"
                rules={[{ required: true, message: 'Please select a language' }]}
              >
                <Select
                  options={[
                    { label: 'JavaScript', value: 'javascript' },
                    { label: 'Python', value: 'python' },
                  ]}
                />
              </Form.Item>

              <Form.Item noStyle shouldUpdate>
                {() => {
                  const language = form.getFieldValue(['config', 'language']) || 'javascript';
                  const placeholder = language === 'javascript'
                    ? `// Access input data via 'input' variable
// Return data will be available to downstream nodes

const result = {
  processed: input.message.toUpperCase(),
  timestamp: new Date().toISOString()
};

return result;`
                    : `# Access input data via 'input' variable
# Return data will be available to downstream nodes

result = {
    "processed": input["message"].upper(),
    "timestamp": datetime.now().isoformat()
}

return result`;

                  return (
                    <Form.Item
                      name={['config', 'code']}
                      label="Code"
                      rules={[{ required: true, message: 'Please enter code to execute' }]}
                    >
                      <TextArea
                        rows={12}
                        placeholder={placeholder}
                        style={{
                          fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                          fontSize: 12,
                          backgroundColor: '#1e1e1e',
                          color: '#d4d4d4',
                          border: '1px solid #3c3c3c',
                        }}
                      />
                    </Form.Item>
                  );
                }}
              </Form.Item>
            </Card>

            <Card size="small" title="Input Mapping" style={{ marginBottom: 16 }}>
              <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
                Map data from upstream nodes to variables in your code. The mapped data will be available in the 'input' object.
              </Typography.Text>

              <Form.List name={['config', 'inputMapping']}>
                {(fields, { add, remove }) => (
                  <>
                    {fields.map(({ key, name, ...restField }) => (
                      <Card key={key} size="small" className="mb-2" style={{ background: '#f9f9f9' }}>
                        <Form.Item
                          {...restField}
                          name={[name, 'variableName']}
                          label="Variable Name"
                          rules={[{ required: true, message: 'Variable name is required' }]}
                        >
                          <Input placeholder="e.g., userMessage" />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'sourceNodeId']}
                          label="Source Node"
                          rules={[{ required: true, message: 'Source node is required' }]}
                        >
                          <Select
                            placeholder="Select source node"
                            options={getUpstreamNodes(selectedNode).map(node => ({
                              label: `${node.data.label} (${node.id})`,
                              value: node.id,
                            }))}
                          />
                        </Form.Item>

                        <Form.Item
                          {...restField}
                          name={[name, 'sourceField']}
                          label="Source Field (Optional)"
                          tooltip="Specific field from node output. Leave empty for entire output."
                        >
                          <Input placeholder="e.g., message, text, data.value" />
                        </Form.Item>

                        <Button
                          type="link"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(name)}
                          size="small"
                        >
                          Remove Mapping
                        </Button>
                      </Card>
                    ))}
                    <Button
                      type="dashed"
                      onClick={() => add()}
                      block
                      icon={<PlusOutlined />}
                    >
                      Add Input Mapping
                    </Button>
                  </>
                )}
              </Form.List>
            </Card>

            <Card size="small" title="Output & Settings" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'outputVariable']}
                label="Output Variable Name"
                initialValue="result"
                tooltip="The variable name returned from your code that will be available to downstream nodes"
              >
                <Input placeholder="result" />
              </Form.Item>

              <Form.Item
                name={['config', 'timeout']}
                label="Timeout (ms)"
                initialValue={30000}
                tooltip="Maximum execution time before the code is terminated"
              >
                <InputNumber
                  min={1000}
                  max={300000}
                  step={1000}
                  style={{ width: '100%' }}
                  placeholder="30000"
                />
              </Form.Item>

              <Form.Item
                name={['config', 'sandboxed']}
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>Run in sandbox (recommended for security)</Checkbox>
              </Form.Item>
            </Card>

            <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
              <strong>Available in code:</strong>
              <ul style={{ margin: '4px 0', paddingLeft: 16 }}>
                <li><code>input</code> - Object with mapped input data</li>
                <li><code>console.log()</code> - Log output (visible in execution trace)</li>
                <li><code>return</code> - Return data to downstream nodes</li>
              </ul>
            </Typography.Text>
          </>
        )}

        {selectedNode.data.type === 'TEXT_TO_AUDIO' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Convert text to speech audio. Supports multiple TTS providers for high-quality voice synthesis.
            </Typography.Text>

            <Card size="small" title="Text Source" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'textSource']}
                label="Source Type"
                initialValue="last_message"
                rules={[{ required: true, message: 'Please select text source' }]}
              >
                <Select
                  options={[
                    { label: 'Last Message (LLM Output)', value: 'last_message' },
                    { label: 'Template', value: 'template' },
                    { label: 'Fixed Text', value: 'fixed' },
                  ]}
                />
              </Form.Item>

              <Form.Item noStyle shouldUpdate>
                {() => {
                  const textSource = form.getFieldValue(['config', 'textSource']) || 'last_message';

                  if (textSource === 'template') {
                    return (
                      <Form.Item
                        name={['config', 'textTemplate']}
                        label="Text Template"
                        tooltip="Use templates to reference upstream node outputs"
                      >
                        <TemplateHelper
                          value={form.getFieldValue(['config', 'textTemplate']) || ''}
                          onChange={(value) => form.setFieldValue(['config', 'textTemplate'], value)}
                          availableNodes={getUpstreamNodes(selectedNode)}
                          placeholder="{{llm-agent-1.response}} or Hello, {{input-1.name}}!"
                          rows={3}
                        />
                      </Form.Item>
                    );
                  }

                  if (textSource === 'fixed') {
                    return (
                      <Form.Item
                        name={['config', 'fixedText']}
                        label="Fixed Text"
                        tooltip="Static text to convert to speech"
                      >
                        <TextArea
                          rows={3}
                          placeholder="Enter the text to convert to speech..."
                        />
                      </Form.Item>
                    );
                  }

                  return (
                    <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                      Will use the last message from the conversation (typically LLM response)
                    </Typography.Text>
                  );
                }}
              </Form.Item>
            </Card>

            <Card size="small" title="TTS Provider" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'provider']}
                label="Provider"
                initialValue="openai_tts"
                rules={[{ required: true, message: 'Please select a provider' }]}
              >
                <Select
                  options={[
                    { label: 'OpenAI TTS', value: 'openai_tts' },
                    { label: 'ElevenLabs', value: 'elevenlabs' },
                    { label: 'Google Cloud TTS', value: 'google_tts' },
                    { label: 'Amazon Polly', value: 'amazon_polly' },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name={['config', 'credentialId']}
                label="API Credential"
                tooltip="Select the API credential for the TTS provider"
                rules={[{ required: true, message: 'Please select a credential' }]}
              >
                <Select
                  placeholder="Select credential"
                  options={credentials
                    .filter(cred => {
                      const provider = form.getFieldValue(['config', 'provider']) || 'openai_tts';
                      if (provider === 'openai_tts') return cred.provider === 'openai';
                      if (provider === 'google_tts') return cred.provider === 'google';
                      return true;
                    })
                    .map(cred => ({
                      label: `${cred.name} (${cred.provider})`,
                      value: cred.id,
                    }))}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>

              <Form.Item noStyle shouldUpdate>
                {() => {
                  const provider = form.getFieldValue(['config', 'provider']) || 'openai_tts';

                  return (
                    <>
                      <Form.Item
                        name={['config', 'voice']}
                        label="Voice"
                        tooltip="Select a voice for speech synthesis"
                      >
                        <Select
                          allowClear
                          placeholder="Default voice"
                          showSearch
                          options={
                            provider === 'openai_tts'
                              ? [
                                  { label: 'Alloy (Neutral)', value: 'alloy' },
                                  { label: 'Echo (Male)', value: 'echo' },
                                  { label: 'Fable (Neutral)', value: 'fable' },
                                  { label: 'Onyx (Male)', value: 'onyx' },
                                  { label: 'Nova (Female)', value: 'nova' },
                                  { label: 'Shimmer (Female)', value: 'shimmer' },
                                ]
                              : provider === 'elevenlabs'
                              ? [
                                  { label: 'Rachel (Female)', value: '21m00Tcm4TlvDq8ikWAM' },
                                  { label: 'Domi (Female)', value: 'AZnzlk1XvdvUeBnXmlld' },
                                  { label: 'Bella (Female)', value: 'EXAVITQu4vr4xnSDxMaL' },
                                  { label: 'Antoni (Male)', value: 'ErXwobaYiN019PkySvjV' },
                                  { label: 'Josh (Male)', value: 'TxGEqnHWrfWFTfGW9XjX' },
                                  { label: 'Arnold (Male)', value: 'VR6AewLTigWG4xSOukaG' },
                                  { label: 'Adam (Male)', value: 'pNInz6obpgDQGcFmaJgB' },
                                  { label: 'Sam (Male)', value: 'yoZ06aMxZJJ28mfd3POQ' },
                                ]
                              : provider === 'google_tts'
                              ? [
                                  { label: 'Wavenet A (Male)', value: 'en-US-Wavenet-A' },
                                  { label: 'Wavenet C (Female)', value: 'en-US-Wavenet-C' },
                                  { label: 'Wavenet D (Male)', value: 'en-US-Wavenet-D' },
                                  { label: 'Wavenet F (Female)', value: 'en-US-Wavenet-F' },
                                  { label: 'Neural2 A (Male)', value: 'en-US-Neural2-A' },
                                  { label: 'Neural2 C (Female)', value: 'en-US-Neural2-C' },
                                ]
                              : provider === 'amazon_polly'
                              ? [
                                  { label: 'Joanna (Female)', value: 'Joanna' },
                                  { label: 'Matthew (Male)', value: 'Matthew' },
                                  { label: 'Ivy (Female)', value: 'Ivy' },
                                  { label: 'Kendra (Female)', value: 'Kendra' },
                                  { label: 'Salli (Female)', value: 'Salli' },
                                  { label: 'Joey (Male)', value: 'Joey' },
                                ]
                              : []
                          }
                        />
                      </Form.Item>

                      {provider === 'openai_tts' && (
                        <Form.Item
                          name={['config', 'model']}
                          label="Model"
                          initialValue="tts-1"
                        >
                          <Select
                            options={[
                              { label: 'TTS-1 (Standard)', value: 'tts-1' },
                              { label: 'TTS-1-HD (High Quality)', value: 'tts-1-hd' },
                            ]}
                          />
                        </Form.Item>
                      )}
                    </>
                  );
                }}
              </Form.Item>
            </Card>

            <Card size="small" title="Output Settings" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'outputFormat']}
                label="Audio Format"
                initialValue="mp3"
              >
                <Select
                  options={[
                    { label: 'MP3', value: 'mp3' },
                    { label: 'WAV', value: 'wav' },
                    { label: 'OGG', value: 'ogg' },
                    { label: 'Mulaw (Twilio)', value: 'mulaw' },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name={['config', 'speed']}
                label="Speech Speed"
                initialValue={1.0}
                tooltip="Speed of speech (0.5 = slow, 1.0 = normal, 2.0 = fast)"
              >
                <InputNumber
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item
                name={['config', 'language']}
                label="Language"
                tooltip="Language for multilingual voices"
              >
                <Select
                  allowClear
                  placeholder="Default (English)"
                  showSearch
                  options={[
                    { label: 'English (US)', value: 'en-US' },
                    { label: 'English (UK)', value: 'en-GB' },
                    { label: 'Spanish', value: 'es-ES' },
                    { label: 'French', value: 'fr-FR' },
                    { label: 'German', value: 'de-DE' },
                    { label: 'Italian', value: 'it-IT' },
                    { label: 'Portuguese', value: 'pt-BR' },
                    { label: 'Japanese', value: 'ja-JP' },
                    { label: 'Korean', value: 'ko-KR' },
                    { label: 'Chinese', value: 'zh-CN' },
                  ]}
                />
              </Form.Item>
            </Card>

            <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
              <strong>Output:</strong> Audio data (base64) available as{' '}
              <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: 2 }}>
                {'{{node_id.audio_data}}'}
              </code>
            </Typography.Text>
          </>
        )}

        {selectedNode.data.type === 'VOICE_INPUT' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Receive incoming voice calls from Twilio or Etisalat. Configure greeting and recording settings.
            </Typography.Text>

            <Card size="small" title="Voice Provider" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'provider']}
                label="Provider"
                initialValue="twilio"
                rules={[{ required: true, message: 'Please select a provider' }]}
              >
                <Select
                  options={[
                    { label: 'Twilio (Global)', value: 'twilio' },
                    { label: 'Etisalat CPaaS (UAE/MENA)', value: 'etisalat' },
                  ]}
                />
              </Form.Item>

              <Form.Item noStyle shouldUpdate={(prev, curr) =>
                prev?.config?.provider !== curr?.config?.provider
              }>
                {() => {
                  const provider = form.getFieldValue(['config', 'provider']) || 'twilio';
                  const filteredCredentials = credentials.filter(cred => cred.provider === provider);

                  return (
                    <Form.Item
                      name={['config', 'credentialId']}
                      label="Voice Credential"
                      tooltip="Select the credential for your voice provider"
                      rules={[{ required: true, message: 'Please select a credential' }]}
                      help={filteredCredentials.length === 0 ?
                        `No ${provider === 'twilio' ? 'Twilio' : 'Etisalat'} credentials found. Create one in the Credentials page.` :
                        undefined
                      }
                    >
                      <Select
                        placeholder={`Select ${provider === 'twilio' ? 'Twilio' : 'Etisalat'} credential`}
                        options={filteredCredentials.map(cred => ({
                          label: cred.name,
                          value: cred.id,
                        }))}
                        showSearch
                        filterOption={(input, option) =>
                          (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                        }
                        notFoundContent={
                          <div style={{ textAlign: 'center', padding: 8 }}>
                            No {provider === 'twilio' ? 'Twilio' : 'Etisalat'} credentials found.
                            <br />
                            <a href="/credentials" target="_blank" rel="noopener noreferrer">
                              Create one in Credentials
                            </a>
                          </div>
                        }
                      />
                    </Form.Item>
                  );
                }}
              </Form.Item>
            </Card>

            <Card size="small" title="Greeting" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'greeting']}
                label="Greeting Message"
                tooltip="Message to play when call connects"
                initialValue="Hello! How can I help you today?"
              >
                <TextArea
                  rows={2}
                  placeholder="Hello! How can I help you today?"
                />
              </Form.Item>

              <Form.Item
                name={['config', 'language']}
                label="Language"
                initialValue="en-US"
                tooltip="Language for text-to-speech"
              >
                <Select
                  showSearch
                  options={[
                    { label: 'English (US)', value: 'en-US' },
                    { label: 'English (UK)', value: 'en-GB' },
                    { label: 'Arabic (UAE)', value: 'ar-AE' },
                    { label: 'Arabic (Saudi)', value: 'ar-SA' },
                    { label: 'Hindi', value: 'hi-IN' },
                    { label: 'French', value: 'fr-FR' },
                    { label: 'German', value: 'de-DE' },
                    { label: 'Spanish', value: 'es-ES' },
                  ]}
                />
              </Form.Item>
            </Card>

            <Card size="small" title="Recording Settings" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'maxDuration']}
                label="Max Duration (seconds)"
                initialValue={60}
                tooltip="Maximum recording duration"
              >
                <InputNumber min={5} max={300} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name={['config', 'silenceTimeout']}
                label="Silence Timeout (seconds)"
                initialValue={3}
                tooltip="Stop recording after this much silence"
              >
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name={['config', 'playBeep']}
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>Play beep before recording</Checkbox>
              </Form.Item>

              <Form.Item
                name={['config', 'trimSilence']}
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>Trim silence from recording</Checkbox>
              </Form.Item>

              <Form.Item
                name={['config', 'audioFormat']}
                label="Audio Format"
                initialValue="mp3"
              >
                <Select
                  options={[
                    { label: 'MP3', value: 'mp3' },
                    { label: 'WAV', value: 'wav' },
                    { label: 'Mulaw (Twilio native)', value: 'mulaw' },
                  ]}
                />
              </Form.Item>
            </Card>

            <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
              <strong>Output:</strong> Audio data available as{' '}
              <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: 2 }}>
                {'{{node_id.audio_data}}'}
              </code>
              {' '}and caller info as{' '}
              <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: 2 }}>
                {'{{node_id.caller_id}}'}
              </code>
            </Typography.Text>
          </>
        )}

        {selectedNode.data.type === 'VOICE_OUTPUT' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Play audio response to the caller. Receives audio from TEXT_TO_AUDIO node.
            </Typography.Text>

            <Card size="small" title="Audio Source" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'inputField']}
                label="Audio Input Field"
                initialValue="audio_data"
                tooltip="Field name containing the audio data from previous node"
              >
                <Select
                  options={[
                    { label: 'audio_data', value: 'audio_data' },
                    { label: 'output_audio', value: 'output_audio' },
                    { label: 'tts_audio', value: 'tts_audio' },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name={['config', 'audioFormat']}
                label="Audio Format"
                initialValue="mp3"
              >
                <Select
                  options={[
                    { label: 'MP3', value: 'mp3' },
                    { label: 'WAV', value: 'wav' },
                    { label: 'Mulaw (Twilio)', value: 'mulaw' },
                  ]}
                />
              </Form.Item>
            </Card>

            <Card size="small" title="Call Action" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'afterResponse']}
                label="After Playing Response"
                initialValue="hangup"
              >
                <Select
                  options={[
                    { label: 'Hang up call', value: 'hangup' },
                    { label: 'Continue conversation', value: 'continue' },
                    { label: 'Transfer call', value: 'transfer' },
                  ]}
                />
              </Form.Item>

              <Form.Item noStyle shouldUpdate>
                {() => {
                  const afterResponse = form.getFieldValue(['config', 'afterResponse']);
                  if (afterResponse === 'transfer') {
                    return (
                      <Form.Item
                        name={['config', 'transferTo']}
                        label="Transfer To"
                        tooltip="Phone number to transfer the call to"
                        rules={[{ required: true, message: 'Please enter transfer number' }]}
                      >
                        <Input placeholder="+1234567890" />
                      </Form.Item>
                    );
                  }
                  return null;
                }}
              </Form.Item>

              <Form.Item
                name={['config', 'loop']}
                label="Loop Count"
                initialValue={1}
                tooltip="Number of times to play the audio"
              >
                <InputNumber min={1} max={5} style={{ width: '100%' }} />
              </Form.Item>
            </Card>

            <Card size="small" title="Fallback" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'fallbackMessage']}
                label="Fallback Message"
                tooltip="Message to speak if no audio is available"
                initialValue="Sorry, I couldn't process that request."
              >
                <TextArea
                  rows={2}
                  placeholder="Sorry, I couldn't process that request."
                />
              </Form.Item>

              <Form.Item
                name={['config', 'fallbackVoice']}
                label="Fallback Voice"
                initialValue="Polly.Joanna"
              >
                <Select
                  options={[
                    { label: 'Polly.Joanna (Female)', value: 'Polly.Joanna' },
                    { label: 'Polly.Matthew (Male)', value: 'Polly.Matthew' },
                    { label: 'Polly.Amy (British Female)', value: 'Polly.Amy' },
                    { label: 'Polly.Brian (British Male)', value: 'Polly.Brian' },
                    { label: 'Polly.Zeina (Arabic)', value: 'Polly.Zeina' },
                  ]}
                />
              </Form.Item>
            </Card>

            <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
              <strong>Tip:</strong> Connect a TEXT_TO_AUDIO node before this to convert LLM responses to speech.
            </Typography.Text>
          </>
        )}

        {selectedNode.data.type === 'WHATSAPP_INPUT' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Receive WhatsApp messages via Meta Cloud API. Configure webhook and message handling.
            </Typography.Text>

            <Card size="small" title="WhatsApp Connection" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'credentialId']}
                label="WhatsApp Credential"
                tooltip="Select your Meta Cloud API credential"
                rules={[{ required: true, message: 'Please select a credential' }]}
                help={credentials.filter(c => c.provider === 'whatsapp_meta').length === 0 ?
                  'No WhatsApp credentials found. Create one in the Credentials page.' :
                  undefined
                }
              >
                <Select
                  placeholder="Select WhatsApp credential"
                  options={credentials
                    .filter(cred => cred.provider === 'whatsapp_meta')
                    .map(cred => ({
                      label: cred.name,
                      value: cred.id,
                    }))}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  notFoundContent={
                    <div style={{ textAlign: 'center', padding: 8 }}>
                      No WhatsApp credentials found.
                      <br />
                      <a href="/credentials" target="_blank" rel="noopener noreferrer">
                        Create one in Credentials
                      </a>
                    </div>
                  }
                />
              </Form.Item>

              <Form.Item
                name={['config', 'verifyToken']}
                label="Webhook Verify Token"
                tooltip="Token for Meta webhook verification (you create this)"
                rules={[{ required: true, message: 'Please enter a verify token' }]}
              >
                <Input placeholder="your_secure_verify_token" />
              </Form.Item>
            </Card>

            <Card size="small" title="Message Settings" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'messageTypes']}
                label="Accepted Message Types"
                initialValue={['text']}
                tooltip="Types of messages to process"
              >
                <Select
                  mode="multiple"
                  placeholder="Select message types"
                  options={[
                    { label: 'Text', value: 'text' },
                    { label: 'Image', value: 'image' },
                    { label: 'Video', value: 'video' },
                    { label: 'Audio', value: 'audio' },
                    { label: 'Document', value: 'document' },
                    { label: 'Location', value: 'location' },
                    { label: 'Interactive (Buttons/Lists)', value: 'interactive' },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name={['config', 'language']}
                label="Language"
                initialValue="en"
                tooltip="Default language for responses"
              >
                <Select
                  showSearch
                  options={[
                    { label: 'English', value: 'en' },
                    { label: 'Arabic', value: 'ar' },
                    { label: 'Hindi', value: 'hi' },
                    { label: 'Spanish', value: 'es' },
                    { label: 'French', value: 'fr' },
                    { label: 'German', value: 'de' },
                    { label: 'Portuguese', value: 'pt' },
                    { label: 'Chinese', value: 'zh' },
                  ]}
                />
              </Form.Item>

              <Form.Item
                name={['config', 'welcomeMessage']}
                label="Welcome Message"
                tooltip="Optional message for new conversations"
              >
                <TextArea
                  rows={2}
                  placeholder="Hello! How can I help you today?"
                />
              </Form.Item>

              <Form.Item
                name={['config', 'errorMessage']}
                label="Error Message"
                tooltip="Message sent when processing fails"
                initialValue="Sorry, I encountered an error. Please try again."
              >
                <TextArea
                  rows={2}
                  placeholder="Sorry, I encountered an error. Please try again."
                />
              </Form.Item>

              <Form.Item
                name={['config', 'autoMarkRead']}
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>Automatically mark messages as read</Checkbox>
              </Form.Item>
            </Card>

            <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
              <strong>Webhook URL:</strong> Configure in Meta Dashboard as{' '}
              <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: 2 }}>
                https://your-domain/api/v1/whatsapp/webhook/{'{{deployment_id}}'}?api_key={'{{api_key}}'}
              </code>
            </Typography.Text>
          </>
        )}

        {selectedNode.data.type === 'WHATSAPP_OUTPUT' && (
          <>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              Send responses back to WhatsApp. Supports text, media, templates, and interactive messages.
            </Typography.Text>

            <Card size="small" title="Response Type" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'responseType']}
                label="Message Type"
                initialValue="text"
                tooltip="Type of message to send"
              >
                <Select
                  options={[
                    { label: 'Text Message', value: 'text' },
                    { label: 'Template Message', value: 'template' },
                    { label: 'Media (Image/Video/Doc)', value: 'media' },
                    { label: 'Interactive (Buttons/List)', value: 'interactive' },
                  ]}
                />
              </Form.Item>
            </Card>

            <Form.Item noStyle shouldUpdate>
              {() => {
                const responseType = form.getFieldValue(['config', 'responseType']);

                if (responseType === 'template') {
                  return (
                    <Card size="small" title="Template Settings" style={{ marginBottom: 16 }}>
                      <Form.Item
                        name={['config', 'templateName']}
                        label="Template Name"
                        tooltip="Name of the approved template"
                        rules={[{ required: true, message: 'Template name is required' }]}
                      >
                        <Input placeholder="order_confirmation" />
                      </Form.Item>

                      <Form.Item
                        name={['config', 'templateLanguage']}
                        label="Template Language"
                        initialValue="en"
                      >
                        <Select
                          options={[
                            { label: 'English', value: 'en' },
                            { label: 'English (US)', value: 'en_US' },
                            { label: 'Arabic', value: 'ar' },
                            { label: 'Spanish', value: 'es' },
                            { label: 'French', value: 'fr' },
                          ]}
                        />
                      </Form.Item>

                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                        Template variables are passed from the workflow context.
                      </Typography.Text>
                    </Card>
                  );
                }

                if (responseType === 'media') {
                  return (
                    <Card size="small" title="Media Settings" style={{ marginBottom: 16 }}>
                      <Form.Item
                        name={['config', 'mediaType']}
                        label="Media Type"
                        initialValue="image"
                      >
                        <Select
                          options={[
                            { label: 'Image', value: 'image' },
                            { label: 'Video', value: 'video' },
                            { label: 'Audio', value: 'audio' },
                            { label: 'Document', value: 'document' },
                          ]}
                        />
                      </Form.Item>

                      <Form.Item
                        name={['config', 'mediaCaption']}
                        label="Caption"
                        tooltip="Optional caption for the media"
                      >
                        <TextArea rows={2} placeholder="Check out this file!" />
                      </Form.Item>

                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                        Media URL is passed from the workflow context.
                      </Typography.Text>
                    </Card>
                  );
                }

                if (responseType === 'interactive') {
                  return (
                    <Card size="small" title="Interactive Settings" style={{ marginBottom: 16 }}>
                      <Form.Item
                        name={['config', 'interactiveType']}
                        label="Interactive Type"
                        initialValue="button"
                      >
                        <Select
                          options={[
                            { label: 'Quick Reply Buttons (max 3)', value: 'button' },
                            { label: 'List Menu (max 10 items)', value: 'list' },
                          ]}
                        />
                      </Form.Item>

                      <Form.Item noStyle shouldUpdate>
                        {() => {
                          const interactiveType = form.getFieldValue(['config', 'interactiveType']);

                          if (interactiveType === 'button') {
                            return (
                              <>
                                <Form.Item
                                  name={['config', 'headerText']}
                                  label="Header (optional)"
                                  tooltip="Max 60 characters"
                                >
                                  <Input placeholder="Choose an option" maxLength={60} />
                                </Form.Item>

                                <Form.List name={['config', 'buttons']} initialValue={[]}>
                                  {(fields, { add, remove }) => (
                                    <>
                                      {fields.map((field, index) => (
                                        <Space key={field.key} align="baseline" style={{ display: 'flex', marginBottom: 8 }}>
                                          <Form.Item
                                            {...field}
                                            name={[field.name, 'id']}
                                            rules={[{ required: true }]}
                                            style={{ marginBottom: 0 }}
                                          >
                                            <Input placeholder="btn_id" style={{ width: 80 }} />
                                          </Form.Item>
                                          <Form.Item
                                            {...field}
                                            name={[field.name, 'title']}
                                            rules={[{ required: true, max: 20 }]}
                                            style={{ marginBottom: 0 }}
                                          >
                                            <Input placeholder="Button Text" maxLength={20} style={{ width: 120 }} />
                                          </Form.Item>
                                          <DeleteOutlined onClick={() => remove(field.name)} style={{ color: '#ff4d4f' }} />
                                        </Space>
                                      ))}
                                      {fields.length < 3 && (
                                        <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                                          Add Button
                                        </Button>
                                      )}
                                    </>
                                  )}
                                </Form.List>
                              </>
                            );
                          }

                          if (interactiveType === 'list') {
                            return (
                              <Form.Item
                                name={['config', 'listButtonText']}
                                label="List Button Text"
                                initialValue="View Options"
                                tooltip="Text shown on the list trigger button"
                              >
                                <Input placeholder="View Options" maxLength={20} />
                              </Form.Item>
                            );
                          }

                          return null;
                        }}
                      </Form.Item>

                      <Form.Item
                        name={['config', 'footerText']}
                        label="Footer (optional)"
                        tooltip="Max 60 characters"
                      >
                        <Input placeholder="Powered by AgentStudio" maxLength={60} />
                      </Form.Item>
                    </Card>
                  );
                }

                return null;
              }}
            </Form.Item>

            <Card size="small" title="Fallback" style={{ marginBottom: 16 }}>
              <Form.Item
                name={['config', 'fallbackMessage']}
                label="Fallback Message"
                tooltip="Sent if the primary message fails"
                initialValue="Sorry, I couldn't send that message. Please try again."
              >
                <TextArea
                  rows={2}
                  placeholder="Sorry, I couldn't send that message. Please try again."
                />
              </Form.Item>
            </Card>

            <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
              <strong>Note:</strong> Template messages can be sent anytime. Other messages require a 24-hour customer service window.
            </Typography.Text>
          </>
        )}
      </Form>
    </div>
  );
};
