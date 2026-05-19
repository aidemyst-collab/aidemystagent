"""add billing tables and seed subscription plans

Creates org_subscriptions and stripe_webhook_events tables.
Seeds subscription_plans rows (free/starter/professional/enterprise)
with the has_demystrag, has_mock_api feature flags and AED pricing.

Revision ID: 018
Revises: 017
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import json

revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    # ── org_subscriptions ────────────────────────────────────────────────────
    op.create_table(
        'org_subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('stripe_customer_id', sa.String(100), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(100), nullable=True),
        sa.Column('stripe_price_id', sa.String(100), nullable=True),
        sa.Column('plan', sa.String(50), nullable=False, server_default='free'),
        sa.Column('status', sa.String(50), nullable=False, server_default='trialing'),
        sa.Column('current_period_start', sa.DateTime, nullable=True),
        sa.Column('current_period_end', sa.DateTime, nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('canceled_at', sa.DateTime, nullable=True),
        sa.Column('trial_end', sa.DateTime, nullable=True),
        sa.Column('payment_failure_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_org_subscriptions_organization_id', 'org_subscriptions', ['organization_id'])
    op.create_index('ix_org_subscriptions_stripe_customer_id', 'org_subscriptions', ['stripe_customer_id'])
    op.create_index('ix_org_subscriptions_stripe_subscription_id', 'org_subscriptions', ['stripe_subscription_id'])

    # ── stripe_webhook_events ────────────────────────────────────────────────
    op.create_table(
        'stripe_webhook_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('stripe_event_id', sa.String(100), nullable=False, unique=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', sa.Text, nullable=False),
        sa.Column('processed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('processed_at', sa.DateTime, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('received_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_stripe_webhook_events_stripe_event_id', 'stripe_webhook_events', ['stripe_event_id'], unique=True)

    # ── Seed / upsert subscription_plans ────────────────────────────────────
    conn = op.get_bind()

    plans = [
        {
            'name': 'free',
            'display_name': 'Free',
            'description': 'Build your first AI agent with no time limit.',
            'max_users': 1,
            'max_agents': 3,
            'max_deployments': 1,
            'max_executions_per_month': 200,
            'max_tools': 5,
            'max_credentials': 3,
            'price_monthly_cents': 0,
            'price_yearly_cents': 0,
            'sort_order': 0,
            'features': {
                'has_demystrag': False,
                'has_mock_api': False,
                'demystrag_max_documents': 0,
                'demystrag_max_storage_mb': 0,
                'demystrag_max_collections': 0,
                'demystrag_embedding_providers': [],
                'custom_tools': False,
                'api_access': False,
                'advanced_analytics': False,
                'audit_logs': False,
                'sso': False,
                'priority_support': False,
                'custom_branding': False,
            },
        },
        {
            'name': 'starter',
            'display_name': 'Starter',
            'description': 'For small teams that need to deploy real agents.',
            'max_users': 5,
            'max_agents': 15,
            'max_deployments': 5,
            'max_executions_per_month': 2000,
            'max_tools': 50,
            'max_credentials': 20,
            'price_monthly_cents': 14900,
            'price_yearly_cents': 149000,
            'sort_order': 1,
            'features': {
                'has_demystrag': False,
                'has_mock_api': False,
                'demystrag_max_documents': 0,
                'demystrag_max_storage_mb': 0,
                'demystrag_max_collections': 0,
                'demystrag_embedding_providers': [],
                'custom_tools': True,
                'api_access': True,
                'advanced_analytics': False,
                'audit_logs': False,
                'sso': False,
                'priority_support': False,
                'custom_branding': False,
            },
        },
        {
            'name': 'professional',
            'display_name': 'Professional',
            'description': 'For teams building production-grade RAG agents and testing pipelines.',
            'max_users': 20,
            'max_agents': 50,
            'max_deployments': 20,
            'max_executions_per_month': 10000,
            'max_tools': 200,
            'max_credentials': 100,
            'price_monthly_cents': 44900,
            'price_yearly_cents': 449000,
            'sort_order': 2,
            'features': {
                'has_demystrag': True,
                'has_mock_api': True,
                'demystrag_max_documents': 2000,
                'demystrag_max_storage_mb': 20480,
                'demystrag_max_collections': 20,
                'demystrag_embedding_providers': ['openai'],
                'custom_tools': True,
                'api_access': True,
                'advanced_analytics': True,
                'audit_logs': True,
                'sso': False,
                'priority_support': True,
                'custom_branding': False,
            },
        },
        {
            'name': 'enterprise',
            'display_name': 'Enterprise',
            'description': 'Unlimited scale for organisations running AI across departments.',
            'max_users': -1,
            'max_agents': -1,
            'max_deployments': -1,
            'max_executions_per_month': -1,
            'max_tools': -1,
            'max_credentials': -1,
            'price_monthly_cents': 129900,
            'price_yearly_cents': 1299000,
            'sort_order': 3,
            'features': {
                'has_demystrag': True,
                'has_mock_api': True,
                'demystrag_max_documents': -1,
                'demystrag_max_storage_mb': -1,
                'demystrag_max_collections': -1,
                'demystrag_embedding_providers': ['openai', 'anthropic', 'cohere'],
                'custom_tools': True,
                'api_access': True,
                'advanced_analytics': True,
                'audit_logs': True,
                'sso': True,
                'priority_support': True,
                'custom_branding': True,
            },
        },
    ]

    for p in plans:
        existing = conn.execute(
            sa.text("SELECT id FROM subscription_plans WHERE name = :name"),
            {"name": p['name']}
        ).fetchone()

        if existing:
            conn.execute(
                sa.text("""
                    UPDATE subscription_plans SET
                        display_name = :display_name,
                        description = :description,
                        max_users = :max_users,
                        max_agents = :max_agents,
                        max_deployments = :max_deployments,
                        max_executions_per_month = :max_executions_per_month,
                        max_tools = :max_tools,
                        max_credentials = :max_credentials,
                        price_monthly_cents = :price_monthly_cents,
                        price_yearly_cents = :price_yearly_cents,
                        sort_order = :sort_order,
                        features = :features::jsonb,
                        updated_at = NOW()
                    WHERE name = :name
                """),
                {**p, 'features': json.dumps(p['features'])}
            )
        else:
            conn.execute(
                sa.text("""
                    INSERT INTO subscription_plans
                        (id, name, display_name, description,
                         max_users, max_agents, max_deployments, max_executions_per_month,
                         max_tools, max_credentials,
                         price_monthly_cents, price_yearly_cents,
                         sort_order, features, is_active, is_public, created_at, updated_at)
                    VALUES
                        (:id, :name, :display_name, :description,
                         :max_users, :max_agents, :max_deployments, :max_executions_per_month,
                         :max_tools, :max_credentials,
                         :price_monthly_cents, :price_yearly_cents,
                         :sort_order, :features::jsonb, true, true, NOW(), NOW())
                """),
                {**p, 'id': str(uuid.uuid4()), 'features': json.dumps(p['features'])}
            )


def downgrade():
    op.drop_table('stripe_webhook_events')
    op.drop_table('org_subscriptions')
