"""Multi-tenant foundation - new tables and updated columns

Revision ID: 005_multi_tenant
Revises: 004_add_database_credential_providers
Create Date: 2024-12-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === CREATE NEW TABLES ===

    # 1. Subscription Plans Table
    op.create_table(
        'subscription_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        # Quotas
        sa.Column('max_users', sa.Integer, default=5, nullable=False),
        sa.Column('max_agents', sa.Integer, default=10, nullable=False),
        sa.Column('max_deployments', sa.Integer, default=5, nullable=False),
        sa.Column('max_executions_per_month', sa.Integer, default=1000, nullable=False),
        sa.Column('max_tools', sa.Integer, default=20, nullable=False),
        sa.Column('max_credentials', sa.Integer, default=10, nullable=False),
        # Features
        sa.Column('features', postgresql.JSONB, default={}, nullable=False),
        # Pricing
        sa.Column('price_monthly_cents', sa.Integer, default=0),
        sa.Column('price_yearly_cents', sa.Integer, default=0),
        # Status
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_public', sa.Boolean, default=True, nullable=False),
        sa.Column('sort_order', sa.Integer, default=0),
        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Insert default subscription plans
    op.execute("""
        INSERT INTO subscription_plans (id, name, display_name, description, max_users, max_agents, max_deployments, max_executions_per_month, max_tools, max_credentials, features, price_monthly_cents, price_yearly_cents, is_active, is_public, sort_order)
        VALUES
            (gen_random_uuid(), 'free', 'Free', 'Free tier with limited features', 3, 5, 2, 500, 10, 5, '{"custom_tools": false, "api_access": true, "audit_logs": false}', 0, 0, true, true, 1),
            (gen_random_uuid(), 'starter', 'Starter', 'For small teams getting started', 10, 25, 10, 5000, 50, 20, '{"custom_tools": true, "api_access": true, "audit_logs": true}', 2900, 29000, true, true, 2),
            (gen_random_uuid(), 'professional', 'Professional', 'For growing businesses', 50, 100, 50, 50000, 200, 100, '{"custom_tools": true, "api_access": true, "audit_logs": true, "advanced_analytics": true}', 9900, 99000, true, true, 3),
            (gen_random_uuid(), 'enterprise', 'Enterprise', 'Unlimited with premium support', -1, -1, -1, -1, -1, -1, '{"custom_tools": true, "api_access": true, "audit_logs": true, "advanced_analytics": true, "sso": true, "priority_support": true}', 0, 0, true, true, 4)
    """)

    # 2. Update Organizations Table
    # Add new columns to organizations
    op.add_column('organizations', sa.Column('slug', sa.String(100), unique=True))
    op.add_column('organizations', sa.Column('description', sa.Text))
    op.add_column('organizations', sa.Column('logo_url', sa.String(500)))
    op.add_column('organizations', sa.Column('subscription_plan_id', postgresql.UUID(as_uuid=True)))
    op.add_column('organizations', sa.Column('subscription_status', sa.String(20), server_default='trial'))
    op.add_column('organizations', sa.Column('trial_ends_at', sa.DateTime))
    op.add_column('organizations', sa.Column('settings', postgresql.JSONB, server_default='{}'))
    op.add_column('organizations', sa.Column('is_active', sa.Boolean, server_default='true', nullable=False))
    op.add_column('organizations', sa.Column('deleted_at', sa.DateTime))
    op.add_column('organizations', sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()))

    # Create index for organizations slug
    op.create_index('idx_organizations_slug', 'organizations', ['slug'])

    # Add foreign key for subscription_plan_id
    op.create_foreign_key(
        'fk_organizations_subscription_plan',
        'organizations', 'subscription_plans',
        ['subscription_plan_id'], ['id']
    )

    # Set default subscription plan for existing organizations
    op.execute("""
        UPDATE organizations
        SET subscription_plan_id = (SELECT id FROM subscription_plans WHERE name = 'starter' LIMIT 1),
            subscription_status = 'active',
            slug = LOWER(REPLACE(REPLACE(name, ' ', '-'), '.', '')) || '-' || SUBSTRING(id::text, 1, 8)
        WHERE subscription_plan_id IS NULL
    """)

    # 3. Update Users Table
    op.add_column('users', sa.Column('full_name', sa.String(255)))
    op.add_column('users', sa.Column('avatar_url', sa.String(500)))
    op.add_column('users', sa.Column('is_platform_admin', sa.Boolean, server_default='false', nullable=False))
    op.add_column('users', sa.Column('is_active', sa.Boolean, server_default='true', nullable=False))
    op.add_column('users', sa.Column('email_verified', sa.Boolean, server_default='false', nullable=False))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer, server_default='0', nullable=False))
    op.add_column('users', sa.Column('locked_until', sa.DateTime))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime))
    op.add_column('users', sa.Column('last_login_ip', sa.String(45)))
    op.add_column('users', sa.Column('metadata', postgresql.JSONB, server_default='{}'))
    op.add_column('users', sa.Column('deleted_at', sa.DateTime))
    op.add_column('users', sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()))

    # Create index for platform admins
    op.create_index('idx_users_platform_admin', 'users', ['is_platform_admin'], postgresql_where=sa.text('is_platform_admin = true'))

    # 4. Roles Table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('scope', sa.String(20), nullable=False, server_default='organization'),
        sa.Column('permissions', postgresql.JSONB, default=[], nullable=False),
        sa.Column('is_system_role', sa.Boolean, default=False, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('name', 'organization_id', name='uq_role_name_org'),
    )

    # Insert system roles
    op.execute("""
        INSERT INTO roles (id, name, display_name, description, scope, permissions, is_system_role)
        VALUES
            (gen_random_uuid(), 'super_admin', 'Super Admin', 'Platform administrator with access to all organizations and system settings', 'platform', '["*"]', true),
            (gen_random_uuid(), 'org_owner', 'Organization Owner', 'Full organization control including billing and deletion', 'organization', '["org:*", "users:*", "agents:*", "tools:*", "credentials:*", "deployments:*", "analytics:*", "audit:read"]', true),
            (gen_random_uuid(), 'org_admin', 'Organization Admin', 'Organization management without billing access', 'organization', '["org:read", "org:update", "users:*", "agents:*", "tools:*", "credentials:*", "deployments:*", "analytics:*", "audit:read"]', true),
            (gen_random_uuid(), 'agent_admin', 'Agent Admin', 'Manage all agents regardless of creator', 'organization', '["org:read", "users:read", "agents:*", "tools:*", "credentials:read", "deployments:*", "analytics:read"]', true),
            (gen_random_uuid(), 'developer', 'Developer', 'Create and edit own agents and tools', 'organization', '["org:read", "users:read", "agents:create", "agents:read", "agents:update:own", "agents:delete:own", "agents:execute", "tools:create", "tools:read", "tools:update:own", "tools:delete:own", "credentials:create", "credentials:read", "deployments:read", "deployments:create:non_prod", "analytics:read"]', true),
            (gen_random_uuid(), 'operator', 'Operator', 'Execute and deploy agents', 'organization', '["org:read", "users:read", "agents:read", "agents:execute", "tools:read", "deployments:*", "analytics:read"]', true),
            (gen_random_uuid(), 'viewer', 'Viewer', 'Read-only access to organization resources', 'organization', '["org:read", "users:read", "agents:read", "tools:read", "deployments:read", "analytics:read"]', true)
    """)

    # 5. User Roles Table (Many-to-Many)
    op.create_table(
        'user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE')),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('assigned_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'role_id', 'organization_id', name='uq_user_role_org'),
    )
    op.create_index('idx_user_roles_user', 'user_roles', ['user_id'])
    op.create_index('idx_user_roles_org', 'user_roles', ['organization_id'])

    # Migrate existing user roles to new system
    # Cast enum to text for comparison since PostgreSQL enum values are case-sensitive
    op.execute("""
        INSERT INTO user_roles (id, user_id, role_id, organization_id, assigned_at)
        SELECT
            gen_random_uuid(),
            u.id,
            r.id,
            u.organization_id,
            CURRENT_TIMESTAMP
        FROM users u
        CROSS JOIN roles r
        WHERE r.is_system_role = true
          AND r.scope = 'organization'
          AND (
              (u.role::text = 'ADMIN' AND r.name = 'org_admin') OR
              (u.role::text = 'CREATOR' AND r.name = 'developer') OR
              (u.role::text = 'VIEWER' AND r.name = 'viewer')
          )
    """)

    # 6. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='SET NULL')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('user_email', sa.String(255)),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(100)),
        sa.Column('resource_name', sa.String(255)),
        sa.Column('old_values', postgresql.JSONB),
        sa.Column('new_values', postgresql.JSONB),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('user_agent', sa.Text),
        sa.Column('request_id', sa.String(100)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('status', sa.String(20), server_default='success'),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_audit_org_created', 'audit_logs', ['organization_id', 'created_at'])
    op.create_index('idx_audit_user_created', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_action_created', 'audit_logs', ['action', 'created_at'])

    # 7. Invitations Table
    op.create_table(
        'invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('token', sa.String(255), unique=True, nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('message', sa.String(500)),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('accepted_at', sa.DateTime),
        sa.Column('accepted_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_invitations_token', 'invitations', ['token'])
    op.create_index('idx_invitations_org_status', 'invitations', ['organization_id', 'status'])
    op.create_index('idx_invitations_email', 'invitations', ['email'])

    # 8. Organization Usage Table
    op.create_table(
        'organization_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_start', sa.Date, nullable=False),
        sa.Column('period_end', sa.Date, nullable=False),
        # Resource counts
        sa.Column('users_count', sa.Integer, server_default='0', nullable=False),
        sa.Column('agents_count', sa.Integer, server_default='0', nullable=False),
        sa.Column('deployments_count', sa.Integer, server_default='0', nullable=False),
        sa.Column('tools_count', sa.Integer, server_default='0', nullable=False),
        sa.Column('credentials_count', sa.Integer, server_default='0', nullable=False),
        # Usage metrics
        sa.Column('executions_count', sa.Integer, server_default='0', nullable=False),
        sa.Column('tokens_used', sa.BigInteger, server_default='0', nullable=False),
        sa.Column('api_calls_count', sa.Integer, server_default='0', nullable=False),
        # Cost tracking
        sa.Column('llm_cost_cents', sa.Integer, server_default='0', nullable=False),
        sa.Column('compute_cost_cents', sa.Integer, server_default='0', nullable=False),
        sa.Column('storage_cost_cents', sa.Integer, server_default='0', nullable=False),
        sa.Column('total_cost_cents', sa.Integer, server_default='0', nullable=False),
        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('organization_id', 'period_start', name='uq_org_usage_period'),
    )
    op.create_index('idx_org_usage_period', 'organization_usage', ['organization_id', 'period_start'])

    # 9. Update Agents Table
    op.add_column('agents', sa.Column('is_template', sa.Boolean, server_default='false', nullable=False))
    op.add_column('agents', sa.Column('is_public_template', sa.Boolean, server_default='false', nullable=False))
    op.add_column('agents', sa.Column('template_source_id', postgresql.UUID(as_uuid=True)))
    op.add_column('agents', sa.Column('tags', postgresql.JSONB, server_default='[]'))
    op.add_column('agents', sa.Column('metadata', postgresql.JSONB, server_default='{}'))
    op.add_column('agents', sa.Column('deleted_at', sa.DateTime))

    op.create_foreign_key(
        'fk_agents_template_source',
        'agents', 'agents',
        ['template_source_id'], ['id']
    )
    op.create_index('idx_agents_org_status', 'agents', ['organization_id', 'status'])
    op.create_index('idx_agents_templates', 'agents', ['is_template', 'is_public_template'])

    # 10. Update Deployments Table
    op.add_column('deployments', sa.Column('organization_id', postgresql.UUID(as_uuid=True)))
    op.add_column('deployments', sa.Column('metadata', postgresql.JSONB, server_default='{}'))
    op.add_column('deployments', sa.Column('deleted_at', sa.DateTime))

    # Populate organization_id from agent
    op.execute("""
        UPDATE deployments d
        SET organization_id = a.organization_id
        FROM agents a
        WHERE d.agent_id = a.id AND d.organization_id IS NULL
    """)

    op.create_foreign_key(
        'fk_deployments_organization',
        'deployments', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_deployments_org_env', 'deployments', ['organization_id', 'environment'])
    op.create_index('idx_deployments_agent_status', 'deployments', ['agent_id', 'status'])


def downgrade() -> None:
    # Remove indexes and constraints from deployments
    op.drop_index('idx_deployments_agent_status', 'deployments')
    op.drop_index('idx_deployments_org_env', 'deployments')
    op.drop_constraint('fk_deployments_organization', 'deployments', type_='foreignkey')
    op.drop_column('deployments', 'deleted_at')
    op.drop_column('deployments', 'metadata')
    op.drop_column('deployments', 'organization_id')

    # Remove indexes and constraints from agents
    op.drop_index('idx_agents_templates', 'agents')
    op.drop_index('idx_agents_org_status', 'agents')
    op.drop_constraint('fk_agents_template_source', 'agents', type_='foreignkey')
    op.drop_column('agents', 'deleted_at')
    op.drop_column('agents', 'metadata')
    op.drop_column('agents', 'tags')
    op.drop_column('agents', 'template_source_id')
    op.drop_column('agents', 'is_public_template')
    op.drop_column('agents', 'is_template')

    # Drop organization_usage
    op.drop_index('idx_org_usage_period', 'organization_usage')
    op.drop_table('organization_usage')

    # Drop invitations
    op.drop_index('idx_invitations_email', 'invitations')
    op.drop_index('idx_invitations_org_status', 'invitations')
    op.drop_index('idx_invitations_token', 'invitations')
    op.drop_table('invitations')

    # Drop audit_logs
    op.drop_index('idx_audit_action_created', 'audit_logs')
    op.drop_index('idx_audit_resource', 'audit_logs')
    op.drop_index('idx_audit_user_created', 'audit_logs')
    op.drop_index('idx_audit_org_created', 'audit_logs')
    op.drop_table('audit_logs')

    # Drop user_roles
    op.drop_index('idx_user_roles_org', 'user_roles')
    op.drop_index('idx_user_roles_user', 'user_roles')
    op.drop_table('user_roles')

    # Drop roles
    op.drop_table('roles')

    # Remove user columns
    op.drop_index('idx_users_platform_admin', 'users')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'metadata')
    op.drop_column('users', 'last_login_ip')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'is_platform_admin')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'full_name')

    # Remove organization columns
    op.drop_constraint('fk_organizations_subscription_plan', 'organizations', type_='foreignkey')
    op.drop_index('idx_organizations_slug', 'organizations')
    op.drop_column('organizations', 'updated_at')
    op.drop_column('organizations', 'deleted_at')
    op.drop_column('organizations', 'is_active')
    op.drop_column('organizations', 'settings')
    op.drop_column('organizations', 'trial_ends_at')
    op.drop_column('organizations', 'subscription_status')
    op.drop_column('organizations', 'subscription_plan_id')
    op.drop_column('organizations', 'logo_url')
    op.drop_column('organizations', 'description')
    op.drop_column('organizations', 'slug')

    # Drop subscription_plans
    op.drop_table('subscription_plans')
