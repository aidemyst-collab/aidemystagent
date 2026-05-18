"""add product feature flags to subscription plans

Adds has_demystrag, has_mock_api, and DemystRAG-specific quota keys to every
subscription plan's features JSONB. These flags are read by build_token_claims()
at login/refresh to populate the JWT products list and plan_limits claims.

Revision ID: 017
Revises: 016
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None

# Keys added per plan — used in both upgrade and downgrade
_NEW_KEYS = [
    'has_demystrag',
    'has_mock_api',
    'demystrag_max_documents',
    'demystrag_max_storage_mb',
    'demystrag_max_collections',
    'demystrag_embedding_providers',
]

# Per-plan feature additions.  Use the JSONB || merge operator so existing
# keys (custom_tools, api_access, etc.) are preserved.
_PLAN_FLAGS = {
    'free': {
        'has_demystrag': False,
        'has_mock_api': False,
        'demystrag_max_documents': 0,
        'demystrag_max_storage_mb': 0,
        'demystrag_max_collections': 0,
        'demystrag_embedding_providers': [],
    },
    'starter': {
        'has_demystrag': True,
        'has_mock_api': True,
        'demystrag_max_documents': 500,
        'demystrag_max_storage_mb': 5000,
        'demystrag_max_collections': 10,
        'demystrag_embedding_providers': ['openai'],
    },
    'professional': {
        'has_demystrag': True,
        'has_mock_api': True,
        'demystrag_max_documents': 5000,
        'demystrag_max_storage_mb': 50000,
        'demystrag_max_collections': 100,
        'demystrag_embedding_providers': ['openai', 'anthropic'],
    },
    'enterprise': {
        'has_demystrag': True,
        'has_mock_api': True,
        'demystrag_max_documents': -1,
        'demystrag_max_storage_mb': -1,
        'demystrag_max_collections': -1,
        'demystrag_embedding_providers': ['openai', 'anthropic', 'cohere'],
    },
}


def upgrade():
    conn = op.get_bind()

    import json
    for plan_name, flags in _PLAN_FLAGS.items():
        conn.execute(sa.text(
            "UPDATE subscription_plans "
            "SET features = features || :flags::jsonb "
            "WHERE name = :name"
        ), {"flags": json.dumps(flags), "name": plan_name})

    # Any custom plans that don't match a known name get the safe no-product defaults
    default_flags = {
        'has_demystrag': False,
        'has_mock_api': False,
        'demystrag_max_documents': 0,
        'demystrag_max_storage_mb': 0,
        'demystrag_max_collections': 0,
        'demystrag_embedding_providers': [],
    }
    known_names = list(_PLAN_FLAGS.keys())
    conn.execute(sa.text(
        "UPDATE subscription_plans "
        "SET features = features || :flags::jsonb "
        "WHERE name != ALL(:known)"
    ), {"flags": json.dumps(default_flags), "known": known_names})


def downgrade():
    conn = op.get_bind()
    # Remove all keys added in upgrade from every plan
    remove_expr = " - ".join(["features"] + [f"'{k}'" for k in _NEW_KEYS])
    conn.execute(sa.text(
        f"UPDATE subscription_plans SET features = {remove_expr}"
    ))
