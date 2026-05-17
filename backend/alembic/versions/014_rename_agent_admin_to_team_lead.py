"""Rename agent_admin role to team_lead

Revision ID: 014
Revises: 013
Create Date: 2026-05-17

Renames the system role 'agent_admin' to 'team_lead', updating the display_name
and description to reflect the new team coordination responsibility.
user_roles only stores role_id FKs so no data update is needed there.
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE roles
        SET name = 'team_lead',
            display_name = 'Team Lead',
            description = 'Manage all agents and coordinate developers within the organization'
        WHERE name = 'agent_admin' AND is_system_role = TRUE
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE roles
        SET name = 'agent_admin',
            display_name = 'Agent Admin',
            description = 'Manage all agents regardless of creator'
        WHERE name = 'team_lead' AND is_system_role = TRUE
    """)
