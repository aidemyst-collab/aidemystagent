export interface User {
  id: string;
  email: string;
  fullName?: string;
  role?: 'admin' | 'creator' | 'viewer' | string;  // Legacy role - can be optional
  organizationId?: string;
  organizationName?: string;
  isActive?: boolean;
  isPlatformAdmin?: boolean;
  emailVerified?: boolean;
  lastLoginAt?: string;
  createdAt: string;
  updatedAt?: string;
  roles?: string[]; // RBAC role display names
  avatarUrl?: string;
  orgApprovalStatus?: 'pending' | 'approved' | 'rejected' | string;
}

export interface Organization {
  id: string;
  name: string;
  slug?: string;
  description?: string;
  logoUrl?: string;
  subscriptionStatus: string;
  trialEndsAt?: string;
  settings?: Record<string, unknown>;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  userCount: number;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  fullName?: string;
  organizationId?: string;  // For joining existing org
  organizationName?: string;  // For creating new org
  role?: 'admin' | 'creator' | 'viewer';
}

export interface PasswordResetRequest {
  email: string;
}

export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Role types
export interface Role {
  id: string;
  name: string;
  displayName: string;
  description?: string;
  isSystemRole: boolean;
  permissions: string[];
}

export interface UserRole {
  id: string;
  roleId: string;
  roleName: string;
  roleDisplayName: string;
  assignedAt: string;
  assignedBy?: string;
}

// Invitation types
export interface Invitation {
  id: string;
  email: string;
  organizationId: string;
  organizationName: string;
  roleId: string;
  roleName: string;
  status: 'pending' | 'accepted' | 'expired' | 'revoked';
  message?: string;
  invitedBy?: string;
  inviterName?: string;
  expiresAt: string;
  acceptedAt?: string;
  createdAt: string;
}

export interface CreateInvitationRequest {
  email: string;
  roleId: string;
  message?: string;
  expiresInDays?: number;
}

export interface AcceptInvitationRequest {
  fullName: string;
  password: string;
}

// Audit types
export interface AuditLog {
  id: string;
  organizationId?: string;
  userId?: string;
  userEmail?: string;
  action: string;
  resourceType: string;
  resourceId?: string;
  resourceName?: string;
  oldValues?: Record<string, unknown>;
  newValues?: Record<string, unknown>;
  ipAddress?: string;
  userAgent?: string;
  status: string;
  errorMessage?: string;
  extraData?: Record<string, unknown>;
  createdAt: string;
}

export interface AuditLogSummary {
  action: string;
  count: number;
  lastOccurrence: string;
}

export interface AuditSummary {
  totalLogs: number;
  logsByAction: AuditLogSummary[];
  logsByResourceType: Record<string, number>;
  logsByStatus: Record<string, number>;
  recentUsers: string[];
}

// Admin types
export interface PlatformStats {
  totalOrganizations: number;
  activeOrganizations: number;
  totalUsers: number;
  activeUsers: number;
  totalAgents: number;
  totalDeployments: number;
  activeDeployments: number;
  totalExecutions: number;
  totalTools: number;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  displayName: string;
  description?: string;
  maxUsers: number;
  maxAgents: number;
  maxDeployments: number;
  maxExecutionsPerMonth: number;
  maxTools: number;
  maxCredentials: number;
  features?: Record<string, unknown>;
  priceMonthyCents: number;
  priceYearlyCents: number;
  isActive: boolean;
  isPublic: boolean;
  sortOrder: number;
  organizationCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface OrganizationAdmin {
  id: string;
  name: string;
  slug?: string;
  description?: string;
  subscriptionStatus: string;
  subscriptionPlanName?: string;
  trialEndsAt?: string;
  isActive: boolean;
  approvalStatus: string;
  userCount: number;
  agentCount: number;
  deploymentCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface UserAdmin {
  id: string;
  email: string;
  fullName?: string;
  organizationId: string;
  organizationName: string;
  role: string;
  isPlatformAdmin: boolean;
  isActive: boolean;
  emailVerified: boolean;
  lastLoginAt?: string;
  createdAt: string;
}

export interface UsageReport {
  organizationId: string;
  organizationName: string;
  periodStart: string;
  periodEnd: string;
  usersCount: number;
  agentsCount: number;
  deploymentsCount: number;
  executionsCount: number;
  tokensUsed: number;
  apiCallsCount: number;
  totalCostCents: number;
}
