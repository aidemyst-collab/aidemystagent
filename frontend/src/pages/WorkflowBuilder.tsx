import { useState, useCallback, useEffect } from 'react';
import { Layout, Button, Input, message, Modal, Form, InputNumber, Tooltip } from 'antd';
import { SaveOutlined, RocketOutlined, UndoOutlined, RedoOutlined, EditOutlined, LoadingOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { AgentCanvas } from '../components/AgentBuilder/AgentCanvas';
import { NodeLibrary } from '../components/AgentBuilder/NodeLibrary';
import { PropertyPanel } from '../components/AgentBuilder/PropertyPanel';
import type { WorkflowNode, WorkflowEdge } from '../types/workflow';
import { useCreateWorkflow, useUpdateWorkflow, useDeployWorkflow, useWorkflow } from '../features/workflows/workflowHooks';

const { Header, Sider, Content } = Layout;
const { TextArea } = Input;

export const WorkflowBuilder = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [workflowId, setWorkflowId] = useState<string | null>(id || null);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [edges, setEdges] = useState<WorkflowEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [history, setHistory] = useState<{ nodes: WorkflowNode[]; edges: WorkflowEdge[] }[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [createModalVisible, setCreateModalVisible] = useState(!id); // Hide modal if editing
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  // API hooks
  const createWorkflow = useCreateWorkflow();
  const updateWorkflow = useUpdateWorkflow();
  const deployWorkflow = useDeployWorkflow();
  const { data: workflowData, isLoading: isLoadingWorkflow } = useWorkflow(id || null);

  // Load workflow data when editing
  useEffect(() => {
    if (workflowData) {
      console.log('Loading workflow data:', workflowData);
      console.log('Config:', workflowData.config);
      console.log('Nodes:', workflowData.config?.nodes);
      console.log('Edges:', workflowData.config?.edges);
      setWorkflowId(workflowData.id);
      setWorkflowName(workflowData.name);
      setWorkflowDescription(workflowData.description || '');
      setNodes(workflowData.config?.nodes || []);
      setEdges(workflowData.config?.edges || []);
      message.success(`Loaded workflow: ${workflowData.name}`);
    }
  }, [workflowData]);

  const handleCreateWorkflow = useCallback(async () => {
    try {
      const values = await createForm.validateFields();
      setWorkflowName(values.name);
      setWorkflowDescription(values.description || '');
      setCreateModalVisible(false);
      message.success('Workflow created! Start building your workflow.');
    } catch (error) {
      console.error('Create error:', error);
    }
  }, [createForm]);

  const handleEditWorkflow = useCallback(() => {
    editForm.setFieldsValue({
      name: workflowName,
      description: workflowDescription,
    });
    setEditModalVisible(true);
  }, [workflowName, workflowDescription, editForm]);

  const handleEditConfirm = useCallback(async () => {
    try {
      const values = await editForm.validateFields();
      setWorkflowName(values.name);
      setWorkflowDescription(values.description || '');
      setEditModalVisible(false);
      message.success('Workflow information updated!');
    } catch (error) {
      console.error('Edit error:', error);
    }
  }, [editForm]);

  const handleSave = useCallback(() => {
    console.log('handleSave called - workflowName:', workflowName, 'nodes:', nodes.length);
    if (!workflowName.trim()) {
      message.error('Please enter a workflow name');
      return;
    }
    console.log('Opening save modal');
    setSaveModalVisible(true);
  }, [workflowName, nodes]);

  const handleSaveConfirm = useCallback(async () => {
    console.log('handleSaveConfirm called');
    try {
      console.log('Validating form fields...');
      const values = await form.validateFields();
      console.log('Form values:', values);

      const workflowConfig = {
        name: workflowName,
        description: workflowDescription,
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

      console.log('Workflow config built:', workflowConfig);

      let result;

      if (workflowId) {
        console.log('Updating existing workflow with ID:', workflowId);
        result = await updateWorkflow.mutateAsync({
          id: workflowId,
          data: workflowConfig,
        });
      } else {
        console.log('Creating new workflow');
        result = await createWorkflow.mutateAsync(workflowConfig);
        console.log('Workflow created with result:', result);
        setWorkflowId(result.id);
      }

      console.log('Closing save modal');
      setSaveModalVisible(false);
    } catch (error) {
      console.error('Save error:', error);
    }
  }, [workflowId, workflowName, workflowDescription, nodes, edges, form, createWorkflow, updateWorkflow]);

  const handleDeploy = useCallback(() => {
    if (!workflowId) {
      message.error('Please save the workflow first');
      return;
    }

    Modal.confirm({
      title: 'Deploy Workflow',
      content: `Are you sure you want to deploy "${workflowName}"? This will make it available via API.`,
      onOk: async () => {
        try {
          const result = await deployWorkflow.mutateAsync(workflowId);
          Modal.success({
            title: 'Workflow Deployed!',
            content: (
              <div>
                <p>Your workflow is now live and accessible at:</p>
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
  }, [workflowId, workflowName, deployWorkflow]);

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

  const handleNodesChange = useCallback((newNodes: WorkflowNode[]) => {
    setNodes(newNodes);
    setHistory((prev) => [...prev.slice(0, historyIndex + 1), { nodes: newNodes, edges }]);
    setHistoryIndex((prev) => prev + 1);
  }, [edges, historyIndex]);

  const handleEdgesChange = useCallback((newEdges: WorkflowEdge[]) => {
    setEdges(newEdges);
    setHistory((prev) => [...prev.slice(0, historyIndex + 1), { nodes, edges: newEdges }]);
    setHistoryIndex((prev) => prev + 1);
  }, [nodes, historyIndex]);

  const handleNodeUpdate = useCallback((nodeId: string, data: any) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          // Deep merge the data to preserve nested config
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

          return { ...node, data: deepMerge(node.data, data) };
        }
        return node;
      })
    );
  }, []);

  // Show loading state while fetching workflow
  if (id && isLoadingWorkflow) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 'calc(100vh - 112px)' }}>
        <LoadingOutlined style={{ fontSize: 48 }} />
        <span style={{ marginLeft: 16, fontSize: 18 }}>Loading workflow...</span>
      </div>
    );
  }

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
        <div className="flex items-start gap-3">
          <div>
            <div className="font-semibold text-lg" style={{ lineHeight: '1.5' }}>
              {workflowName || 'Untitled Workflow'}
            </div>
            {workflowDescription && (
              <div style={{ fontSize: '12px', color: '#666', maxWidth: 400, lineHeight: '1.4', marginTop: '2px' }}>
                {workflowDescription}
              </div>
            )}
          </div>
          <Tooltip title="Edit workflow name and description">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={handleEditWorkflow}
              size="small"
              style={{ marginTop: '2px' }}
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
            icon={createWorkflow.isPending || updateWorkflow.isPending ? <LoadingOutlined /> : <SaveOutlined />}
            onClick={handleSave}
            type="default"
            loading={createWorkflow.isPending || updateWorkflow.isPending}
          >
            {workflowId ? 'Update' : 'Save'}
          </Button>
          <Button
            type="primary"
            icon={deployWorkflow.isPending ? <LoadingOutlined /> : <RocketOutlined />}
            onClick={handleDeploy}
            loading={deployWorkflow.isPending}
            disabled={!workflowId}
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
            initialNodes={nodes as any}
            initialEdges={edges as any}
            onNodesChange={handleNodesChange as any}
            onEdgesChange={handleEdgesChange as any}
            onNodeSelect={setSelectedNode as any}
          />
        </Content>
        <Sider width={300} theme="light" style={{ borderLeft: '1px solid #f0f0f0' }}>
          <PropertyPanel
            selectedNode={selectedNode}
            onUpdate={handleNodeUpdate}
            allNodes={nodes}
            allEdges={edges}
          />
        </Sider>
      </Layout>

      {/* Create Workflow Modal */}
      <Modal
        title="Create New Workflow"
        open={createModalVisible}
        onOk={handleCreateWorkflow}
        onCancel={() => navigate('/agents')}
        width={500}
        okText="Create Workflow"
        cancelText="Cancel"
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
            label="Workflow Name"
            name="name"
            rules={[
              { required: true, message: 'Please enter a workflow name' },
              { min: 3, message: 'Name must be at least 3 characters' },
            ]}
          >
            <Input
              placeholder="e.g., Customer Support Workflow"
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
              placeholder="Brief description of what this workflow does... (optional)"
            />
          </Form.Item>
        </Form>

        <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 4, fontSize: 12, color: '#666' }}>
          <strong>💡 Tip:</strong> You can edit the name and description later by clicking the edit icon.
        </div>
      </Modal>

      {/* Edit Workflow Modal */}
      <Modal
        title="Edit Workflow Information"
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
            label="Workflow Name"
            name="name"
            rules={[
              { required: true, message: 'Please enter a workflow name' },
              { min: 3, message: 'Name must be at least 3 characters' },
            ]}
          >
            <Input placeholder="Workflow name" />
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
        title={workflowId ? 'Update Workflow Configuration' : 'Save Workflow Configuration'}
        open={saveModalVisible}
        onOk={handleSaveConfirm}
        onCancel={() => setSaveModalVisible(false)}
        width={600}
        okText={workflowId ? 'Update Workflow' : 'Save Workflow'}
        confirmLoading={createWorkflow.isPending || updateWorkflow.isPending}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 14, marginBottom: 4 }}>
            <strong>Workflow:</strong> {workflowName}
          </div>
          {workflowDescription && (
            <div style={{ fontSize: 12, color: '#666' }}>
              {workflowDescription}
            </div>
          )}
        </div>

        <Form
          form={form}
          layout="vertical"
          initialValues={{
            timeout: 30000,
            maxRetries: 3,
            retryDelay: 1000,
          }}
        >
          <div style={{ marginBottom: 16, padding: 12, background: '#e6f7ff', borderRadius: 4, border: '1px solid #91d5ff' }}>
            <p style={{ margin: 0, fontSize: 12, color: '#0050b3' }}>
              <strong>ℹ️ Note:</strong> Model configuration is now set per LLM node. Configure each LLM Agent node individually in the Property Panel.
            </p>
          </div>

          <Form.Item label="Execution Timeout (ms)" name="timeout">
            <InputNumber min={1000} max={300000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="Max Retries" name="maxRetries">
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="Retry Delay (ms)" name="retryDelay">
            <InputNumber min={100} max={10000} style={{ width: '100%' }} />
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
