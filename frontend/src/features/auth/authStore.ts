import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, AuthTokens, Organization } from '../../types/auth';

interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  organization: Organization | null;
  // Platform admin organization switching
  switchedOrganization: Organization | null;
  isAuthenticated: boolean;
  // Impersonation state
  isImpersonating: boolean;
  impersonatedUser: User | null;
  realAdminTokens: AuthTokens | null;
  setAuth: (user: User, tokens: AuthTokens) => void;
  setOrganization: (organization: Organization) => void;
  updateUser: (user: Partial<User>) => void;
  logout: () => void;
  updateTokens: (tokens: AuthTokens) => void;
  // Organization switching for platform admins
  switchOrganization: (org: Organization | null) => void;
  getEffectiveOrganization: () => Organization | null;
  getSwitchedOrganizationId: () => string | null;
  // Impersonation
  startImpersonation: (targetUser: User, impersonationAccessToken: string) => void;
  endImpersonation: () => void;
  // Permission utilities
  isPlatformAdmin: () => boolean;
  isOrgAdmin: () => boolean;
  hasRole: (roleName: string) => boolean;
  hasAnyRole: (roleNames: string[]) => boolean;
  canAccess: (feature: string) => boolean;
  hasProduct: (product: string) => boolean;
}

// Feature access mapping based on roles
const featureAccessMap: Record<string, string[]> = {
  'admin-dashboard': ['Super Admin'],
  'org-management': ['Super Admin', 'Organization Owner', 'Organization Admin'],
  'user-management': ['Super Admin', 'Organization Owner', 'Organization Admin'],
  'invite-users': ['Super Admin', 'Organization Owner', 'Organization Admin'],
  'audit-logs': ['Super Admin', 'Organization Owner', 'Organization Admin'],
  'subscription-management': ['Super Admin'],
  'agent-management': ['Super Admin', 'Organization Owner', 'Organization Admin', 'Team Lead', 'Developer'],
  'tool-management': ['Super Admin', 'Organization Owner', 'Organization Admin', 'Team Lead', 'Developer'],
  'deployment-management': ['Super Admin', 'Organization Owner', 'Organization Admin', 'Team Lead', 'Operator'],
  'analytics': ['Super Admin', 'Organization Owner', 'Organization Admin', 'Team Lead', 'Developer', 'Operator', 'Viewer'],
  'credentials-access': ['Super Admin', 'Organization Owner', 'Organization Admin', 'Team Lead', 'Developer'],
  'settings': ['Super Admin', 'Organization Owner', 'Organization Admin'],
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      tokens: null,
      organization: null,
      switchedOrganization: null,
      isAuthenticated: false,
      isImpersonating: false,
      impersonatedUser: null,
      realAdminTokens: null,

      setAuth: (user, tokens) =>
        set({ user, tokens, isAuthenticated: true }),

      setOrganization: (organization) =>
        set({ organization }),

      updateUser: (userData) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        })),

      logout: () =>
        set({
          user: null,
          tokens: null,
          organization: null,
          switchedOrganization: null,
          isAuthenticated: false,
          isImpersonating: false,
          impersonatedUser: null,
          realAdminTokens: null,
        }),

      updateTokens: (tokens) => set({ tokens }),

      // Impersonation
      startImpersonation: (targetUser, impersonationAccessToken) =>
        set((state) => ({
          realAdminTokens: state.tokens,
          tokens: state.tokens
            ? { ...state.tokens, accessToken: impersonationAccessToken }
            : { accessToken: impersonationAccessToken, refreshToken: '' },
          impersonatedUser: targetUser,
          isImpersonating: true,
        })),

      endImpersonation: () =>
        set((state) => ({
          tokens: state.realAdminTokens,
          impersonatedUser: null,
          isImpersonating: false,
          realAdminTokens: null,
        })),

      // Organization switching for platform admins
      switchOrganization: (org) => set({ switchedOrganization: org }),

      getEffectiveOrganization: () => {
        const { switchedOrganization, organization } = get();
        return switchedOrganization || organization;
      },

      getSwitchedOrganizationId: () => {
        const { switchedOrganization } = get();
        return switchedOrganization?.id || null;
      },

      // Permission utilities
      isPlatformAdmin: () => {
        const { user } = get();
        return user?.isPlatformAdmin ?? false;
      },

      isOrgAdmin: () => {
        const { user } = get();
        if (!user) return false;
        if (user.isPlatformAdmin) return true;
        const adminRoles = ['Organization Owner', 'Organization Admin'];
        const roles = user.roles || [];
        // Also check legacy role field for backwards compatibility
        if (user.role === 'admin') return true;
        return roles.some(role => adminRoles.includes(role));
      },

      hasRole: (roleName: string) => {
        const { user } = get();
        if (!user) return false;
        if (user.isPlatformAdmin) return true; // Platform admins have all roles
        const roles = user.roles || [];
        return roles.includes(roleName);
      },

      hasAnyRole: (roleNames: string[]) => {
        const { user } = get();
        if (!user) return false;
        if (user.isPlatformAdmin) return true;
        const roles = user.roles || [];
        return roleNames.some(role => roles.includes(role));
      },

      canAccess: (feature: string) => {
        const { user } = get();
        if (!user) return false;
        if (user.isPlatformAdmin) return true;
        // Check legacy role for backwards compatibility
        if (user.role === 'admin') return true;

        const allowedRoles = featureAccessMap[feature];
        if (!allowedRoles) return true; // If feature not in map, allow by default

        const roles = user.roles || [];
        return roles.some(role => allowedRoles.includes(role));
      },

      hasProduct: (product: string) => {
        const { user, tokens } = get();
        if (!user) return false;
        if (user.isPlatformAdmin) return true;

        // Always decode the current JWT first — refreshTokenAfterUpgrade updates
        // tokens.accessToken without updating user.products, so reading user.products
        // would miss newly unlocked products after a plan upgrade.
        if (tokens?.accessToken) {
          try {
            const b64 = tokens.accessToken.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
            const payload = JSON.parse(atob(b64)) as Record<string, unknown>;
            if (payload.is_platform_admin) return true;
            const jwtProducts = payload.products as string[] | undefined;
            if (jwtProducts !== undefined) return jwtProducts.includes(product);
          } catch {
            // fall through to user object
          }
        }

        return user.products?.includes(product) ?? false;
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        organization: state.organization,
        switchedOrganization: state.switchedOrganization,
        isAuthenticated: state.isAuthenticated,
        isImpersonating: state.isImpersonating,
        impersonatedUser: state.impersonatedUser,
        realAdminTokens: state.realAdminTokens,
      }),
    }
  )
);

// Custom hook for checking permissions in components
export const usePermissions = () => {
  const user = useAuthStore((state) => state.user);
  const isPlatformAdmin = useAuthStore((state) => state.isPlatformAdmin);
  const isOrgAdmin = useAuthStore((state) => state.isOrgAdmin);
  const hasRole = useAuthStore((state) => state.hasRole);
  const hasAnyRole = useAuthStore((state) => state.hasAnyRole);
  const canAccess = useAuthStore((state) => state.canAccess);
  const hasProduct = useAuthStore((state) => state.hasProduct);

  return {
    user,
    isPlatformAdmin: isPlatformAdmin(),
    isOrgAdmin: isOrgAdmin(),
    hasRole,
    hasAnyRole,
    canAccess,
    hasProduct,
  };
};

// Hook for impersonation state and actions
export const useImpersonation = () => {
  const isImpersonating = useAuthStore((state) => state.isImpersonating);
  const impersonatedUser = useAuthStore((state) => state.impersonatedUser);
  const startImpersonation = useAuthStore((state) => state.startImpersonation);
  const endImpersonation = useAuthStore((state) => state.endImpersonation);
  return { isImpersonating, impersonatedUser, startImpersonation, endImpersonation };
};

// Hook for organization switching (platform admins only)
export const useOrganizationSwitcher = () => {
  const switchedOrganization = useAuthStore((state) => state.switchedOrganization);
  const organization = useAuthStore((state) => state.organization);
  const switchOrganization = useAuthStore((state) => state.switchOrganization);
  const getEffectiveOrganization = useAuthStore((state) => state.getEffectiveOrganization);
  const isPlatformAdmin = useAuthStore((state) => state.isPlatformAdmin);

  return {
    switchedOrganization,
    originalOrganization: organization,
    effectiveOrganization: getEffectiveOrganization(),
    isSwitched: !!switchedOrganization,
    canSwitch: isPlatformAdmin(),
    switchOrganization,
    clearSwitch: () => switchOrganization(null),
  };
};
