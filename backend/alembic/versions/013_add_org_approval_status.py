"""Add org approval status to organizations

Revision ID: 013
Revises: 012
Create Date: 2026-05-17

Adds approval_status, approval_rejected_reason, approved_at, and approved_by_id
columns to the organizations table to support the org approval gate (Milestone 1 RBAC).
Existing orgs default to 'active' so there is no disruption.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add approval_status with server_default 'active' so existing rows are set
    op.add_column(
        'organizations',
        sa.Column(
            'approval_status',
            sa.String(20),
            nullable=False,
            server_default='active',
        ),
    )

    # Add optional rejection reason
    op.add_column(
        'organizations',
        sa.Column('approval_rejected_reason', sa.Text, nullable=True),
    )

    # Add timestamp for when the org was approved
    op.add_column(
        'organizations',
        sa.Column('approved_at', sa.DateTime, nullable=True),
    )

    # Add reference to the admin who approved this org
    op.add_column(
        'organizations',
        sa.Column(
            'approved_by_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # Foreign key from approved_by_id -> users.id (SET NULL on delete)
    op.create_foreign_key(
        'fk_organizations_approved_by',
        'organizations', 'users',
        ['approved_by_id'], ['id'],
        ondelete='SET NULL',
    )

    # Index on approval_status to make the admin approval queue query fast
    op.create_index(
        'idx_organizations_approval_status',
        'organizations',
        ['approval_status'],
    )


def downgrade() -> None:
    op.drop_index('idx_organizations_approval_status', table_name='organizations')
    op.drop_constraint('fk_organizations_approved_by', 'organizations', type_='foreignkey')
    op.drop_column('organizations', 'approved_by_id')
    op.drop_column('organizations', 'approved_at')
    op.drop_column('organizations', 'approval_rejected_reason')
    op.drop_column('organizations', 'approval_status')
