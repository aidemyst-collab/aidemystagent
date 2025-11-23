import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authService } from './authService';
import { useAuthStore } from './authStore';
import type { LoginRequest, RegisterRequest, PasswordResetRequest } from '../../types/auth';
import { useNavigate } from 'react-router-dom';

export const useLogin = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore(state => state.setAuth);

  return useMutation({
    mutationFn: (data: LoginRequest) => authService.login(data),
    onSuccess: (response) => {
      setAuth(response.user, response.tokens);
      navigate('/dashboard');
    },
  });
};

export const useRegister = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore(state => state.setAuth);

  return useMutation({
    mutationFn: (data: RegisterRequest) => authService.register(data),
    onSuccess: (response) => {
      setAuth(response.user, response.tokens);
      navigate('/dashboard');
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
