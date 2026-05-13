import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../features/auth/authStore';
import { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
  allowedRoles?: Array<'admin' | 'creator' | 'viewer'>;
}

function isTokenExpired(token: string | null | undefined): boolean {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

export const ProtectedRoute = ({ children, allowedRoles }: ProtectedRouteProps) => {
  const { isAuthenticated, user, tokens, logout } = useAuthStore();

  if (!isAuthenticated || isTokenExpired(tokens?.accessToken)) {
    if (isAuthenticated) logout();
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};
