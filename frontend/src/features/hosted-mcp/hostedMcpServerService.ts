import { apiClient } from '../../services/api';

// Types
export type HostedMCPServerStatus = 'pending' | 'deploying' | 'running' | 'stopped' | 'failed' | 'deleted';
export type HostedMCPServerSourceType = 'registry' | 'github' | 'docker';

export interface RegistrySourceConfig {
  package: string;
  version?: string;
}

export interface GitHubSourceConfig {
  repo: string;
  branch?: string;
  dockerfile_path?: string;
}

export interface DockerSourceConfig {
  image: string;
  registry_credential_id?: string;
}

export type SourceConfig = RegistrySourceConfig | GitHubSourceConfig | DockerSourceConfig;

export interface DiscoveredTool {
  name: string;
  description?: string;
  input_schema?: Record<string, any>;
}

export interface DiscoveredResource {
  uri: string;
  name?: string;
  description?: string;
  mime_type?: string;
}

export interface DiscoveredPrompt {
  name: string;
  description?: string;
  arguments?: Record<string, any>[];
}

export interface HostedMCPServer {
  id: string;
  organization_id: string;
  creator_id: string;
  name: string;
  description: string | null;
  source_type: HostedMCPServerSourceType;
  source_config: SourceConfig;
  azure_app_name: string | null;
  azure_app_url: string | null;
  azure_resource_id: string | null;
  environment_variables: Record<string, string>;
  port: number;
  cpu_cores: number;
  memory_gb: number;
  min_replicas: number;
  max_replicas: number;
  status: HostedMCPServerStatus;
  last_health_check: string | null;
  error_message: string | null;
  discovered_tools: DiscoveredTool[];
  discovered_resources: DiscoveredResource[];
  discovered_prompts: DiscoveredPrompt[];
  tool_count: number;
  resource_count: number;
  prompt_count: number;
  created_at: string;
  updated_at: string;
}

export interface HostedMCPServerCreateRequest {
  name: string;
  description?: string;
  source_type: HostedMCPServerSourceType;
  source_config: SourceConfig;
  environment_variables?: Record<string, string>;
  port?: number;
  cpu_cores?: number;
  memory_gb?: number;
  min_replicas?: number;
  max_replicas?: number;
}

export interface HostedMCPServerUpdateRequest {
  name?: string;
  description?: string;
  environment_variables?: Record<string, string>;
  cpu_cores?: number;
  memory_gb?: number;
  min_replicas?: number;
  max_replicas?: number;
}

export interface HostedMCPServerListResponse {
  servers: HostedMCPServer[];
  total: number;
}

export interface HostedMCPServerLogs {
  logs: string;
  timestamp: string;
}

export interface HostedMCPServerDiscoveryResponse {
  tools: DiscoveredTool[];
  resources: DiscoveredResource[];
  prompts: DiscoveredPrompt[];
  discovered_at: string;
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

export const hostedMcpServerService = {
  /**
   * Get all hosted MCP servers for the organization
   */
  getServers: async (
    skip: number = 0,
    limit: number = 100,
    statusFilter?: HostedMCPServerStatus
  ): Promise<HostedMCPServerListResponse> => {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (statusFilter) {
      params.append('status_filter', statusFilter);
    }
    return apiClient.get<HostedMCPServerListResponse>(`/hosted-mcp-servers?${params.toString()}`);
  },

  /**
   * Get a single hosted MCP server by ID
   */
  getServer: async (serverId: string): Promise<HostedMCPServer> => {
    return apiClient.get<HostedMCPServer>(`/hosted-mcp-servers/${serverId}`);
  },

  /**
   * Create and deploy a new hosted MCP server
   */
  createServer: async (data: HostedMCPServerCreateRequest): Promise<HostedMCPServer> => {
    return apiClient.post<HostedMCPServer>('/hosted-mcp-servers', data);
  },

  /**
   * Update a hosted MCP server
   */
  updateServer: async (serverId: string, data: HostedMCPServerUpdateRequest): Promise<HostedMCPServer> => {
    return apiClient.patch<HostedMCPServer>(`/hosted-mcp-servers/${serverId}`, data);
  },

  /**
   * Delete a hosted MCP server
   */
  deleteServer: async (serverId: string): Promise<void> => {
    return apiClient.delete<void>(`/hosted-mcp-servers/${serverId}`);
  },

  /**
   * Start a stopped server
   */
  startServer: async (serverId: string): Promise<HostedMCPServer> => {
    return apiClient.post<HostedMCPServer>(`/hosted-mcp-servers/${serverId}/start`, {});
  },

  /**
   * Stop a running server
   */
  stopServer: async (serverId: string): Promise<HostedMCPServer> => {
    return apiClient.post<HostedMCPServer>(`/hosted-mcp-servers/${serverId}/stop`, {});
  },

  /**
   * Force redeploy a server
   */
  redeployServer: async (serverId: string): Promise<HostedMCPServer> => {
    return apiClient.post<HostedMCPServer>(`/hosted-mcp-servers/${serverId}/redeploy`, {});
  },

  /**
   * Get container logs
   */
  getLogs: async (serverId: string, lines: number = 100): Promise<HostedMCPServerLogs> => {
    return apiClient.get<HostedMCPServerLogs>(`/hosted-mcp-servers/${serverId}/logs?lines=${lines}`);
  },

  /**
   * Discover MCP capabilities from a running server
   */
  discoverCapabilities: async (serverId: string): Promise<HostedMCPServerDiscoveryResponse> => {
    return apiClient.post<HostedMCPServerDiscoveryResponse>(`/hosted-mcp-servers/${serverId}/discover`, {});
  },

  /**
   * Execute a tool on a hosted MCP server
   */
  executeTool: async (
    serverId: string,
    toolName: string,
    args: Record<string, any>
  ): Promise<ToolExecuteResponse> => {
    return apiClient.post<ToolExecuteResponse>(
      `/hosted-mcp-servers/${serverId}/tools/${toolName}/execute`,
      { arguments: args }
    );
  },
};

// Status color mapping for UI
export const statusColors: Record<HostedMCPServerStatus, string> = {
  pending: 'default',
  deploying: 'processing',
  running: 'success',
  stopped: 'warning',
  failed: 'error',
  deleted: 'default',
};

// Status display names
export const statusDisplayNames: Record<HostedMCPServerStatus, string> = {
  pending: 'Pending',
  deploying: 'Deploying',
  running: 'Running',
  stopped: 'Stopped',
  failed: 'Failed',
  deleted: 'Deleted',
};

// Source type display names
export const sourceTypeDisplayNames: Record<HostedMCPServerSourceType, string> = {
  registry: 'npm Registry',
  github: 'GitHub',
  docker: 'Docker Image',
};
