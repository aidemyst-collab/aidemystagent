import { apiClient } from '../../services/api';
import type { User, AuthTokens, LoginRequest, RegisterRequest, PasswordResetRequest } from '../../types/auth';

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
    return apiClient.post<RegisterResponse>('/auth/register', data, { skipAuth: true });
  },

  logout: async (): Promise<void> => {
    return apiClient.post<void>('/auth/logout');
  },

  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    return apiClient.post<AuthTokens>('/auth/refresh', { refreshToken }, { skipAuth: true });
  },

  resetPassword: async (data: PasswordResetRequest): Promise<void> => {
    return apiClient.post<void>('/auth/reset-password', data, { skipAuth: true });
  },

  getCurrentUser: async (): Promise<User> => {
    return apiClient.get<User>('/auth/me');
  },
};
