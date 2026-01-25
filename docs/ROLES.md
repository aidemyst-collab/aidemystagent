# AgentStudio - Roles & Access Control

This document defines the Role-Based Access Control (RBAC) system for AgentStudio.

## Overview

AgentStudio uses a hierarchical role system with two scopes:
- **Platform Scope**: System-wide access across all organizations
- **Organization Scope**: Access limited to a specific organization

## Role Hierarchy

| Level | Role | Scope | Description |
|-------|------|-------|-------------|
| 1 | **Super Admin** | Platform | Full access to ALL organizations and system settings |
| 2 | **Org Owner** | Organization | Full control including billing & deletion |
| 3 | **Org Admin** | Organization | Organization management without billing access |
| 4 | **Agent Admin** | Organization | Manage all agents regardless of creator |
| 5 | **Developer** | Organization | Create and edit own agents & tools |
| 6 | **Operator** | Organization | Execute and deploy agents |
| 7 | **Viewer** | Organization | Read-only access to resources |

---

## Role Definitions

### 1. Super Admin (Platform)

**Description**: Platform administrator with unrestricted access to all organizations and system settings.

**Use Case**: System administrators, platform operations team.

**Permissions**: `*` (all permissions)

---

### 2. Organization Owner

**Description**: Full organization control including billing, settings, and the ability to delete the organization.

**Use Case**: Company owner, department head who created the organization.

**Permissions**:
- `org:*` - Full organization control
- `users:*` - Manage all users
- `agents:*` - Full agent management
- `tools:*` - Full tool management
- `credentials:*` - Manage all credentials
- `deployments:*` - Full deployment control
- `analytics:*` - Full analytics access
- `audit:read` - View audit logs

---

### 3. Organization Admin

**Description**: Organization management capabilities without access to billing or organization deletion.

**Use Case**: Team leads, department managers.

**Permissions**:
- `org:read` - View organization details
- `org:update` - Update organization settings
- `users:*` - Manage all users
- `agents:*` - Full agent management
- `tools:*` - Full tool management
- `credentials:*` - Manage all credentials
- `deployments:*` - Full deployment control
- `analytics:*` - Full analytics access
- `audit:read` - View audit logs

---

### 4. Agent Admin

**Description**: Manage all agents in the organization regardless of who created them.

**Use Case**: AI/ML team leads, agent operations managers.

**Permissions**:
- `org:read` - View organization details
- `users:read` - View users
- `agents:*` - Full agent management
- `tools:*` - Full tool management
- `credentials:read` - View credentials (masked)
- `deployments:*` - Full deployment control
- `analytics:read` - View analytics

---

### 5. Developer

**Description**: Create and manage their own agents and tools. Cannot modify resources created by others.

**Use Case**: AI developers, workflow builders, prompt engineers.

**Permissions**:
- `org:read` - View organization details
- `users:read` - View users
- `agents:create` - Create new agents
- `agents:read` - View all agents
- `agents:update:own` - Edit own agents only
- `agents:delete:own` - Delete own agents only
- `agents:execute` - Execute agents
- `tools:create` - Create new tools
- `tools:read` - View all tools
- `tools:update:own` - Edit own tools only
- `tools:delete:own` - Delete own tools only
- `credentials:create` - Create credentials
- `credentials:read` - View credentials (masked)
- `deployments:read` - View deployments
- `deployments:create:non_prod` - Deploy to dev/staging only
- `analytics:read` - View analytics

---

### 6. Operator

**Description**: Execute agents and manage deployments. Cannot create or modify agents.

**Use Case**: Operations team, DevOps engineers, support staff.

**Permissions**:
- `org:read` - View organization details
- `users:read` - View users
- `agents:read` - View agents
- `agents:execute` - Execute agents
- `tools:read` - View tools
- `deployments:*` - Full deployment control
- `analytics:read` - View analytics

---

### 7. Viewer

**Description**: Read-only access to all organization resources. Cannot create, modify, or execute anything.

**Use Case**: Stakeholders, auditors, external reviewers.

**Permissions**:
- `org:read` - View organization details
- `users:read` - View users
- `agents:read` - View agents
- `tools:read` - View tools
- `deployments:read` - View deployments
- `analytics:read` - View analytics

---

## Permissions Matrix

### Organization Permissions

| Permission | Super Admin | Org Owner | Org Admin | Agent Admin | Developer | Operator | Viewer |
|------------|:-----------:|:---------:|:---------:|:-----------:|:---------:|:--------:|:------:|
| org:read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| org:update | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| org:delete | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| org:billing | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### User Management Permissions

| Permission | Super Admin | Org Owner | Org Admin | Agent Admin | Developer | Operator | Viewer |
|------------|:-----------:|:---------:|:---------:|:-----------:|:---------:|:--------:|:------:|
| users:read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| users:create | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| users:update | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| users:delete | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| users:invite | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

### Agent Permissions

| Permission | Super Admin | Org Owner | Org Admin | Agent Admin | Developer | Operator | Viewer |
|------------|:-----------:|:---------:|:---------:|:-----------:|:---------:|:--------:|:------:|
| agents:read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| agents:create | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| agents:update | ✅ | ✅ | ✅ | ✅ | own | ❌ | ❌ |
| agents:delete | ✅ | ✅ | ✅ | ✅ | own | ❌ | ❌ |
| agents:execute | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### Tool Permissions

| Permission | Super Admin | Org Owner | Org Admin | Agent Admin | Developer | Operator | Viewer |
|------------|:-----------:|:---------:|:---------:|:-----------:|:---------:|:--------:|:------:|
| tools:read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| tools:create | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| tools:update | ✅ | ✅ | ✅ | ✅ | own | ❌ | ❌ |
| tools:delete | ✅ | ✅ | ✅ | ✅ | own | ❌ | ❌ |
| tools:execute | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### Credential Permissions

| Permission | Super Admin | Org Owner | Org Admin | Agent Admin | Developer | Operator | Viewer |
|------------|:-----------:|:---------:|:---------:|:-----------:|:---------:|:--------:|:------:|
| credentials:read | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| credentials:create | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| credentials:update | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| credentials:delete | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

### Deployment Permissions

| Permission | Super Admin | Org Owner | Org Admin | Agent Admin | Developer | Operator | Viewer |
|------------|:-----------:|:---------:|:---------:|:-----------:|:---------:|:--------:|:------:|
| deployments:read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| deployments:create | ✅ | ✅ | ✅ | ✅ | non-prod | ✅ | ❌ |
| deployments:update | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| deployments:delete | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |

### Analytics & Audit Permissions

| Permission | Super Admin | Org Owner | Org Admin | Agent Admin | Developer | Operator | Viewer |
|------------|:-----------:|:---------:|:---------:|:-----------:|:---------:|:--------:|:------:|
| analytics:read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| analytics:export | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| audit:read | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Full access |
| ❌ | No access |
| **own** | Only resources created by the user |
| **non-prod** | Only development and staging environments |

---

## Permission Format

Permissions follow the format: `resource:action` or `resource:action:scope`

### Resources
- `org` - Organization settings
- `users` - User management
- `agents` - AI agents/workflows
- `tools` - Built-in and custom tools
- `credentials` - API keys and secrets
- `deployments` - Deployment management
- `analytics` - Usage analytics
- `audit` - Audit logs

### Actions
- `read` - View resources
- `create` - Create new resources
- `update` - Modify existing resources
- `delete` - Remove resources
- `execute` - Run/invoke resources
- `*` - All actions (wildcard)

### Scopes
- `own` - Only resources created by the user
- `non_prod` - Only non-production environments

---

## Custom Roles

Organizations can create custom roles with specific permission combinations.

### Creating Custom Roles

Custom roles can be created by Organization Owners and Admins via:
- **API**: `POST /api/v1/roles`
- **UI**: Settings > Roles > Create Role

### Custom Role Restrictions

- Custom roles cannot exceed the permissions of the creator's role
- Custom roles are scoped to the organization only
- System roles cannot be modified or deleted

---

## Role Assignment

### Assigning Roles to Users

Roles can be assigned via:
- **API**: `POST /api/v1/users/{user_id}/roles`
- **UI**: Users > Select User > Manage Roles

### Multiple Roles

Users can have multiple roles. Effective permissions are the **union** of all assigned role permissions.

Example: A user with both `Developer` and `Operator` roles has:
- All Developer permissions
- All Operator permissions (combined)

---

## Best Practices

1. **Principle of Least Privilege**: Assign the minimum role needed for the user's job function.

2. **Use Developer for most team members**: Allows them to build and test without affecting others' work.

3. **Reserve Org Admin for team leads**: They need to manage users and resources.

4. **Use Viewer for stakeholders**: Provides visibility without risk of accidental changes.

5. **Audit role assignments regularly**: Review who has elevated access quarterly.

---

## Related Documentation

- [User Guide](./USER_HELP_GUIDE.md) - End-user documentation
- [API Documentation](./API_DOCUMENTATION.md) - API reference
- [Deployment Guide](./DEPLOYMENT.md) - Production deployment

---

**Last Updated**: 2026-01-25
