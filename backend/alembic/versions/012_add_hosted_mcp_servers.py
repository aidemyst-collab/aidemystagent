"""add hosted mcp servers table

Revision ID: 012
Revises: 011
Create Date: 2026-03-09

This migration creates the hosted_mcp_servers table for managing
MCP servers deployed to Azure Container Apps.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    # ==================================================================
    # Create hosted_mcp_servers table
    # ==================================================================
    op.create_table(
        'hosted_mcp_servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Server Identity
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Source Configuration
        sa.Column('source_type', sa.String(20), nullable=False),  # 'registry', 'github', 'docker'
        sa.Column('source_config', postgresql.JSON(), nullable=False),

        # Azure Container App Details
        sa.Column('azure_app_name', sa.String(63), nullable=True),
        sa.Column('azure_app_url', sa.String(255), nullable=True),
        sa.Column('azure_resource_id', sa.String(500), nullable=True),

        # Runtime Configuration
        sa.Column('environment_variables', postgresql.JSON(), nullable=True, server_default='{}'),
        sa.Column('port', sa.Integer(), nullable=False, server_default='3000'),
        sa.Column('cpu_cores', sa.Numeric(3, 2), nullable=False, server_default='0.25'),
        sa.Column('memory_gb', sa.Numeric(3, 1), nullable=False, server_default='0.5'),
        sa.Column('min_replicas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_replicas', sa.Integer(), nullable=False, server_default='3'),

        # Status
        sa.Column('status', sa.String(20), nullable=False, server_default="'pending'"),
        sa.Column('last_health_check', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Discovered Capabilities
        sa.Column('discovered_tools', postgresql.JSON(), nullable=True, server_default='[]'),
        sa.Column('discovered_resources', postgresql.JSON(), nullable=True, server_default='[]'),
        sa.Column('discovered_prompts', postgresql.JSON(), nullable=True, server_default='[]'),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes
    op.create_index(
        op.f('ix_hosted_mcp_servers_organization_id'),
        'hosted_mcp_servers',
        ['organization_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_hosted_mcp_servers_creator_id'),
        'hosted_mcp_servers',
        ['creator_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_hosted_mcp_servers_status'),
        'hosted_mcp_servers',
        ['status'],
        unique=False
    )
    # Server name must be unique within organization (excluding soft-deleted)
    op.create_index(
        'ix_hosted_mcp_servers_org_name',
        'hosted_mcp_servers',
        ['organization_id', 'name'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade():
    # Drop indexes
    op.drop_index('ix_hosted_mcp_servers_org_name', table_name='hosted_mcp_servers')
    op.drop_index(op.f('ix_hosted_mcp_servers_status'), table_name='hosted_mcp_servers')
    op.drop_index(op.f('ix_hosted_mcp_servers_creator_id'), table_name='hosted_mcp_servers')
    op.drop_index(op.f('ix_hosted_mcp_servers_organization_id'), table_name='hosted_mcp_servers')

    # Drop table
    op.drop_table('hosted_mcp_servers')
