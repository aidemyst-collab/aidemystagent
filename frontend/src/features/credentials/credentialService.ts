/**
 * Credential Service
 * Handles API calls for LLM credential management
 */
import { apiClient } from '../../services/api';

export type CredentialProvider =
  | 'openai'
  | 'anthropic'
  | 'google'
  | 'azure_openai'
  | 'custom'
  | 'redis'
  | 'postgresql'
  | 'mongodb'
  | 'twilio'
  | 'etisalat'
  | 'whatsapp_meta';

export interface Credential {
  id: string;
  user_id: string;
  organization_id: string;
  name: string;
  provider: CredentialProvider;
  api_key_preview: string;
  api_base?: string;
  api_version?: string;
  organization_key?: string;
  is_active: string;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
}

export interface CreateCredentialRequest {
  name: string;
  provider: CredentialProvider;
  api_key?: string;
  connection_config?: Record<string, any>;
  api_base?: string;
  api_version?: string;
  organization_key?: string;
}

export interface UpdateCredentialRequest {
  name?: string;
  api_key?: string;
  connection_config?: Record<string, any>;
  api_base?: string;
  api_version?: string;
  organization_key?: string;
  is_active?: string;
}

export interface CredentialListResponse {
  credentials: Credential[];
  total: number;
}

export interface TestCredentialRequest {
  credential_id?: string;
  provider: CredentialProvider;
  api_key?: string;
  connection_config?: Record<string, any>;
  api_base?: string;
  api_version?: string;
}

export interface TestCredentialResponse {
  success: boolean;
  message: string;
  details?: Record<string, any>;
}

export const credentialService = {
  /**
   * Get all credentials
   */
  async getCredentials(skip?: number, limit?: number, provider?: CredentialProvider): Promise<CredentialListResponse> {
    const params = new URLSearchParams();
    if (skip !== undefined) params.append('skip', skip.toString());
    if (limit !== undefined) params.append('limit', limit.toString());
    if (provider) params.append('provider', provider);

    return apiClient.get(`/credentials?${params.toString()}`);
  },

  /**
   * Get a single credential by ID
   */
  async getCredential(credentialId: string): Promise<Credential> {
    return apiClient.get(`/credentials/${credentialId}`);
  },

  /**
   * Create a new credential
   */
  async createCredential(data: CreateCredentialRequest): Promise<Credential> {
    return apiClient.post('/credentials', data);
  },

  /**
   * Update an existing credential
   */
  async updateCredential(credentialId: string, data: UpdateCredentialRequest): Promise<Credential> {
    return apiClient.put(`/credentials/${credentialId}`, data);
  },

  /**
   * Delete a credential
   */
  async deleteCredential(credentialId: string): Promise<void> {
    return apiClient.delete(`/credentials/${credentialId}`);
  },

  /**
   * Test a credential to verify it works
   */
  async testCredential(data: TestCredentialRequest): Promise<TestCredentialResponse> {
    return apiClient.post('/credentials/test', data);
  },
};
