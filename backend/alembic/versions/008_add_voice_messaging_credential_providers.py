"""Add voice and messaging credential providers

Revision ID: 008
Revises: 007
Create Date: 2026-02-07

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values for voice and messaging providers
    op.execute("ALTER TYPE credentialprovider ADD VALUE IF NOT EXISTS 'twilio'")
    op.execute("ALTER TYPE credentialprovider ADD VALUE IF NOT EXISTS 'etisalat'")
    op.execute("ALTER TYPE credentialprovider ADD VALUE IF NOT EXISTS 'whatsapp_meta'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly
    # The values will remain in place during downgrade
    pass
