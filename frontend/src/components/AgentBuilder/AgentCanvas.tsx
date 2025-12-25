import { useCallback, useState, useEffect, DragEvent } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
} from '@xyflow/react';
import type { Connection, NodeTypes, EdgeTypes } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  InputNode,
  MemoryNode,
  LLMAgentNode,
  RAGRetrieverNode,
  DecisionNode,
  ToolNode,
  OutputNode,
  SubgraphNode,
  FileReaderNode,
  StructuredOutputParserNode,
} from './nodes';
import { CustomEdge } from './CustomEdge';
import type { AgentNode, AgentEdge, NodeType } from '../../types/agent';

const nodeTypes: NodeTypes = {
  InputNode,
  MemoryNode,
  LLMAgentNode,
  RAGRetrieverNode,
  DecisionNode,
  ToolNode,
  OutputNode,
  SubgraphNode,
  FileReaderNode,
  StructuredOutputParserNode,
};

// Map NodeType to component name
const nodeTypeMapping: Record<string, string> = {
  'INPUT': 'InputNode',
  'MEMORY': 'MemoryNode',
  'LLM_AGENT': 'LLMAgentNode',
  'RAG_RETRIEVER': 'RAGRetrieverNode',
  'DECISION': 'DecisionNode',
  'TOOL': 'ToolNode',
  'OUTPUT': 'OutputNode',
  'SUBGRAPH': 'SubgraphNode',
  'FILE_READER': 'FileReaderNode',
  'STRUCTURED_OUTPUT_PARSER': 'StructuredOutputParserNode',
};

const edgeTypes: EdgeTypes = {
  default: CustomEdge,
};

const defaultEdgeOptions = {
  animated: false,
  style: { stroke: '#b1b1b7', strokeWidth: 2 },
  type: 'default',
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

  // Update nodes and edges when props change (e.g., when loading a workflow)
  useEffect(() => {
    setNodes(initialNodes as any);
    setEdges(initialEdges as any);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

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
        type: nodeTypeMapping[nodeType] || 'InputNode',
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
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        attributionPosition="bottom-right"
        deleteKeyCode="Delete"
        elementsSelectable={true}
        nodesConnectable={true}
        nodesDraggable={true}
        edgesFocusable={true}
        edgesReconnectable={true}
      >
        <Controls />
        <MiniMap />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
      </ReactFlow>
    </div>
  );
};
