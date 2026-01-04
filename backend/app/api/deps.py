from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional, List, Callable

from app.core.database import get_db
from app.core.security import decode_token
from app.core.logging_config import logger
from app.models.user import User
from app.services.permission_service import PermissionService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    """
    token = credentials.credentials
    logger.info(f"Auth attempt - Token received (length: {len(token) if token else 0})")
    logger.info(f"Token starts with: {token[:30] if token else 'None'}...")

    # Decode and validate token
    payload = decode_token(token)
    logger.info(f"Token decode result: {payload is not None}")

    if not payload:
        logger.error("Token decode failed - invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.deleted_at.is_(None))  # Exclude soft-deleted users
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current active user.
    Checks if user is active and not locked.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    if current_user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is temporarily locked",
        )

    return current_user


async def get_permission_service(
    db: AsyncSession = Depends(get_db),
) -> PermissionService:
    """Get an instance of the permission service."""
    return PermissionService(db)


def require_permission(permission: str):
    """
    Dependency factory to require a specific permission.

    Usage:
        @router.get("/")
        async def list_agents(
            current_user: User = Depends(get_current_active_user),
            _: None = Depends(require_permission("agents:read")),
        ):
            ...
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        permission_service: PermissionService = Depends(get_permission_service),
    ) -> None:
        has_perm = await permission_service.has_permission(current_user, permission)
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
    return permission_checker


def require_any_permission(permissions: List[str]):
    """
    Dependency factory to require any of the specified permissions.

    Usage:
        @router.get("/")
        async def endpoint(
            _: None = Depends(require_any_permission(["agents:read", "agents:*"])),
        ):
            ...
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        permission_service: PermissionService = Depends(get_permission_service),
    ) -> None:
        has_any = await permission_service.has_any_permission(current_user, permissions)
        if not has_any:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires one of {permissions}",
            )
    return permission_checker


def require_all_permissions(permissions: List[str]):
    """
    Dependency factory to require all of the specified permissions.

    Usage:
        @router.get("/")
        async def endpoint(
            _: None = Depends(require_all_permissions(["agents:read", "deployments:read"])),
        ):
            ...
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        permission_service: PermissionService = Depends(get_permission_service),
    ) -> None:
        has_all = await permission_service.has_all_permissions(current_user, permissions)
        if not has_all:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires all of {permissions}",
            )
    return permission_checker


async def require_platform_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency to require platform admin (super admin) access.

    Usage:
        @router.get("/admin/organizations")
        async def list_all_orgs(
            current_user: User = Depends(require_platform_admin),
        ):
            ...
    """
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return current_user


async def require_org_admin(
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
) -> User:
    """
    Dependency to require organization admin (org_owner or org_admin) access.

    Usage:
        @router.post("/organization/users/invite")
        async def invite_user(
            current_user: User = Depends(require_org_admin),
        ):
            ...
    """
    # Platform admins can do anything
    if current_user.is_platform_admin:
        return current_user

    # Check for org admin permissions
    has_perm = await permission_service.has_any_permission(
        current_user,
        ["org:*", "users:*"]
    )
    if not has_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin access required",
        )
    return current_user


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request."""
    # Check for forwarded headers (when behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Direct connection
    if request.client:
        return request.client.host

    return None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")


class OrganizationContext:
    """
    Context class that holds the effective organization for the current request.
    For platform admins, this may be different from their own organization.
    """
    def __init__(
        self,
        organization_id: UUID,
        is_switched: bool = False,
        original_org_id: Optional[UUID] = None
    ):
        self.organization_id = organization_id
        self.is_switched = is_switched
        self.original_org_id = original_org_id


async def get_organization_context(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationContext:
    """
    Get the effective organization context for the current request.

    Platform admins can switch to view other organizations by sending
    the X-Organization-Id header. Regular users always see their own org.

    Usage:
        @router.get("/agents")
        async def list_agents(
            org_context: OrganizationContext = Depends(get_organization_context),
        ):
            # Use org_context.organization_id for queries
            ...
    """
    # Check for organization switch header
    switch_org_header = request.headers.get("X-Organization-Id")

    if switch_org_header and current_user.is_platform_admin:
        try:
            switched_org_id = UUID(switch_org_header)

            # Verify the organization exists and is active
            from app.models.user import Organization
            result = await db.execute(
                select(Organization).where(
                    Organization.id == switched_org_id,
                    Organization.deleted_at.is_(None),
                )
            )
            org = result.scalar_one_or_none()

            if org:
                logger.info(
                    f"Platform admin {current_user.email} switched to org {org.name} ({switched_org_id})"
                )
                return OrganizationContext(
                    organization_id=switched_org_id,
                    is_switched=True,
                    original_org_id=current_user.organization_id,
                )
            else:
                logger.warning(
                    f"Platform admin {current_user.email} tried to switch to non-existent org {switch_org_header}"
                )
        except ValueError:
            logger.warning(f"Invalid organization ID in header: {switch_org_header}")

    # Default: use user's own organization
    return OrganizationContext(
        organization_id=current_user.organization_id,
        is_switched=False,
    )


async def get_effective_organization_id(
    org_context: OrganizationContext = Depends(get_organization_context),
) -> UUID:
    """
    Simple dependency that returns just the effective organization ID.

    Usage:
        @router.get("/agents")
        async def list_agents(
            org_id: UUID = Depends(get_effective_organization_id),
        ):
            # Use org_id for queries
            ...
    """
    return org_context.organization_id
