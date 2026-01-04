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
  setAuth: (user: User, tokens: AuthTokens) => void;
  setOrganization: (organization: Organization) => void;
  updateUser: (user: Partial<User>) => void;
  logout: () => void;
  updateTokens: (tokens: AuthTokens) => void;
  // Organization switching for platform admins
  switchOrganization: (org: Organization | null) => void;
  getEffectiveOrganization: () => Organization | null;
  getSwitchedOrganizationId: () => string | null;
  // Permission utilities
  isPlatformAdmin: () => boolean;
  isOrgAdmin: () => boolean;
  hasRole: (roleName: string) => boolean;
  hasAnyRole: (roleNames: string[]) => boolean;
  canAccess: (feature: string) => boolean;
}

// Feature access mapping based on roles
const featureAccessMap: Record<string, string[]> = {
  'admin-dashboard': ['Super Admin'],
  'org-management': ['Super Admin', 'Organization Owner', 'Organization Admin'],
  'user-management': ['Super Admin', 'Organization Owner', 'Organization Admin'],
  'invite-users': ['Super Admin', 'Organization Owner', 'Organization Admin'],
  'audit-logs': ['Super Admin', 'Organization Owner', 'Organization Admin'],
  'subscription-management': ['Super Admin'],
  'agent-management': ['Super Admin', 'Organization Owner', 'Organization Admin', 'Agent Admin', 'Developer'],
  'tool-management': ['Super Admin', 'Organization Owner', 'Organization Admin', 'Agent Admin', 'Developer'],
  'deployment-management': ['Super Admin', 'Organization Owner', 'Organization Admin', 'Agent Admin', 'Operator'],
  'analytics': ['Super Admin', 'Organization Owner', 'Organization Admin', 'Agent Admin', 'Developer', 'Operator', 'Viewer'],
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      tokens: null,
      organization: null,
      switchedOrganization: null,
      isAuthenticated: false,

      setAuth: (user, tokens) =>
        set({ user, tokens, isAuthenticated: true }),

      setOrganization: (organization) =>
        set({ organization }),

      updateUser: (userData) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        })),

      logout: () =>
        set({ user: null, tokens: null, organization: null, switchedOrganization: null, isAuthenticated: false }),

      updateTokens: (tokens) => set({ tokens }),

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
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        organization: state.organization,
        switchedOrganization: state.switchedOrganization,
        isAuthenticated: state.isAuthenticated,
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

  return {
    user,
    isPlatformAdmin: isPlatformAdmin(),
    isOrgAdmin: isOrgAdmin(),
    hasRole,
    hasAnyRole,
    canAccess,
  };
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
