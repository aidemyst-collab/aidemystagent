import { Node, Edge } from 'reactflow';

export type NodeType =
  | 'INPUT'
  | 'LLM_AGENT'
  | 'RAG_RETRIEVER'
  | 'DECISION'
  | 'TOOL'
  | 'OUTPUT'
  | 'SUBGRAPH';

export interface AgentNodeData {
  label: string;
  type: NodeType;
  config?: Record<string, any>;
}

export type AgentNode = Node<AgentNodeData>;
export type AgentEdge = Edge;

export interface AgentConfig {
  id?: string;
  name: string;
  description: string;
  modelConfig: {
    model: string;
    temperature: number;
    maxTokens: number;
  };
  systemPrompt: string;
  tools: string[];
  ragConfig?: {
    endpoint: string;
    authType: 'api_key' | 'oauth2' | 'basic';
    searchMethod: 'semantic' | 'hybrid' | 'keyword';
    topK: number;
    scoreThreshold: number;
  };
  executionSettings: {
    timeout: number;
    retryPolicy: {
      maxRetries: number;
      retryDelay: number;
    };
  };
  nodes: AgentNode[];
  edges: AgentEdge[];
  status: 'draft' | 'deployed' | 'archived';
  version: number;
  createdAt?: string;
  updatedAt?: string;
  creatorId?: string;
  organizationId?: string;
}

export interface Agent extends AgentConfig {
  id: string;
  createdAt: string;
  updatedAt: string;
  creatorId: string;
  organizationId: string;
}
