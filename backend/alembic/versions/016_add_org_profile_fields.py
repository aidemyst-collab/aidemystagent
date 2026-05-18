"""add org profile fields

Revision ID: 016
Revises: 015
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('organizations', sa.Column('website', sa.String(500), nullable=True))
    op.add_column('organizations', sa.Column('phone_number', sa.String(50), nullable=True))
    op.add_column('organizations', sa.Column('country', sa.String(100), nullable=True))
    op.add_column('organizations', sa.Column('industry', sa.String(100), nullable=False, server_default='Other'))
    op.add_column('organizations', sa.Column('employee_count', sa.String(50), nullable=False, server_default='1-10'))
    op.add_column('organizations', sa.Column('intended_use_case', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('organizations', 'intended_use_case')
    op.drop_column('organizations', 'employee_count')
    op.drop_column('organizations', 'industry')
    op.drop_column('organizations', 'country')
    op.drop_column('organizations', 'phone_number')
    op.drop_column('organizations', 'website')
