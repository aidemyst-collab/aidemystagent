"""Seed default admin user

Revision ID: 006
Revises: 005
Create Date: 2026-01-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Default admin credentials
ADMIN_EMAIL = "admin@agentstudio.io"
ADMIN_PASSWORD = "AgentStudio@2026!"
ADMIN_FULL_NAME = "Platform Administrator"
ORG_NAME = "AgentStudio"


def upgrade() -> None:
    # Generate password hash
    password_hash = pwd_context.hash(ADMIN_PASSWORD)

    # Check if admin user already exists
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": ADMIN_EMAIL}
    )
    existing_user = result.fetchone()

    if existing_user:
        print(f"Admin user {ADMIN_EMAIL} already exists, skipping...")
        return

    # Check if organization exists, if not create it
    result = conn.execute(
        sa.text("SELECT id FROM organizations WHERE name = :name"),
        {"name": ORG_NAME}
    )
    org = result.fetchone()

    if not org:
        # Get the starter plan id
        result = conn.execute(
            sa.text("SELECT id FROM subscription_plans WHERE name = 'starter' LIMIT 1")
        )
        plan = result.fetchone()
        plan_id = plan[0] if plan else None

        # Create organization
        conn.execute(
            sa.text("""
                INSERT INTO organizations (id, name, slug, subscription_plan_id, subscription_status, is_active, created_at, updated_at)
                VALUES (gen_random_uuid(), :name, :slug, :plan_id, 'active', true, NOW(), NOW())
            """),
            {"name": ORG_NAME, "slug": "agentstudio", "plan_id": plan_id}
        )
        print(f"Created organization: {ORG_NAME}")

    # Get the organization id
    result = conn.execute(
        sa.text("SELECT id FROM organizations WHERE name = :name"),
        {"name": ORG_NAME}
    )
    org = result.fetchone()
    org_id = org[0]

    # Create admin user
    conn.execute(
        sa.text("""
            INSERT INTO users (
                id, organization_id, email, hashed_password, role,
                full_name, is_platform_admin, is_active, email_verified,
                created_at, updated_at
            )
            VALUES (
                gen_random_uuid(), :org_id, :email, :password_hash, 'ADMIN',
                :full_name, true, true, true,
                NOW(), NOW()
            )
        """),
        {
            "org_id": org_id,
            "email": ADMIN_EMAIL,
            "password_hash": password_hash,
            "full_name": ADMIN_FULL_NAME
        }
    )
    print(f"Created admin user: {ADMIN_EMAIL}")

    # Get the user id and org_owner role id to assign role
    result = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": ADMIN_EMAIL}
    )
    user = result.fetchone()
    user_id = user[0]

    result = conn.execute(
        sa.text("SELECT id FROM roles WHERE name = 'org_owner' AND is_system_role = true LIMIT 1")
    )
    role = result.fetchone()

    if role:
        role_id = role[0]
        # Assign org_owner role to admin
        conn.execute(
            sa.text("""
                INSERT INTO user_roles (id, user_id, role_id, organization_id, assigned_at)
                VALUES (gen_random_uuid(), :user_id, :role_id, :org_id, NOW())
                ON CONFLICT DO NOTHING
            """),
            {"user_id": user_id, "role_id": role_id, "org_id": org_id}
        )
        print(f"Assigned org_owner role to admin user")

    print(f"""
    ============================================
    Default Admin User Created Successfully!
    ============================================
    Email:    {ADMIN_EMAIL}
    Password: {ADMIN_PASSWORD}
    Role:     Platform Administrator
    ============================================
    Please change this password after first login!
    ============================================
    """)


def downgrade() -> None:
    conn = op.get_bind()

    # Get user id
    result = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": ADMIN_EMAIL}
    )
    user = result.fetchone()

    if user:
        user_id = user[0]
        # Delete user roles first
        conn.execute(
            sa.text("DELETE FROM user_roles WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        # Delete user
        conn.execute(
            sa.text("DELETE FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        print(f"Deleted admin user: {ADMIN_EMAIL}")
