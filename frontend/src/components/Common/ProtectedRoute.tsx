import { Navigate, useLocation } from 'react-router-dom';
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
  const location = useLocation();

  if (!isAuthenticated || isTokenExpired(tokens?.accessToken)) {
    if (isAuthenticated) logout();
    return <Navigate to="/login" replace />;
  }

  // Redirect org-pending users away from all protected routes
  if (
    user?.orgApprovalStatus === 'pending' &&
    location.pathname !== '/pending-approval'
  ) {
    return <Navigate to="/pending-approval" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};

interface FeatureRouteProps {
  children: ReactNode;
  feature: string;
}

/** Route guard that redirects to /dashboard when the current user lacks the required feature. */
export const FeatureRoute = ({ children, feature }: FeatureRouteProps) => {
  const canAccess = useAuthStore((state) => state.canAccess);

  if (!canAccess(feature)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};
