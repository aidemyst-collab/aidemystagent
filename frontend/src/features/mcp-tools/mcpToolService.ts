import { apiClient } from '../../services/api';

export interface ToolParameter {
  name: string;
  type: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object';
  description?: string;
  required: boolean;
  default?: any;
  enum?: string[];
}

export interface DynamicMCPTool {
  id: string;
  organization_id: string;
  creator_id: string;
  name: string;
  description: string;
  api_endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  parameters: ToolParameter[];
  headers?: Record<string, string>;
  query_params?: Record<string, string>;
  body_template?: Record<string, any>;
  credential_id?: string;
  response_path?: string;
  response_template?: string;
  timeout_seconds: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DynamicMCPToolCreateRequest {
  name: string;
  description: string;
  api_endpoint: string;
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  parameters?: ToolParameter[];
  headers?: Record<string, string>;
  query_params?: Record<string, string>;
  body_template?: Record<string, any>;
  credential_id?: string;
  response_path?: string;
  response_template?: string;
  timeout_seconds?: number;
}

export interface DynamicMCPToolUpdateRequest {
  name?: string;
  description?: string;
  api_endpoint?: string;
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  parameters?: ToolParameter[];
  headers?: Record<string, string>;
  query_params?: Record<string, string>;
  body_template?: Record<string, any>;
  credential_id?: string;
  response_path?: string;
  response_template?: string;
  timeout_seconds?: number;
}

export interface DynamicMCPToolListResponse {
  tools: DynamicMCPTool[];
  total: number;
}

export const mcpToolService = {
  /**
   * Get all Dynamic MCP tools for the organization
   */
  getTools: async (
    skip: number = 0,
    limit: number = 100,
    activeOnly: boolean = true
  ): Promise<DynamicMCPToolListResponse> => {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    params.append('active_only', activeOnly.toString());
    return apiClient.get<DynamicMCPToolListResponse>(`/mcp-tools?${params.toString()}`);
  },

  /**
   * Get a single Dynamic MCP tool by ID
   */
  getTool: async (toolId: string): Promise<DynamicMCPTool> => {
    return apiClient.get<DynamicMCPTool>(`/mcp-tools/${toolId}`);
  },

  /**
   * Create a new Dynamic MCP tool
   */
  createTool: async (data: DynamicMCPToolCreateRequest): Promise<DynamicMCPTool> => {
    return apiClient.post<DynamicMCPTool>('/mcp-tools', data);
  },

  /**
   * Update a Dynamic MCP tool
   */
  updateTool: async (
    toolId: string,
    data: DynamicMCPToolUpdateRequest
  ): Promise<DynamicMCPTool> => {
    return apiClient.patch<DynamicMCPTool>(`/mcp-tools/${toolId}`, data);
  },

  /**
   * Delete a Dynamic MCP tool
   */
  deleteTool: async (toolId: string): Promise<void> => {
    return apiClient.delete<void>(`/mcp-tools/${toolId}`);
  },

  /**
   * Toggle a Dynamic MCP tool's active status
   */
  toggleTool: async (toolId: string): Promise<DynamicMCPTool> => {
    return apiClient.post<DynamicMCPTool>(`/mcp-tools/${toolId}/toggle`, {});
  },

  /**
   * Notify the Dynamic MCP Server to refresh tool definitions
   */
  refreshServer: async (): Promise<{ success: boolean; message: string }> => {
    return apiClient.post<{ success: boolean; message: string }>('/mcp-tools/refresh', {});
  },

  /**
   * Get all tools as MCP schemas (for Dynamic MCP Server)
   */
  getToolSchemas: async (): Promise<{ tools: any[]; total: number }> => {
    return apiClient.get<{ tools: any[]; total: number }>('/mcp-tools/schemas');
  },
};
