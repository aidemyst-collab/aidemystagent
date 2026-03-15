/**
 * Organization Settings Hooks
 *
 * React Query hooks for fetching and updating organization settings.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';
import { organizationSettingsService } from './organizationSettingsService';
import type {
  OrganizationSettingsUpdate,
  OrganizationGuardrailsConfig,
} from '../../types/organizationSettings';

// Query keys
export const organizationSettingsKeys = {
  all: ['organizationSettings'] as const,
  current: () => [...organizationSettingsKeys.all, 'current'] as const,
  currentGuardrails: () => [...organizationSettingsKeys.current(), 'guardrails'] as const,
  byOrg: (orgId: string) => [...organizationSettingsKeys.all, orgId] as const,
  guardrails: (orgId: string) => [...organizationSettingsKeys.byOrg(orgId), 'guardrails'] as const,
};

/**
 * Hook to fetch current organization settings
 */
export function useCurrentOrganizationSettings() {
  return useQuery({
    queryKey: organizationSettingsKeys.current(),
    queryFn: () => organizationSettingsService.getCurrentSettings(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch current organization guardrails only
 */
export function useCurrentOrganizationGuardrails() {
  return useQuery({
    queryKey: organizationSettingsKeys.currentGuardrails(),
    queryFn: () => organizationSettingsService.getCurrentGuardrails(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch organization settings by ID
 */
export function useOrganizationSettings(organizationId: string | undefined) {
  return useQuery({
    queryKey: organizationSettingsKeys.byOrg(organizationId || ''),
    queryFn: () => organizationSettingsService.getSettings(organizationId!),
    enabled: !!organizationId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch organization guardrails by ID
 */
export function useOrganizationGuardrails(organizationId: string | undefined) {
  return useQuery({
    queryKey: organizationSettingsKeys.guardrails(organizationId || ''),
    queryFn: () => organizationSettingsService.getGuardrails(organizationId!),
    enabled: !!organizationId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to update current organization settings
 */
export function useUpdateCurrentSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (updates: OrganizationSettingsUpdate) =>
      organizationSettingsService.updateCurrentSettings(updates),
    onSuccess: (data) => {
      queryClient.setQueryData(organizationSettingsKeys.current(), data);
      // Also invalidate guardrails if guardrails were updated
      queryClient.invalidateQueries({
        queryKey: organizationSettingsKeys.currentGuardrails(),
      });
      message.success('Settings updated successfully');
    },
    onError: (error: Error) => {
      message.error(`Failed to update settings: ${error.message}`);
    },
  });
}

/**
 * Hook to update organization settings by ID
 */
export function useUpdateOrganizationSettings(organizationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (updates: OrganizationSettingsUpdate) =>
      organizationSettingsService.updateSettings(organizationId, updates),
    onSuccess: (data) => {
      queryClient.setQueryData(organizationSettingsKeys.byOrg(organizationId), data);
      queryClient.invalidateQueries({
        queryKey: organizationSettingsKeys.guardrails(organizationId),
      });
      message.success('Settings updated successfully');
    },
    onError: (error: Error) => {
      message.error(`Failed to update settings: ${error.message}`);
    },
  });
}

/**
 * Hook to update organization guardrails
 */
export function useUpdateOrganizationGuardrails(organizationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (updates: {
      enforced?: OrganizationGuardrailsConfig['enforced'];
      defaults?: OrganizationGuardrailsConfig['defaults'];
      global?: OrganizationGuardrailsConfig['global'];
    }) => organizationSettingsService.updateGuardrails(organizationId, updates),
    onSuccess: (data) => {
      queryClient.setQueryData(organizationSettingsKeys.guardrails(organizationId), data);
      // Also invalidate the full settings
      queryClient.invalidateQueries({
        queryKey: organizationSettingsKeys.byOrg(organizationId),
      });
      message.success('Guardrails updated successfully');
    },
    onError: (error: Error) => {
      message.error(`Failed to update guardrails: ${error.message}`);
    },
  });
}

/**
 * Hook to update only enforced guardrails
 */
export function useUpdateEnforcedGuardrails(organizationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (enforced: OrganizationGuardrailsConfig['enforced']) =>
      organizationSettingsService.updateEnforcedGuardrails(organizationId, enforced),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: organizationSettingsKeys.guardrails(organizationId),
      });
      queryClient.invalidateQueries({
        queryKey: organizationSettingsKeys.byOrg(organizationId),
      });
      message.success('Enforced guardrails updated successfully');
    },
    onError: (error: Error) => {
      message.error(`Failed to update enforced guardrails: ${error.message}`);
    },
  });
}
