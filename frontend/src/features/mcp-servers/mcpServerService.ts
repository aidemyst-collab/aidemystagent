import { apiClient } from '../../services/api';

export interface MCPServer {
  id: string;
  organization_id: string;
  creator_id: string;
  name: string;
  description: string | null;
  server_url: string;
  transport_type: 'sse' | 'http' | 'stdio';
  credential_id: string | null;
  status: 'active' | 'inactive' | 'error';
  last_health_check: string | null;
  last_error: string | null;
  discovered_tools: MCPToolSchema[];
  discovered_resources: MCPResourceSchema[];
  discovered_prompts: MCPPromptSchema[];
  created_at: string;
  updated_at: string;
}

export interface MCPToolSchema {
  name: string;
  description?: string;
  input_schema?: Record<string, any>;
}

export interface MCPResourceSchema {
  uri: string;
  name?: string;
  description?: string;
  mime_type?: string;
}

export interface MCPPromptSchema {
  name: string;
  description?: string;
  arguments?: Record<string, any>[];
}

export interface MCPServerCreateRequest {
  name: string;
  description?: string;
  server_url: string;
  transport_type?: 'sse' | 'http' | 'stdio';
  credential_id?: string;
}

export interface MCPServerUpdateRequest {
  name?: string;
  description?: string;
  server_url?: string;
  transport_type?: 'sse' | 'http' | 'stdio';
  credential_id?: string;
  status?: 'active' | 'inactive' | 'error';
}

export interface MCPServerListResponse {
  servers: MCPServer[];
  total: number;
}

export interface MCPServerTestRequest {
  server_url?: string;
  auth_token?: string;
}

export interface MCPServerTestResponse {
  success: boolean;
  message: string;
  response_time_ms?: number;
  server_info?: Record<string, any>;
  error?: string;
}

export interface MCPServerDiscoveryResponse {
  success: boolean;
  tools: MCPToolSchema[];
  resources: MCPResourceSchema[];
  prompts: MCPPromptSchema[];
  error?: string;
}

export interface MCPServerHealthResponse {
  server_id: string;
  status: 'active' | 'inactive' | 'error';
  last_check: string;
  response_time_ms?: number;
  error?: string;
}

export const mcpServerService = {
  /**
   * Get all MCP servers for the organization
   */
  getServers: async (
    skip: number = 0,
    limit: number = 100,
    statusFilter?: string
  ): Promise<MCPServerListResponse> => {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (statusFilter) {
      params.append('status_filter', statusFilter);
    }
    return apiClient.get<MCPServerListResponse>(`/mcp-servers?${params.toString()}`);
  },

  /**
   * Get a single MCP server by ID
   */
  getServer: async (serverId: string): Promise<MCPServer> => {
    return apiClient.get<MCPServer>(`/mcp-servers/${serverId}`);
  },

  /**
   * Create a new MCP server
   */
  createServer: async (data: MCPServerCreateRequest): Promise<MCPServer> => {
    return apiClient.post<MCPServer>('/mcp-servers', data);
  },

  /**
   * Update an MCP server
   */
  updateServer: async (serverId: string, data: MCPServerUpdateRequest): Promise<MCPServer> => {
    return apiClient.patch<MCPServer>(`/mcp-servers/${serverId}`, data);
  },

  /**
   * Delete an MCP server
   */
  deleteServer: async (serverId: string): Promise<void> => {
    return apiClient.delete<void>(`/mcp-servers/${serverId}`);
  },

  /**
   * Test connection to an MCP server
   */
  testConnection: async (
    serverId: string,
    request?: MCPServerTestRequest
  ): Promise<MCPServerTestResponse> => {
    return apiClient.post<MCPServerTestResponse>(`/mcp-servers/${serverId}/test`, request || {});
  },

  /**
   * Discover tools, resources, and prompts from an MCP server
   */
  discoverCapabilities: async (serverId: string): Promise<MCPServerDiscoveryResponse> => {
    return apiClient.post<MCPServerDiscoveryResponse>(`/mcp-servers/${serverId}/discover`, {});
  },

  /**
   * Get health status of an MCP server
   */
  getHealth: async (serverId: string): Promise<MCPServerHealthResponse> => {
    return apiClient.get<MCPServerHealthResponse>(`/mcp-servers/${serverId}/health`);
  },
};
