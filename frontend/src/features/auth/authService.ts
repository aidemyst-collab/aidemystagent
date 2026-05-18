import { apiClient } from '../../services/api';
import type { User, AuthTokens, LoginRequest, RegisterRequest, PasswordResetRequest, Organization } from '../../types/auth';

interface LoginResponse {
  user: User;
  tokens: AuthTokens;
}

interface RegisterResponse {
  user: User;
  tokens: AuthTokens;
}

export const authService = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    return apiClient.post<LoginResponse>('/auth/login', data, { skipAuth: true });
  },

  register: async (data: RegisterRequest): Promise<RegisterResponse> => {
    return apiClient.post<RegisterResponse>('/auth/register', {
      email: data.email,
      password: data.password,
      full_name: data.fullName,
      organization_id: data.organizationId,
      organization_name: data.organizationName,
      role: data.role,
      website: data.website,
      phone_number: data.phoneNumber,
      country: data.country,
      industry: data.industry,
      employee_count: data.employeeCount,
      intended_use_case: data.intendedUseCase,
    }, { skipAuth: true });
  },

  logout: async (): Promise<void> => {
    return apiClient.post<void>('/auth/logout');
  },

  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    return apiClient.post<AuthTokens>('/auth/refresh', { refreshToken: refreshToken }, { skipAuth: true });
  },

  resetPassword: async (data: PasswordResetRequest): Promise<void> => {
    return apiClient.post<void>('/auth/reset-password', data, { skipAuth: true });
  },

  getCurrentUser: async (): Promise<User> => {
    return apiClient.get<User>('/auth/me');
  },

  getCurrentOrganization: async (): Promise<Organization> => {
    return apiClient.get<Organization>('/organizations/current');
  },
};
