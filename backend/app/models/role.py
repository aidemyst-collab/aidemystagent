"""
Role and UserRole models for RBAC
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class RoleScope(str, enum.Enum):
    """Scope of the role - platform-wide or organization-specific."""
    PLATFORM = "platform"
    ORGANIZATION = "organization"


class Role(Base):
    """
    Role definitions for RBAC.
    Supports both system roles and custom organization roles.
    """
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False)  # e.g., 'super_admin', 'org_owner', 'developer'
    display_name = Column(String(100), nullable=False)  # e.g., 'Super Admin', 'Organization Owner'
    description = Column(Text)

    # Scope determines if this is a platform-wide or org-specific role
    # Using String instead of Enum to match database values (lowercase)
    scope = Column(String(20), nullable=False, default="organization")

    # Permissions as JSON array of permission strings
    permissions = Column(JSONB, default=list, nullable=False)
    # Example permissions:
    # ["org:read", "org:update", "users:*", "agents:create", "agents:read", "agents:update:own"]

    # System roles cannot be modified or deleted
    is_system_role = Column(Boolean, default=False, nullable=False)

    # For custom organization roles, this links to the org
    # NULL for platform-wide roles
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    organization = relationship("Organization", back_populates="custom_roles")

    __table_args__ = (
        # Allow same role name in different organizations, but unique within an org
        UniqueConstraint('name', 'organization_id', name='uq_role_name_org'),
    )

    def __repr__(self):
        return f"<Role(name={self.name}, scope={self.scope})>"

    def has_permission(self, permission: str) -> bool:
        """
        Check if role has a specific permission.
        Supports wildcards: 'agents:*' matches 'agents:read', 'agents:create', etc.
        """
        if not self.permissions:
            return False

        # Full access
        if "*" in self.permissions:
            return True

        # Direct match
        if permission in self.permissions:
            return True

        # Wildcard match (e.g., 'agents:*' matches 'agents:read')
        permission_parts = permission.split(':')
        for perm in self.permissions:
            perm_parts = perm.split(':')
            if len(perm_parts) >= 1 and perm_parts[-1] == '*':
                # Check if prefix matches
                prefix = ':'.join(perm_parts[:-1])
                if permission.startswith(prefix + ':') or permission == prefix:
                    return True

        return False


class UserRole(Base):
    """
    Many-to-many relationship between users and roles.
    A user can have multiple roles, potentially in different organizations.
    """
    __tablename__ = "user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    # Organization context for the role assignment
    # NULL for platform-wide roles (e.g., super_admin)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    # Who assigned this role
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    organization = relationship("Organization", back_populates="user_role_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        # A user can only have a role once per organization
        UniqueConstraint('user_id', 'role_id', 'organization_id', name='uq_user_role_org'),
    )

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role={self.role.name if self.role else None})>"


# Default system roles with their permissions
# Note: scope values are lowercase strings to match database values
SYSTEM_ROLES = [
    {
        "name": "super_admin",
        "display_name": "Super Admin",
        "description": "Platform administrator with access to all organizations and system settings",
        "scope": "platform",
        "is_system_role": True,
        "permissions": ["*"]
    },
    {
        "name": "org_owner",
        "display_name": "Organization Owner",
        "description": "Full organization control including billing and deletion",
        "scope": "organization",
        "is_system_role": True,
        "permissions": [
            "org:*",
            "users:*",
            "agents:*",
            "tools:*",
            "credentials:*",
            "deployments:*",
            "analytics:*",
            "audit:read"
        ]
    },
    {
        "name": "org_admin",
        "display_name": "Organization Admin",
        "description": "Organization management without billing access",
        "scope": "organization",
        "is_system_role": True,
        "permissions": [
            "org:read",
            "org:update",
            "users:*",
            "agents:*",
            "tools:*",
            "credentials:*",
            "deployments:*",
            "analytics:*",
            "audit:read"
        ]
    },
    {
        "name": "team_lead",
        "display_name": "Team Lead",
        "description": "Manage all agents and coordinate developers within the organization",
        "scope": "organization",
        "is_system_role": True,
        "permissions": [
            "org:read",
            "users:read",
            "agents:*",
            "tools:*",
            "credentials:read",
            "deployments:*",
            "analytics:read"
        ]
    },
    {
        "name": "developer",
        "display_name": "Developer",
        "description": "Create and edit own agents and tools",
        "scope": "organization",
        "is_system_role": True,
        "permissions": [
            "org:read",
            "users:read",
            "agents:create",
            "agents:read",
            "agents:update:own",
            "agents:delete:own",
            "agents:execute",
            "tools:create",
            "tools:read",
            "tools:update:own",
            "tools:delete:own",
            "credentials:create",
            "credentials:read",
            "deployments:read",
            "deployments:create:non_prod",
            "analytics:read"
        ]
    },
    {
        "name": "operator",
        "display_name": "Operator",
        "description": "Execute and deploy agents",
        "scope": "organization",
        "is_system_role": True,
        "permissions": [
            "org:read",
            "users:read",
            "agents:read",
            "agents:execute",
            "tools:read",
            "deployments:*",
            "analytics:read"
        ]
    },
    {
        "name": "viewer",
        "display_name": "Viewer",
        "description": "Read-only access to organization resources",
        "scope": "organization",
        "is_system_role": True,
        "permissions": [
            "org:read",
            "users:read",
            "agents:read",
            "tools:read",
            "deployments:read",
            "analytics:read"
        ]
    }
]
