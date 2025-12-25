import { apiClient } from '../../services/api';

export interface Tool {
  id: string;
  organization_id: string;
  creator_id: string;
  name: string;
  description: string;
  type: 'built-in' | 'custom' | 'api' | 'mcp';
  config: any;
  visibility: 'public' | 'private' | 'organization';
  status: 'active' | 'deprecated';
  created_at: string;
  updated_at: string;
}

export interface CreateToolRequest {
  name: string;
  description: string;
  type: 'custom' | 'api' | 'mcp';
  config: any;
  visibility?: 'public' | 'private' | 'organization';
}

export interface UpdateToolRequest {
  name?: string;
  description?: string;
  config?: any;
  visibility?: 'public' | 'private' | 'organization';
  status?: 'active' | 'deprecated';
}

export interface ToolListResponse {
  tools: Tool[];
  total: number;
}

export interface ToolExecuteRequest {
  input_data: Record<string, any>;
}

export interface ToolExecuteResponse {
  success: boolean;
  result: any;
  error?: string;
  execution_time?: number;
}

export const toolService = {
  /**
   * Get all built-in tools
   */
  getBuiltInTools: async (): Promise<{ tools: any[] }> => {
    return apiClient.get<{ tools: any[] }>('/tools/built-in');
  },

  /**
   * Execute a built-in tool
   */
  executeBuiltInTool: async (toolName: string, inputData: Record<string, any>): Promise<any> => {
    return apiClient.post<any>(`/tools/built-in/${toolName}/execute`, { input_data: inputData });
  },

  /**
   * Get all custom tools, optionally filtered by type
   */
  getTools: async (skip: number = 0, limit: number = 100, toolType?: string): Promise<ToolListResponse> => {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (toolType) {
      params.append('tool_type', toolType);
    }
    return apiClient.get<ToolListResponse>(`/tools/?${params.toString()}`);
  },

  /**
   * Get tool by ID
   */
  getTool: async (toolId: string): Promise<Tool> => {
    return apiClient.get<Tool>(`/tools/${toolId}`);
  },

  /**
   * Create a new custom tool
   */
  createTool: async (data: CreateToolRequest): Promise<Tool> => {
    return apiClient.post<Tool>('/tools/', data);
  },

  /**
   * Update a tool
   */
  updateTool: async (toolId: string, data: UpdateToolRequest): Promise<Tool> => {
    return apiClient.put<Tool>(`/tools/${toolId}`, data);
  },

  /**
   * Delete a tool
   */
  deleteTool: async (toolId: string): Promise<void> => {
    return apiClient.delete<void>(`/tools/${toolId}`);
  },

  /**
   * Test a custom tool
   */
  testTool: async (toolId: string, request: ToolExecuteRequest): Promise<ToolExecuteResponse> => {
    return apiClient.post<ToolExecuteResponse>(`/tools/${toolId}/test`, request);
  },

  /**
   * Get tool categories
   */
  getToolCategories: async (): Promise<any> => {
    return apiClient.get<any>('/tools/categories/list');
  },
};
