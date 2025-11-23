"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-11-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'CREATOR', 'VIEWER', name='userrole'), nullable=False, server_default='CREATOR'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Agents table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('config', postgresql.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.Enum('DRAFT', 'DEPLOYED', 'ARCHIVED', name='agentstatus'), nullable=False, server_default='DRAFT'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id']),
    )
    op.create_index('idx_agents_organization_id', 'agents', ['organization_id'])
    op.create_index('idx_agents_creator_id', 'agents', ['creator_id'])
    op.create_index('idx_agents_status', 'agents', ['status'])

    # Agent executions table
    op.create_table(
        'agent_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('input', postgresql.JSON(), nullable=False),
        sa.Column('output', postgresql.JSON(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('execution_time', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    op.create_index('idx_agent_executions_agent_id', 'agent_executions', ['agent_id'])
    op.create_index('idx_agent_executions_user_id', 'agent_executions', ['user_id'])

    # Tools table
    op.create_table(
        'tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('type', sa.Enum('BUILT_IN', 'API', 'CUSTOM', name='tooltype'), nullable=False),
        sa.Column('config', postgresql.JSON(), nullable=False),
        sa.Column('visibility', sa.Enum('PUBLIC', 'PRIVATE', 'ORGANIZATION', name='toolvisibility'), nullable=False, server_default='PRIVATE'),
        sa.Column('status', sa.Enum('ACTIVE', 'DEPRECATED', name='toolstatus'), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id']),
    )
    op.create_index('idx_tools_organization_id', 'tools', ['organization_id'])
    op.create_index('idx_tools_type', 'tools', ['type'])

    # Tool executions table
    op.create_table(
        'tool_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('input', postgresql.JSON(), nullable=False),
        sa.Column('output', postgresql.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('execution_time', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tool_id'], ['tools.id']),
        sa.ForeignKeyConstraint(['execution_id'], ['agent_executions.id']),
    )
    op.create_index('idx_tool_executions_tool_id', 'tool_executions', ['tool_id'])

    # Deployments table
    op.create_table(
        'deployments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('environment', sa.Enum('DEVELOPMENT', 'STAGING', 'PRODUCTION', name='deploymentenvironment'), nullable=False, server_default='DEVELOPMENT'),
        sa.Column('status', sa.Enum('PENDING', 'DEPLOYING', 'ACTIVE', 'FAILED', 'STOPPED', name='deploymentstatus'), nullable=False, server_default='PENDING'),
        sa.Column('endpoint_url', sa.String(), nullable=True),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('config', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('deployed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deployed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['deployed_by'], ['users.id']),
    )
    op.create_index('idx_deployments_agent_id', 'deployments', ['agent_id'])
    op.create_index('idx_deployments_status', 'deployments', ['status'])

    # Agent versions table
    op.create_table(
        'agent_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('version_tag', sa.String(), nullable=True),
        sa.Column('config', postgresql.JSON(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )
    op.create_index('idx_agent_versions_agent_id', 'agent_versions', ['agent_id'])
    op.create_unique_constraint('uq_agent_version', 'agent_versions', ['agent_id', 'version_number'])


def downgrade() -> None:
    op.drop_table('agent_versions')
    op.drop_table('deployments')
    op.drop_table('tool_executions')
    op.drop_table('tools')
    op.drop_table('agent_executions')
    op.drop_table('agents')
    op.drop_table('users')
    op.drop_table('organizations')

    op.execute('DROP TYPE IF EXISTS deploymentstatus')
    op.execute('DROP TYPE IF EXISTS deploymentenvironment')
    op.execute('DROP TYPE IF EXISTS toolstatus')
    op.execute('DROP TYPE IF EXISTS toolvisibility')
    op.execute('DROP TYPE IF EXISTS tooltype')
    op.execute('DROP TYPE IF EXISTS agentstatus')
    op.execute('DROP TYPE IF EXISTS userrole')
