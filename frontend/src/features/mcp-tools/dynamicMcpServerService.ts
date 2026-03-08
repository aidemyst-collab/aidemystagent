import { apiClient } from '../../services/api';

// ==============================================================================
// Types
// ==============================================================================

export type HTTPMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
export type ParameterType = 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object';

export interface ToolParameter {
  name: string;
  type: ParameterType;
  description?: string;
  required: boolean;
  default?: any;
  enum?: string[];
}

// Tool within a provider
export interface DynamicMCPTool {
  id: string;
  server_id: string;
  name: string;
  description: string;
  path: string;
  method: HTTPMethod;
  parameters: ToolParameter[];
  headers?: Record<string, string>;
  query_params?: Record<string, string>;
  body_template?: Record<string, any>;
  response_path?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Provider containing multiple tools
export interface DynamicMCPServer {
  id: string;
  organization_id: string;
  creator_id: string;
  name: string;
  description?: string;
  base_url: string;
  credential_id?: string;
  default_headers?: Record<string, string>;
  timeout_seconds: number;
  is_active: boolean;
  tools: DynamicMCPTool[];
  tool_count: number;
  active_tool_count: number;
  created_at: string;
  updated_at: string;
}

// ==============================================================================
// Request/Response Types
// ==============================================================================

export interface ToolCreateRequest {
  name: string;
  description: string;
  path: string;
  method?: HTTPMethod;
  parameters?: ToolParameter[];
  headers?: Record<string, string>;
  query_params?: Record<string, string>;
  body_template?: Record<string, any>;
  response_path?: string;
}

export interface ToolUpdateRequest {
  name?: string;
  description?: string;
  path?: string;
  method?: HTTPMethod;
  parameters?: ToolParameter[];
  headers?: Record<string, string>;
  query_params?: Record<string, string>;
  body_template?: Record<string, any>;
  response_path?: string;
  is_active?: boolean;
}

export interface ServerCreateRequest {
  name: string;
  description?: string;
  base_url: string;
  credential_id?: string;
  default_headers?: Record<string, string>;
  timeout_seconds?: number;
  tools?: ToolCreateRequest[];
}

export interface ServerUpdateRequest {
  name?: string;
  description?: string;
  base_url?: string;
  credential_id?: string;
  default_headers?: Record<string, string>;
  timeout_seconds?: number;
  is_active?: boolean;
}

export interface ServerListResponse {
  servers: DynamicMCPServer[];
  total: number;
}

export interface ToolExecuteRequest {
  arguments: Record<string, any>;
}

export interface ToolExecuteResponse {
  success: boolean;
  result?: any;
  error?: string;
  execution_time_ms?: number;
}

// ==============================================================================
// Service
// ==============================================================================

const BASE_PATH = '/dynamic-mcp-servers';

export const dynamicMcpServerService = {
  // ============================================================================
  // Provider CRUD
  // ============================================================================

  /**
   * List all Tool Providers for the organization
   */
  getServers: async (
    skip: number = 0,
    limit: number = 100,
    activeOnly: boolean = false
  ): Promise<ServerListResponse> => {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    params.append('active_only', activeOnly.toString());
    return apiClient.get<ServerListResponse>(`${BASE_PATH}?${params.toString()}`);
  },

  /**
   * Get a single Tool Provider by ID with all its tools
   */
  getServer: async (serverId: string): Promise<DynamicMCPServer> => {
    return apiClient.get<DynamicMCPServer>(`${BASE_PATH}/${serverId}`);
  },

  /**
   * Create a new Tool Provider with optional initial tools
   */
  createServer: async (data: ServerCreateRequest): Promise<DynamicMCPServer> => {
    return apiClient.post<DynamicMCPServer>(BASE_PATH, data);
  },

  /**
   * Update a Tool Provider
   */
  updateServer: async (
    serverId: string,
    data: ServerUpdateRequest
  ): Promise<DynamicMCPServer> => {
    return apiClient.patch<DynamicMCPServer>(`${BASE_PATH}/${serverId}`, data);
  },

  /**
   * Delete a Tool Provider and all its tools
   */
  deleteServer: async (serverId: string): Promise<void> => {
    return apiClient.delete<void>(`${BASE_PATH}/${serverId}`);
  },

  /**
   * Toggle a provider's active status
   */
  toggleServer: async (serverId: string): Promise<DynamicMCPServer> => {
    return apiClient.post<DynamicMCPServer>(`${BASE_PATH}/${serverId}/toggle`, {});
  },

  // ============================================================================
  // Tool CRUD (within a provider)
  // ============================================================================

  /**
   * Add a new tool to a provider
   */
  addTool: async (
    serverId: string,
    data: ToolCreateRequest
  ): Promise<DynamicMCPTool> => {
    return apiClient.post<DynamicMCPTool>(`${BASE_PATH}/${serverId}/tools`, data);
  },

  /**
   * Update a tool within a provider
   */
  updateTool: async (
    serverId: string,
    toolId: string,
    data: ToolUpdateRequest
  ): Promise<DynamicMCPTool> => {
    return apiClient.patch<DynamicMCPTool>(
      `${BASE_PATH}/${serverId}/tools/${toolId}`,
      data
    );
  },

  /**
   * Delete a tool from a provider
   */
  deleteTool: async (serverId: string, toolId: string): Promise<void> => {
    return apiClient.delete<void>(`${BASE_PATH}/${serverId}/tools/${toolId}`);
  },

  /**
   * Toggle a tool's active status within a provider
   */
  toggleTool: async (
    serverId: string,
    toolId: string
  ): Promise<DynamicMCPTool> => {
    return apiClient.post<DynamicMCPTool>(
      `${BASE_PATH}/${serverId}/tools/${toolId}/toggle`,
      {}
    );
  },

  // ============================================================================
  // Tool Execution
  // ============================================================================

  /**
   * Test execute a tool with provided arguments
   */
  testTool: async (
    serverId: string,
    toolId: string,
    request: ToolExecuteRequest
  ): Promise<ToolExecuteResponse> => {
    return apiClient.post<ToolExecuteResponse>(
      `${BASE_PATH}/${serverId}/tools/${toolId}/test`,
      request
    );
  },
};

// ==============================================================================
// Helper Functions
// ==============================================================================

/**
 * Get the full URL for a tool by combining provider base_url and tool path
 */
export function getToolFullUrl(server: DynamicMCPServer, tool: DynamicMCPTool): string {
  const baseUrl = server.base_url.replace(/\/$/, '');
  const path = tool.path.startsWith('/') ? tool.path : `/${tool.path}`;
  return `${baseUrl}${path}`;
}

/**
 * Create an empty tool template
 */
export function createEmptyTool(): ToolCreateRequest {
  return {
    name: '',
    description: '',
    path: '/',
    method: 'GET',
    parameters: [],
    headers: {},
    query_params: {},
    body_template: {},
    response_path: undefined,
  };
}

/**
 * Create an empty provider template
 */
export function createEmptyServer(): ServerCreateRequest {
  return {
    name: '',
    description: '',
    base_url: 'https://',
    credential_id: undefined,
    default_headers: {},
    timeout_seconds: 30,
    tools: [],
  };
}

/**
 * Create an empty parameter template
 */
export function createEmptyParameter(): ToolParameter {
  return {
    name: '',
    type: 'string',
    description: '',
    required: false,
    default: undefined,
    enum: undefined,
  };
}
