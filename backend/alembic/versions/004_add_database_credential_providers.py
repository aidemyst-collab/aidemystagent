"""add database credential providers

Revision ID: 004
Revises: 003
Create Date: 2024-12-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Add new enum values to the credentialprovider enum
    # PostgreSQL requires using ALTER TYPE to add new enum values
    op.execute("ALTER TYPE credentialprovider ADD VALUE IF NOT EXISTS 'redis'")
    op.execute("ALTER TYPE credentialprovider ADD VALUE IF NOT EXISTS 'postgresql'")
    op.execute("ALTER TYPE credentialprovider ADD VALUE IF NOT EXISTS 'mongodb'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type and updating all references
    # For safety, we'll leave the enum values in place during downgrade
    # If you need to remove them, you'll need to:
    # 1. Create a new enum type without the values
    # 2. Alter the column to use the new type
    # 3. Drop the old enum type
    pass
