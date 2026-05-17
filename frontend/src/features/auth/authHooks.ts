import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authService } from './authService';
import { useAuthStore } from './authStore';
import type { LoginRequest, RegisterRequest, PasswordResetRequest } from '../../types/auth';
import { useNavigate } from 'react-router-dom';

export const useLogin = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore(state => state.setAuth);
  const setOrganization = useAuthStore(state => state.setOrganization);

  return useMutation({
    mutationFn: (data: LoginRequest) => authService.login(data),
    onSuccess: async (response) => {
      setAuth(response.user, response.tokens);

      // Fetch and store organization details
      try {
        const organization = await authService.getCurrentOrganization();
        setOrganization(organization);
      } catch (error) {
        console.error('Failed to fetch organization details:', error);
      }

      if (response.user?.orgApprovalStatus === 'pending') {
        navigate('/pending-approval');
      } else {
        navigate('/dashboard');
      }
    },
  });
};

export const useRegister = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore(state => state.setAuth);
  const setOrganization = useAuthStore(state => state.setOrganization);

  return useMutation({
    mutationFn: (data: RegisterRequest) => authService.register(data),
    onSuccess: async (response) => {
      setAuth(response.user, response.tokens);

      // Fetch and store organization details
      try {
        const organization = await authService.getCurrentOrganization();
        setOrganization(organization);
      } catch (error) {
        console.error('Failed to fetch organization details:', error);
      }

      if (response.user?.orgApprovalStatus === 'pending') {
        navigate('/pending-approval');
      } else {
        navigate('/dashboard');
      }
    },
  });
};

export const useLogout = () => {
  const navigate = useNavigate();
  const logout = useAuthStore(state => state.logout);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => authService.logout(),
    onSuccess: () => {
      logout();
      queryClient.clear();
      navigate('/login');
    },
  });
};

export const useResetPassword = () => {
  return useMutation({
    mutationFn: (data: PasswordResetRequest) => authService.resetPassword(data),
  });
};

/**
 * Hook to initialize/refresh organization data.
 * Call this in MainLayout or ProtectedRoute to ensure organization is loaded
 * after page refresh (when user is loaded from persisted storage but org might be stale).
 */
export const useInitializeOrganization = () => {
  const setOrganization = useAuthStore(state => state.setOrganization);

  return useMutation({
    mutationFn: () => authService.getCurrentOrganization(),
    onSuccess: (org) => {
      setOrganization(org);
    },
    onError: (error) => {
      console.error('Failed to initialize organization:', error);
    },
  });
};
