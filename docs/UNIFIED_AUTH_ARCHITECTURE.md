# Unified Authentication Architecture — Single Login Across AgentStudio, DemystRAG & Mock API

**Version:** 1.4  
**Date:** 2026-05-18  
**Status:** Proposal — Pending Review  
**Authors:** Tech Lead + Product Owner

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State & Pain Points](#2-current-state--pain-points)
3. [Target Architecture](#3-target-architecture)
4. [Data Model Changes](#4-data-model-changes)
5. [JWT Token Design](#5-jwt-token-design)
6. [Registration Flow](#6-registration-flow)
7. [Login Flow](#7-login-flow)
8. [Product Entitlement & Role Mapping Flow](#8-product-entitlement--role-mapping-flow)
9. [Platform Admin Flow](#9-platform-admin-flow)
10. [Sub-App Integration](#10-sub-app-integration)
11. [Organisation Data Flow](#11-organisation-data-flow)
12. [Edge Cases & Error Scenarios](#12-edge-cases--error-scenarios)
13. [Security Considerations](#13-security-considerations)
14. [Migration Plan](#14-migration-plan)
15. [Implementation Checklist](#15-implementation-checklist)
16. [Cost & Risk Assessment](#16-cost--risk-assessment)

---

## 1. Executive Summary

### What Changes

Today each product (AgentStudio, DemystRAG, Mock API) maintains its own user database, login screen, and session. A user must create separate accounts for each tool and log in independently — even though all three products belong to the same organisation.

After this change:
- **One registration** — users register once on AgentStudio
- **One login** — a single credential pair grants access to all products the organisation has purchased
- **DemystRAG and Mock API become purchasable add-ons** — unlocked by upgrading the subscription plan, not by creating separate accounts
- **Platform admins** manage everything from the AgentStudio admin panel — no separate admin portals

### Why This Change

| Problem | Impact |
|---------|--------|
| Users forget which product they registered for | Support tickets, abandoned sessions |
| Password resets happen in multiple systems | Operational overhead |
| Organisation admins cannot see a single user list | Compliance and security risk |
| Separate billing / access control per product | Friction for upsell, revenue loss |
| Platform admin must log in 3 times | Inefficiency |

### What Does Not Change

- The frontend UI and features of DemystRAG and Mock API remain unchanged from the user's perspective
- AgentStudio's existing auth endpoints (`/auth/login`, `/auth/register`, `/auth/refresh`) remain unchanged in their URL structure
- The PostgreSQL schema of DemystRAG and Mock API drops only the `users` table — all other domain data is untouched

---

## 2. Current State & Pain Points

### 2.1 Current Architecture (Three Isolated Silos)

```
AgentStudio                 DemystRAG                  Mock API
──────────────────          ──────────────────         ──────────────────
Own users table             Own users table             Own users table
Own JWT secret              Own JWT secret              Own JWT secret
Own login page              Own login page               Own login page
Own registration            Own registration             Own registration
Own admin panel             Own admin panel (basic)      Own admin panel (basic)
```

### 2.2 Data Duplication Today

When a user registers for all three products they have:
- 3 rows in 3 different `users` tables (possibly with different passwords)
- 3 active sessions that expire independently
- 3 sets of JWT refresh tokens
- No shared concept of their organisation

### 2.3 Subscription Gating Today

Product access is controlled by infrastructure (separate URLs, separate credentials) — there is no entitlement system. Buying DemystRAG is a manual process that creates a separate account in a separate system.

---

## 3. Target Architecture

### 3.1 High-Level Overview

```
                         ┌─────────────────────────────┐
                         │    AgentStudio (Identity     │
                         │        Anchor)               │
                         │                             │
                         │  • User registration        │
                         │  • Login / password reset   │
                         │  • Token issuance           │
                         │  • Organisation management  │
                         │  • Subscription plan mgmt   │
                         │  • Platform admin panel     │
                         └────────────┬────────────────┘
                                      │ JWT (enriched with
                                      │ products, org_id,
                                      │ org_role, is_platform_admin)
                          ┌───────────┼────────────┐
                          │           │            │
                    ┌─────▼───┐  ┌────▼────┐  ┌──▼──────┐
                    │AgentStu-│  │DemystRAG│  │Mock API │
                    │  dio    │  │(add-on) │  │(add-on) │
                    │         │  │         │  │         │
                    │ Full    │  │Validates│  │Validates│
                    │ access  │  │JWT only │  │JWT only │
                    └─────────┘  └─────────┘  └─────────┘
```

### 3.2 Identity Anchor Principle

AgentStudio is the **single source of truth** for:
- User identity (email, hashed password, profile)
- Organisation identity and profile
- Subscription plan and entitlements
- Platform admin designation

DemystRAG and Mock API are **relying parties** that:
- Accept only JWTs issued by AgentStudio
- Validate the token locally (no DB call to AgentStudio)
- Read entitlements from the token claims
- Reject requests if the relevant product is not in the `products` claim

### 3.3 Shared Secret Strategy

All three apps share one `SECRET_KEY`. This key already exists in Azure Key Vault (`agentstudio-rg`). DemystRAG and Mock API read it via a new environment variable `AGENTSTUDIO_JWT_SECRET`.

```
Azure Key Vault: agentstudio-kv
  └── SECRET_KEY  ──► AgentStudio backend (issues tokens)
                  ──► DemystRAG backend   (validates tokens via AGENTSTUDIO_JWT_SECRET)
                  ──► Mock API backend    (validates tokens via AGENTSTUDIO_JWT_SECRET)
```

No additional key distribution infrastructure is required.

---

## 4. Data Model Changes

### 4.1 AgentStudio — Changes Required

#### SubscriptionPlan.features — Add Product Keys

The `features` JSONB column already exists on `SubscriptionPlan` and has a working `has_feature()` method. Add two keys to gate sub-product access:

```json
{
  "has_demystrag": true,
  "has_mock_api": false,
  "custom_tools": true,
  "api_access": true,
  ...existing keys...
}
```

**Migration required:** `UPDATE subscription_plans SET features = features || '{"has_demystrag": false, "has_mock_api": false}'` for all existing plans, then set `true` for plans that should include those products.

#### JWT Payload — Add Claims

The `create_access_token` function in `backend/app/core/security.py` needs to embed additional claims at login time (loaded from the database during login, not on every request):

```json
{
  "sub": "user-uuid",
  "org_id": "org-uuid",
  "org_name": "Acme Corp",
  "org_slug": "acme-corp",
  "org_role": "developer",
  "is_platform_admin": false,
  "products": ["agentstudio", "demystrag"],
  "plan_limits": {
    "max_users": 50,
    "max_documents": 5000,
    "max_storage_mb": 50000,
    "max_collections": 100,
    "embedding_providers": ["openai", "anthropic"]
  },
  "exp": 1234567890
}
```

`org_name`, `org_slug`, and `plan_limits` are **new claims** required for sub-app JIT provisioning (see §4.2 and §4.3). They are derived at login from `Organization` and `SubscriptionPlan` records — no extra DB queries beyond what login already does.

No schema changes to `users` or `organizations` tables are needed — `is_platform_admin` and `organization_id` already exist.

### 4.2 DemystRAG — Changes Required

**Current state (from code analysis):**
- `Organization` table uses **Integer PK** — incompatible with AgentStudio's UUID org IDs
- Quota enforcement (`QuotaChecker`) reads `org.max_documents`, `org.max_users`, `org.max_storage_mb` directly from the local `Organization` row
- Has its own `users` table, `organization_users` junction table, `organization_invitations` table
- Has its own plan tier definitions (`PLAN_TIERS` dict) separate from AgentStudio

**What changes:**

#### Step 1 — Migrate org integer IDs to UUIDs

All `organization_id` columns must change from `INT` to `VARCHAR(36)` before switching auth. This is the largest migration step.

```sql
-- Run after user email-matching migration (§13.2) to establish UUID mapping
ALTER TABLE organizations ALTER COLUMN id TYPE VARCHAR(36);
ALTER TABLE collections ALTER COLUMN organization_id TYPE VARCHAR(36);
ALTER TABLE documents ALTER COLUMN organization_id TYPE VARCHAR(36);
ALTER TABLE document_chunks ALTER COLUMN organization_id TYPE VARCHAR(36);
ALTER TABLE organization_credentials ALTER COLUMN organization_id TYPE VARCHAR(36);
ALTER TABLE organization_api_keys ALTER COLUMN organization_id TYPE VARCHAR(36);
ALTER TABLE repository_folders ALTER COLUMN organization_id TYPE VARCHAR(36);
ALTER TABLE repository_documents ALTER COLUMN organization_id TYPE VARCHAR(36);
-- Populate UUID values from the AgentStudio org UUID mapping
```

#### Step 2 — Convert Organization to a JIT shadow record

The `organizations` table is kept but becomes a lightweight cache — populated automatically from JWT claims on every request. The local `plan_type`, billing, and plan tier logic (`PLAN_TIERS`) are removed; quota limits come from the JWT `plan_limits` claim instead.

Fields retained: `id` (UUID), `name`, `slug`, `max_users`, `max_documents`, `max_storage_mb`, `is_active`.  
Fields removed: `billing_email`, `plan_type`, `embedding_provider`, `subscription_started_at`, `trial_ends_at`, `created_by`.

The JWT validator performs an UPSERT on every authenticated request:

```python
async def _upsert_org(db: Session, payload: dict):
    limits = payload.get("plan_limits", {})
    db.execute(text("""
        INSERT INTO organizations (id, name, slug, max_users, max_documents, max_storage_mb, is_active)
        VALUES (:id, :name, :slug, :max_users, :max_documents, :max_storage_mb, true)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            max_users = EXCLUDED.max_users,
            max_documents = EXCLUDED.max_documents,
            max_storage_mb = EXCLUDED.max_storage_mb
    """), {
        "id": payload["org_id"],
        "name": payload.get("org_name", ""),
        "slug": payload.get("org_slug", payload["org_id"]),
        "max_users": limits.get("max_users", 5),
        "max_documents": limits.get("max_documents", 100),
        "max_storage_mb": limits.get("max_storage_mb", 1000),
    })
    db.commit()
```

**`QuotaChecker` is unchanged** — it still reads `org.max_users`, `org.max_documents`, `org.max_storage_mb` from the local row. Those values are now sourced from the JWT plan limits, synced on every request.

#### Step 3 — Drop user/membership tables

```
Drop:  users, organization_users, organization_invitations
Keep:  organizations (shadow), collections, documents, document_chunks,
       organization_credentials, organization_api_keys,
       repository_folders, repository_documents, organization_usage
```

#### Step 4 — Remove DemystRAG auth and org management endpoints

```
Remove:  /auth/login, /auth/register, /auth/refresh
Remove:  /api/v2/organizations (create, invite members, update plan)
Keep:    all document, collection, credential, repository, search endpoints
```

### 4.3 Mock API — Changes Required

**Current state (from code analysis):**
- Uses `Tenant` model with **UUID PK** — already compatible with AgentStudio UUIDs. No PK migration needed.
- Domain hierarchy: `Tenant → Project → [Configurations, OAuthClients, APIKeys]`
- `Tenant` is minimal: just `id`, `slug`, `name`, `description`, `is_active`
- Auth is full OAuth2 via `oauth_service.validate_token` (DB lookup for every request)
- Super admins switch tenant context via `X-Tenant-ID` header

**What changes:**

#### Step 1 — Convert Tenant to a JIT shadow record

The `tenants` table stays for FK integrity (`Project.tenant_id`). The JWT validator upserts the tenant on every request:

```python
async def _upsert_tenant(db: AsyncSession, payload: dict):
    await db.execute(text("""
        INSERT INTO tenants (id, name, slug, is_active)
        VALUES (:id, :name, :slug, true)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            slug = EXCLUDED.slug
    """), {
        "id": payload["org_id"],
        "name": payload.get("org_name", ""),
        "slug": payload.get("org_slug", payload["org_id"]),
    })
    await db.commit()
```

No quota columns exist on `Tenant` today so no quota sync is needed for Mock API.

#### Step 2 — Replace `X-Tenant-ID` super admin switching

The `get_tenant_context` dependency currently reads `X-Tenant-ID` header for super admins. After migration, `is_platform_admin` from the JWT replaces this. Platform admins can pass `X-Org-ID` header to scope to a specific org (or the JWT `org_id` is used by default).

#### Step 3 — Drop OAuth user/token tables

```
Drop:  OAuthUser (users), OAuth access tokens, refresh tokens, auth codes
Keep:  tenants (shadow), projects, api_configurations, oauth_clients
       (client credentials remain for Mock API's own OAuth simulation feature —
        these are not for authenticating Mock API users, they are mock data for agents)
```

**Important distinction:** Mock API's `OAuthClient` and token tables serve a different purpose — they are the *mock insurance API's OAuth simulation* that agents under test call. These are domain data, not auth infrastructure, and must be kept.

#### Step 4 — Remove Mock API auth endpoints

```
Remove:  /api/v1/auth/login, /api/v1/auth/refresh, /api/v1/auth/logout, /api/v1/auth/me
Remove:  /api/v1/admin/tenants (create/update tenant — now managed by AgentStudio)
Keep:    /api/v1/admin/projects, /api/v1/admin/configurations, /api/v1/admin/monitoring
Keep:    all dynamic API routes (the mock insurance APIs agents call)
Keep:    /api/v1/admin/projects/{id}/oauth/clients (mock OAuth setup — domain data)
```

### 4.4 Summary Table

| Change | AgentStudio | DemystRAG | Mock API |
|--------|-------------|-----------|----------|
| Add `org_name`, `org_slug`, `plan_limits` to JWT | ✅ Required | — | — |
| Add `has_demystrag`, `has_mock_api` to subscription plan features | ✅ Required | — | — |
| Migrate `organization_id` columns: `INT` → `VARCHAR(36)` | — | ✅ Required | — (already UUID) |
| Convert local org/tenant table to JIT shadow record | — | ✅ Required | ✅ Required |
| Add UPSERT on every authenticated request | — | ✅ Required | ✅ Required |
| Drop `users` / `OAuthUser` table | — | ✅ Required | ✅ Required |
| Drop `organization_users`, `organization_invitations` | — | ✅ Required | — |
| Remove `/auth/login`, `/auth/register` | — | ✅ Required | ✅ Required |
| Remove org/tenant management admin endpoints | — | ✅ Required | ✅ Partial (keep project endpoints) |
| Add shared JWT validator middleware | — | ✅ Required | ✅ Required |
| Set `AGENTSTUDIO_JWT_SECRET` env var | — | ✅ Required | ✅ Required |
| Keep domain data tables unchanged | — | ✅ Yes | ✅ Yes |
| Keep mock OAuth simulation tables (domain data) | — | — | ✅ Keep as-is |

---

## 5. JWT Token Design

### 5.1 Access Token Claims

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "jane@acme.com",
  "full_name": "Jane Smith",
  "org_id": "7f3c8200-a12b-4d3e-b800-112233445566",
  "org_name": "Acme Corp",
  "org_slug": "acme-corp",
  "org_role": "developer",
  "is_platform_admin": false,
  "products": ["agentstudio", "demystrag"],
  "plan_limits": {
    "max_users": 50,
    "max_documents": 5000,
    "max_storage_mb": 50000,
    "max_collections": 100,
    "embedding_providers": ["openai", "anthropic"]
  },
  "iat": 1716000000,
  "exp": 1716001800
}
```

**Field definitions:**

| Claim | Type | Source | Description |
|-------|------|--------|-------------|
| `sub` | UUID string | `users.id` | User identity — used as `user_id` in all sub-apps |
| `email` | string | `users.email` | Display only — never used for lookups |
| `full_name` | string | `users.full_name` | Display only |
| `org_id` | UUID string | `users.organization_id` | Organisation scope for all sub-apps |
| `org_name` | string | `organizations.name` | Used by sub-apps to JIT-create/update their local org shadow record |
| `org_slug` | string | `organizations.slug` | Used by sub-apps to JIT-create/update their local org shadow record |
| `org_role` | string | RBAC user role assignment | One of: `org_owner`, `org_admin`, `team_lead`, `developer`, `operator`, `viewer` — mapped to a permission tier by each sub-app (see §8.4) |
| `is_platform_admin` | bool | `users.is_platform_admin` | Grants full access in all sub-apps when `true` |
| `products` | string[] | Derived from `subscription_plan.features` at login | Which products this org has access to |
| `plan_limits` | object | Derived from `subscription_plan` columns at login | Quota limits — sub-apps sync these into their local shadow org record so existing quota enforcement code continues to work without change |
| `iat` | int | Server time | Issued-at timestamp |
| `exp` | int | `iat + 1800` | 30-minute expiry (access token) |

### 5.2 Refresh Token

The refresh token remains opaque (random UUID stored in Redis) and is only accepted by AgentStudio's `/auth/refresh` endpoint. Sub-apps never see the refresh token.

### 5.3 Token Lifetime

| Token | Lifetime | Storage |
|-------|----------|---------|
| Access token | 30 minutes | Frontend memory / localStorage |
| Refresh token | 7 days | HttpOnly cookie or localStorage |

### 5.4 Products Claim Construction

At login time, AgentStudio loads the organisation's subscription plan and builds the `products` list:

```python
products = ["agentstudio"]  # always included
if plan.has_feature("has_demystrag"):
    products.append("demystrag")
if plan.has_feature("has_mock_api"):
    products.append("mock_api")
```

This runs once at login and is embedded in the token — no database call is made on subsequent requests.

---

## 6. Registration Flow

### 6.1 New User Registration (Full Flow)

```
User fills registration form on AgentStudio
         │
         ▼
POST /api/v1/auth/register
         │
         ├── Validate: email not already registered
         ├── Validate: industry and employee_count provided (mandatory)
         ├── Create Organization record
         │     ├── approval_status = "pending"
         │     ├── subscription_status = "trial"
         │     ├── subscription_plan_id = free_plan_id
         │     └── profile fields: website, phone, country, industry,
         │           employee_count, intended_use_case
         │
         ├── Create User record
         │     ├── role = "admin" (first user in org)
         │     ├── is_platform_admin = false
         │     └── is_active = true
         │
         └── Return 201: { user, access_token, refresh_token }
                  │
                  ▼
        User lands on AgentStudio dashboard
        (pending approval banner shown if approval_status == "pending")
```

### 6.2 What Registration Does NOT Do

- **Does not create any record in DemystRAG or Mock API** — these apps have no user database
- **Does not automatically unlock DemystRAG or Mock API** — they are locked until subscription plan includes them
- **Does not send invitations** — sub-app access is automatic once the plan is upgraded

### 6.3 Registration Form Fields

| Field | Required | Purpose |
|-------|----------|---------|
| Email | Yes | Identity |
| Password | Yes | Credential |
| Full Name | No | Display |
| Organisation Name | Yes (new org) | Creates org record |
| Industry | **Yes** | Admin review |
| Employee Count | **Yes** | Admin review + plan recommendation |
| Website | No | Admin review |
| Phone Number | No | Admin review |
| Country | No | Admin review |
| Intended Use Case | No | Admin review |

### 6.4 Invitation-Based Registration (Existing Team Members)

When an admin invites a team member via the Users page:
1. Admin creates invite → `invitations` table record created
2. Invited user clicks email link → lands on registration form with email pre-filled and org pre-selected
3. User completes registration → immediately joins the existing organisation
4. `approval_status` on the org is already `active` — user gets immediate access
5. Products available match the org's subscription plan (already granted)

---

## 7. Login Flow

### 7.1 Login Sequence

```
User enters email + password on AgentStudio login page
         │
         ▼
POST /api/v1/auth/login  { email, password }
         │
         ├── Verify password hash
         ├── Check user.is_active
         ├── Check user account not locked (failed_login_attempts)
         ├── Load user.organization (with subscription_plan)
         │
         ├── Check org.is_active
         ├── Check org.approval_status == "active"
         │     └── If "pending"  → return 403: "Organisation pending approval"
         │     └── If "rejected" → return 403: "Organisation access denied"
         │     └── If "suspended"→ return 403: "Organisation suspended"
         │
         ├── Build products list from subscription_plan.features
         │
         ├── Issue access_token (JWT, 30 min, enriched claims)
         ├── Issue refresh_token (opaque, 7 days, stored in Redis)
         │
         └── Return 200: { user, tokens: { access_token, refresh_token } }
```

### 7.2 Token Refresh

```
Frontend detects access_token near expiry (or receives 401)
         │
         ▼
POST /api/v1/auth/refresh  { refresh_token }
         │
         ├── Validate refresh_token in Redis
         ├── Load user + org + subscription_plan (re-derive products)
         ├── Issue new access_token
         │
         └── Return 200: { access_token, refresh_token (rotated) }
```

**Important:** The `products` claim is re-derived on every refresh. If the platform admin upgrades an org's plan while the user is logged in, the user gets the new products on their next token refresh (within 30 minutes).

### 7.3 Accessing DemystRAG After Login

The user does not log in to DemystRAG. The frontend passes the same `Authorization: Bearer <access_token>` header to DemystRAG's API. DemystRAG validates the token locally:

```
User clicks "Open DemystRAG" in the navigation
         │
         ▼
Frontend opens DemystRAG URL (same tab or new tab)
         │
         ▼
DemystRAG frontend reads access_token from localStorage / shared cookie
         │
         ▼
DemystRAG makes API call with Authorization: Bearer <token>
         │
         ▼
DemystRAG backend validates token (see §10.2)
         │
         ├── Check "demystrag" in token.products
         │     └── No → 403: "DemystRAG not included in your plan. Upgrade to access."
         │
         └── Request proceeds, user_id = token.sub, org_id = token.org_id
```

### 7.4 Single Sign-Out

Logout is handled by AgentStudio:

```
POST /api/v1/auth/logout
         │
         ├── Delete refresh_token from Redis
         └── Return 200
```

The frontend must clear `localStorage` (access_token) and redirect to the AgentStudio login page. Since access tokens are stateless JWTs, they technically remain valid until expiry (30 min). This is acceptable — if immediate invalidation is required, a Redis token blacklist can be added as a later enhancement.

---

## 8. Product Entitlement Flow

### 8.1 Plan Tiers and Product Inclusions

Platform admins configure which plans include which add-on products:

| Plan | AgentStudio | DemystRAG | Mock API |
|------|-------------|-----------|----------|
| Free | ✅ | ❌ | ❌ |
| Starter | ✅ | ❌ | ❌ |
| Professional | ✅ | ✅ | ❌ |
| Enterprise | ✅ | ✅ | ✅ |
| Custom (any) | ✅ | configurable | configurable |

This mapping is stored in `subscription_plans.features` JSONB and can be changed by a platform admin at any time without a deployment.

### 8.2 Upgrading a Plan — Effect on Existing Users

```
Platform admin upgrades Org A from "Starter" to "Professional"
         │
         ├── adminService.updateOrganizationStatus(orgId, { subscriptionPlanId: professionalPlanId })
         │
         └── PATCH /api/v1/admin/organizations/{orgId}
               └── Updates org.subscription_plan_id in DB

Next time any Org A user refreshes their token:
         │
         └── POST /api/v1/auth/refresh
               └── Re-derives products: now includes "demystrag"
               └── New access_token contains: "products": ["agentstudio", "demystrag"]

User navigates to DemystRAG → access granted
```

**Maximum lag:** 30 minutes (access token lifetime). Users do not need to log out and back in — the next automatic token refresh picks up the new entitlement.

### 8.3 Downgrading a Plan — Effect on Existing Users

```
Platform admin downgrades Org B from "Professional" to "Starter"
         │
         └── org.subscription_plan_id updated in DB

Org B user's current access_token still has "demystrag" in products
         │
         └── Remains valid for up to 30 minutes

On next token refresh:
         └── "demystrag" is no longer in products
         └── DemystRAG API returns 403 on next request after refresh
```

For immediate revocation (e.g., cancelled subscription): a Redis blacklist entry can be added for the org's tokens, forcing all users to re-authenticate immediately. This is an optional enhancement.

### 8.4 Role-Based Access Within Sub-Apps

Sub-apps do not have their own role tables. They read `org_role` from the JWT and map it to a local permission tier. AgentStudio has 6 system roles; sub-apps collapse these into 3 tiers. The mapping can differ between sub-apps depending on their domain requirements.

#### Role Tier Mapping

| AgentStudio Role | DemystRAG Tier | Mock API Tier |
|-----------------|----------------|---------------|
| `org_owner` | **admin** | **admin** |
| `org_admin` | **admin** | **admin** |
| `team_lead` | **admin** | **contributor** |
| `developer` | **contributor** | **contributor** |
| `operator` | **contributor** | **contributor** |
| `viewer` | **reader** | **reader** |
| `is_platform_admin: true` | **admin** (overrides all) | **admin** (overrides all) |
| Any unknown/custom role | **reader** (least-privilege default) | **reader** (least-privilege default) |

> **Why `team_lead` → `admin` in DemystRAG only:** DemystRAG has a document approval workflow where documents must be reviewed and approved by a trusted user before entering the RAG knowledge base. Team leads are responsible for content quality within their team and must be able to approve documents. In Mock API, approval is not a concept — `team_lead` retains `contributor` tier so they manage their own endpoints without full admin access to all org configurations.

#### DemystRAG — Tier Permissions

DemystRAG's domain: documents, collections, vector search, query history, document approval workflow.

| Tier | AgentStudio Roles | Permissions |
|------|------------------|-------------|
| **admin** | `org_owner`, `org_admin`, `team_lead` | Create/delete collections, upload documents, run queries, view and delete any org document, **approve/reject documents for RAG ingestion**, manage RAG settings |
| **contributor** | `developer`, `operator` | Create collections, upload documents, run queries, view and delete own documents, submit documents for approval |
| **reader** | `viewer` | Run queries only — no upload, no collection management, no approval |

#### Mock API — Tier Permissions

Mock API's domain: mock endpoints, request logs, API keys, response templates.

| Tier | AgentStudio Roles | Permissions |
|------|------------------|-------------|
| **admin** | `org_owner`, `org_admin` | Create/edit/delete any endpoint, manage org API keys, view all request logs, manage settings |
| **contributor** | `team_lead`, `developer`, `operator` | Create/edit/delete own endpoints, create API keys scoped to own endpoints, run tests, view own logs |
| **reader** | `viewer` | View endpoint definitions, send test requests, view own logs — no create/edit/delete |

#### Role Change Propagation

Role changes made in AgentStudio (e.g., promoting a `developer` to `team_lead`) take effect in sub-apps on the user's next token refresh — within 30 minutes. No action is required in the sub-apps. For DemystRAG, a `developer` promoted to `team_lead` gains document approval permissions on their next refresh.

---

## 9. Platform Admin Flow

### 9.1 Platform Admin Access Across All Apps

The `is_platform_admin: true` claim in the JWT bypasses all tenant and product restrictions in all three apps.

```
Platform admin logs into AgentStudio
         │
         └── JWT contains: is_platform_admin: true, products: ["agentstudio", "demystrag", "mock_api"]

Platform admin navigates to DemystRAG admin panel
         │
         └── DemystRAG validates token: is_platform_admin = true
         └── DemystRAG grants full administrative access regardless of org plan
```

### 9.2 Platform Admin Capabilities by App

| Capability | AgentStudio | DemystRAG | Mock API |
|-----------|-------------|-----------|----------|
| View all organisations | ✅ Admin panel | ✅ via JWT bypass | ✅ via JWT bypass |
| View all users | ✅ Admin panel | Read from JWT claims when impersonating | Read from JWT claims |
| Manage subscription plans | ✅ Admin panel | — | — |
| Approve / reject orgs | ✅ Admin panel | — | — |
| Access any org's data | ✅ Impersonation | ✅ org_id override header | ✅ org_id override header |

### 9.3 Platform Admin: No Separate Account in Sub-Apps

There is no `is_platform_admin` flag in DemystRAG or Mock API databases — those tables no longer exist. The `is_platform_admin` JWT claim is the sole mechanism. A platform admin's identity is their AgentStudio user record.

### 9.4 Creating Platform Admins

Only existing platform admins can designate another user as a platform admin:

```
PATCH /api/v1/admin/users/{userId}/platform-admin?is_admin=true
         │
         ├── Requires caller to have is_platform_admin = true
         ├── Sets users.is_platform_admin = true in DB
         └── System log: WARNING "Platform admin privileges granted to {email} by {admin_email}"

Next login or token refresh for that user:
         └── is_platform_admin: true appears in their JWT
```

---

## 10. Sub-App Integration

### 10.1 Environment Configuration

Each sub-app needs one new environment variable:

```bash
# DemystRAG and Mock API .env / Azure Key Vault
AGENTSTUDIO_JWT_SECRET=<same value as AgentStudio's SECRET_KEY>
AGENTSTUDIO_ALGORITHM=HS256  # optional, default
```

### 10.2 Shared JWT Validator (Python / FastAPI)

The validator handles two concerns: product entitlement check and role tier enforcement. Each sub-app ships one copy of this file, with `REQUIRED_PRODUCT` set to its own product key.

```python
# app/core/agentstudio_auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database import get_db

bearer = HTTPBearer()

# Set to "demystrag" in DemystRAG, "mock_api" in Mock API
REQUIRED_PRODUCT = "demystrag"

TIER_ORDER = {"reader": 0, "contributor": 1, "admin": 2}

# DemystRAG-specific mapping — team_lead is admin here because they approve documents
ROLE_TO_TIER_DEMYSTRAG = {
    "org_owner":  "admin",
    "org_admin":  "admin",
    "team_lead":  "admin",       # can approve/reject documents for RAG ingestion
    "developer":  "contributor",
    "operator":   "contributor",
    "viewer":     "reader",
}

# Mock API mapping — team_lead stays contributor (no approval workflow)
ROLE_TO_TIER_MOCK_API = {
    "org_owner":  "admin",
    "org_admin":  "admin",
    "team_lead":  "contributor",
    "developer":  "contributor",
    "operator":   "contributor",
    "viewer":     "reader",
}

# Set ROLE_TO_TIER to the correct dict for this app
ROLE_TO_TIER = ROLE_TO_TIER_DEMYSTRAG  # change to ROLE_TO_TIER_MOCK_API in Mock API


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.AGENTSTUDIO_JWT_SECRET,
            algorithms=["HS256"],
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    is_platform_admin = payload.get("is_platform_admin", False)

    if not is_platform_admin and REQUIRED_PRODUCT not in payload.get("products", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{REQUIRED_PRODUCT} is not included in your subscription plan",
        )

    # JIT: sync three shadow records so all existing FK constraints and role
    # checks (require_org_admin, require_org_creator, QuotaChecker) continue
    # to work without modification.
    _upsert_org(db, payload)
    _upsert_user(db, payload)
    _upsert_org_member(db, payload)

    org_role = payload.get("org_role", "viewer")
    payload["_tier"] = "admin" if is_platform_admin else ROLE_TO_TIER.get(org_role, "reader")
    return payload


def _upsert_org(db: Session, payload: dict) -> None:
    """
    Create or update the local org shadow record from JWT claims.
    Called on every authenticated request — the UPSERT is a no-op when nothing changed.
    DemystRAG: syncs quota limits so QuotaChecker works without modification.
    Mock API:  syncs name/slug so the tenants FK anchor stays current.
    """
    limits = payload.get("plan_limits", {})
    db.execute(text("""
        INSERT INTO organizations (id, name, slug, max_users, max_documents, max_storage_mb, is_active)
        VALUES (:id, :name, :slug, :max_users, :max_documents, :max_storage_mb, true)
        ON CONFLICT (id) DO UPDATE SET
            name           = EXCLUDED.name,
            slug           = EXCLUDED.slug,
            max_users      = EXCLUDED.max_users,
            max_documents  = EXCLUDED.max_documents,
            max_storage_mb = EXCLUDED.max_storage_mb
    """), {
        "id":             payload["org_id"],
        "name":           payload.get("org_name", ""),
        "slug":           payload.get("org_slug", payload["org_id"]),
        "max_users":      limits.get("max_users", 5),
        "max_documents":  limits.get("max_documents", 100),
        "max_storage_mb": limits.get("max_storage_mb", 1000),
    })
    db.commit()
    # Mock API: replace "organizations" with "tenants" in the INSERT above


def _upsert_user(db: Session, payload: dict) -> None:
    """
    Create or update the local user shadow record from JWT claims.
    Required because document_approvals.requested_by / reviewed_by FK
    references the local users table. Without this row the FK insert fails.
    email is not in the JWT — username falls back to sub UUID on first creation;
    a subsequent profile-fetch endpoint can fill it in if needed.
    """
    db.execute(text("""
        INSERT INTO users (id, username, email, role, platform_role, is_active)
        VALUES (:id, :username, :email, 'user', :platform_role, true)
        ON CONFLICT (id) DO UPDATE SET
            platform_role = EXCLUDED.platform_role,
            is_active     = true
    """), {
        "id":            payload["sub"],
        "username":      payload.get("sub"),          # overwritten later if profile sync added
        "email":         payload.get("sub"),          # placeholder — unique constraint satisfied
        "platform_role": "platform_admin" if payload.get("is_platform_admin") else "user",
    })
    db.commit()


def _upsert_org_member(db: Session, payload: dict) -> None:
    """
    Create or update the OrganizationUser membership record from JWT claims.
    This is what require_org_admin / require_org_creator read to enforce roles.
    The DemystRAG role is derived from the JWT tier using DEMYSTRAG_TIER_TO_ROLE.
    Called on every request so role promotions take effect immediately after refresh.
    """
    DEMYSTRAG_TIER_TO_ROLE = {
        "admin":       "org_admin",
        "contributor": "org_creator",
        "reader":      "org_viewer",
    }
    is_platform_admin = payload.get("is_platform_admin", False)
    org_role = payload.get("org_role", "viewer")
    tier = "admin" if is_platform_admin else ROLE_TO_TIER.get(org_role, "reader")
    demystrag_role = DEMYSTRAG_TIER_TO_ROLE[tier]

    db.execute(text("""
        INSERT INTO organization_users (user_id, organization_id, role, is_active)
        VALUES (:user_id, :org_id, :role, true)
        ON CONFLICT (user_id, organization_id) DO UPDATE SET
            role      = EXCLUDED.role,
            is_active = true
    """), {
        "user_id": payload["sub"],
        "org_id":  payload["org_id"],
        "role":    demystrag_role,
    })
    db.commit()
    # Mock API: this function is not needed — Mock API has no OrganizationUser table.


def require_tier(min_tier: str):
    """Dependency factory — rejects if the user's tier is below the minimum required."""
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if TIER_ORDER[user["_tier"]] < TIER_ORDER[min_tier]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires {min_tier} access",
            )
        return user
    return dependency
```

Usage in endpoints:

```python
# Anyone with product access can run queries (reader+)
@router.post("/query")
async def run_query(user: dict = Depends(require_tier("reader"))):
    org_id = user["org_id"]
    ...

# Contributors and above can upload documents
@router.post("/documents")
async def upload_document(user: dict = Depends(require_tier("contributor"))):
    user_id = user["sub"]
    org_id = user["org_id"]
    ...

# Only admins can delete collections
@router.delete("/collections/{collection_id}")
async def delete_collection(user: dict = Depends(require_tier("admin"))):
    ...
```

### 10.3 Replacing Existing Auth Middleware

DemystRAG and Mock API currently use their own `get_current_user` dependency that queries their local `users` table. The new `agentstudio_auth.get_current_user` validates the AgentStudio JWT and JIT-provisions three shadow records on every request:

1. `_upsert_org()` — org/tenant shadow row (quota limits, name, slug)
2. `_upsert_user()` — user shadow row (required for FK references in `document_approvals.requested_by` / `reviewed_by`)
3. `_upsert_org_member()` — `OrganizationUser` membership row with the correct DemystRAG role derived from the JWT tier

After dropping in `agentstudio_auth.py`, the following existing DemystRAG dependencies require **no code changes** because the JIT-provisioned `OrganizationUser` row makes them work exactly as before:
- `require_org_admin` — approving/rejecting documents, deleting collections, managing settings
- `require_org_creator` — submitting documents for approval, creating collections
- `require_org_auditor` — view-only access to own documents

> **Mock API note:** Mock API does not have an `OrganizationUser` table or a document approval workflow, so `_upsert_user()` and `_upsert_org_member()` are not needed there. Only `_upsert_tenant()` (the Mock API equivalent of `_upsert_org()`) is required.

### 10.4 Frontend Token Sharing

**Option A — Shared localStorage key (recommended for same-domain deployments)**

All three frontends read and write `localStorage.getItem("access_token")` and `localStorage.getItem("refresh_token")`. This works when all three apps are served under the same domain (e.g., `agentstudio365.com`, `rag.agentstudio365.com`, `mock.agentstudio365.com`) because `localStorage` is per-origin — they must either share the same origin or use Option B.

**Option B — Token passed via URL fragment on navigation**

When AgentStudio navigates to a sub-app, it appends `#token=<access_token>` to the URL. The sub-app reads the fragment on load, stores the token in its own `localStorage`, and strips the fragment. This is the standard SSO hand-off pattern and works across different origins.

**Option C — Shared HttpOnly cookie (most secure, requires shared parent domain)**

Set `access_token` as a `Secure; HttpOnly; SameSite=Strict` cookie on the parent domain `agentstudio365.com`. All sub-apps on `*.agentstudio365.com` receive the cookie automatically. The cookie is read server-side — no JavaScript access.

**Recommendation:** Option B for current deployment (different Container Apps, different FQDNs until custom domains are configured), then migrate to Option C once all apps share `*.agentstudio365.com`.

---

## 11. Organisation Data Flow

This section traces exactly how organisation details travel from AgentStudio into DemystRAG and Mock API — covering creation, first access, quota enforcement, plan changes, and org suspension.

### 11.1 Current State vs Target

| | Current (3 silos) | After migration |
|---|---|---|
| **DemystRAG org record** | Created manually via `/api/v2/organizations` with its own billing email, plan tier, quota fields | JIT-created from JWT claims on first authenticated request |
| **Mock API tenant record** | Created manually via `/api/v1/admin/tenants` by a super admin | JIT-created from JWT claims on first authenticated request |
| **Quota limits source** | Stored in DemystRAG's own `organizations` table (`max_documents`, `max_users`, `max_storage_mb`) | JWT `plan_limits` claim, synced into DemystRAG's shadow org row on every request |
| **Org name / slug** | Typed manually into each app's admin UI | Carried in JWT from AgentStudio's `organizations` table |
| **Org status (active/suspended)** | Managed per-app | Managed only in AgentStudio; propagated via login/refresh gate |

### 11.2 Organisation Lifecycle Flow

#### A — New Organisation Registered

```
User registers on AgentStudio
         │
         ▼
AgentStudio creates:
  organizations row  ─── name, slug, website, industry, employee_count, intended_use_case
                    ─── approval_status = "pending"
                    ─── subscription_plan_id → free plan
                    ─── subscription_status = "trial"
         │
         ▼
Platform admin reviews and approves organisation
  organizations.approval_status = "active"
         │
         ▼
User logs in → JWT issued with:
  org_id, org_name, org_slug,
  plan_limits { max_documents: 100, max_users: 5, max_storage_mb: 1000 },
  products: ["agentstudio"]   ← DemystRAG not yet purchased
         │
DemystRAG and Mock API: org not yet accessible (403 on product check)
```

#### B — Organisation Upgrades Plan (Unlocks DemystRAG)

```
Platform admin assigns "Professional" plan to the org:
  PATCH /api/v1/admin/organizations/{orgId}
    { subscriptionPlanId: "professional-plan-uuid" }
         │
         ▼
AgentStudio DB: org.subscription_plan_id updated
         │
         ▼
User's next token refresh (within 30 min):
  POST /api/v1/auth/refresh
         │
  AgentStudio re-derives:
    products: ["agentstudio", "demystrag"]   ← now included
    plan_limits: {
      max_documents: 5000,
      max_users: 50,
      max_storage_mb: 50000,
      max_collections: 100,
      embedding_providers: ["openai", "anthropic", "deepseek", "ollama"]
    }
         │
         ▼
User makes first DemystRAG API call:
  Authorization: Bearer <new_token>
         │
         ▼
DemystRAG JWT validator:
  1. Verifies signature ✓
  2. Checks "demystrag" in products ✓
  3. Calls _upsert_org(db, payload):

     INSERT INTO organizations
       (id, name, slug, max_users, max_documents, max_storage_mb, is_active)
     VALUES
       ('7f3c8200-...', 'Acme Corp', 'acme-corp', 50, 5000, 50000, true)
     ON CONFLICT (id) DO UPDATE SET
       name = 'Acme Corp', max_users = 50,
       max_documents = 5000, max_storage_mb = 50000
         │
         ▼
DemystRAG org shadow row now exists.
Collections, documents, credentials are scoped to org_id = '7f3c8200-...'

User sees empty DemystRAG workspace — expected "blank slate" for new orgs.
```

#### C — Subsequent Requests (Steady State)

```
Every DemystRAG / Mock API request:

  Request arrives with Bearer token
         │
         ▼
  _upsert_org() runs — PostgreSQL evaluates ON CONFLICT:
    - If nothing changed → UPDATE sets same values → no-op, effectively free
    - If plan changed (limits updated) → UPDATE writes new quota values
         │
         ▼
  Endpoint handler runs:
    user_id = payload["sub"]       → scopes user-owned resources
    org_id  = payload["org_id"]    → scopes all org resources
    tier    = payload["_tier"]     → enforces role permissions
```

#### D — Quota Enforcement (DemystRAG)

```
User uploads a document:
  POST /documents  { file: ... }
         │
         ▼
  QuotaChecker.check_document_quota(org, db):
    SELECT COUNT(*) FROM documents WHERE organization_id = '7f3c8200-...'
    → current_count = 4823

    if current_count >= org.max_documents:   # org.max_documents = 5000 (from last UPSERT)
        raise 402 "Document quota exceeded"
         │
         ▼
  If within quota → document saved with:
    organization_id = payload["org_id"]
    created_by      = payload["sub"]
```

`org.max_documents` is the value last written by `_upsert_org` from the JWT `plan_limits`. The `QuotaChecker` code is **unchanged** — it simply reads from the local row as before.

#### E — Plan Downgrade (Quota Tightened)

```
Platform admin downgrades org from Professional → Starter:
  org.subscription_plan_id → starter plan (max_documents: 500)
         │
         ▼
User's existing token still has max_documents: 5000 in plan_limits.
DemystRAG's org row still shows max_documents = 5000.

  → User can still upload until token expires (max 30 min).

On next token refresh:
  plan_limits.max_documents = 500  ← new value from starter plan
         │
         ▼
Next DemystRAG request:
  _upsert_org() writes max_documents = 500 into org row
         │
         ▼
Next upload attempt:
  current_count (e.g. 1200) >= org.max_documents (500)
  → 402 "Document quota exceeded. Upgrade your plan."
```

Existing documents are not deleted on downgrade — only new uploads are blocked.

#### F — Organisation Suspended

```
Platform admin suspends org:
  org.approval_status = "suspended"
         │
         ▼
Current user tokens remain valid until expiry (max 30 min).
Sub-apps are stateless — they cannot detect the suspension mid-token.

On next login or token refresh:
  AgentStudio checks org.approval_status
  → "suspended" → returns 403: "Organisation suspended"
         │
         ▼
User cannot obtain a new token.
DemystRAG / Mock API: next request after token expiry → 401 (no valid token).

For immediate effect:
  Platform admin adds org_id to Redis blacklist.
  Sub-apps check blacklist on each request (optional enhancement — see §12.6).
```

### 11.3 Organisation Name / Slug Sync

AgentStudio is the source of truth for org name and slug. Sub-apps display the org name in their UIs but never let users edit it — changes made in AgentStudio propagate automatically on the next request via `_upsert_org`.

```
Platform admin renames org in AgentStudio:
  PATCH /api/v1/admin/organizations/{orgId}  { name: "Acme Global Corp" }
         │
         ▼
Next user token refresh:
  org_name: "Acme Global Corp"  ← now in JWT
         │
         ▼
Next DemystRAG request:
  _upsert_org() → UPDATE organizations SET name = 'Acme Global Corp' WHERE id = '...'
         │
         ▼
DemystRAG UI shows new org name on next page load.
```

### 11.4 Mock API — Tenant + Project Hierarchy Flow

Mock API has an additional layer: `Tenant → Project → [Configurations, APIKeys, OAuthClients]`. The `org_id` from the JWT maps to `tenants.id`. Projects are created by org users and continue to belong to their tenant.

```
Org "Acme Corp" (org_id = '7f3c8200-...') gets Mock API access.

User makes first Mock API request:
  _upsert_tenant() creates:
    tenants row: { id: '7f3c8200-...', name: 'Acme Corp', slug: 'acme-corp' }

User creates a project:
  POST /api/v1/admin/projects  { name: "Travel Insurance API", tenant_id: "7f3c8200-..." }
    → project.tenant_id = payload["org_id"]   (from JWT, not from a local users table)

All project-scoped resources (configurations, api_keys, oauth_clients) inherit tenant isolation
through the project FK → tenant FK chain.

Platform admin can see all tenants and projects:
  payload["is_platform_admin"] = true → no tenant filter applied to queries
```

### 11.5 Embedding Provider Config (DemystRAG)

DemystRAG's `Organization` table currently stores `embedding_provider` and `embedding_model` per org. These are DemystRAG-specific settings that have no equivalent in AgentStudio's subscription plan. They remain stored in the DemystRAG shadow org row and are managed via the DemystRAG admin UI — AgentStudio does not own or sync them.

The `plan_limits.embedding_providers` JWT claim controls **which providers are allowed** for the org (derived from the subscription plan). The specific **default provider chosen** within that allowed list is still DemystRAG's concern.

```
JWT plan_limits.embedding_providers: ["openai", "anthropic"]
   → DemystRAG enforces: org cannot use "ollama" (not in allowed list)

DemystRAG org row: embedding_provider = "anthropic"  (user's chosen default)
   → DemystRAG uses "anthropic" as default when user doesn't specify
   → This field is NOT synced from JWT — it's set by the org admin in DemystRAG settings
```

### 11.6 What Sub-Apps Never Need to Call AgentStudio For

Sub-apps operate entirely from the JWT — no HTTP call back to AgentStudio is ever made at request time.

| Information | Source |
|------------|--------|
| User identity (`user_id`) | JWT `sub` claim |
| Org identity (`org_id`) | JWT `org_id` claim |
| Org name, slug | JWT `org_name`, `org_slug` claims |
| Product access | JWT `products` claim |
| Quota limits | JWT `plan_limits` claim → synced to local shadow row |
| User's role/tier | JWT `org_role` claim → mapped by `ROLE_TO_TIER` |
| Platform admin status | JWT `is_platform_admin` claim |

This means DemystRAG and Mock API continue to function normally even if AgentStudio is temporarily down — all requests using existing (non-expired) tokens succeed without degradation.

---

## 12. Edge Cases & Error Scenarios

### 12.1 Token Expired Mid-Session

| Scenario | Behaviour |
|----------|-----------|
| User is on DemystRAG, token expires | DemystRAG returns 401. Frontend detects 401, calls AgentStudio `/auth/refresh`, gets new token, retries original request transparently. |
| Refresh token also expired | User is redirected to AgentStudio login page. |
| Refresh token stolen and revoked by admin | Redis entry deleted. Next refresh call returns 401. User must re-login. |

### 12.2 Organisation Suspended While User Is Active

| When | Behaviour |
|------|-----------|
| Org suspended; user's current token still valid (< 30 min) | User can still make API calls until token expires. Sub-apps are stateless — they cannot check org status. |
| Token refreshes after suspension | AgentStudio `/auth/refresh` checks `org.approval_status`. Returns 403 immediately. User cannot get a new token. |
| Immediate effect required | Platform admin adds org_id to a Redis blacklist. Sub-apps check this list on each request. (Optional enhancement — not in initial scope.) |

### 12.3 Plan Downgrade — User Actively Using DemystRAG

| When | Behaviour |
|------|-----------|
| Admin downgrades plan; user is mid-session in DemystRAG | Existing token still has `"demystrag"` in products. User can continue for up to 30 minutes. |
| User's token refreshes | New token does not include `"demystrag"`. Next DemystRAG API call returns 403 with clear message: "DemystRAG not included in your subscription plan. Contact your administrator." |
| User navigates back to DemystRAG after refresh | Frontend reads the plan change from the JWT claims and can show an upgrade prompt. |

### 12.4 Org Still Pending Approval

| Scenario | Behaviour |
|----------|-----------|
| New org registers; admin has not approved yet | Login returns 403: "Your organisation is pending approval. You will be notified when access is granted." |
| Token was issued before org was set to pending (impossible in current flow since tokens require login which checks approval) | N/A — approval is checked at login time. |

### 12.5 User Deactivated by Org Admin

| Scenario | Behaviour |
|----------|-----------|
| Org admin deactivates a user | `users.is_active = false` in DB. |
| Deactivated user's current token is still valid | Access continues for up to 30 minutes on sub-apps (stateless). |
| Deactivated user attempts token refresh | AgentStudio checks `user.is_active`. Returns 401. |
| Deactivated user attempts new login | AgentStudio returns 401 immediately. |

### 12.6 Platform Admin Loses Admin Status

Same pattern as user deactivation: next token refresh re-derives `is_platform_admin = false`. The admin loses elevated access within 30 minutes without being forced to log out.

### 12.7 Multiple Tabs / Devices

Each tab/device uses the same `access_token` and `refresh_token` (if stored in localStorage). Token refresh is idempotent — refreshing from two tabs simultaneously will rotate the refresh token once; the second tab will receive a 401 on refresh and fall back to the login page. This is standard JWT refresh token rotation behaviour.

### 12.8 First Access to a Newly Unlocked Product

When an org's plan is upgraded to include DemystRAG:
1. User's next token refresh includes `"demystrag"` in `products`
2. User navigates to DemystRAG
3. DemystRAG has no record of this user or org — this is fine
4. The first request uses `org_id` from the token to scope all data
5. DemystRAG returns empty collections — expected "blank slate" for new orgs
6. No onboarding record needs to be created in advance

---

## 13. Security Considerations

### 13.1 Shared Secret Risk

Using one `SECRET_KEY` across three apps means a compromise of any one app's environment exposes token validation for all three. Mitigations:

- Store `SECRET_KEY` only in Azure Key Vault — never in source code or `.env` files committed to Git
- Sub-apps receive the secret as a read-only Key Vault reference — they cannot modify it
- Rotate the key quarterly (requires all three apps to redeploy simultaneously with the new value)
- Monitor for unexpected token validation failures in Application Insights

### 13.2 Claims Tampering

JWT tokens are signed with HS256. Tampering with any claim invalidates the signature. Sub-apps must always verify the signature before reading claims — the shared JWT validator does this (see §10.2).

**Never skip signature verification** even in development environments.

### 13.3 Products Claim Elevation Attack

A user cannot add products to their own token — the token is issued by AgentStudio and its claims are derived server-side from the database. The user only receives the encoded token and cannot modify it without invalidating the signature.

### 13.4 is_platform_admin Claim Abuse

If an attacker obtains a valid platform admin token, they have full access to all three apps. Mitigations:
- Short token lifetime (30 min)
- Monitor all `is_platform_admin: true` requests in Application Insights
- Require MFA for platform admin accounts (future enhancement)
- Log all platform admin actions to the `system_logs` table (already implemented in AgentStudio)

### 13.5 Sub-App Data Isolation

Sub-apps must scope all database queries to `org_id` from the JWT. They must never return data for other organisations. The `org_id` claim is verified as part of the signed JWT — it cannot be forged.

**Implementation check:** Every sub-app query that touches tenant data must include `WHERE organization_id = :org_id` using the value from `token["org_id"]`.

### 13.6 CORS

Sub-apps must configure CORS to allow requests only from known AgentStudio-related origins:

```python
allow_origins=[
    "https://agentstudio365.com",
    "https://rag.agentstudio365.com",
    "https://mock.agentstudio365.com",
    "http://localhost:5173",  # dev only
]
```

---

## 14. Migration Plan

### 13.1 Phases

#### Phase 1 — AgentStudio Changes (No Sub-App Impact)

All changes are backward-compatible. Existing sub-app users continue to use their own login during this phase.

**Tasks:**
1. Add `has_demystrag` and `has_mock_api` to `SubscriptionPlan.features` for all existing plans (SQL migration)
2. Enrich `create_access_token()` with new claims (`products`, `org_id`, `org_role`, `is_platform_admin`)
3. At login and refresh, load subscription plan and derive `products` list
4. Deploy to production — existing AgentStudio users get enriched tokens
5. Verify token claims in AgentStudio using `/auth/me` response

**Duration:** 1–2 days  
**Rollback:** Revert token enrichment — sub-apps are unchanged, no impact

#### Phase 2 — DemystRAG Integration

**Tasks:**
1. Add `AGENTSTUDIO_JWT_SECRET` to DemystRAG Azure Container App settings (from Key Vault)
2. Add `app/core/agentstudio_auth.py` to DemystRAG codebase
3. Replace all uses of the old `get_current_user` dependency with the new validator
4. Deploy DemystRAG to staging — test with AgentStudio tokens
5. Verify: existing DemystRAG users can access via AgentStudio JWT with `has_demystrag: true`
6. **Migration step for existing DemystRAG users:** Users who have existing DemystRAG accounts must register on AgentStudio. If their email is the same, they seamlessly take over their data (since `user_id` in DemystRAG tables can be migrated from DemystRAG user UUID → AgentStudio user UUID in a one-time migration script).
7. Drop DemystRAG `users` table
8. Remove DemystRAG `/auth/login`, `/auth/register` endpoints
9. Deploy to production

**Duration:** 3–5 days  
**Rollback:** Keep old DemystRAG `/auth/` endpoints behind a feature flag until migration is confirmed

#### Phase 3 — Mock API Integration

Same pattern as Phase 2, applied to Mock API.

**Duration:** 2–3 days

#### Phase 4 — Frontend Navigation Update

Update AgentStudio frontend navigation to show DemystRAG and Mock API as items in the sidebar or app switcher, conditionally rendered based on `products` in the decoded JWT.

**Duration:** 1 day

### 13.2 Existing User Migration (DemystRAG & Mock API)

For users who already have accounts in DemystRAG or Mock API:

```
1. Export existing DemystRAG/Mock API users: { email, user_id }
2. Match by email against AgentStudio users table
3. For matched users: run UPDATE on DemystRAG/Mock API data tables:
     UPDATE documents SET user_id = '<agentstudio_user_uuid>'
     WHERE user_id = '<demystrag_user_uuid>'
4. For unmatched users (no AgentStudio account):
     - Send email: "Your account has been merged. Log in at agentstudio365.com"
     - Create AgentStudio account with same email (password reset required on first login)
5. After migration validation: drop sub-app users tables
```

### 13.3 Rollback Strategy

| Phase | Rollback Action |
|-------|----------------|
| Phase 1 | Remove new JWT claims from `create_access_token` — sub-apps unaffected |
| Phase 2 | Re-enable DemystRAG's old auth endpoints; revert `agentstudio_auth.py` import |
| Phase 3 | Same as Phase 2 applied to Mock API |
| Phase 4 | Revert frontend navigation changes |

---

## 15. Implementation Checklist

### AgentStudio Backend

- [ ] `backend/app/core/security.py` — Add `org_name`, `org_slug`, `org_role`, `org_id`, `is_platform_admin`, `products`, `plan_limits` claims to `create_access_token()`
- [ ] `backend/app/api/v1/auth.py` — At login and refresh: load org + subscription plan, build `products` list and `plan_limits` object, pass all to `create_access_token()`
- [ ] SQL migration — Add `has_demystrag: false, has_mock_api: false` to all existing subscription plan `features` JSONB
- [ ] SQL migration — Update Professional/Enterprise plans to set `has_demystrag: true` as appropriate
- [ ] `backend/app/schemas/user.py` — Add new claims fields to `TokenData` schema
- [ ] Test: login response JWT contains `org_name`, `org_slug`, `plan_limits`
- [ ] Test: token refresh re-derives `products` and `plan_limits` after plan upgrade

### DemystRAG Backend

- [ ] **Schema migration:** Change `organization_id` columns from `INT` to `VARCHAR(36)` across all tables (see §4.2)
- [ ] **Data migration:** Map existing integer org IDs to AgentStudio UUIDs (email-match script from §13.2 first)
- [ ] **Schema migration:** Slim down `organizations` table — remove `billing_email`, `plan_type`, `subscription_*`, `created_by`; add `UNIQUE` constraint on `id` if not present
- [ ] Create `app/core/agentstudio_auth.py` (set `REQUIRED_PRODUCT = "demystrag"`, `ROLE_TO_TIER = ROLE_TO_TIER_DEMYSTRAG`, use sync SQLAlchemy `Session`)
- [ ] Implement `_upsert_org()` — syncs org shadow row with quota limits from JWT `plan_limits`
- [ ] Implement `_upsert_user()` — syncs user shadow row so `document_approvals.requested_by` / `reviewed_by` FK references resolve
- [ ] Implement `_upsert_org_member()` — syncs `OrganizationUser` row with DemystRAG role derived from JWT tier; `team_lead` → `org_admin`
- [ ] Replace all uses of old `get_current_user` from `auth.py` with `agentstudio_auth.get_current_user`
- [ ] **No changes needed** to `require_org_admin`, `require_org_creator`, `require_org_auditor` — JIT-provisioned rows make them work as-is
- [ ] **No changes needed** to `ApprovalService`, `repository_routes.py`, or any approval endpoint logic
- [ ] Remove `organization_routes.py` (org create/invite/plan endpoints — now managed by AgentStudio)
- [ ] Remove `auth.py` (login, register, refresh endpoints)
- [ ] Remove `users`, `organization_users`, `organization_invitations` models and drop migrations (after migration in §13.2)
- [ ] Add `AGENTSTUDIO_JWT_SECRET` to Azure Container App settings
- [ ] Test: first request with new org UUID → org shadow row, user shadow row, and `OrganizationUser` row all created
- [ ] Test: plan upgrade in AgentStudio → next request updates `max_documents` in DemystRAG org row
- [ ] Test: `QuotaChecker.check_document_quota()` still blocks correctly using synced limits
- [ ] Test: `org_owner` token → `org_admin` in `OrganizationUser` → can delete collections, can approve documents
- [ ] Test: `team_lead` token → `org_admin` in `OrganizationUser` → can approve/reject documents ✓
- [ ] Test: `developer` token → `org_creator` in `OrganizationUser` → can upload and submit for approval, cannot approve (403)
- [ ] Test: `viewer` token → `org_viewer` in `OrganizationUser` → can query only, cannot upload (403), cannot approve (403)
- [ ] Test: `team_lead` promoted from `developer` in AgentStudio → after token refresh, `OrganizationUser.role` updates to `org_admin` → can now approve documents
- [ ] Test: `has_demystrag: false` → 403 regardless of role
- [ ] Test: expired token → 401; tampered token → 401
- [ ] Test: `is_platform_admin: true` → tier `admin`, bypasses product check, `OrganizationUser.role = org_admin`

### Mock API Backend

- [ ] Create `app/core/agentstudio_auth.py` (set `REQUIRED_PRODUCT = "mock_api"`, use async SQLAlchemy session; replace `organizations` with `tenants` in UPSERT)
- [ ] Replace `get_tenant_context` / `require_tenant_context` dependencies with `agentstudio_auth.get_current_user`
- [ ] Replace `require_role([UserRole.TENANT_ADMIN])` with `require_tier("admin")`
- [ ] Platform admin `X-Tenant-ID` header → replace with `is_platform_admin` JWT claim
- [ ] Remove `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me`
- [ ] Remove `/api/v1/admin/tenants` create/update/delete endpoints (keep GET for platform admin visibility)
- [ ] Remove `OAuthUser` model and table (the users who log into Mock API admin — not the simulated OAuth clients)
- [ ] Remove `oauth_service.validate_token` DB-lookup auth path; `oauth_clients` and token simulation tables are kept (they are domain data, not admin auth)
- [ ] Add `AGENTSTUDIO_JWT_SECRET` to Azure Container App settings
- [ ] Test: first request with new org UUID → `tenants` shadow row created
- [ ] Test: `developer` token can create/edit own projects (contributor tier)
- [ ] Test: `viewer` token is read-only (reader tier)
- [ ] Test: `has_mock_api: false` → 403
- [ ] Test: `is_platform_admin: true` → full access, correct tenant scoping

### AgentStudio Frontend

- [ ] Decode `products` from JWT on login and store in auth state
- [ ] Show/hide DemystRAG and Mock API navigation items based on `products`
- [ ] Show "upgrade plan" prompt when user tries to access a locked product
- [ ] Implement token sharing strategy (Option B — URL fragment, or Option C — shared cookie)
- [ ] Handle 403 from sub-apps with user-friendly upgrade message

### DemystRAG Frontend

- [ ] Remove login/registration pages
- [ ] On app load: read token from localStorage / URL fragment / cookie
- [ ] If no token found: redirect to AgentStudio login at `https://agentstudio365.com/login?redirect=demystrag`
- [ ] On 401 from API: call AgentStudio `/auth/refresh`, retry, or redirect to login if refresh fails

### Mock API Frontend

- [ ] Same checklist as DemystRAG Frontend

### Infrastructure

- [ ] Azure Key Vault: share `SECRET_KEY` reference with DemystRAG and Mock API Container Apps as `AGENTSTUDIO_JWT_SECRET`
- [ ] CORS: update allowed origins in all three backends

---

## 16. Cost & Risk Assessment

### 15.1 Development Effort

| Component | Estimated Effort |
|-----------|-----------------|
| AgentStudio backend (JWT enrichment) | 0.5 days |
| AgentStudio frontend (navigation, token sharing) | 1 day |
| DemystRAG backend integration | 2 days |
| DemystRAG frontend login removal + redirect | 1 day |
| Mock API backend integration | 1.5 days |
| Mock API frontend login removal + redirect | 0.5 days |
| Data migration scripts | 1 day |
| Testing (all three apps) | 2 days |
| **Total** | **~9.5 days** |

### 15.2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Existing DemystRAG users lose access during migration | Medium | High | Phase 2 keeps old endpoints until migration confirmed; email users in advance |
| Token refresh loop if sub-apps and AgentStudio have different token expiry expectations | Low | Medium | Standardise on 30-min access, 7-day refresh across all apps |
| Shared secret leaked via any one app's environment | Low | Critical | Key Vault only; never in code; quarterly rotation |
| Platform admin claim abused if token stolen | Very Low | Critical | Short token lifetime; MFA for admin accounts (future) |
| Plan downgrade causes delayed access loss (30-min window) | High | Low | Acceptable; document the lag to customers |

### 15.3 Business Value

| Metric | Before | After |
|--------|--------|-------|
| User accounts per person (using all 3 apps) | 3 | 1 |
| Login actions per work session | 3 | 1 |
| Password reset complexity | Per-app | Single |
| Time to unlock DemystRAG after plan upgrade | Manual account creation | Automatic within 30 min |
| Platform admin login actions | 3 | 1 |
| Upsell funnel friction | High (new account required) | Low (one click to upgrade plan) |

---

*Document maintained in: `aidemystagent/docs/UNIFIED_AUTH_ARCHITECTURE.md`*  
*Related plans: `documentation/RBAC_DESIGN.md`, `documentation/MULTI_TENANT_ARCHITECTURE.md`*
