"""
Permission Service for Role-Based Access Control (RBAC)

This service handles:
- Permission checking for users
- Role management
- Ownership validation for resources
"""
from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.role import Role, UserRole as UserRoleAssignment


class PermissionService:
    """Service for managing permissions and role-based access control."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._permission_cache: dict = {}

    async def get_user_roles(self, user: User, organization_id: Optional[UUID] = None) -> List[Role]:
        """
        Get all roles for a user.

        Args:
            user: The user to get roles for
            organization_id: Optional organization context (defaults to user's org)

        Returns:
            List of Role objects
        """
        org_id = organization_id or user.organization_id

        # Get user's role assignments with roles
        query = (
            select(UserRoleAssignment)
            .options(selectinload(UserRoleAssignment.role))
            .where(UserRoleAssignment.user_id == user.id)
            .where(
                (UserRoleAssignment.organization_id == org_id) |
                (UserRoleAssignment.organization_id.is_(None))  # Platform roles
            )
        )

        result = await self.db.execute(query)
        user_role_assignments = result.scalars().all()

        return [ura.role for ura in user_role_assignments if ura.role]

    async def get_user_permissions(self, user: User, organization_id: Optional[UUID] = None) -> Set[str]:
        """
        Get all permissions for a user (combined from all roles).

        Args:
            user: The user to get permissions for
            organization_id: Optional organization context

        Returns:
            Set of permission strings
        """
        # Check if user is platform admin (super admin shortcut)
        if user.is_platform_admin:
            return {"*"}

        roles = await self.get_user_roles(user, organization_id)
        permissions: Set[str] = set()

        for role in roles:
            if role.permissions:
                permissions.update(role.permissions)

        return permissions

    async def has_permission(
        self,
        user: User,
        permission: str,
        organization_id: Optional[UUID] = None,
        resource_owner_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user: The user to check
            permission: The permission string (e.g., 'agents:create', 'agents:update:own')
            organization_id: Optional organization context
            resource_owner_id: Optional owner ID for ownership-based permissions

        Returns:
            True if user has the permission, False otherwise
        """
        # Platform admins have all permissions
        if user.is_platform_admin:
            return True

        permissions = await self.get_user_permissions(user, organization_id)

        # Check for full access
        if "*" in permissions:
            return True

        # Direct match
        if permission in permissions:
            return True

        # Check for wildcard matches
        permission_parts = permission.split(':')

        for perm in permissions:
            perm_parts = perm.split(':')

            # Wildcard at end (e.g., 'agents:*' matches 'agents:read')
            if perm_parts[-1] == '*':
                prefix = ':'.join(perm_parts[:-1])
                if permission.startswith(prefix + ':') or permission == prefix:
                    return True

            # Check for ownership-based permissions (e.g., 'agents:update:own')
            if len(perm_parts) == 3 and perm_parts[2] == 'own':
                base_permission = ':'.join(perm_parts[:2])
                if permission == base_permission:
                    # Permission requires ownership check
                    if resource_owner_id and resource_owner_id == user.id:
                        return True

        return False

    async def has_any_permission(
        self,
        user: User,
        permissions: List[str],
        organization_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has any of the specified permissions."""
        for permission in permissions:
            if await self.has_permission(user, permission, organization_id):
                return True
        return False

    async def has_all_permissions(
        self,
        user: User,
        permissions: List[str],
        organization_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has all specified permissions."""
        for permission in permissions:
            if not await self.has_permission(user, permission, organization_id):
                return False
        return True

    async def can_access_resource(
        self,
        user: User,
        resource_type: str,
        action: str,
        resource_org_id: UUID,
        resource_owner_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if user can perform an action on a resource.

        Args:
            user: The user attempting access
            resource_type: Type of resource (e.g., 'agents', 'tools')
            action: Action being performed (e.g., 'read', 'update', 'delete')
            resource_org_id: Organization ID of the resource
            resource_owner_id: Owner ID of the resource (for ownership checks)

        Returns:
            True if access is allowed, False otherwise
        """
        # Platform admins can access anything
        if user.is_platform_admin:
            return True

        # Users can only access resources in their organization
        if user.organization_id != resource_org_id:
            return False

        # Build permission string
        permission = f"{resource_type}:{action}"

        # Check for direct permission
        if await self.has_permission(user, permission, resource_org_id, resource_owner_id):
            return True

        # Check for ownership-based permission if owner is known
        if resource_owner_id:
            own_permission = f"{resource_type}:{action}:own"
            user_permissions = await self.get_user_permissions(user, resource_org_id)
            if own_permission in user_permissions and resource_owner_id == user.id:
                return True

        return False

    async def get_role_by_name(self, name: str, organization_id: Optional[UUID] = None) -> Optional[Role]:
        """Get a role by name, optionally scoped to an organization."""
        query = select(Role).where(Role.name == name)

        if organization_id:
            query = query.where(
                (Role.organization_id == organization_id) |
                (Role.organization_id.is_(None))
            )
        else:
            query = query.where(Role.organization_id.is_(None))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def assign_role_to_user(
        self,
        user_id: UUID,
        role_id: UUID,
        organization_id: UUID,
        assigned_by: Optional[UUID] = None
    ) -> UserRoleAssignment:
        """Assign a role to a user."""
        user_role = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            organization_id=organization_id,
            assigned_by=assigned_by
        )
        self.db.add(user_role)
        await self.db.flush()
        return user_role

    async def revoke_role_from_user(
        self,
        user_id: UUID,
        role_id: UUID,
        organization_id: UUID
    ) -> bool:
        """Revoke a role from a user."""
        query = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role_id == role_id,
            UserRoleAssignment.organization_id == organization_id
        )
        result = await self.db.execute(query)
        user_role = result.scalar_one_or_none()

        if user_role:
            await self.db.delete(user_role)
            return True
        return False

    async def get_available_roles(self, organization_id: Optional[UUID] = None) -> List[Role]:
        """Get all available roles for an organization (system + custom)."""
        query = select(Role).where(
            (Role.organization_id == organization_id) |
            (Role.organization_id.is_(None) & (Role.scope == "organization"))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())


# Permission string constants for easy reference
class Permissions:
    """Permission string constants."""

    # Organization permissions
    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    ORG_DELETE = "org:delete"

    # User permissions
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    USERS_MANAGE_ROLES = "users:manage_roles"

    # Agent permissions
    AGENTS_READ = "agents:read"
    AGENTS_CREATE = "agents:create"
    AGENTS_UPDATE = "agents:update"
    AGENTS_UPDATE_OWN = "agents:update:own"
    AGENTS_DELETE = "agents:delete"
    AGENTS_DELETE_OWN = "agents:delete:own"
    AGENTS_EXECUTE = "agents:execute"

    # Tool permissions
    TOOLS_READ = "tools:read"
    TOOLS_CREATE = "tools:create"
    TOOLS_UPDATE = "tools:update"
    TOOLS_UPDATE_OWN = "tools:update:own"
    TOOLS_DELETE = "tools:delete"
    TOOLS_DELETE_OWN = "tools:delete:own"

    # Credential permissions
    CREDENTIALS_READ = "credentials:read"
    CREDENTIALS_CREATE = "credentials:create"
    CREDENTIALS_UPDATE = "credentials:update"
    CREDENTIALS_DELETE = "credentials:delete"

    # Deployment permissions
    DEPLOYMENTS_READ = "deployments:read"
    DEPLOYMENTS_CREATE = "deployments:create"
    DEPLOYMENTS_CREATE_NON_PROD = "deployments:create:non_prod"
    DEPLOYMENTS_UPDATE = "deployments:update"
    DEPLOYMENTS_DELETE = "deployments:delete"

    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # Audit permissions
    AUDIT_READ = "audit:read"
