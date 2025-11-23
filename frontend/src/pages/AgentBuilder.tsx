import { useState, useCallback } from 'react';
import { Layout, Button, Input, message, Modal, Form, InputNumber, Select, Tooltip, Spin } from 'antd';
import { SaveOutlined, RocketOutlined, UndoOutlined, RedoOutlined, EditOutlined, LoadingOutlined } from '@ant-design/icons';
import { AgentCanvas } from '../components/AgentBuilder/AgentCanvas';
import { NodeLibrary } from '../components/AgentBuilder/NodeLibrary';
import { PropertyPanel } from '../components/AgentBuilder/PropertyPanel';
import type { AgentNode, AgentEdge } from '../types/agent';
import { useCreateAgent, useUpdateAgent, useDeployAgent } from '../features/agents/agentHooks';

const { Header, Sider, Content } = Layout;
const { TextArea } = Input;

export const AgentBuilder = () => {
  const [agentId, setAgentId] = useState<string | null>(null);
  const [agentName, setAgentName] = useState('');
  const [agentDescription, setAgentDescription] = useState('');
  const [nodes, setNodes] = useState<AgentNode[]>([]);
  const [edges, setEdges] = useState<AgentEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<AgentNode | null>(null);
  const [history, setHistory] = useState<{ nodes: AgentNode[]; edges: AgentEdge[] }[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [createModalVisible, setCreateModalVisible] = useState(true);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  // API hooks
  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent();
  const deployAgent = useDeployAgent();

  const handleCreateAgent = useCallback(async () => {
    try {
      const values = await createForm.validateFields();
      setAgentName(values.name);
      setAgentDescription(values.description || '');
      setCreateModalVisible(false);
      message.success('Agent created! Start building your workflow.');
    } catch (error) {
      console.error('Create error:', error);
    }
  }, [createForm]);

  const handleEditAgent = useCallback(() => {
    editForm.setFieldsValue({
      name: agentName,
      description: agentDescription,
    });
    setEditModalVisible(true);
  }, [agentName, agentDescription, editForm]);

  const handleEditConfirm = useCallback(async () => {
    try {
      const values = await editForm.validateFields();
      setAgentName(values.name);
      setAgentDescription(values.description || '');
      setEditModalVisible(false);
      message.success('Agent information updated!');
    } catch (error) {
      console.error('Edit error:', error);
    }
  }, [editForm]);

  const handleSave = useCallback(() => {
    if (!agentName.trim()) {
      message.error('Please enter an agent name');
      return;
    }
    if (nodes.length === 0) {
      message.error('Please add at least one node to your agent');
      return;
    }
    setSaveModalVisible(true);
  }, [agentName, nodes]);

  const handleSaveConfirm = useCallback(async () => {
    try {
      const values = await form.validateFields();

      const agentConfig = {
        name: agentName,
        description: agentDescription,
        modelConfig: {
          model: values.model || 'gpt-4',
          temperature: values.temperature || 0.7,
          maxTokens: values.maxTokens || 2000,
        },
        systemPrompt: values.systemPrompt || '',
        tools: values.tools || [],
        ragConfig: values.ragEnabled ? {
          endpoint: values.ragEndpoint || '',
          authType: values.ragAuthType || 'api_key',
          searchMethod: values.ragSearchMethod || 'semantic',
          topK: values.ragTopK || 5,
          scoreThreshold: values.ragScoreThreshold || 0.7,
        } : undefined,
        executionSettings: {
          timeout: values.timeout || 30000,
          retryPolicy: {
            maxRetries: values.maxRetries || 3,
            retryDelay: values.retryDelay || 1000,
          },
        },
        nodes,
        edges,
        status: 'draft' as const,
        version: 1,
      };

      let result;

      if (agentId) {
        // Update existing agent
        result = await updateAgent.mutateAsync({
          id: agentId,
          data: agentConfig,
        });
      } else {
        // Create new agent
        result = await createAgent.mutateAsync(agentConfig);
        setAgentId(result.id);
      }

      setSaveModalVisible(false);
    } catch (error) {
      console.error('Save error:', error);
      // Error message is handled by the mutation hook
    }
  }, [agentId, agentName, agentDescription, nodes, edges, form, createAgent, updateAgent]);

  const handleDeploy = useCallback(() => {
    if (!agentId) {
      message.error('Please save the agent first');
      return;
    }

    Modal.confirm({
      title: 'Deploy Agent',
      content: `Are you sure you want to deploy "${agentName}"? This will make it available via API.`,
      onOk: async () => {
        try {
          const result = await deployAgent.mutateAsync(agentId);
          Modal.success({
            title: 'Agent Deployed!',
            content: (
              <div>
                <p>Your agent is now live and accessible at:</p>
                <p style={{ fontFamily: 'monospace', background: '#f5f5f5', padding: '8px', marginTop: '8px' }}>
                  {result.endpoint}
                </p>
              </div>
            ),
          });
        } catch (error) {
          console.error('Deploy error:', error);
        }
      },
    });
  }, [agentId, agentName, deployAgent]);

  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      const state = history[newIndex];
      setNodes(state.nodes);
      setEdges(state.edges);
      setHistoryIndex(newIndex);
    }
  }, [history, historyIndex]);

  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      const state = history[newIndex];
      setNodes(state.nodes);
      setEdges(state.edges);
      setHistoryIndex(newIndex);
    }
  }, [history, historyIndex]);

  const handleNodesChange = useCallback((newNodes: AgentNode[]) => {
    setNodes(newNodes);
    // Add to history
    setHistory((prev) => [...prev.slice(0, historyIndex + 1), { nodes: newNodes, edges }]);
    setHistoryIndex((prev) => prev + 1);
  }, [edges, historyIndex]);

  const handleEdgesChange = useCallback((newEdges: AgentEdge[]) => {
    setEdges(newEdges);
    // Add to history
    setHistory((prev) => [...prev.slice(0, historyIndex + 1), { nodes, edges: newEdges }]);
    setHistoryIndex((prev) => prev + 1);
  }, [nodes, historyIndex]);

  const handleNodeUpdate = useCallback((nodeId: string, data: any) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node
      )
    );
  }, []);

  return (
    <Layout style={{ height: 'calc(100vh - 112px)' }}>
      <Header
        style={{
          background: '#fff',
          padding: '0 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <div className="flex items-center gap-2">
          <div>
            <div className="font-semibold text-lg">
              {agentName || 'Untitled Agent'}
            </div>
            {agentDescription && (
              <div style={{ fontSize: '12px', color: '#666', maxWidth: 400 }}>
                {agentDescription}
              </div>
            )}
          </div>
          <Tooltip title="Edit agent name and description">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={handleEditAgent}
              size="small"
            />
          </Tooltip>
        </div>
        <div className="flex gap-2">
          <Button
            icon={<UndoOutlined />}
            onClick={handleUndo}
            disabled={historyIndex <= 0}
          >
            Undo
          </Button>
          <Button
            icon={<RedoOutlined />}
            onClick={handleRedo}
            disabled={historyIndex >= history.length - 1}
          >
            Redo
          </Button>
          <Button
            icon={createAgent.isPending || updateAgent.isPending ? <LoadingOutlined /> : <SaveOutlined />}
            onClick={handleSave}
            type="default"
            loading={createAgent.isPending || updateAgent.isPending}
          >
            {agentId ? 'Update' : 'Save'}
          </Button>
          <Button
            type="primary"
            icon={deployAgent.isPending ? <LoadingOutlined /> : <RocketOutlined />}
            onClick={handleDeploy}
            loading={deployAgent.isPending}
            disabled={!agentId}
          >
            Deploy
          </Button>
        </div>
      </Header>
      <Layout>
        <Sider width={250} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
          <NodeLibrary />
        </Sider>
        <Content>
          <AgentCanvas
            initialNodes={nodes}
            initialEdges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onNodeSelect={setSelectedNode}
          />
        </Content>
        <Sider width={300} theme="light" style={{ borderLeft: '1px solid #f0f0f0' }}>
          <PropertyPanel selectedNode={selectedNode} onUpdate={handleNodeUpdate} />
        </Sider>
      </Layout>

      {/* Create Agent Modal */}
      <Modal
        title="Create New Agent"
        open={createModalVisible}
        onOk={handleCreateAgent}
        onCancel={() => {
          message.warning('Please create an agent to continue');
        }}
        closable={false}
        maskClosable={false}
        width={500}
        okText="Create Agent"
      >
        <Form
          form={createForm}
          layout="vertical"
          initialValues={{
            name: '',
            description: '',
          }}
        >
          <Form.Item
            label="Agent Name"
            name="name"
            rules={[
              { required: true, message: 'Please enter an agent name' },
              { min: 3, message: 'Name must be at least 3 characters' },
            ]}
          >
            <Input
              placeholder="e.g., Customer Support Bot"
              autoFocus
            />
          </Form.Item>

          <Form.Item
            label="Description"
            name="description"
            rules={[
              { max: 500, message: 'Description must be less than 500 characters' },
            ]}
          >
            <TextArea
              rows={3}
              placeholder="Brief description of what this agent does... (optional)"
            />
          </Form.Item>
        </Form>

        <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4, fontSize: 12, color: '#666' }}>
          <strong>💡 Tip:</strong> You can edit the name and description later by clicking the edit icon.
        </div>
      </Modal>

      {/* Edit Agent Modal */}
      <Modal
        title="Edit Agent Information"
        open={editModalVisible}
        onOk={handleEditConfirm}
        onCancel={() => setEditModalVisible(false)}
        width={500}
        okText="Update"
      >
        <Form
          form={editForm}
          layout="vertical"
        >
          <Form.Item
            label="Agent Name"
            name="name"
            rules={[
              { required: true, message: 'Please enter an agent name' },
              { min: 3, message: 'Name must be at least 3 characters' },
            ]}
          >
            <Input placeholder="Agent name" />
          </Form.Item>

          <Form.Item
            label="Description"
            name="description"
            rules={[
              { max: 500, message: 'Description must be less than 500 characters' },
            ]}
          >
            <TextArea
              rows={3}
              placeholder="Brief description (optional)"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Save Configuration Modal */}
      <Modal
        title={agentId ? 'Update Agent Configuration' : 'Save Agent Configuration'}
        open={saveModalVisible}
        onOk={handleSaveConfirm}
        onCancel={() => setSaveModalVisible(false)}
        width={600}
        okText={agentId ? 'Update Agent' : 'Save Agent'}
        confirmLoading={createAgent.isPending || updateAgent.isPending}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 14, marginBottom: 4 }}>
            <strong>Agent:</strong> {agentName}
          </div>
          {agentDescription && (
            <div style={{ fontSize: 12, color: '#666' }}>
              {agentDescription}
            </div>
          )}
        </div>

        <Form
          form={form}
          layout="vertical"
          initialValues={{
            model: 'gpt-4',
            temperature: 0.7,
            maxTokens: 2000,
            timeout: 30000,
            maxRetries: 3,
            retryDelay: 1000,
          }}
        >
          <Form.Item
            label="LLM Model"
            name="model"
            rules={[{ required: true, message: 'Please select a model' }]}
          >
            <Select>
              <Select.Option value="gpt-4">GPT-4</Select.Option>
              <Select.Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Select.Option>
              <Select.Option value="claude-3-opus">Claude 3 Opus</Select.Option>
              <Select.Option value="claude-3-sonnet">Claude 3 Sonnet</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="Temperature" name="temperature">
            <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="Max Tokens" name="maxTokens">
            <InputNumber min={1} max={100000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="System Prompt" name="systemPrompt">
            <TextArea rows={3} placeholder="Optional system prompt for the agent..." />
          </Form.Item>

          <Form.Item label="Execution Timeout (ms)" name="timeout">
            <InputNumber min={1000} max={300000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="Max Retries" name="maxRetries">
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
        </Form>

        <div style={{ marginTop: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
          <p style={{ margin: 0, fontSize: 12, color: '#666' }}>
            <strong>Workflow Summary:</strong> {nodes.length} node(s), {edges.length} connection(s)
          </p>
        </div>
      </Modal>
    </Layout>
  );
};
