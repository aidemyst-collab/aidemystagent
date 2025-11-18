import { useCallback, useState, DragEvent } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  BackgroundVariant,
  NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  InputNode,
  LLMAgentNode,
  RAGRetrieverNode,
  DecisionNode,
  ToolNode,
  OutputNode,
  SubgraphNode,
} from './nodes';
import { AgentNode, AgentEdge, NodeType } from '../../types/agent';

const nodeTypes: NodeTypes = {
  InputNode,
  LLMAgentNode,
  RAGRetrieverNode,
  DecisionNode,
  ToolNode,
  OutputNode,
  SubgraphNode,
};

interface AgentCanvasProps {
  initialNodes?: AgentNode[];
  initialEdges?: AgentEdge[];
  onNodesChange?: (nodes: AgentNode[]) => void;
  onEdgesChange?: (edges: AgentEdge[]) => void;
  onNodeSelect?: (node: AgentNode | null) => void;
}

export const AgentCanvas = ({
  initialNodes = [],
  initialEdges = [],
  onNodesChange,
  onEdgesChange,
  onNodeSelect,
}: AgentCanvasProps) => {
  const [nodes, setNodes, onNodesChangeInternal] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState(initialEdges);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  const onConnect = useCallback(
    (params: Connection) => {
      const newEdges = addEdge(params, edges);
      setEdges(newEdges);
      onEdgesChange?.(newEdges as AgentEdge[]);
    },
    [edges, setEdges, onEdgesChange]
  );

  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();

      if (!reactFlowInstance) return;

      const data = event.dataTransfer.getData('application/reactflow');
      if (!data) return;

      const { nodeType, label } = JSON.parse(data);

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: AgentNode = {
        id: `${nodeType.toLowerCase()}_${Date.now()}`,
        type: `${nodeType.charAt(0)}${nodeType.slice(1).toLowerCase()}Node`,
        position,
        data: { label, type: nodeType as NodeType, config: {} },
      };

      const newNodes = [...nodes, newNode];
      setNodes(newNodes);
      onNodesChange?.(newNodes);
    },
    [reactFlowInstance, nodes, setNodes, onNodesChange]
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: AgentNode) => {
      onNodeSelect?.(node);
    },
    [onNodeSelect]
  );

  const onPaneClick = useCallback(() => {
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  const handleNodesChange = useCallback(
    (changes: any) => {
      onNodesChangeInternal(changes);
      onNodesChange?.(nodes);
    },
    [onNodesChangeInternal, onNodesChange, nodes]
  );

  const handleEdgesChange = useCallback(
    (changes: any) => {
      onEdgesChangeInternal(changes);
      onEdgesChange?.(edges);
    },
    [onEdgesChangeInternal, onEdgesChange, edges]
  );

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
      >
        <Controls />
        <MiniMap />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
      </ReactFlow>
    </div>
  );
};
