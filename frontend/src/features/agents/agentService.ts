import { apiClient } from '../../services/api';
import type { Agent, AgentConfig } from '../../types/agent';

interface CreateAgentRequest {
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
    authType: string;
    searchMethod: string;
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
  nodes: any[];
  edges: any[];
  status: 'draft' | 'deployed' | 'archived';
  version: number;
}

interface UpdateAgentRequest extends CreateAgentRequest {
  id: string;
}

interface DeployAgentResponse {
  id: string;
  status: 'deployed';
  endpoint: string;
  deployedAt: string;
}

export const agentService = {
  /**
   * Create a new agent
   */
  createAgent: async (data: CreateAgentRequest): Promise<Agent> => {
    const { name, description, ...config } = data;
    const payload = {
      name,
      description,
      config
    };
    console.log('Creating agent with payload:', payload);
    return apiClient.post<Agent>('/agents', payload);
  },

  /**
   * Update an existing agent
   */
  updateAgent: async (id: string, data: Partial<CreateAgentRequest>): Promise<Agent> => {
    const { name, description, ...config } = data;
    return apiClient.put<Agent>(`/agents/${id}`, {
      name,
      description,
      config
    });
  },

  /**
   * Deploy an agent (change status to deployed)
   */
  deployAgent: async (id: string): Promise<DeployAgentResponse> => {
    return apiClient.post<DeployAgentResponse>(`/agents/${id}/deploy`, {});
  },

  /**
   * Get agent by ID
   */
  getAgent: async (id: string): Promise<Agent> => {
    return apiClient.get<Agent>(`/agents/${id}`);
  },

  /**
   * Get all agents for current user
   */
  getAgents: async (): Promise<Agent[]> => {
    return apiClient.get<Agent[]>('/agents');
  },

  /**
   * Delete an agent
   */
  deleteAgent: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/agents/${id}`);
  },

  /**
   * Execute an agent
   */
  executeAgent: async (id: string, input: string): Promise<any> => {
    return apiClient.post<any>(`/agents/${id}/execute`, { input });
  },
};
