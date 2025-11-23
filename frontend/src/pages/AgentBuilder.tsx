import { useState, useCallback } from 'react';
import { Layout, Button, Input, message } from 'antd';
import { SaveOutlined, RocketOutlined, UndoOutlined, RedoOutlined } from '@ant-design/icons';
import { AgentCanvas } from '../components/AgentBuilder/AgentCanvas';
import { NodeLibrary } from '../components/AgentBuilder/NodeLibrary';
import { PropertyPanel } from '../components/AgentBuilder/PropertyPanel';
import type { AgentNode, AgentEdge } from '../types/agent';

const { Header, Sider, Content } = Layout;

export const AgentBuilder = () => {
  const [agentName, setAgentName] = useState('Untitled Agent');
  const [nodes, setNodes] = useState<AgentNode[]>([]);
  const [edges, setEdges] = useState<AgentEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<AgentNode | null>(null);
  const [history, setHistory] = useState<{ nodes: AgentNode[]; edges: AgentEdge[] }[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const handleSave = useCallback(() => {
    const agentConfig = {
      name: agentName,
      nodes,
      edges,
    };
    console.log('Saving agent:', agentConfig);
    message.success('Agent saved successfully!');
    // TODO: Call API to save agent
  }, [agentName, nodes, edges]);

  const handleDeploy = useCallback(() => {
    console.log('Deploying agent');
    message.info('Deployment feature coming soon!');
    // TODO: Implement deployment
  }, []);

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
        <Input
          value={agentName}
          onChange={(e) => setAgentName(e.target.value)}
          style={{ width: 300 }}
          placeholder="Agent name"
          bordered={false}
          className="font-semibold text-lg"
        />
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
          <Button icon={<SaveOutlined />} onClick={handleSave}>
            Save
          </Button>
          <Button type="primary" icon={<RocketOutlined />} onClick={handleDeploy}>
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
    </Layout>
  );
};
