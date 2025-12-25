export interface NodeField {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  description?: string;
  example?: any;
  required?: boolean;
}

export interface NodeSchema {
  inputs: NodeField[];
  outputs: NodeField[];
  customizable: boolean; // Can user add custom fields?
}

// Schema definitions for each node type
export const NODE_SCHEMAS: Record<string, NodeSchema> = {
  INPUT: {
    inputs: [],
    outputs: [
      { name: 'message', type: 'string', description: 'User input message', required: true },
      { name: 'mode', type: 'string', description: 'Input mode (chat/json/form)' },
      { name: 'timestamp', type: 'string', description: 'Input timestamp' },
      { name: 'user_id', type: 'string', description: 'User ID (if provided)' },
    ],
    customizable: true,
  },

  LLM_AGENT: {
    inputs: [
      { name: 'message', type: 'string', description: 'Input message or prompt' },
      { name: 'context', type: 'object', description: 'Additional context data' },
    ],
    outputs: [
      { name: 'response', type: 'string', description: 'LLM generated response', required: true },
      { name: 'tokens', type: 'object', description: 'Token usage stats' },
      { name: 'cost', type: 'number', description: 'API call cost' },
      { name: 'model', type: 'string', description: 'Model used' },
    ],
    customizable: false,
  },

  TOOL: {
    inputs: [
      { name: 'arguments', type: 'object', description: 'Tool input arguments' },
    ],
    outputs: [
      { name: 'result', type: 'object', description: 'Tool execution result', required: true },
      { name: 'success', type: 'boolean', description: 'Whether tool succeeded' },
      { name: 'error', type: 'string', description: 'Error message if failed' },
    ],
    customizable: true,
  },

  OUTPUT: {
    inputs: [
      { name: 'data', type: 'object', description: 'Data to format as output' },
    ],
    outputs: [
      { name: 'output', type: 'string', description: 'Final formatted output' },
    ],
    customizable: true,
  },

  MEMORY: {
    inputs: [
      { name: 'session_id', type: 'string', description: 'Session identifier' },
      { name: 'message', type: 'string', description: 'Current message' },
    ],
    outputs: [
      { name: 'chat_history', type: 'array', description: 'Previous conversation messages' },
      { name: 'context', type: 'object', description: 'Memory context' },
    ],
    customizable: false,
  },

  RAG_RETRIEVER: {
    inputs: [
      { name: 'query', type: 'string', description: 'Search query' },
    ],
    outputs: [
      { name: 'chunks', type: 'array', description: 'Retrieved document chunks' },
      { name: 'context', type: 'string', description: 'Formatted RAG context' },
      { name: 'scores', type: 'array', description: 'Relevance scores' },
    ],
    customizable: false,
  },

  FILE_READER: {
    inputs: [
      { name: 'file_path', type: 'string', description: 'Path to the file (can be templated)' },
    ],
    outputs: [
      { name: 'file_content', type: 'string', description: 'File content or parsed data', required: true },
      { name: 'file_path', type: 'string', description: 'Resolved file path' },
      { name: 'file_size', type: 'number', description: 'File size in bytes' },
      { name: 'metadata', type: 'object', description: 'File metadata (modified date, mime type, etc.)' },
      { name: 'success', type: 'boolean', description: 'Whether operation succeeded' },
      { name: 'error', type: 'string', description: 'Error message if failed' },
    ],
    customizable: false,
  },

  STRUCTURED_OUTPUT_PARSER: {
    inputs: [
      { name: 'response', type: 'string', description: 'LLM output text to parse', required: true },
    ],
    outputs: [
      { name: 'parsed_data', type: 'object', description: 'Structured parsed output', required: true },
      { name: 'parsing_success', type: 'boolean', description: 'Whether parsing succeeded' },
      { name: 'validation_errors', type: 'array', description: 'List of validation errors' },
      { name: 'fields_extracted', type: 'array', description: 'Names of extracted fields' },
    ],
    customizable: true,
  },
};
