import { apiClient } from '../../services/api';

export interface OrgUser {
  id: string;
  email: string;
  fullName?: string;
  isActive: boolean;
  emailVerified: boolean;
  isPlatformAdmin: boolean;
  roles: Array<{
    id: string;
    name: string;
    displayName: string;
    assignedAt: string;
  }>;
  createdAt: string;
  lastLoginAt?: string;
}

export interface OrgRole {
  id: string;
  name: string;
  displayName: string;
  description?: string;
  isSystemRole: boolean;
}

interface UserListResponse {
  users: OrgUser[];
  total: number;
}

interface RoleListResponse {
  roles: OrgRole[];
}

interface UserProfile {
  id: string;
  email: string;
  fullName?: string;
  organizationId?: string;
  organizationName?: string;
  roles: string[];
  isPlatformAdmin: boolean;
  isActive: boolean;
  emailVerified: boolean;
  createdAt: string;
  lastLoginAt?: string;
}

export const userService = {
  // List users in organization
  list: async (params?: {
    skip?: number;
    limit?: number;
    isActive?: boolean;
    roleId?: string;
    search?: string;
  }): Promise<UserListResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.isActive !== undefined) queryParams.append('is_active', params.isActive.toString());
    if (params?.roleId) queryParams.append('role_id', params.roleId);
    if (params?.search) queryParams.append('search', params.search);

    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await apiClient.get<{
      users: Array<{
        id: string;
        email: string;
        full_name?: string;
        is_active: boolean;
        email_verified: boolean;
        is_platform_admin: boolean;
        roles: Array<{
          id: string;
          name: string;
          display_name: string;
          assigned_at: string;
        }>;
        created_at: string;
        last_login_at?: string;
      }>;
      total: number;
    }>(`/users${query}`);

    return {
      users: response.users.map((u) => ({
        id: u.id,
        email: u.email,
        fullName: u.full_name,
        isActive: u.is_active,
        emailVerified: u.email_verified,
        isPlatformAdmin: u.is_platform_admin,
        roles: u.roles.map((r) => ({
          id: r.id,
          name: r.name,
          displayName: r.display_name,
          assignedAt: r.assigned_at,
        })),
        createdAt: u.created_at,
        lastLoginAt: u.last_login_at,
      })),
      total: response.total,
    };
  },

  // Get current user profile
  getProfile: async (): Promise<UserProfile> => {
    const response = await apiClient.get<{
      id: string;
      email: string;
      full_name?: string;
      organization_id?: string;
      organization_name?: string;
      roles: string[];
      is_platform_admin: boolean;
      is_active: boolean;
      email_verified: boolean;
      created_at: string;
      last_login_at?: string;
    }>('/users/me');

    return {
      id: response.id,
      email: response.email,
      fullName: response.full_name,
      organizationId: response.organization_id,
      organizationName: response.organization_name,
      roles: response.roles,
      isPlatformAdmin: response.is_platform_admin,
      isActive: response.is_active,
      emailVerified: response.email_verified,
      createdAt: response.created_at,
      lastLoginAt: response.last_login_at,
    };
  },

  // Update current user profile
  updateProfile: async (data: {
    fullName?: string;
  }): Promise<UserProfile> => {
    const response = await apiClient.patch<{
      id: string;
      email: string;
      full_name?: string;
      organization_id?: string;
      organization_name?: string;
      roles: string[];
      is_platform_admin: boolean;
      is_active: boolean;
      email_verified: boolean;
      created_at: string;
      last_login_at?: string;
    }>('/users/me', {
      full_name: data.fullName,
    });

    return {
      id: response.id,
      email: response.email,
      fullName: response.full_name,
      organizationId: response.organization_id,
      organizationName: response.organization_name,
      roles: response.roles,
      isPlatformAdmin: response.is_platform_admin,
      isActive: response.is_active,
      emailVerified: response.email_verified,
      createdAt: response.created_at,
      lastLoginAt: response.last_login_at,
    };
  },

  // Activate user
  activate: async (userId: string): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>(`/users/${userId}/activate`, {});
  },

  // Deactivate user
  deactivate: async (userId: string): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>(`/users/${userId}/deactivate`, {});
  },

  // Unlock user account
  unlock: async (userId: string): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>(`/users/${userId}/unlock`, {});
  },

  // Assign role to user
  assignRole: async (userId: string, roleId: string): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>(`/users/${userId}/roles`, {
      role_id: roleId,
    });
  },

  // Remove role from user
  removeRole: async (userId: string, roleId: string): Promise<{ message: string }> => {
    return apiClient.delete(`/users/${userId}/roles/${roleId}`);
  },

  // Delete user
  delete: async (userId: string): Promise<void> => {
    return apiClient.delete(`/users/${userId}`);
  },

  // Get available roles for organization
  getRoles: async (): Promise<OrgRole[]> => {
    const response = await apiClient.get<RoleListResponse>('/users/roles');
    return response.roles.map((r) => ({
      id: r.id,
      name: r.name,
      displayName: r.display_name,
      description: r.description,
      isSystemRole: r.is_system_role,
    }));
  },
};
