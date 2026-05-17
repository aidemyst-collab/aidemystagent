# AgentStudio — RBAC & Onboarding Design

> **Status:** Decisions locked — ready for implementation
> **Authors:** Product Owner + Tech Lead
> **Replaces:** `ROLES.md` (to be archived once implementation is complete)
> **Decisions locked:** 2026-05-17

---

## 1. The Two Planes — Core Concept

The most important design principle is a hard separation between two planes of operation. These planes must never bleed into each other.

```
╔══════════════════════════════════════╗   ╔══════════════════════════════════════╗
║          PLATFORM PLANE              ║   ║         ORGANISATION PLANE           ║
║                                      ║   ║                                      ║
║  Platform Admin                      ║   ║  Org Owner                           ║
║    │ manages                         ║   ║    │ manages                         ║
║    ▼                                 ║   ║    ▼                                 ║
║  All Orgs & Users (cross-org)        ║   ║  Org Admins, Team Leads,             ║
║  Org approval queue                  ║   ║  Developers, Operators, Viewers      ║
║  Platform audit log                  ║   ║  (own org only)                      ║
║                                      ║   ║                                      ║
║  ✗ CANNOT touch agents/tools/        ║   ║  ✗ CANNOT touch other orgs           ║
║    deployments/credentials           ║   ║                                      ║
╚══════════════════════════════════════╝   ╚══════════════════════════════════════╝
```

**Rule:** Platform Admin manages accounts. Org roles manage AI work. No role spans both planes.

---

## 2. Role Hierarchy Overview

| Level | Role | Plane | Scope | Assigned By |
|-------|------|-------|-------|-------------|
| 0 | **Platform Admin** | Platform | All orgs | Another Platform Admin |
| 1 | **Org Owner** | Organisation | One org | Auto (first user) or Org Owner |
| 2 | **Org Admin** | Organisation | One org | Org Owner |
| 3 | **Team Lead** | Organisation | One org | Org Owner / Org Admin |
| 4 | **Developer** | Organisation | One org | Org Owner / Org Admin |
| 5 | **Operator** | Organisation | One org | Org Owner / Org Admin |
| 6 | **Viewer** | Organisation | One org | Org Owner / Org Admin |

> **Migration note:** The previous `agent_admin` role is renamed to `team_lead`. Existing users with `agent_admin` are migrated automatically — see [Section 9 — Gaps](#9-gaps-in-current-implementation) item G8.

> **One role per user:** Each user holds exactly one org-level role. If a user needs broader access, they are promoted to a higher role. Multiple roles are not permitted.

---

## 3. Role Definitions

### 3.1 Platform Admin

> Manages the platform itself — not a member of any organisation.

**Identity in the system:** `User.is_platform_admin = true` flag (not an RBAC role)

**What they can do:**

| Area | Actions |
|------|---------|
| **Organisations** | View all orgs with full detail (name, owner, status, user count, created date) |
| | Approve pending orgs (org becomes active, owner notified by email) |
| | Reject pending orgs (org owner notified with reason) |
| | Suspend active orgs (all users lose access immediately) |
| | Reactivate suspended orgs |
| | Create an org manually (for enterprise onboarding) |
| **Users (cross-org)** | Search any user by email across all orgs |
| | View any user's full profile and role assignments |
| | **Update any user's full name, avatar** |
| | **Update any user's email address** (triggers re-verification email, audit logged) |
| | Deactivate / reactivate any user in any org |
| | Unlock any locked account |
| | Assign or remove org-level roles for users in any org |
| | Promote a user to Platform Admin |
| | Revoke Platform Admin status from another admin |
| **Impersonation** | Start a 30-minute read-access troubleshooting session as any non-admin user |
| | Every session start/end is recorded in the platform audit log |
| **Platform** | View the platform-wide audit log |
| | Access system health / usage stats |

**What they cannot do:**

- Create, view, edit, or run agents / tools / deployments / credentials
- Access any org's AI content
- Delete an org that has active users (must deactivate all users first)
- Impersonate another Platform Admin
- Start an impersonation session while already in one
- Destructive or sensitive operations are blocked by the API during any impersonation session

**UI Experience:**

Platform Admin logs in → sees **"Platform Administration"** section only in the sidebar (no org nav). Sidebar contains:
- `Organizations` — full list with status badges and approval queue
- `Users` — all users across all orgs, searchable by email
- `Audit Log` — platform-wide event log

---

### 3.2 Org Owner

> Full control of one organisation including billing and deletion.

**Identity in the system:** RBAC role `org_owner`

**Auto-assigned to:** The first user who registers under an org (after platform admin approval)

**What they can do:**

| Area | Actions |
|------|---------|
| **Org Settings** | View and update org name, logo, description |
| | View and manage billing / subscription |
| | Delete the organisation (with confirmation) |
| **Users** | Invite new team members via email |
| | **Update any org member's full name and avatar** |
| | Assign or remove any role up to and including Org Owner |
| | Promote any member to Org Owner |
| | Demote any Org Owner (at least one owner must remain) |
| | Transfer ownership to another member |
| | Deactivate / reactivate / unlock any user |
| | Remove a user from the org |
| **AI Work** | Full access — create, edit, delete, deploy, execute all agents, tools, credentials |
| **Analytics** | View all org analytics and audit logs |

**What they cannot do:**

- Change any user's email address (Platform Admin only)
- Access other organisations
- Assign Platform Admin status

---

### 3.3 Org Admin

> Delegated administrator — everything the Org Owner can do except billing and org deletion.

**Identity in the system:** RBAC role `org_admin`

**Assigned by:** Org Owner

**What they can do:**

| Area | Actions |
|------|---------|
| **Org Settings** | View and update org name, logo, description (not billing) |
| **Users** | Invite new team members via email |
| | **Update any org member's full name and avatar — except Org Owners** |
| | Assign or remove roles up to and including Org Admin (cannot assign Org Owner) |
| | Deactivate / reactivate / unlock any non-owner user |
| | Remove any non-owner user from the org |
| **AI Work** | Full access — create, edit, delete, deploy, execute all agents, tools, credentials |
| **Analytics** | View all org analytics and audit logs |

**What they cannot do:**

- View or manage billing
- Delete the organisation
- Assign Org Owner role
- Update Org Owner's profile details
- Change any user's email address
- Access other organisations

---

### 3.4 Team Lead

> Senior technical role — full access to all AI work but no people management or org admin responsibilities.

**Identity in the system:** RBAC role `team_lead` (renamed from legacy `agent_admin`)

**Assigned by:** Org Owner / Org Admin

**What they can do:**

| Area | Actions |
|------|---------|
| **Agents** | Create new agents |
| | View all agents in the org |
| | Edit and delete **any** agent (including other developers') |
| | Execute any agent |
| **Tools** | Create new tools |
| | View all tools in the org |
| | Edit and delete **any** tool |
| **Credentials** | Create, view, and delete credentials |
| **Deployments** | View all deployments |
| | Deploy to any environment including production |
| | Start, stop, restart any deployment |
| | Delete any deployment |
| **Analytics** | View all org analytics and audit logs |

**What they cannot do:**

- Manage users, roles, or invitations
- Update other users' profile details
- View or manage billing
- Modify org name, logo, or settings
- Delete the organisation
- Access other organisations

**Key distinction from Org Admin:** Team Lead has identical AI work permissions but cannot manage people or org settings. It is a pure technical lead role.

---

### 3.5 Developer

> Creates and maintains AI agents and tools. Can only edit their own work.

**Identity in the system:** RBAC role `developer`

**Assigned by:** Org Owner / Org Admin

**What they can do:**

| Area | Actions |
|------|---------|
| **Agents** | Create new agents |
| | View all agents in the org |
| | Edit and delete **own** agents only |
| | Execute any agent (test/run) |
| **Tools** | Create new tools |
| | View all tools in the org |
| | Edit and delete **own** tools only |
| **Credentials** | Create and view credentials |
| **Deployments** | View all deployments |
| | Deploy to **non-production** environments only |
| **Analytics** | View analytics |

**What they cannot do:**

- Edit or delete another developer's agents or tools
- Deploy to production
- Manage users, org settings, or billing
- Access other orgs

---

### 3.6 Operator

> Runs and monitors live agent deployments. Cannot build or modify agents.

**Identity in the system:** RBAC role `operator`

**Assigned by:** Org Owner / Org Admin

**What they can do:**

| Area | Actions |
|------|---------|
| **Agents** | View all agents and tools (read-only) |
| | Execute any agent |
| **Deployments** | Deploy to any environment (including production) |
| | Start, stop, restart deployments |
| | Monitor deployment health and execution logs |
| **Analytics** | View analytics |

**What they cannot do:**

- Create, edit, or delete agents or tools
- Manage credentials
- Manage users or org settings

---

### 3.7 Viewer

> Read-only visibility. Safe for stakeholders, clients, and auditors. Cannot trigger any action.

**Identity in the system:** RBAC role `viewer`

**Assigned by:** Org Owner / Org Admin

**What they can do:**

| Area | Actions |
|------|---------|
| **Everything** | View agents, tools, deployments, analytics (read-only) |

**What they cannot do:**

- Create, edit, or delete anything
- Execute or run agents (including playground/test mode)
- Manage deployments
- Manage users or settings

> **Decision locked:** Viewer is strictly read-only. No execution capability of any kind.

---

## 4. User Profile Update — Detailed Rules

This is a new capability. Currently no endpoint exists to update another user's profile (`PATCH /users/{id}`). The rules below define what must be built.

### 4.1 What "update profile" means

| Field | Editable by self | Editable by Org Admin/Owner | Editable by Platform Admin |
|-------|:---:|:---:|:---:|
| Full name | ✅ | ✅ | ✅ |
| Avatar URL | ✅ | ✅ | ✅ |
| Email address | ✅ (triggers re-verify) | ❌ | ✅ (triggers re-verify + audit log) |
| Password | ✅ (own password change flow) | ❌ | ❌ (use password reset flow) |
| Role assignments | ❌ | ✅ (within limits) | ✅ (all roles) |
| is_platform_admin | ❌ | ❌ | ✅ (Platform Admin only) |

### 4.2 Who can update whose profile

| Editor → | Platform Admin | Org Owner | Org Admin | Team Lead | Developer / Operator / Viewer |
|----------|:-:|:-:|:-:|:-:|:-:|
| Update own profile | ✅ | ✅ | ✅ | ✅ | ✅ |
| Update any user in any org | ✅ | ❌ | ❌ | ❌ | ❌ |
| Update Org Owner's profile (own org) | ✅ | ✅ (themselves) | ❌ | ❌ | ❌ |
| Update Org Admin's profile (own org) | ✅ | ✅ | ✅ | ❌ | ❌ |
| Update Team Lead / Developer / Operator / Viewer (own org) | ✅ | ✅ | ✅ | ❌ | ❌ |
| Change anyone's email | ✅ | ❌ | ❌ | ❌ | ❌ |

### 4.3 Audit requirements

Every profile update made by someone other than the user themselves must be recorded:
- **Who** made the change (editor's user ID and name)
- **Whose** profile was changed
- **What** fields were changed (before → after)
- **When** (UTC timestamp)
- **Platform Admin changes** also appear in the platform-wide audit log

---

## 5. Role Assignment Rules — Who Can Assign Whom

A role can only assign roles **strictly below its own level** in the hierarchy. No self-promotion. No lateral assignment.

| Assigner → | Platform Admin | Org Owner | Org Admin | Team Lead | Developer | Operator | Viewer |
|------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Platform Admin** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Org Owner** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Org Admin** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Team Lead** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Developer** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Operator** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Viewer** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Rules enforced by the system:**
- The Org Owner role is shown in the assignment UI only for Org Owners and Platform Admins
- Org Admin cannot assign Org Owner (the option is hidden + blocked at API level)
- Team Lead has no role assignment capability at all
- Assigning Platform Admin is only possible from the Platform Admin panel, not from any org-level UI
- Each user holds exactly one org role — assigning a new role replaces the existing one
- Duplicate role assignments are rejected with a clear error

---

## 6. Onboarding Flows

### 6.1 New Organisation Registration

```
User visits /register
    │
    ▼
Fills in: Full Name, Email, Organisation Name, Password
    │
    ▼
System creates:
  - User account (status: active, email_verified: false)
  - Organisation (org_status: PENDING)
  - Assigns user as org_owner automatically
    │
    ▼
User sees: "Your organisation '[Name]' is pending platform admin approval.
            You'll receive an email when it's activated."
    │
    ▼
Platform Admin logs into admin panel
    │
    ├── Approves → org_status: ACTIVE
    │              Org Owner receives: "Your organisation has been approved" email
    │              Org Owner can now log in and use the platform
    │
    └── Rejects → org_status: REJECTED
                  Org Owner receives: "Your organisation was not approved" email with reason
```

**The "Join Existing Organisation" option on the registration form is removed.** Joining an existing org happens exclusively via invitation email.

---

### 6.2 Pending Approval State (Org Owner UX)

When an Org Owner logs in before their org is approved:
- They are **not** redirected to the dashboard
- They see a full-screen **"Pending Approval"** page:
  ```
  ⏳  Your organisation "[OrgName]" is awaiting approval.

  A platform administrator will review your registration.
  You will receive an email at [email] once your account is activated.

  Questions? Contact support@aidemyst.com
  ```
- They cannot access any org features until approved

---

### 6.3 Inviting Team Members (within an approved org)

```
Org Owner / Org Admin opens Team Settings → "Invite Member"
    │
    ▼
Enters: Email address, selects Role (Org Admin / Team Lead / Developer / Operator / Viewer)
    │
    ▼
System creates: Invitation record (status: PENDING, expires in 7 days)
                Unique invitation token generated
    │
    ▼
Azure Communication Services sends email:
  Subject: "You've been invited to join [OrgName] on AgentStudio"
  Body: Inviter's name, org name, role being offered, [Accept Invitation] button
    │
    ▼
Invitee clicks link → /invitations/accept/[token]
    │
    ▼
Page shows: "You've been invited to join [OrgName] as [Role Name]"
            Form: Full Name, Password, Confirm Password
    │
    ▼
On submit:
  - User account created with exactly one role (the invited role)
  - Automatically joined to org with assigned role
  - No platform admin approval needed (org is already approved)
  - Redirected to login → then dashboard
```

**Email is sent by Azure Communication Services (ACS)** — not a third-party SMTP library.

**Invited users bypass the org approval gate** — they join an already-approved org directly.

---

### 6.4 Platform Admin Provisioning

```
First Platform Admin:
  - Created via database seed (migration 006 or env-var seeding)
  - Login: email + password set in environment variables
  - No self-service Platform Admin registration

Subsequent Platform Admins:
  - Existing Platform Admin opens Platform Admin panel → Users
  - Searches for the user by email
  - Clicks "Promote to Platform Admin"
  - Confirmation dialog: "This gives [name] full platform-wide access. Confirm?"
  - Action is audit-logged
```

---

## 7. Complete Capability Matrix (Target State)

### Platform Management (Platform Admin only)

| Capability | Plat. Admin | Org Owner | Org Admin | Team Lead | Developer | Operator | Viewer |
|------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| View all organisations | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Approve / reject orgs | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Suspend / reactivate orgs | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Create org manually | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| View platform audit log | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Promote / revoke Platform Admin | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### User Management

| Capability | Plat. Admin | Org Owner | Org Admin | Team Lead | Developer | Operator | Viewer |
|------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Update own profile | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Update any user profile (any org) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Update org user profile (name/avatar) | — | ✅ all | ✅ excl. owners | ❌ | ❌ | ❌ | ❌ |
| Change any user's email | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Invite team members | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign / remove roles | ✅ all | ✅ ≤ Owner | ✅ ≤ Admin | ❌ | ❌ | ❌ | ❌ |
| Deactivate / reactivate users | ✅ any | ✅ own org | ✅ excl. owners | ❌ | ❌ | ❌ | ❌ |
| Unlock locked accounts | ✅ any | ✅ own org | ✅ own org | ❌ | ❌ | ❌ | ❌ |
| Remove user from org | ✅ | ✅ | ✅ excl. owners | ❌ | ❌ | ❌ | ❌ |

### Organisation Settings

| Capability | Plat. Admin | Org Owner | Org Admin | Team Lead | Developer | Operator | Viewer |
|------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| View org details | ❌ (list only) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Update org name/logo/description | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| View & manage billing | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Delete organisation | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Transfer ownership | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Agents

| Capability | Plat. Admin | Org Owner | Org Admin | Team Lead | Developer | Operator | Viewer |
|------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| View all agents | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create agents | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Edit / delete **any** agent | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit / delete **own** agent | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Execute / test agents | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### Tools & Credentials

| Capability | Plat. Admin | Org Owner | Org Admin | Team Lead | Developer | Operator | Viewer |
|------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| View all tools | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create tools | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Edit / delete **any** tool | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit / delete **own** tool | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Create / view credentials | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Delete credentials | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### Deployments

| Capability | Plat. Admin | Org Owner | Org Admin | Team Lead | Developer | Operator | Viewer |
|------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| View all deployments | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Deploy to non-production | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Deploy to production | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Start / stop / restart | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Delete deployment | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |

### Analytics & Audit

| Capability | Plat. Admin | Org Owner | Org Admin | Team Lead | Developer | Operator | Viewer |
|------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| View org analytics | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Export analytics | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| View org audit log | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| View platform audit log | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 8. Decisions — Locked

| # | Decision | Resolution |
|---|----------|------------|
| **1** | What to do with `agent_admin` role? | **Renamed to `team_lead`** — existing users migrated, DB value updated |
| **2** | Should Viewer be able to execute agents? | **No** — Viewer is strictly read-only; no execution of any kind |
| **3** | Multiple roles per user: allow or restrict? | **One role per user** — assigning a new role replaces the existing one |

---

## 9. Gaps in Current Implementation

These are gaps between the design above and what is currently built.

| # | Gap | Priority | Notes |
|---|-----|----------|-------|
| **G1** | `PATCH /users/{id}` endpoint does not exist — only `/me` | **P0** | Blocks Platform Admin and Org Owner/Admin from updating user profiles |
| **G2** | No org approval gate — orgs go live immediately on registration | **P0** | New registrations must create org in `PENDING` state |
| **G3** | Registration form has confusing "Join Existing Org" option | **P0** | Remove this — joining via invitation is the correct flow |
| **G4** | Platform Admin has no dedicated sidebar section | **P0** | They currently share the same nav as org users |
| **G5** | Email invitations are not sent — ACS integration missing | **P1** | Invitation tokens exist in DB but no email delivery |
| **G6** | No `/invitations/accept/:token` page in the frontend | **P1** | Invitees have nowhere to land when they click the link |
| **G7** | Role assignment matrix not enforced — Org Admin can assign Org Owner | **P1** | Privilege escalation risk |
| **G8** | `agent_admin` role must be renamed to `team_lead` in DB + code | **P1** | DB migration: update `user_roles.role` enum value and existing rows |
| **G9** | Multi-role support must be removed — enforce one role per user | **P1** | Drop composite role logic; API must replace, not append |
| **G10** | No "pending approval" screen for users in pending orgs | **P1** | Users in pending orgs currently see a broken dashboard |
| **G11** | No platform audit log endpoint or UI | **P2** | Platform Admin needs cross-org audit visibility |
| **G12** | No "Promote to Platform Admin" UI — requires DB access | **P2** | Should be a button in the Platform Admin panel |
| **G13** | No org ownership transfer flow | **P2** | Org Owner offboarding has no safe path |

---

## 10. User Stories

### US-RBAC-01: Platform Admin Updates User Profile

| Field | Value |
|-------|-------|
| Points | 3 |
| Priority | P0 |
| Assignee | Backend + Frontend |

**As a** Platform Admin, **I want to** view and edit the profile details of any user on the platform, **so that** I can correct account information without requiring database access.

**Acceptance Criteria:**
1. Platform Admin can search for any user by email across all orgs from the admin panel
2. Platform Admin can update: full name, avatar URL of any user
3. Platform Admin can update email address — a confirmation dialog warns "This will require the user to verify their new email address" before saving
4. Every profile update made by Platform Admin is recorded in the platform audit log (editor, target user, fields changed, old → new values, timestamp)
5. The user whose profile was changed receives a notification email
6. The change is reflected immediately in the user's profile without page refresh

**Out of Scope:** Password reset on behalf of another user
**Dependencies:** Platform Admin sidebar section (G4)

---

### US-RBAC-02: Org Owner and Admin Update User Profile

| Field | Value |
|-------|-------|
| Points | 3 |
| Priority | P0 |
| Assignee | Backend + Frontend |

**As an** Org Owner or Org Admin, **I want to** edit the profile details of members in my organisation, **so that** I can correct names or avatars without asking each person to do it themselves.

**Acceptance Criteria:**
1. Org Owner can update full name and avatar of any user in their org, including other Org Owners
2. Org Admin can update full name and avatar of any user **except** Org Owners
3. Neither Org Owner nor Org Admin can change another user's email address — the email field is greyed out with tooltip "Email changes can only be made by a Platform Admin"
4. Every update is recorded in the org audit log (who changed what, for whom)
5. The change is visible in the team member list without page refresh

**Out of Scope:** Role changes (separate action), email changes
**Dependencies:** US-RBAC-01 (shares the same backend endpoint with different permission scope)

---

### US-RBAC-03: Org Approval Gate

| Field | Value |
|-------|-------|
| Points | 5 |
| Priority | P0 |
| Assignee | Backend + Frontend |

**As a** Platform Admin, **I want** new organisations to require my approval before going live, **so that** I can control which accounts get access to the platform.

**Acceptance Criteria:**
1. When a new user registers with a new org name, the org is created in `PENDING` status
2. The registering user sees a "pending approval" page when they log in — not the dashboard
3. Platform Admin sees a list of pending orgs with: org name, owner name, owner email, registration date
4. Platform Admin can approve an org — the org status becomes `ACTIVE` and the owner receives an email notification
5. Platform Admin can reject an org with a required reason — the org status becomes `REJECTED` and the owner is notified by email with the reason
6. Once approved, the org owner is redirected to the dashboard on next login
7. Existing orgs are not affected by this change (they remain active)

**Out of Scope:** Automatic approval rules, trial period configuration
**Dependencies:** Platform Admin sidebar (G4)

---

### US-RBAC-04: Simplify Registration Form

| Field | Value |
|-------|-------|
| Points | 2 |
| Priority | P0 |
| Assignee | Frontend |

**As a** new user, **I want** a simple, clear registration form, **so that** I can sign up without confusion about org IDs or join modes.

**Acceptance Criteria:**
1. The registration form has exactly 4 fields: Full Name, Email, Organisation Name, Password
2. The "Join Existing Organisation" option and org ID field are removed entirely
3. After successful registration, the user sees a confirmation screen (not the dashboard): "Your account is pending approval. We'll email you at [email] once activated."
4. The login page shows a clear message for users with pending orgs: "Your organisation is awaiting approval"

**Out of Scope:** SSO / social login
**Dependencies:** US-RBAC-03 (approval gate must exist)

---

### US-RBAC-05: Email Invitation via ACS

| Field | Value |
|-------|-------|
| Points | 5 |
| Priority | P1 |
| Assignee | Backend + Frontend |

**As an** Org Owner or Org Admin, **I want to** invite team members by email, **so that** they can join my org with the correct role without needing platform admin intervention.

**Acceptance Criteria:**
1. Org Owner/Admin opens Team Settings → "Invite Member" → enters email + selects role → clicks "Send Invitation"
2. The system sends an invitation email via Azure Communication Services with an "Accept Invitation" button
3. The email displays: inviter's name, organisation name, role being offered, expiry date (7 days)
4. Invitee clicks the link → lands on `/invitations/accept/[token]` page showing org name, role, and a form (Full Name, Password)
5. On successful acceptance, the user is created with exactly one role and joins the org — no platform admin approval required
6. The invitation shows as "Accepted" in the Pending Invitations list
7. If the token is expired, the page shows a clear error: "This invitation has expired. Ask [org name] to send a new one."
8. Org Owner/Admin can resend or revoke any pending invitation from the team settings page

**Out of Scope:** Bulk invitations, inviting users already in another org
**Dependencies:** ACS email service configured, `/invitations/accept/:token` frontend page

---

### US-RBAC-06: Role Assignment Enforcement

| Field | Value |
|-------|-------|
| Points | 2 |
| Priority | P1 |
| Assignee | Backend |

**As an** Org Admin, **I want** the system to prevent me from assigning roles higher than my own, **so that** privilege escalation is impossible.

**Acceptance Criteria:**
1. The role selection dropdown when assigning a role only shows roles the assigner is permitted to assign
2. Org Admin does not see the Org Owner option in the role dropdown
3. Any API call that attempts to assign a role above the caller's level returns a clear error: "You cannot assign a role equal to or higher than your own"
4. Platform Admin can assign any role including Org Owner from the platform admin panel
5. Assigning a role to a user who already has a role replaces the existing role (no multi-role stacking)

**Out of Scope:** Custom role creation
**Dependencies:** None

---

### US-RBAC-07: Rename `agent_admin` → `team_lead` and Enforce One Role

| Field | Value |
|-------|-------|
| Points | 3 |
| Priority | P1 |
| Assignee | Backend + DB Migration |

**As a** Platform Admin, **I want** every user to have a single, consistent role definition, **so that** there is no confusion between old and new role names or multi-role assignments.

**Acceptance Criteria:**
1. All existing users with role `agent_admin` are migrated to `team_lead`
2. All existing users with `ADMIN` role are migrated to `org_owner` (first user in org) or `org_admin` (others)
3. All existing users with `CREATOR` role are migrated to `developer`
4. All existing users with `VIEWER` role are migrated to `viewer`
5. All existing users with multiple roles are reduced to their highest role
6. New role assignments replace the existing role — no user can hold two org roles simultaneously
7. No user experiences any change in their actual permissions as a result of the migration

**Out of Scope:** Removing the legacy database column (done separately after validation)
**Dependencies:** Must run after all role assignments are confirmed complete

---

## 11. Implementation Order

| # | Task | Depends On | Risk | Effort |
|---|------|------------|------|--------|
| 1 | DB migration: `org_status` column on organisations | — | Low | 1h |
| 2 | Registration creates orgs in `PENDING` state | #1 | Low | 1h |
| 3 | `require_active_org` guard on all org endpoints | #1 | Medium | 2h |
| 4 | Platform Admin sidebar section + Orgs page | — | Low | 4h |
| 5 | Org approval / reject / suspend endpoints | #1, #4 | Low | 3h |
| 6 | Pending approval screen (post-login for pending orgs) | #1 | Low | 1h |
| 7 | Simplify registration form (remove "Join Org" mode) | #2 | Low | 2h |
| 8 | DB migration: rename `agent_admin` → `team_lead` + enforce one role per user | — | Medium | 2h |
| 9 | `PATCH /users/{id}` endpoint with permission matrix | — | Medium | 3h |
| 10 | Update user profile UI (Platform Admin + Org Owner/Admin) | #9 | Low | 3h |
| 11 | Role assignment enforcement (privilege escalation guard + one-role replace) | #8 | Medium | 2h |
| 12 | ACS email service integration | — | Medium | 3h |
| 13 | Send invitation email on invitation creation | #12 | Low | 1h |
| 14 | `/invitations/accept/:token` frontend page | — | Low | 2h |
| 15 | Platform audit log endpoint + UI | #4 | Low | 3h |
| 16 | "Promote to Platform Admin" UI in admin panel | #4 | Low | 1h |
| 17 | Org ownership transfer flow | — | Low | 2h |

**Milestone 1 (Steps 1–7):** Org approval gate + Platform Admin dashboard
**Milestone 2 (Steps 8–11):** Role normalisation + user profile management + one-role enforcement
**Milestone 3 (Steps 12–14):** Email invitations via ACS
**Milestone 4 (Steps 15–17):** Platform audit log, admin promotion UI, ownership transfer

---

## 12. Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Full access |
| ❌ | No access |
| **own** | Only resources created by the user |
| **non-prod** | Non-production environments only |
| **excl. owners** | All users except Org Owners |
| **≤ Owner / ≤ Admin** | Roles at or below that level |

---

*Last updated: 2026-05-17 | Decisions locked — implementation can begin*
