# Multi-Tenant Architecture Design for AgentStudio

## Executive Summary

This document outlines the changes required to transform AgentStudio into a fully multi-tenant SaaS application with comprehensive role-based access control (RBAC), tenant isolation, and platform administration capabilities.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Multi-Tenancy Architecture](#multi-tenancy-architecture)
3. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
4. [Database Schema Changes](#database-schema-changes)
5. [API Changes](#api-changes)
6. [Security Considerations](#security-considerations)
7. [Implementation Phases](#implementation-phases)
8. [Migration Strategy](#migration-strategy)

---

## Current State Analysis

### Existing Models

| Model | Organization Scoped | User Scoped | Issues |
|-------|---------------------|-------------|--------|
| User | Yes (organization_id) | N/A | No is_active flag, no full_name |
| Organization | N/A | N/A | Minimal fields, no settings |
| Agent | Yes | Yes (creator_id) | API uses mock values, no auth |
| Tool | Yes | Yes (creator_id) | Good visibility model |
| Credential | Yes | Yes (user_id) | Well implemented |
| Deployment | Via Agent | Yes (deployed_by) | No direct org scope |

### Current Roles

```python
class UserRole(str, enum.Enum):
    ADMIN = "admin"      # Organization admin only
    CREATOR = "creator"  # Can create/edit agents
    VIEWER = "viewer"    # Read-only access
```

### Critical Gaps Identified

1. **No Platform Super Admin** - Cannot manage multiple organizations
2. **Inconsistent Auth Enforcement** - `agents.py` uses mock values instead of `get_current_user`
3. **Missing Tenant Isolation** - Some endpoints don't filter by organization
4. **No Organization Settings** - No subscription plans, quotas, or configurations
5. **Public Organization Endpoints** - Anyone can list/create organizations
6. **No Audit Trail** - No logging of who did what
7. **No Soft Delete** - Hard deletes lose data and history
8. **Missing User Fields** - No full_name, is_active, last_login, etc.

---

## Multi-Tenancy Architecture

### Tenancy Model: Organization-Based Multi-Tenancy

```
┌─────────────────────────────────────────────────────────────────┐
│                     PLATFORM LEVEL                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Super Admin / Platform Admin                │    │
│  │  - Manage all organizations                              │    │
│  │  - Platform settings & configuration                     │    │
│  │  - System-wide analytics                                 │    │
│  │  - Billing & subscription management                     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Org A        │     │  Org B        │     │  Org C        │
│  (Tenant)     │     │  (Tenant)     │     │  (Tenant)     │
├───────────────┤     ├───────────────┤     ├───────────────┤
│ - Users       │     │ - Users       │     │ - Users       │
│ - Agents      │     │ - Agents      │     │ - Agents      │
│ - Tools       │     │ - Tools       │     │ - Tools       │
│ - Credentials │     │ - Credentials │     │ - Credentials │
│ - Deployments │     │ - Deployments │     │ - Deployments │
│ - Settings    │     │ - Settings    │     │ - Settings    │
└───────────────┘     └───────────────┘     └───────────────┘
```

### Data Isolation Strategy

- **Logical Isolation**: All tenant data stored in shared tables with `organization_id` foreign key
- **Row-Level Security**: All queries MUST filter by `organization_id`
- **API Middleware**: Automatic tenant context injection from JWT token

---

## Role-Based Access Control (RBAC)

### New Role Hierarchy

```
PLATFORM LEVEL
├── SUPER_ADMIN          (Platform-wide access)
│
ORGANIZATION LEVEL
├── ORG_OWNER            (Full organization control)
├── ORG_ADMIN            (Organization management)
├── AGENT_ADMIN          (Agent management)
├── DEVELOPER            (Create/edit agents)
├── OPERATOR             (Execute/deploy agents)
└── VIEWER               (Read-only access)
```

### Role Definitions

#### Platform Roles

| Role | Description | Scope |
|------|-------------|-------|
| **SUPER_ADMIN** | Platform administrator with access to all organizations, system settings, and platform-wide analytics | Platform-wide |

#### Organization Roles

| Role | Description | Scope |
|------|-------------|-------|
| **ORG_OWNER** | Organization owner with full control including billing, subscription management, and ability to delete the organization | Single Organization |
| **ORG_ADMIN** | Can manage users, settings, and all resources within the organization | Single Organization |
| **AGENT_ADMIN** | Can manage all agents in the organization regardless of creator | Single Organization |
| **DEVELOPER** | Can create, edit, and test their own agents and tools | Single Organization |
| **OPERATOR** | Can execute and deploy agents but not modify them | Single Organization |
| **VIEWER** | Read-only access to agents and dashboards | Single Organization |

### Permission Matrix

| Permission | SUPER_ADMIN | ORG_OWNER | ORG_ADMIN | AGENT_ADMIN | DEVELOPER | OPERATOR | VIEWER |
|------------|-------------|-----------|-----------|-------------|-----------|----------|--------|
| **Platform** |
| Manage all orgs | Yes | - | - | - | - | - | - |
| View platform analytics | Yes | - | - | - | - | - | - |
| Manage subscriptions | Yes | - | - | - | - | - | - |
| **Organization** |
| Delete organization | Yes | Yes | - | - | - | - | - |
| Manage billing | Yes | Yes | - | - | - | - | - |
| Update org settings | Yes | Yes | Yes | - | - | - | - |
| View org settings | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Users** |
| Invite users | Yes | Yes | Yes | - | - | - | - |
| Remove users | Yes | Yes | Yes | - | - | - | - |
| Change user roles | Yes | Yes | Yes* | - | - | - | - |
| View users | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Agents** |
| Create agents | Yes | Yes | Yes | Yes | Yes | - | - |
| Edit any agent | Yes | Yes | Yes | Yes | - | - | - |
| Edit own agents | Yes | Yes | Yes | Yes | Yes | - | - |
| Delete any agent | Yes | Yes | Yes | Yes | - | - | - |
| Delete own agents | Yes | Yes | Yes | Yes | Yes | - | - |
| View all agents | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Deployments** |
| Deploy to production | Yes | Yes | Yes | Yes | - | Yes | - |
| Deploy to staging/dev | Yes | Yes | Yes | Yes | Yes | Yes | - |
| Stop deployments | Yes | Yes | Yes | Yes | Yes | Yes | - |
| View deployments | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Credentials** |
| Create credentials | Yes | Yes | Yes | - | Yes | - | - |
| View credentials | Yes | Yes | Yes | Yes | Yes | Yes | - |
| Delete credentials | Yes | Yes | Yes | - | - | - | - |
| **Tools** |
| Create custom tools | Yes | Yes | Yes | Yes | Yes | - | - |
| Edit any tool | Yes | Yes | Yes | Yes | - | - | - |
| Edit own tools | Yes | Yes | Yes | Yes | Yes | - | - |
| Use tools | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Executions** |
| Execute agents | Yes | Yes | Yes | Yes | Yes | Yes | - |
| View execution logs | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Analytics** |
| View org analytics | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Export analytics | Yes | Yes | Yes | - | - | - | - |

*ORG_ADMIN cannot assign ORG_OWNER role

---

## Database Schema Changes

### New Tables

#### 1. `subscription_plans` (Platform-managed)

```sql
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    -- Quotas
    max_users INTEGER DEFAULT 5,
    max_agents INTEGER DEFAULT 10,
    max_deployments INTEGER DEFAULT 5,
    max_executions_per_month INTEGER DEFAULT 1000,
    max_tools INTEGER DEFAULT 20,
    -- Features
    features JSONB DEFAULT '{}',
    -- Pricing
    price_monthly DECIMAL(10,2),
    price_yearly DECIMAL(10,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default plans
INSERT INTO subscription_plans (name, description, max_users, max_agents, max_deployments, max_executions_per_month)
VALUES
    ('free', 'Free tier with limited features', 3, 5, 2, 500),
    ('starter', 'For small teams', 10, 25, 10, 5000),
    ('professional', 'For growing businesses', 50, 100, 50, 50000),
    ('enterprise', 'Unlimited with premium support', -1, -1, -1, -1);
```

#### 2. `organization_settings` (Extended Organization)

```sql
-- Extend organizations table
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS
    slug VARCHAR(100) UNIQUE,
    description TEXT,
    logo_url VARCHAR(500),
    subscription_plan_id UUID REFERENCES subscription_plans(id),
    subscription_status VARCHAR(50) DEFAULT 'active', -- active, past_due, cancelled, trial
    trial_ends_at TIMESTAMP,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    deleted_at TIMESTAMP, -- Soft delete
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_subscription ON organizations(subscription_plan_id);
```

#### 3. `organization_usage` (Usage Tracking)

```sql
CREATE TABLE organization_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    -- Counters
    users_count INTEGER DEFAULT 0,
    agents_count INTEGER DEFAULT 0,
    deployments_count INTEGER DEFAULT 0,
    executions_count INTEGER DEFAULT 0,
    tools_count INTEGER DEFAULT 0,
    tokens_used BIGINT DEFAULT 0,
    -- Cost tracking
    estimated_cost DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(organization_id, period_start)
);

CREATE INDEX idx_org_usage_period ON organization_usage(organization_id, period_start);
```

#### 4. `roles` (Flexible Role Management)

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    scope VARCHAR(20) NOT NULL, -- 'platform' or 'organization'
    permissions JSONB NOT NULL DEFAULT '[]',
    is_system_role BOOLEAN DEFAULT false, -- Cannot be modified
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE, -- NULL for platform roles
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(name, organization_id) -- Allows same name in different orgs for custom roles
);

-- Insert system roles
INSERT INTO roles (name, display_name, description, scope, is_system_role, permissions) VALUES
('super_admin', 'Super Admin', 'Platform administrator', 'platform', true, '["*"]'),
('org_owner', 'Organization Owner', 'Full organization control', 'organization', true, '["org:*", "users:*", "agents:*", "tools:*", "credentials:*", "deployments:*", "analytics:*"]'),
('org_admin', 'Organization Admin', 'Organization management', 'organization', true, '["org:read", "org:update", "users:*", "agents:*", "tools:*", "credentials:*", "deployments:*", "analytics:*"]'),
('agent_admin', 'Agent Admin', 'Agent management', 'organization', true, '["org:read", "users:read", "agents:*", "tools:*", "credentials:read", "deployments:*", "analytics:read"]'),
('developer', 'Developer', 'Create and edit agents', 'organization', true, '["org:read", "users:read", "agents:create", "agents:read", "agents:update:own", "agents:delete:own", "tools:create", "tools:read", "tools:update:own", "credentials:create", "credentials:read", "deployments:create:non_prod", "analytics:read"]'),
('operator', 'Operator', 'Execute and deploy agents', 'organization', true, '["org:read", "users:read", "agents:read", "agents:execute", "tools:read", "deployments:*", "analytics:read"]'),
('viewer', 'Viewer', 'Read-only access', 'organization', true, '["org:read", "users:read", "agents:read", "tools:read", "deployments:read", "analytics:read"]');
```

#### 5. `user_roles` (Many-to-Many User-Role Assignment)

```sql
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE, -- NULL for platform roles
    assigned_by UUID REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, role_id, organization_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_org ON user_roles(organization_id);
```

#### 6. `audit_logs` (Audit Trail)

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- e.g., 'agent.create', 'user.invite', 'deployment.start'
    resource_type VARCHAR(50) NOT NULL, -- e.g., 'agent', 'user', 'deployment'
    resource_id VARCHAR(100), -- UUID of affected resource
    old_values JSONB, -- Previous state (for updates)
    new_values JSONB, -- New state (for creates/updates)
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_org ON audit_logs(organization_id, created_at DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action, created_at DESC);
```

#### 7. `invitations` (User Invitations)

```sql
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role_id UUID NOT NULL REFERENCES roles(id),
    invited_by UUID NOT NULL REFERENCES users(id),
    token VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'pending', -- pending, accepted, expired, revoked
    expires_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(organization_id, email, status) -- Only one pending invitation per email per org
);

CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_org ON invitations(organization_id, status);
```

### Modified Tables

#### `users` Table Updates

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    is_platform_admin BOOLEAN DEFAULT false, -- Quick check for super admin
    last_login_at TIMESTAMP,
    password_changed_at TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    email_verified BOOLEAN DEFAULT false,
    email_verified_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    deleted_at TIMESTAMP, -- Soft delete
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Remove the old role column after migration
-- ALTER TABLE users DROP COLUMN role;

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_org ON users(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_platform_admin ON users(is_platform_admin) WHERE is_platform_admin = true;
```

#### `agents` Table Updates

```sql
ALTER TABLE agents ADD COLUMN IF NOT EXISTS
    is_template BOOLEAN DEFAULT false,
    template_source_id UUID REFERENCES agents(id),
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    deleted_at TIMESTAMP; -- Soft delete

CREATE INDEX idx_agents_org ON agents(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_agents_creator ON agents(creator_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_agents_templates ON agents(is_template) WHERE is_template = true AND deleted_at IS NULL;
```

#### `deployments` Table Updates

```sql
ALTER TABLE deployments ADD COLUMN IF NOT EXISTS
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    deleted_at TIMESTAMP; -- Soft delete

-- Populate organization_id from agent
UPDATE deployments d
SET organization_id = a.organization_id
FROM agents a
WHERE d.agent_id = a.id AND d.organization_id IS NULL;

ALTER TABLE deployments ALTER COLUMN organization_id SET NOT NULL;

CREATE INDEX idx_deployments_org ON deployments(organization_id) WHERE deleted_at IS NULL;
```

---

## API Changes

### New Endpoints

#### Platform Admin Endpoints (Super Admin Only)

```
# Organizations Management
GET    /api/v1/admin/organizations              # List all organizations
GET    /api/v1/admin/organizations/{id}         # Get organization details
PATCH  /api/v1/admin/organizations/{id}         # Update organization
DELETE /api/v1/admin/organizations/{id}         # Delete organization
POST   /api/v1/admin/organizations/{id}/suspend # Suspend organization
POST   /api/v1/admin/organizations/{id}/activate # Activate organization

# Users Management (Platform-wide)
GET    /api/v1/admin/users                      # List all users
GET    /api/v1/admin/users/{id}                 # Get user details
PATCH  /api/v1/admin/users/{id}                 # Update user
DELETE /api/v1/admin/users/{id}                 # Delete user
POST   /api/v1/admin/users/{id}/impersonate     # Impersonate user (for support)

# Platform Analytics
GET    /api/v1/admin/analytics/overview         # Platform overview
GET    /api/v1/admin/analytics/usage            # Usage statistics
GET    /api/v1/admin/analytics/revenue          # Revenue metrics

# Subscription Plans
GET    /api/v1/admin/plans                      # List plans
POST   /api/v1/admin/plans                      # Create plan
PATCH  /api/v1/admin/plans/{id}                 # Update plan
DELETE /api/v1/admin/plans/{id}                 # Delete plan

# Audit Logs (Platform-wide)
GET    /api/v1/admin/audit-logs                 # View all audit logs
```

#### Organization Management Endpoints

```
# Organization Settings (ORG_OWNER, ORG_ADMIN)
GET    /api/v1/organization                     # Get current org details
PATCH  /api/v1/organization                     # Update org settings
GET    /api/v1/organization/usage               # Get usage statistics
GET    /api/v1/organization/subscription        # Get subscription details

# User Management (ORG_OWNER, ORG_ADMIN)
GET    /api/v1/organization/users               # List org users
POST   /api/v1/organization/users/invite        # Invite user
DELETE /api/v1/organization/users/{id}          # Remove user
PATCH  /api/v1/organization/users/{id}/role     # Change user role

# Invitations
GET    /api/v1/organization/invitations         # List pending invitations
DELETE /api/v1/organization/invitations/{id}    # Revoke invitation
POST   /api/v1/invitations/{token}/accept       # Accept invitation (public)

# Roles (ORG_OWNER, ORG_ADMIN)
GET    /api/v1/organization/roles               # List available roles
POST   /api/v1/organization/roles               # Create custom role
PATCH  /api/v1/organization/roles/{id}          # Update custom role
DELETE /api/v1/organization/roles/{id}          # Delete custom role

# Audit Logs (ORG_OWNER, ORG_ADMIN)
GET    /api/v1/organization/audit-logs          # View org audit logs
```

### Modified Endpoints

All existing endpoints need these changes:

1. **Add Authentication**: Use `get_current_user` dependency
2. **Add Organization Scoping**: Filter by `current_user.organization_id`
3. **Add Permission Checks**: Verify user has required permissions
4. **Add Audit Logging**: Log significant actions

Example refactor for agents:

```python
# Before (agents.py)
@router.get("/")
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent))  # NO SCOPING!
    ...

# After
@router.get("/")
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    permission: None = Depends(require_permission("agents:read")),
):
    result = await db.execute(
        select(Agent)
        .where(Agent.organization_id == current_user.organization_id)
        .where(Agent.deleted_at.is_(None))  # Soft delete
    )
    ...
```

---

## Security Considerations

### 1. Authentication Enhancements

```python
# Add to JWT payload
{
    "sub": "user_id",
    "org": "organization_id",
    "roles": ["developer"],
    "permissions": ["agents:read", "agents:create", ...],
    "is_platform_admin": false,
    "exp": timestamp
}
```

### 2. Permission Middleware

```python
# New dependency for permission checking
from functools import wraps
from fastapi import HTTPException, status

def require_permission(permission: str):
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        # Super admins have all permissions
        if current_user.is_platform_admin:
            return True

        # Get user's roles and permissions
        user_permissions = await get_user_permissions(db, current_user)

        # Check if user has the required permission
        if not has_permission(user_permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}"
            )
        return True
    return permission_checker
```

### 3. Rate Limiting by Organization

```python
# Implement organization-based rate limits
RATE_LIMITS = {
    "free": {"requests_per_minute": 60, "executions_per_day": 100},
    "starter": {"requests_per_minute": 200, "executions_per_day": 1000},
    "professional": {"requests_per_minute": 500, "executions_per_day": 10000},
    "enterprise": {"requests_per_minute": 1000, "executions_per_day": -1},
}
```

### 4. Data Isolation Validation

```python
# Middleware to validate organization access
@app.middleware("http")
async def validate_organization_access(request: Request, call_next):
    # Extract resource organization from path/body
    # Validate against user's organization
    # Reject if mismatch
    ...
```

---

## Implementation Phases

### Phase 1: Foundation (Priority: Critical)

**Duration Estimate: 2-3 weeks**

1. **Database Schema Migration**
   - Create new tables (subscription_plans, roles, user_roles, audit_logs, invitations)
   - Modify existing tables (users, organizations, agents, deployments)
   - Create migration scripts with rollback support

2. **Authentication Fixes**
   - Fix `agents.py` to use `get_current_user`
   - Add organization scoping to all endpoints
   - Implement soft delete across all models

3. **Basic RBAC Implementation**
   - Create permission checking middleware
   - Add role-based guards to existing endpoints
   - Migrate from enum-based roles to table-based roles

### Phase 2: Platform Administration (Priority: High)

**Duration Estimate: 2 weeks**

1. **Super Admin Functionality**
   - Create admin-only endpoints
   - Build platform analytics dashboard
   - Implement organization management

2. **Organization Management**
   - Subscription plan enforcement
   - Usage tracking and quotas
   - Organization settings UI

### Phase 3: User Management (Priority: High)

**Duration Estimate: 1-2 weeks**

1. **Invitation System**
   - Email invitation flow
   - Accept/decline invitations
   - Role assignment on invite

2. **User Administration**
   - User listing and management
   - Role assignment UI
   - User activity tracking

### Phase 4: Audit & Compliance (Priority: Medium)

**Duration Estimate: 1-2 weeks**

1. **Audit Logging**
   - Implement audit log middleware
   - Create audit log viewer UI
   - Export capabilities

2. **Security Hardening**
   - Rate limiting per organization
   - Failed login protection
   - Session management

### Phase 5: Frontend Updates (Priority: High)

**Duration Estimate: 2-3 weeks**

1. **Auth Store Updates**
   - Store user permissions
   - Permission-based UI rendering
   - Role context provider

2. **Admin UI**
   - Platform admin dashboard
   - Organization settings page
   - User management interface

3. **Permission-Based Components**
   - Hide/show based on permissions
   - Disable actions based on role
   - Role-aware navigation

---

## Migration Strategy

### Step 1: Prepare Database

```bash
# Create migration
alembic revision --autogenerate -m "multi_tenant_foundation"

# Apply in development first
alembic upgrade head
```

### Step 2: Data Migration

```sql
-- Migrate existing roles to new system
INSERT INTO user_roles (user_id, role_id, organization_id, assigned_at)
SELECT
    u.id,
    r.id,
    u.organization_id,
    CURRENT_TIMESTAMP
FROM users u
JOIN roles r ON (
    CASE
        WHEN u.role = 'admin' THEN r.name = 'org_admin'
        WHEN u.role = 'creator' THEN r.name = 'developer'
        WHEN u.role = 'viewer' THEN r.name = 'viewer'
    END
)
WHERE r.scope = 'organization';

-- Create default subscription for existing orgs
UPDATE organizations
SET subscription_plan_id = (SELECT id FROM subscription_plans WHERE name = 'starter')
WHERE subscription_plan_id IS NULL;
```

### Step 3: Gradual Rollout

1. Deploy database changes
2. Deploy backend with feature flag for new auth
3. Test thoroughly in staging
4. Enable for single organization
5. Monitor and fix issues
6. Roll out to all organizations

### Step 4: Cleanup

```sql
-- After successful migration
ALTER TABLE users DROP COLUMN role;
```

---

## File Changes Summary

### Backend Files to Create

```
backend/app/
├── models/
│   ├── role.py                 # New: Role and UserRole models
│   ├── audit_log.py            # New: AuditLog model
│   ├── invitation.py           # New: Invitation model
│   └── subscription.py         # New: SubscriptionPlan model
├── api/v1/
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── organizations.py    # New: Platform org management
│   │   ├── users.py            # New: Platform user management
│   │   ├── analytics.py        # New: Platform analytics
│   │   └── plans.py            # New: Subscription plans
│   ├── invitations.py          # New: Invitation endpoints
│   └── audit.py                # New: Audit log endpoints
├── services/
│   ├── permission_service.py   # New: Permission checking logic
│   ├── audit_service.py        # New: Audit logging service
│   └── usage_service.py        # New: Usage tracking service
├── middleware/
│   └── tenant_context.py       # New: Tenant context middleware
└── schemas/
    ├── role.py                 # New: Role schemas
    ├── invitation.py           # New: Invitation schemas
    └── audit.py                # New: Audit log schemas
```

### Backend Files to Modify

```
backend/app/
├── models/
│   ├── user.py                 # Add fields, remove role enum
│   ├── agent.py                # Add soft delete, tags
│   └── deployment.py           # Add organization_id
├── api/v1/
│   ├── agents.py               # Add auth, scoping, permissions
│   ├── tools.py                # Add auth, scoping, permissions
│   ├── deployments.py          # Add auth, scoping, permissions
│   ├── workflows.py            # Add auth, scoping, permissions
│   ├── organizations.py        # Restrict access, add settings
│   └── users.py                # Enhanced user management
├── api/
│   └── deps.py                 # Add permission dependencies
├── core/
│   └── security.py             # Enhanced JWT with permissions
└── main.py                     # Add new routers
```

### Frontend Files to Modify

```
frontend/src/
├── features/auth/
│   └── authStore.ts            # Add permissions to store
├── components/
│   ├── Common/
│   │   ├── PermissionGate.tsx  # New: Permission-based rendering
│   │   └── RoleGuard.tsx       # New: Role-based route guard
│   └── Admin/                  # New: Admin components
├── pages/
│   ├── Admin/                  # New: Admin pages
│   │   ├── Organizations.tsx
│   │   ├── Users.tsx
│   │   └── Analytics.tsx
│   └── Organization/           # New: Org settings pages
│       ├── Settings.tsx
│       ├── Users.tsx
│       └── Billing.tsx
└── types/
    ├── auth.ts                 # Add permission types
    └── role.ts                 # New: Role types
```

---

## Appendix: Permission Strings Reference

```
# Organization permissions
org:read                    # View organization details
org:update                  # Update organization settings
org:delete                  # Delete organization

# User permissions
users:read                  # View users list
users:create                # Invite new users
users:update                # Update user details
users:delete                # Remove users
users:manage_roles          # Change user roles

# Agent permissions
agents:read                 # View agents
agents:create               # Create new agents
agents:update               # Update any agent
agents:update:own           # Update own agents only
agents:delete               # Delete any agent
agents:delete:own           # Delete own agents only
agents:execute              # Execute agents

# Tool permissions
tools:read                  # View tools
tools:create                # Create custom tools
tools:update                # Update any tool
tools:update:own            # Update own tools only
tools:delete                # Delete any tool
tools:delete:own            # Delete own tools only

# Credential permissions
credentials:read            # View credentials (masked)
credentials:create          # Create credentials
credentials:update          # Update credentials
credentials:delete          # Delete credentials

# Deployment permissions
deployments:read            # View deployments
deployments:create          # Create deployments
deployments:create:non_prod # Create non-production deployments only
deployments:update          # Update deployments
deployments:delete          # Delete deployments

# Analytics permissions
analytics:read              # View analytics
analytics:export            # Export analytics data
```

---

## Questions for Review

1. **Custom Roles**: Should organizations be able to create custom roles beyond the system roles?
2. **Cross-Organization Sharing**: Should agents/tools be shareable across organizations?
3. **SSO Integration**: Is SAML/OIDC integration required for enterprise customers?
4. **API Key Authentication**: Should we support API keys for programmatic access in addition to JWT?
5. **Billing Integration**: Which payment provider (Stripe, etc.) for subscription management?
6. **Data Retention**: How long should audit logs be retained?
7. **GDPR Compliance**: Do we need data export/deletion capabilities per user request?

---

**Document Version**: 1.0
**Created**: 2025-12-13
**Author**: Claude Code Assistant
**Status**: Draft - Pending Review
