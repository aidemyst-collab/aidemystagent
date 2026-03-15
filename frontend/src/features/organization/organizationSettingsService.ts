/**
 * Organization Settings Service
 *
 * API service for managing organization-level settings including
 * guardrails, LLM defaults, security, and general preferences.
 */

import { apiClient } from '../../services/api';
import type {
  OrganizationSettings,
  OrganizationSettingsResponse,
  OrganizationSettingsUpdate,
  OrganizationGuardrailsConfig,
} from '../../types/organizationSettings';

interface GuardrailsOnlyResponse {
  organizationId: string;
  guardrails: OrganizationGuardrailsConfig;
  updatedAt: string | null;
}

interface GuardrailsOnlyUpdate {
  enforced?: OrganizationGuardrailsConfig['enforced'];
  defaults?: OrganizationGuardrailsConfig['defaults'];
  global?: OrganizationGuardrailsConfig['global'];
}

export const organizationSettingsService = {
  /**
   * Get settings for the current user's organization
   */
  getCurrentSettings: async (): Promise<OrganizationSettingsResponse> => {
    return apiClient.get<OrganizationSettingsResponse>('/organizations/current/settings');
  },

  /**
   * Update settings for the current user's organization
   */
  updateCurrentSettings: async (
    updates: OrganizationSettingsUpdate
  ): Promise<OrganizationSettingsResponse> => {
    return apiClient.patch<OrganizationSettingsResponse>('/organizations/current/settings', updates);
  },

  /**
   * Get guardrails for the current user's organization
   */
  getCurrentGuardrails: async (): Promise<GuardrailsOnlyResponse> => {
    return apiClient.get<GuardrailsOnlyResponse>('/organizations/current/settings/guardrails');
  },

  /**
   * Get settings for a specific organization
   */
  getSettings: async (organizationId: string): Promise<OrganizationSettingsResponse> => {
    return apiClient.get<OrganizationSettingsResponse>(`/organizations/${organizationId}/settings`);
  },

  /**
   * Update settings for a specific organization
   */
  updateSettings: async (
    organizationId: string,
    updates: OrganizationSettingsUpdate
  ): Promise<OrganizationSettingsResponse> => {
    return apiClient.patch<OrganizationSettingsResponse>(
      `/organizations/${organizationId}/settings`,
      updates
    );
  },

  /**
   * Get guardrails for a specific organization
   */
  getGuardrails: async (organizationId: string): Promise<GuardrailsOnlyResponse> => {
    return apiClient.get<GuardrailsOnlyResponse>(
      `/organizations/${organizationId}/settings/guardrails`
    );
  },

  /**
   * Update guardrails for a specific organization
   */
  updateGuardrails: async (
    organizationId: string,
    updates: GuardrailsOnlyUpdate
  ): Promise<GuardrailsOnlyResponse> => {
    return apiClient.patch<GuardrailsOnlyResponse>(
      `/organizations/${organizationId}/settings/guardrails`,
      updates
    );
  },

  /**
   * Update only the enforced guardrails section
   */
  updateEnforcedGuardrails: async (
    organizationId: string,
    enforced: OrganizationGuardrailsConfig['enforced']
  ): Promise<GuardrailsOnlyResponse> => {
    return apiClient.patch<GuardrailsOnlyResponse>(
      `/organizations/${organizationId}/settings/guardrails`,
      { enforced }
    );
  },

  /**
   * Update only the default guardrails section
   */
  updateDefaultGuardrails: async (
    organizationId: string,
    defaults: OrganizationGuardrailsConfig['defaults']
  ): Promise<GuardrailsOnlyResponse> => {
    return apiClient.patch<GuardrailsOnlyResponse>(
      `/organizations/${organizationId}/settings/guardrails`,
      { defaults }
    );
  },

  /**
   * Update global guardrail settings
   */
  updateGlobalGuardrailSettings: async (
    organizationId: string,
    globalSettings: OrganizationGuardrailsConfig['global']
  ): Promise<GuardrailsOnlyResponse> => {
    return apiClient.patch<GuardrailsOnlyResponse>(
      `/organizations/${organizationId}/settings/guardrails`,
      { global: globalSettings }
    );
  },
};

export default organizationSettingsService;
