"""add mcp tool type

Revision ID: 003
Revises: 002
Create Date: 2025-12-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add MCP to tooltype enum
    op.execute("ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'mcp'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values easily
    # You would need to recreate the enum type to remove a value
    pass
