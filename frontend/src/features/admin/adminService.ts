import { apiClient } from '../../services/api';
import type {
  PlatformStats,
  SubscriptionPlan,
  OrganizationAdmin,
  UserAdmin,
  UsageReport,
} from '../../types/auth';

interface OrganizationAdminListResponse {
  organizations: OrganizationAdmin[];
  total: number;
}

interface UserAdminListResponse {
  users: UserAdmin[];
  total: number;
}

interface SubscriptionPlanListResponse {
  plans: SubscriptionPlan[];
  total: number;
}

interface UsageReportListResponse {
  usage_reports: UsageReport[];
  total: number;
}

interface CreateSubscriptionPlanRequest {
  name: string;
  displayName: string;
  description?: string;
  maxUsers?: number;
  maxAgents?: number;
  maxDeployments?: number;
  maxExecutionsPerMonth?: number;
  maxTools?: number;
  maxCredentials?: number;
  features?: Record<string, unknown>;
  priceMonthyCents?: number;
  priceYearlyCents?: number;
  isPublic?: boolean;
  sortOrder?: number;
}

interface UpdateSubscriptionPlanRequest {
  displayName?: string;
  description?: string;
  maxUsers?: number;
  maxAgents?: number;
  maxDeployments?: number;
  maxExecutionsPerMonth?: number;
  maxTools?: number;
  maxCredentials?: number;
  features?: Record<string, unknown>;
  priceMonthyCents?: number;
  priceYearlyCents?: number;
  isActive?: boolean;
  isPublic?: boolean;
  sortOrder?: number;
}

interface UpdateOrganizationStatusRequest {
  isActive?: boolean;
  subscriptionStatus?: string;
  subscriptionPlanId?: string;
}

interface CreateOrganizationRequest {
  name: string;
  slug?: string;
  description?: string;
  logoUrl?: string;
  settings?: Record<string, unknown>;
}

interface CreateUserAdminRequest {
  email: string;
  password: string;
  fullName?: string;
  organizationId: string;
  role?: string;
  isPlatformAdmin?: boolean;
  isActive?: boolean;
}

export const adminService = {
  // Platform Statistics
  getStats: async (): Promise<PlatformStats> => {
    const response = await apiClient.get<{
      total_organizations: number;
      active_organizations: number;
      total_users: number;
      active_users: number;
      total_agents: number;
      total_deployments: number;
      active_deployments: number;
      total_executions: number;
      total_tools: number;
    }>('/admin/stats');

    return {
      totalOrganizations: response.total_organizations,
      activeOrganizations: response.active_organizations,
      totalUsers: response.total_users,
      activeUsers: response.active_users,
      totalAgents: response.total_agents,
      totalDeployments: response.total_deployments,
      activeDeployments: response.active_deployments,
      totalExecutions: response.total_executions,
      totalTools: response.total_tools,
    };
  },

  // Organization Management
  listOrganizations: async (params?: {
    skip?: number;
    limit?: number;
    isActive?: boolean;
    subscriptionStatus?: string;
    search?: string;
  }): Promise<OrganizationAdminListResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.isActive !== undefined) queryParams.append('is_active', params.isActive.toString());
    if (params?.subscriptionStatus) queryParams.append('subscription_status', params.subscriptionStatus);
    if (params?.search) queryParams.append('search', params.search);

    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await apiClient.get<{
      organizations: Array<{
        id: string;
        name: string;
        slug?: string;
        description?: string;
        subscription_status: string;
        subscription_plan_name?: string;
        trial_ends_at?: string;
        is_active: boolean;
        user_count: number;
        agent_count: number;
        deployment_count: number;
        created_at: string;
        updated_at: string;
      }>;
      total: number;
    }>(`/admin/organizations${query}`);

    return {
      organizations: response.organizations.map((o) => ({
        id: o.id,
        name: o.name,
        slug: o.slug,
        description: o.description,
        subscriptionStatus: o.subscription_status,
        subscriptionPlanName: o.subscription_plan_name,
        trialEndsAt: o.trial_ends_at,
        isActive: o.is_active,
        userCount: o.user_count,
        agentCount: o.agent_count,
        deploymentCount: o.deployment_count,
        createdAt: o.created_at,
        updatedAt: o.updated_at,
      })),
      total: response.total,
    };
  },

  createOrganization: async (data: CreateOrganizationRequest): Promise<OrganizationAdmin> => {
    return apiClient.post<OrganizationAdmin>('/organizations/', {
      name: data.name,
      slug: data.slug,
      description: data.description,
      logo_url: data.logoUrl,
      settings: data.settings,
    });
  },

  updateOrganizationStatus: async (
    organizationId: string,
    data: UpdateOrganizationStatusRequest
  ): Promise<OrganizationAdmin> => {
    return apiClient.patch<OrganizationAdmin>(`/admin/organizations/${organizationId}`, {
      is_active: data.isActive,
      subscription_status: data.subscriptionStatus,
      subscription_plan_id: data.subscriptionPlanId,
    });
  },

  // Subscription Plan Management
  listSubscriptionPlans: async (params?: {
    skip?: number;
    limit?: number;
    includeInactive?: boolean;
  }): Promise<SubscriptionPlanListResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.includeInactive) queryParams.append('include_inactive', 'true');

    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await apiClient.get<{
      plans: Array<{
        id: string;
        name: string;
        display_name: string;
        description?: string;
        max_users: number;
        max_agents: number;
        max_deployments: number;
        max_executions_per_month: number;
        max_tools: number;
        max_credentials: number;
        features?: Record<string, unknown>;
        price_monthly_cents: number;
        price_yearly_cents: number;
        is_active: boolean;
        is_public: boolean;
        sort_order: number;
        organization_count: number;
        created_at: string;
        updated_at: string;
      }>;
      total: number;
    }>(`/admin/subscription-plans${query}`);

    return {
      plans: response.plans.map((p) => ({
        id: p.id,
        name: p.name,
        displayName: p.display_name,
        description: p.description,
        maxUsers: p.max_users,
        maxAgents: p.max_agents,
        maxDeployments: p.max_deployments,
        maxExecutionsPerMonth: p.max_executions_per_month,
        maxTools: p.max_tools,
        maxCredentials: p.max_credentials,
        features: p.features,
        priceMonthyCents: p.price_monthly_cents,
        priceYearlyCents: p.price_yearly_cents,
        isActive: p.is_active,
        isPublic: p.is_public,
        sortOrder: p.sort_order,
        organizationCount: p.organization_count,
        createdAt: p.created_at,
        updatedAt: p.updated_at,
      })),
      total: response.total,
    };
  },

  createSubscriptionPlan: async (data: CreateSubscriptionPlanRequest): Promise<SubscriptionPlan> => {
    return apiClient.post<SubscriptionPlan>('/admin/subscription-plans', {
      name: data.name,
      display_name: data.displayName,
      description: data.description,
      max_users: data.maxUsers,
      max_agents: data.maxAgents,
      max_deployments: data.maxDeployments,
      max_executions_per_month: data.maxExecutionsPerMonth,
      max_tools: data.maxTools,
      max_credentials: data.maxCredentials,
      features: data.features,
      price_monthly_cents: data.priceMonthyCents,
      price_yearly_cents: data.priceYearlyCents,
      is_public: data.isPublic,
      sort_order: data.sortOrder,
    });
  },

  getSubscriptionPlan: async (planId: string): Promise<SubscriptionPlan> => {
    return apiClient.get<SubscriptionPlan>(`/admin/subscription-plans/${planId}`);
  },

  updateSubscriptionPlan: async (
    planId: string,
    data: UpdateSubscriptionPlanRequest
  ): Promise<SubscriptionPlan> => {
    return apiClient.patch<SubscriptionPlan>(`/admin/subscription-plans/${planId}`, {
      display_name: data.displayName,
      description: data.description,
      max_users: data.maxUsers,
      max_agents: data.maxAgents,
      max_deployments: data.maxDeployments,
      max_executions_per_month: data.maxExecutionsPerMonth,
      max_tools: data.maxTools,
      max_credentials: data.maxCredentials,
      features: data.features,
      price_monthly_cents: data.priceMonthyCents,
      price_yearly_cents: data.priceYearlyCents,
      is_active: data.isActive,
      is_public: data.isPublic,
      sort_order: data.sortOrder,
    });
  },

  deleteSubscriptionPlan: async (planId: string): Promise<void> => {
    return apiClient.delete(`/admin/subscription-plans/${planId}`);
  },

  // Usage Reports
  getUsageReports: async (params?: {
    organizationId?: string;
    periodStart?: string;
    periodEnd?: string;
    skip?: number;
    limit?: number;
  }): Promise<UsageReportListResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.organizationId) queryParams.append('organization_id', params.organizationId);
    if (params?.periodStart) queryParams.append('period_start', params.periodStart);
    if (params?.periodEnd) queryParams.append('period_end', params.periodEnd);
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());

    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    return apiClient.get<UsageReportListResponse>(`/admin/usage${query}`);
  },

  // User Management (Admin)
  listAllUsers: async (params?: {
    skip?: number;
    limit?: number;
    organizationId?: string;
    isActive?: boolean;
    isPlatformAdmin?: boolean;
    search?: string;
  }): Promise<UserAdminListResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.organizationId) queryParams.append('organization_id', params.organizationId);
    if (params?.isActive !== undefined) queryParams.append('is_active', params.isActive.toString());
    if (params?.isPlatformAdmin !== undefined) queryParams.append('is_platform_admin', params.isPlatformAdmin.toString());
    if (params?.search) queryParams.append('search', params.search);

    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const response = await apiClient.get<{
      users: Array<{
        id: string;
        email: string;
        full_name?: string;
        organization_id: string;
        organization_name: string;
        role: string;
        is_platform_admin: boolean;
        is_active: boolean;
        email_verified: boolean;
        last_login_at?: string;
        created_at: string;
      }>;
      total: number;
    }>(`/admin/users${query}`);

    return {
      users: response.users.map((u) => ({
        id: u.id,
        email: u.email,
        fullName: u.full_name,
        organizationId: u.organization_id,
        organizationName: u.organization_name,
        role: u.role,
        isPlatformAdmin: u.is_platform_admin,
        isActive: u.is_active,
        emailVerified: u.email_verified,
        lastLoginAt: u.last_login_at,
        createdAt: u.created_at,
      })),
      total: response.total,
    };
  },

  togglePlatformAdmin: async (userId: string, isAdmin: boolean): Promise<{ message: string }> => {
    return apiClient.patch<{ message: string }>(`/admin/users/${userId}/platform-admin?is_admin=${isAdmin}`, {});
  },

  updateUserStatus: async (userId: string, isActive: boolean): Promise<{ message: string }> => {
    return apiClient.patch<{ message: string }>(`/admin/users/${userId}/status?is_active=${isActive}`, {});
  },

  createUser: async (data: CreateUserAdminRequest): Promise<UserAdmin> => {
    const response = await apiClient.post<{
      id: string;
      email: string;
      full_name?: string;
      organization_id: string;
      organization_name: string;
      role: string;
      is_platform_admin: boolean;
      is_active: boolean;
      email_verified: boolean;
      last_login_at?: string;
      created_at: string;
    }>('/admin/users', {
      email: data.email,
      password: data.password,
      full_name: data.fullName,
      organization_id: data.organizationId,
      role: data.role || 'creator',
      is_platform_admin: data.isPlatformAdmin || false,
      is_active: data.isActive !== false,
    });

    return {
      id: response.id,
      email: response.email,
      fullName: response.full_name,
      organizationId: response.organization_id,
      organizationName: response.organization_name,
      role: response.role,
      isPlatformAdmin: response.is_platform_admin,
      isActive: response.is_active,
      emailVerified: response.email_verified,
      lastLoginAt: response.last_login_at,
      createdAt: response.created_at,
    };
  },
};
