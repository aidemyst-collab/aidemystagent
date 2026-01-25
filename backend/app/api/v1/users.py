"""
API endpoints for user management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.role import Role, UserRole
from app.api.deps import get_current_active_user, require_permission, require_org_admin, get_effective_organization_id
from pydantic import BaseModel, EmailStr, Field


# ============== Schemas ==============

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str  # Legacy role field
    organization_id: str
    is_active: bool
    is_platform_admin: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    roles: List[str] = []  # RBAC roles

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response with additional fields."""
    avatar_url: Optional[str] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    avatar_url: Optional[str] = None


class UserRoleAssign(BaseModel):
    role_id: UUID


class UserRoleResponse(BaseModel):
    id: str
    role_id: str
    role_name: str
    role_display_name: str
    assigned_at: datetime
    assigned_by: Optional[str] = None

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    is_system_role: bool
    permissions: List[str] = []

    class Config:
        from_attributes = True


router = APIRouter()


# ============== Role Listing ==============
# NOTE: This must come BEFORE dynamic routes like /{user_id}
# to avoid FastAPI matching "roles" as a user_id

@router.get("/roles/available", response_model=List[RoleResponse])
async def list_available_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("users:read")),
):
    """
    List all roles available for assignment in the organization.
    """
    # Get system roles (excluding super_admin)
    query = select(Role).where(
        Role.name != "super_admin",
    ).order_by(Role.name)

    result = await db.execute(query)
    roles = result.scalars().all()

    return [
        RoleResponse(
            id=str(role.id),
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            is_system_role=role.is_system_role,
            permissions=role.permissions or [],
        )
        for role in roles
    ]


async def get_user_roles(db: AsyncSession, user_id: UUID, organization_id: UUID) -> List[str]:
    """Get list of role names for a user in an organization."""
    result = await db.execute(
        select(Role.display_name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            UserRole.organization_id == organization_id,
        )
    )
    return [row[0] for row in result.all()]


async def build_user_response(db: AsyncSession, user: User) -> UserResponse:
    """Build a UserResponse with roles."""
    roles = await get_user_roles(db, user.id, user.organization_id)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        organization_id=str(user.organization_id),
        is_active=user.is_active,
        is_platform_admin=user.is_platform_admin,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=roles,
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("users:read")),
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
):
    """
    List all users in the effective organization (supports admin "Viewing As" feature).
    Excludes platform admins from the list.
    """
    query = select(User).where(
        User.organization_id == effective_org_id,
        User.deleted_at.is_(None),
        User.is_platform_admin == False,  # Exclude platform admins
    )

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") |
            User.full_name.ilike(f"%{search}%")
        )

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    user_responses = []
    for user in users:
        user_responses.append(await build_user_response(db, user))

    return UserListResponse(users=user_responses, total=total)


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the current user's profile.
    """
    roles = await get_user_roles(db, current_user.id, current_user.organization_id)

    return UserDetailResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        organization_id=str(current_user.organization_id),
        is_active=current_user.is_active,
        is_platform_admin=current_user.is_platform_admin,
        email_verified=current_user.email_verified,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        roles=roles,
        avatar_url=current_user.avatar_url,
        failed_login_attempts=current_user.failed_login_attempts,
        locked_until=current_user.locked_until,
    )


@router.patch("/me", response_model=UserDetailResponse)
async def update_current_user_profile(
    update_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update the current user's profile.
    """
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name

    if update_data.avatar_url is not None:
        current_user.avatar_url = update_data.avatar_url

    await db.commit()
    await db.refresh(current_user)

    roles = await get_user_roles(db, current_user.id, current_user.organization_id)

    return UserDetailResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        organization_id=str(current_user.organization_id),
        is_active=current_user.is_active,
        is_platform_admin=current_user.is_platform_admin,
        email_verified=current_user.email_verified,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        roles=roles,
        avatar_url=current_user.avatar_url,
        failed_login_attempts=current_user.failed_login_attempts,
        locked_until=current_user.locked_until,
    )


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("users:read")),
):
    """
    Get a specific user by ID.
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if user is in the same organization (unless platform admin)
    if user.organization_id != current_user.organization_id and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this user",
        )

    roles = await get_user_roles(db, user.id, user.organization_id)

    return UserDetailResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        organization_id=str(user.organization_id),
        is_active=user.is_active,
        is_platform_admin=user.is_platform_admin,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=roles,
        avatar_url=user.avatar_url,
        failed_login_attempts=user.failed_login_attempts,
        locked_until=user.locked_until,
    )


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_org_admin),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Deactivate a user account.
    Requires org admin permission. Supports "Viewing As" feature.
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == effective_org_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate yourself",
        )

    if user.is_platform_admin and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate a platform admin",
        )

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    return await build_user_response(db, user)


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_org_admin),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Reactivate a user account.
    Requires org admin permission. Supports "Viewing As" feature.
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == effective_org_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = True
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
    await db.refresh(user)

    return await build_user_response(db, user)


@router.post("/{user_id}/unlock", response_model=UserResponse)
async def unlock_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_org_admin),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Unlock a locked user account.
    Requires org admin permission. Supports "Viewing As" feature.
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == effective_org_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.reset_failed_logins()
    await db.commit()
    await db.refresh(user)

    return await build_user_response(db, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("users:delete")),
):
    """
    Soft delete a user (admin only).
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if user is in the same organization
    if user.organization_id != current_user.organization_id and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete users from your organization",
        )

    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself",
        )

    # Prevent deleting platform admins unless you are one
    if user.is_platform_admin and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete a platform admin",
        )

    # Soft delete
    user.deleted_at = datetime.utcnow()
    user.is_active = False
    await db.commit()

    return None


# ============== Role Management ==============

@router.get("/{user_id}/roles", response_model=List[UserRoleResponse])
async def get_user_roles_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("users:read")),
):
    """
    Get all roles assigned to a user.
    """
    # Verify user exists and is in same org
    user_result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.organization_id != current_user.organization_id and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this user",
        )

    # Get user roles
    result = await db.execute(
        select(UserRole, Role)
        .join(Role, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            UserRole.organization_id == user.organization_id,
        )
    )
    user_roles = result.all()

    return [
        UserRoleResponse(
            id=str(ur.id),
            role_id=str(role.id),
            role_name=role.name,
            role_display_name=role.display_name,
            assigned_at=ur.assigned_at,
            assigned_by=str(ur.assigned_by) if ur.assigned_by else None,
        )
        for ur, role in user_roles
    ]


@router.post("/{user_id}/roles", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    user_id: UUID,
    role_data: UserRoleAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_org_admin),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Assign a role to a user.
    Requires org admin permission. Supports "Viewing As" feature.
    """
    # Verify user exists and is in effective org
    user_result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == effective_org_id,
            User.deleted_at.is_(None),
        )
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify role exists and is assignable
    role_result = await db.execute(
        select(Role).where(
            Role.id == role_data.role_id,
            Role.name != "super_admin",  # Can't assign super_admin role
        )
    )
    role = role_result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found or not assignable",
        )

    # Check if user already has this role
    existing = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_data.role_id,
            UserRole.organization_id == effective_org_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has this role",
        )

    # Create role assignment
    user_role = UserRole(
        user_id=user_id,
        role_id=role_data.role_id,
        organization_id=effective_org_id,
        assigned_by=current_user.id,
    )

    db.add(user_role)
    await db.commit()
    await db.refresh(user_role)

    return UserRoleResponse(
        id=str(user_role.id),
        role_id=str(role.id),
        role_name=role.name,
        role_display_name=role.display_name,
        assigned_at=user_role.assigned_at,
        assigned_by=str(current_user.id),
    )


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_org_admin),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Remove a role from a user.
    Requires org admin permission. Supports "Viewing As" feature.
    """
    # Verify user exists and is in effective org
    user_result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == effective_org_id,
            User.deleted_at.is_(None),
        )
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Find the role assignment
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.organization_id == effective_org_id,
        )
    )
    user_role = result.scalar_one_or_none()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have this role",
        )

    await db.delete(user_role)
    await db.commit()

    return None


