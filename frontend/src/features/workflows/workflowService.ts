import { apiClient } from '../../services/api';
import type { Workflow, WorkflowConfig } from '../../types/workflow';

interface CreateWorkflowRequest {
  name: string;
  description: string;
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

interface DeployWorkflowResponse {
  id: string;
  status: 'deployed';
  endpoint: string;
  deployedAt: string;
}

export const workflowService = {
  /**
   * Create a new workflow
   */
  createWorkflow: async (data: CreateWorkflowRequest): Promise<Workflow> => {
    const { name, description, ...config } = data;
    const payload = {
      name,
      description,
      config
    };
    console.log('Creating workflow with payload:', payload);
    return apiClient.post<Workflow>('/workflows/', payload);
  },

  /**
   * Update an existing workflow
   */
  updateWorkflow: async (id: string, data: Partial<CreateWorkflowRequest>): Promise<Workflow> => {
    const { name, description, ...config } = data;
    return apiClient.put<Workflow>(`/workflows/${id}/`, {
      name,
      description,
      config
    });
  },

  /**
   * Deploy a workflow (change status to deployed)
   */
  deployWorkflow: async (id: string): Promise<DeployWorkflowResponse> => {
    return apiClient.post<DeployWorkflowResponse>(`/workflows/${id}/deploy`, {});
  },

  /**
   * Get workflow by ID
   */
  getWorkflow: async (id: string): Promise<Workflow> => {
    return apiClient.get<Workflow>(`/workflows/${id}/`);
  },

  /**
   * Get all workflows for current user
   */
  getWorkflows: async (): Promise<Workflow[]> => {
    const response = await apiClient.get<{ total: number; workflows: Workflow[] }>('/workflows/');
    return response.workflows;
  },

  /**
   * Delete a workflow
   */
  deleteWorkflow: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/workflows/${id}/`);
  },

  /**
   * Execute a workflow
   */
  executeWorkflow: async (id: string, input: string, inputMode?: string, sessionId?: string): Promise<any> => {
    return apiClient.post<any>(`/workflows/${id}/execute/`, {
      input,
      input_mode: inputMode,
      session_id: sessionId
    });
  },
};
