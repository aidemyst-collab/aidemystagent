"""restructure dynamic mcp - add servers and update tools

Revision ID: 011
Revises: 010
Create Date: 2026-03-07

This migration restructures the Dynamic MCP system:
1. Creates dynamic_mcp_servers table (parent)
2. Restructures dynamic_mcp_tools table (child with server_id)

Tools now belong to servers and inherit base_url, credentials, and headers.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    # ==================================================================
    # Step 1: Create dynamic_mcp_servers table
    # ==================================================================
    op.create_table(
        'dynamic_mcp_servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Server identification
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),

        # API configuration (shared by all tools)
        sa.Column('base_url', sa.String(500), nullable=False),

        # Authentication (shared credential)
        sa.Column('credential_id', sa.String(), nullable=True),

        # Default request configuration
        sa.Column('default_headers', postgresql.JSON(), nullable=True, server_default='{}'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['credential_id'], ['credentials.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for servers
    op.create_index(
        op.f('ix_dynamic_mcp_servers_organization_id'),
        'dynamic_mcp_servers',
        ['organization_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_dynamic_mcp_servers_creator_id'),
        'dynamic_mcp_servers',
        ['creator_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_dynamic_mcp_servers_is_active'),
        'dynamic_mcp_servers',
        ['is_active'],
        unique=False
    )
    # Server name must be unique within organization
    op.create_index(
        'ix_dynamic_mcp_servers_org_name',
        'dynamic_mcp_servers',
        ['organization_id', 'name'],
        unique=True
    )

    # ==================================================================
    # Step 2: Drop old dynamic_mcp_tools table and recreate with new schema
    # ==================================================================
    # Drop indexes first
    op.drop_index('ix_dynamic_mcp_tools_org_name', table_name='dynamic_mcp_tools')
    op.drop_index(op.f('ix_dynamic_mcp_tools_is_active'), table_name='dynamic_mcp_tools')
    op.drop_index(op.f('ix_dynamic_mcp_tools_creator_id'), table_name='dynamic_mcp_tools')
    op.drop_index(op.f('ix_dynamic_mcp_tools_organization_id'), table_name='dynamic_mcp_tools')

    # Drop old table
    op.drop_table('dynamic_mcp_tools')

    # Create new tools table with server_id relationship
    op.create_table(
        'dynamic_mcp_tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # Parent server relationship
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Tool identification
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),

        # Endpoint configuration (relative to server base_url)
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('method', sa.String(10), nullable=False, server_default='GET'),

        # Parameters schema (JSON array)
        sa.Column('parameters', postgresql.JSON(), nullable=True, server_default='[]'),

        # Request configuration (overrides server defaults if set)
        sa.Column('headers', postgresql.JSON(), nullable=True, server_default='{}'),
        sa.Column('query_params', postgresql.JSON(), nullable=True, server_default='{}'),
        sa.Column('body_template', postgresql.JSON(), nullable=True, server_default='{}'),

        # Response handling
        sa.Column('response_path', sa.String(200), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['server_id'], ['dynamic_mcp_servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for tools
    op.create_index(
        op.f('ix_dynamic_mcp_tools_server_id'),
        'dynamic_mcp_tools',
        ['server_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_dynamic_mcp_tools_is_active'),
        'dynamic_mcp_tools',
        ['is_active'],
        unique=False
    )
    # Tool name must be unique within server
    op.create_index(
        'ix_dynamic_mcp_tools_server_name',
        'dynamic_mcp_tools',
        ['server_id', 'name'],
        unique=True
    )


def downgrade():
    # ==================================================================
    # Reverse: Drop new structure and recreate old
    # ==================================================================

    # Drop new tools table indexes and table
    op.drop_index('ix_dynamic_mcp_tools_server_name', table_name='dynamic_mcp_tools')
    op.drop_index(op.f('ix_dynamic_mcp_tools_is_active'), table_name='dynamic_mcp_tools')
    op.drop_index(op.f('ix_dynamic_mcp_tools_server_id'), table_name='dynamic_mcp_tools')
    op.drop_table('dynamic_mcp_tools')

    # Drop servers table indexes and table
    op.drop_index('ix_dynamic_mcp_servers_org_name', table_name='dynamic_mcp_servers')
    op.drop_index(op.f('ix_dynamic_mcp_servers_is_active'), table_name='dynamic_mcp_servers')
    op.drop_index(op.f('ix_dynamic_mcp_servers_creator_id'), table_name='dynamic_mcp_servers')
    op.drop_index(op.f('ix_dynamic_mcp_servers_organization_id'), table_name='dynamic_mcp_servers')
    op.drop_table('dynamic_mcp_servers')

    # Recreate old dynamic_mcp_tools table (from migration 010)
    op.create_table(
        'dynamic_mcp_tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('api_endpoint', sa.String(1000), nullable=False),
        sa.Column('method', sa.String(10), nullable=False, server_default='GET'),
        sa.Column('parameters', postgresql.JSON(), nullable=True, server_default='[]'),
        sa.Column('headers', postgresql.JSON(), nullable=True, server_default='{}'),
        sa.Column('query_params', postgresql.JSON(), nullable=True, server_default='{}'),
        sa.Column('body_template', postgresql.JSON(), nullable=True, server_default='{}'),
        sa.Column('credential_id', sa.String(), nullable=True),
        sa.Column('response_path', sa.String(200), nullable=True),
        sa.Column('response_template', sa.String(1000), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['credential_id'], ['credentials.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        op.f('ix_dynamic_mcp_tools_organization_id'),
        'dynamic_mcp_tools',
        ['organization_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_dynamic_mcp_tools_creator_id'),
        'dynamic_mcp_tools',
        ['creator_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_dynamic_mcp_tools_is_active'),
        'dynamic_mcp_tools',
        ['is_active'],
        unique=False
    )
    op.create_index(
        'ix_dynamic_mcp_tools_org_name',
        'dynamic_mcp_tools',
        ['organization_id', 'name'],
        unique=True
    )
