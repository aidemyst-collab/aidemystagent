import type { Node, Edge } from '@xyflow/react';
import type { NodeField } from './nodeSchemas';

// Node Types
export type NodeType =
  | 'INPUT'
  | 'MEMORY'
  | 'LLM_AGENT'
  | 'RAG_RETRIEVER'
  | 'DECISION'
  | 'TOOL'
  | 'OUTPUT'
  | 'SUBGRAPH'
  | 'FILE_READER'
  | 'STRUCTURED_OUTPUT_PARSER';

// Node-Specific Configuration Interfaces

export interface InputNodeConfig {
  schema?: Record<string, any>; // Optional input validation schema
  customOutputFields?: NodeField[]; // Custom output fields defined by user
}

export interface MemoryNodeConfig {
  type?: 'buffer' | 'buffer-window' | 'summary' | 'vector' | 'entity';
  windowSize?: number;
  persistence?: {
    enabled: boolean;
    backend?: 'redis' | 'postgres' | 'mongodb';
    ttlDays?: number;
  };
}

export interface LLMAgentNodeConfig {
  credentialId?: string; // ID of the credential to use for this LLM node
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
  customOutputFields?: NodeField[]; // Custom output fields defined by user
}

export interface OutputNodeConfig {
  format: 'json' | 'text' | 'markdown';
  template?: string;
  customOutputFields?: NodeField[]; // Custom output fields defined by user
}

export interface SubgraphNodeConfig {
  workflowId: string; // Reference to another workflow
}

export interface FileReaderNodeConfig {
  filePath: string;
  operation: 'read_text' | 'read_binary' | 'read_json' | 'read_csv' | 'read_lines' | 'get_metadata';
  encoding?: string;
  maxFileSizeMB?: number;
  errorHandling: 'fail' | 'continue' | 'default_value';
  defaultValue?: string;
  outputVarName?: string;
  // CSV Options
  csvDelimiter?: string;
  csvHasHeader?: boolean;
  csvSkipEmpty?: boolean;
  csvTrimFields?: boolean;
  // JSON Options
  validateSchema?: boolean;
  jsonSchema?: string;
  // Line Reading Options
  linesSkipEmpty?: boolean;
  linesTrim?: boolean;
  linesStart?: number;
  linesEnd?: number;
}

// Union type for all node configs
export type NodeConfig =
  | InputNodeConfig
  | LLMAgentNodeConfig
  | RAGRetrieverNodeConfig
  | DecisionNodeConfig
  | ToolNodeConfig
  | OutputNodeConfig
  | SubgraphNodeConfig
  | FileReaderNodeConfig;

// Node Data Interface
export interface WorkflowNodeData {
  label: string;
  type: NodeType;
  config?: NodeConfig;
  [key: string]: unknown; // Index signature for ReactFlow compatibility
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
