"""add dynamic_mcp_tools table

Revision ID: 010
Revises: 009
Create Date: 2026-03-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # Create dynamic_mcp_tools table
    op.create_table(
        'dynamic_mcp_tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Tool identification
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),

        # API configuration
        sa.Column('api_endpoint', sa.String(1000), nullable=False),
        sa.Column('method', sa.String(10), nullable=False, server_default='GET'),

        # Parameters schema (JSON array)
        sa.Column('parameters', postgresql.JSON(), nullable=True, server_default='[]'),

        # Request configuration
        sa.Column('headers', postgresql.JSON(), nullable=True, server_default='{}'),
        sa.Column('query_params', postgresql.JSON(), nullable=True, server_default='{}'),
        sa.Column('body_template', postgresql.JSON(), nullable=True, server_default='{}'),

        # Authentication (credential reference)
        sa.Column('credential_id', sa.String(), nullable=True),

        # Response handling
        sa.Column('response_path', sa.String(200), nullable=True),
        sa.Column('response_template', sa.String(1000), nullable=True),

        # Timeout
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

    # Create indexes
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
    # Unique constraint: tool name must be unique within organization
    op.create_index(
        'ix_dynamic_mcp_tools_org_name',
        'dynamic_mcp_tools',
        ['organization_id', 'name'],
        unique=True
    )


def downgrade():
    op.drop_index('ix_dynamic_mcp_tools_org_name', table_name='dynamic_mcp_tools')
    op.drop_index(op.f('ix_dynamic_mcp_tools_is_active'), table_name='dynamic_mcp_tools')
    op.drop_index(op.f('ix_dynamic_mcp_tools_creator_id'), table_name='dynamic_mcp_tools')
    op.drop_index(op.f('ix_dynamic_mcp_tools_organization_id'), table_name='dynamic_mcp_tools')
    op.drop_table('dynamic_mcp_tools')
