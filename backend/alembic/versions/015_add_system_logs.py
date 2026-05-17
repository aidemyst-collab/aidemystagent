"""Add system_logs table

Revision ID: 015
Revises: 014
Create Date: 2026-05-17

Additive migration: creates system_logs table for platform audit/observability.
Auto-cleanup of entries older than 30 days is handled in application code.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '015'
down_revision: Union[str, None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'system_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('level', sa.String(10), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('details', JSONB, nullable=True),
        sa.Column('source', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_system_logs_level', 'system_logs', ['level'])
    op.create_index('ix_system_logs_category', 'system_logs', ['category'])
    op.create_index('ix_system_logs_created_at', 'system_logs', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_system_logs_created_at', table_name='system_logs')
    op.drop_index('ix_system_logs_category', table_name='system_logs')
    op.drop_index('ix_system_logs_level', table_name='system_logs')
    op.drop_table('system_logs')
