"""Add organization_id to agent_executions

Revision ID: 007
Revises: 006
Create Date: 2026-01-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add organization_id column to agent_executions
    op.add_column(
        'agent_executions',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_agent_executions_organization_id',
        'agent_executions',
        'organizations',
        ['organization_id'],
        ['id']
    )

    # Add index for performance
    op.create_index(
        'idx_agent_executions_organization_id',
        'agent_executions',
        ['organization_id']
    )

    # Backfill organization_id from the agent's organization
    op.execute("""
        UPDATE agent_executions ae
        SET organization_id = a.organization_id
        FROM agents a
        WHERE ae.agent_id = a.id
        AND ae.organization_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index('idx_agent_executions_organization_id', 'agent_executions')
    op.drop_constraint('fk_agent_executions_organization_id', 'agent_executions', type_='foreignkey')
    op.drop_column('agent_executions', 'organization_id')
