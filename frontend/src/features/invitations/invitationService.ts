import { apiClient } from '../../services/api';
import type {
  Invitation,
  CreateInvitationRequest,
  AcceptInvitationRequest,
  Role,
} from '../../types/auth';

interface InvitationListResponse {
  invitations: Invitation[];
  total: number;
}

interface VerifyInvitationResponse {
  email: string;
  organization_name: string;
  role_name: string;
  message?: string;
  expires_at: string;
}

interface AcceptInvitationResponse {
  message: string;
  user_id: string;
  organization_id: string;
  organization_name: string;
}

interface AvailableRolesResponse {
  roles: Array<{
    id: string;
    name: string;
    display_name: string;
    description?: string;
    is_system_role: boolean;
  }>;
}

export const invitationService = {
  // Create invitation
  create: async (data: CreateInvitationRequest): Promise<Invitation> => {
    return apiClient.post<Invitation>('/invitations', {
      email: data.email,
      role_id: data.roleId,
      message: data.message,
      expires_in_days: data.expiresInDays,
    });
  },

  // List invitations for organization
  list: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<InvitationListResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.status) queryParams.append('status_filter', params.status);

    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    return apiClient.get<InvitationListResponse>(`/invitations${query}`);
  },

  // Get specific invitation
  get: async (invitationId: string): Promise<Invitation> => {
    return apiClient.get<Invitation>(`/invitations/${invitationId}`);
  },

  // Revoke invitation
  revoke: async (invitationId: string): Promise<void> => {
    return apiClient.delete(`/invitations/${invitationId}`);
  },

  // Resend invitation
  resend: async (invitationId: string): Promise<Invitation> => {
    return apiClient.post<Invitation>(`/invitations/${invitationId}/resend`, {});
  },

  // Verify invitation token (public)
  verify: async (token: string): Promise<VerifyInvitationResponse> => {
    return apiClient.get<VerifyInvitationResponse>(`/invitations/verify/${token}`, { skipAuth: true });
  },

  // Accept invitation (public)
  accept: async (token: string, data: AcceptInvitationRequest): Promise<AcceptInvitationResponse> => {
    return apiClient.post<AcceptInvitationResponse>(
      `/invitations/accept/${token}`,
      {
        full_name: data.fullName,
        password: data.password,
      },
      { skipAuth: true }
    );
  },

  // Get available roles for invitations
  getAvailableRoles: async (): Promise<Role[]> => {
    const response = await apiClient.get<AvailableRolesResponse>('/invitations/roles/available');
    return response.roles.map(role => ({
      id: role.id,
      name: role.name,
      displayName: role.display_name,
      description: role.description,
      isSystemRole: role.is_system_role,
      permissions: [],
    }));
  },
};
