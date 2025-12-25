import { apiClient } from '../../services/api';
import type { AuditLog, AuditSummary } from '../../types/auth';

interface AuditLogListResponse {
  audit_logs: AuditLog[];
  total: number;
}

interface AuditActionsResponse {
  actions: Record<string, string[]>;
}

interface ResourceTypesResponse {
  resource_types: string[];
}

export const auditService = {
  // List audit logs
  list: async (params?: {
    skip?: number;
    limit?: number;
    action?: string;
    resourceType?: string;
    resourceId?: string;
    userId?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
    search?: string;
  }): Promise<AuditLogListResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.action) queryParams.append('action', params.action);
    if (params?.resourceType) queryParams.append('resource_type', params.resourceType);
    if (params?.resourceId) queryParams.append('resource_id', params.resourceId);
    if (params?.userId) queryParams.append('user_id', params.userId);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.startDate) queryParams.append('start_date', params.startDate);
    if (params?.endDate) queryParams.append('end_date', params.endDate);
    if (params?.search) queryParams.append('search', params.search);

    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    return apiClient.get<AuditLogListResponse>(`/audit/logs${query}`);
  },

  // Get specific audit log
  get: async (logId: string): Promise<AuditLog> => {
    return apiClient.get<AuditLog>(`/audit/logs/${logId}`);
  },

  // Get audit summary
  getSummary: async (params?: {
    startDate?: string;
    endDate?: string;
  }): Promise<AuditSummary> => {
    const queryParams = new URLSearchParams();
    if (params?.startDate) queryParams.append('start_date', params.startDate);
    if (params?.endDate) queryParams.append('end_date', params.endDate);

    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await apiClient.get<{
      total_logs: number;
      logs_by_action: Array<{
        action: string;
        count: number;
        last_occurrence: string;
      }>;
      logs_by_resource_type: Record<string, number>;
      logs_by_status: Record<string, number>;
      recent_users: string[];
    }>(`/audit/summary${query}`);

    return {
      totalLogs: response.total_logs,
      logsByAction: response.logs_by_action.map(item => ({
        action: item.action,
        count: item.count,
        lastOccurrence: item.last_occurrence,
      })),
      logsByResourceType: response.logs_by_resource_type,
      logsByStatus: response.logs_by_status,
      recentUsers: response.recent_users,
    };
  },

  // Export audit logs
  exportLogs: async (params: {
    format: 'csv' | 'json';
    action?: string;
    resourceType?: string;
    startDate?: string;
    endDate?: string;
    limit?: number;
  }): Promise<Blob> => {
    const queryParams = new URLSearchParams();
    queryParams.append('format', params.format);
    if (params.action) queryParams.append('action', params.action);
    if (params.resourceType) queryParams.append('resource_type', params.resourceType);
    if (params.startDate) queryParams.append('start_date', params.startDate);
    if (params.endDate) queryParams.append('end_date', params.endDate);
    if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());

    const response = await fetch(`/api/v1/audit/export?${queryParams.toString()}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth-storage') ? JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.tokens?.accessToken : ''}`,
      },
    });

    if (!response.ok) {
      throw new Error('Export failed');
    }

    return response.blob();
  },

  // Get available action types
  getActions: async (): Promise<Record<string, string[]>> => {
    const response = await apiClient.get<AuditActionsResponse>('/audit/actions');
    return response.actions;
  },

  // Get resource types with audit logs
  getResourceTypes: async (): Promise<string[]> => {
    const response = await apiClient.get<ResourceTypesResponse>('/audit/resource-types');
    return response.resource_types;
  },
};
