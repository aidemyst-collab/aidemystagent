"""add mcp_servers table

Revision ID: 009
Revises: 008
Create Date: 2026-03-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Debug: Print to verify latest code is deployed
    print("=== MIGRATION 009: Running with idempotent ENUM creation (v2) ===")

    # Create enums (with IF NOT EXISTS to make migration idempotent)
    print("Creating mcpserverstatus enum (idempotent)...")
    op.execute("DO $$ BEGIN CREATE TYPE mcpserverstatus AS ENUM ('active', 'inactive', 'error'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    print("Creating mcptransporttype enum (idempotent)...")
    op.execute("DO $$ BEGIN CREATE TYPE mcptransporttype AS ENUM ('sse', 'http', 'stdio'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # Create mcp_servers table
    op.create_table(
        'mcp_servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('server_url', sa.String(500), nullable=False),
        sa.Column('transport_type', sa.Enum('sse', 'http', 'stdio', name='mcptransporttype', create_type=False), nullable=False, server_default='sse'),
        sa.Column('credential_id', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'error', name='mcpserverstatus', create_type=False), nullable=False, server_default='active'),
        sa.Column('last_health_check', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.String(1000), nullable=True),
        sa.Column('discovered_tools', postgresql.JSON(), nullable=True, server_default='[]'),
        sa.Column('discovered_resources', postgresql.JSON(), nullable=True, server_default='[]'),
        sa.Column('discovered_prompts', postgresql.JSON(), nullable=True, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['credential_id'], ['credentials.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for common queries
    op.create_index(op.f('ix_mcp_servers_organization_id'), 'mcp_servers', ['organization_id'], unique=False)
    op.create_index(op.f('ix_mcp_servers_creator_id'), 'mcp_servers', ['creator_id'], unique=False)
    op.create_index(op.f('ix_mcp_servers_status'), 'mcp_servers', ['status'], unique=False)
    op.create_index(
        'ix_mcp_servers_org_name',
        'mcp_servers',
        ['organization_id', 'name'],
        unique=True
    )


def downgrade():
    op.drop_index('ix_mcp_servers_org_name', table_name='mcp_servers')
    op.drop_index(op.f('ix_mcp_servers_status'), table_name='mcp_servers')
    op.drop_index(op.f('ix_mcp_servers_creator_id'), table_name='mcp_servers')
    op.drop_index(op.f('ix_mcp_servers_organization_id'), table_name='mcp_servers')
    op.drop_table('mcp_servers')
    op.execute('DROP TYPE mcpserverstatus')
    op.execute('DROP TYPE mcptransporttype')
