"""add credentials table

Revision ID: 002
Revises: 001
Create Date: 2024-11-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create credentials table
    op.create_table(
        'credentials',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider', sa.Enum('openai', 'anthropic', 'google', 'azure_openai', 'custom', name='credentialprovider'), nullable=False),
        sa.Column('api_key', sa.String(), nullable=False),
        sa.Column('api_base', sa.String(), nullable=True),
        sa.Column('api_version', sa.String(), nullable=True),
        sa.Column('organization_key', sa.String(), nullable=True),
        sa.Column('is_active', sa.String(), server_default='active', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_credentials_user_id'), 'credentials', ['user_id'], unique=False)
    op.create_index(op.f('ix_credentials_organization_id'), 'credentials', ['organization_id'], unique=False)
    op.create_index(op.f('ix_credentials_provider'), 'credentials', ['provider'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_credentials_provider'), table_name='credentials')
    op.drop_index(op.f('ix_credentials_organization_id'), table_name='credentials')
    op.drop_index(op.f('ix_credentials_user_id'), table_name='credentials')
    op.drop_table('credentials')
    op.execute('DROP TYPE credentialprovider')
