import type { Node, Edge } from '@xyflow/react';

// Node Types
export type NodeType =
  | 'INPUT'
  | 'LLM_AGENT'
  | 'RAG_RETRIEVER'
  | 'DECISION'
  | 'TOOL'
  | 'OUTPUT'
  | 'SUBGRAPH';

// Node-Specific Configuration Interfaces

export interface InputNodeConfig {
  schema?: Record<string, any>; // Optional input validation schema
}

export interface LLMAgentNodeConfig {
  modelConfig: {
    model: string; // 'gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', etc.
    temperature: number;
    maxTokens: number;
  };
  systemPrompt: string;
  tools: string[]; // Array of tool IDs available to this LLM
}

export interface RAGRetrieverNodeConfig {
  endpoint: string;
  authType: 'api_key' | 'oauth2' | 'basic';
  searchMethod: 'semantic' | 'hybrid' | 'keyword';
  topK: number;
  scoreThreshold: number;
}

export interface DecisionNodeConfig {
  conditions: Array<{
    field: string;
    operator: '==' | '!=' | '>' | '<' | '>=' | '<=' | 'contains';
    value: any;
    targetNode: string;
  }>;
}

export interface ToolNodeConfig {
  toolId: string;
  parameters: Record<string, any>;
}

export interface OutputNodeConfig {
  format: 'json' | 'text' | 'markdown';
  template?: string;
}

export interface SubgraphNodeConfig {
  workflowId: string; // Reference to another workflow
}

// Union type for all node configs
export type NodeConfig =
  | InputNodeConfig
  | LLMAgentNodeConfig
  | RAGRetrieverNodeConfig
  | DecisionNodeConfig
  | ToolNodeConfig
  | OutputNodeConfig
  | SubgraphNodeConfig;

// Node Data Interface
export interface WorkflowNodeData {
  label: string;
  type: NodeType;
  config?: NodeConfig;
}

// Node and Edge Types for ReactFlow
export type WorkflowNode = Node<WorkflowNodeData>;
export type WorkflowEdge = Edge;

// Workflow Configuration
export interface WorkflowConfig {
  id?: string;
  name: string;
  description: string;
  executionSettings: {
    timeout: number; // milliseconds
    retryPolicy: {
      maxRetries: number;
      retryDelay: number; // milliseconds
    };
  };
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  status: 'draft' | 'deployed' | 'archived';
  version: number;
  createdAt?: string;
  updatedAt?: string;
  creatorId?: string;
  organizationId?: string;
}

// Complete Workflow Interface
export interface Workflow extends WorkflowConfig {
  id: string;
  createdAt: string;
  updatedAt: string;
  creatorId: string;
  organizationId: string;
}

// Helper type guards
export function isLLMAgentNode(node: WorkflowNode): node is WorkflowNode & { data: { config: LLMAgentNodeConfig } } {
  return node.data.type === 'LLM_AGENT';
}

export function isRAGRetrieverNode(node: WorkflowNode): node is WorkflowNode & { data: { config: RAGRetrieverNodeConfig } } {
  return node.data.type === 'RAG_RETRIEVER';
}

export function isDecisionNode(node: WorkflowNode): node is WorkflowNode & { data: { config: DecisionNodeConfig } } {
  return node.data.type === 'DECISION';
}

export function isToolNode(node: WorkflowNode): node is WorkflowNode & { data: { config: ToolNodeConfig } } {
  return node.data.type === 'TOOL';
}

export function isOutputNode(node: WorkflowNode): node is WorkflowNode & { data: { config: OutputNodeConfig } } {
  return node.data.type === 'OUTPUT';
}

export function isSubgraphNode(node: WorkflowNode): node is WorkflowNode & { data: { config: SubgraphNodeConfig } } {
  return node.data.type === 'SUBGRAPH';
}
