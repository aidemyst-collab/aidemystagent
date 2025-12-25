from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
import re

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User, Organization
from app.api.deps import get_current_active_user

router = APIRouter()


# ============== Schemas ==============

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    organization_id: Optional[str] = None  # Optional - can create new org
    organization_name: Optional[str] = None  # For creating new organization
    role: Optional[str] = None


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"


class UserRoleResponse(BaseModel):
    id: str
    name: str
    displayName: str


class UserResponseAuth(BaseModel):
    id: str
    email: str
    fullName: Optional[str] = None
    organizationId: Optional[str] = None
    organizationName: Optional[str] = None
    role: Optional[str] = None  # Legacy role
    roles: List[str] = []  # New RBAC roles
    isPlatformAdmin: bool = False
    isActive: bool = True
    emailVerified: bool = False
    createdAt: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    user: UserResponseAuth
    tokens: TokenPair


class RegisterResponse(BaseModel):
    user: UserResponseAuth
    tokens: TokenPair


class RefreshTokenRequest(BaseModel):
    refreshToken: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


# ============== Helper Functions ==============

def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from organization name."""
    slug = name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug[:100]


async def get_user_roles(db: AsyncSession, user: User) -> List[str]:
    """Get user's role names from UserRole table."""
    try:
        from app.models.role import UserRole, Role
        result = await db.execute(
            select(Role.display_name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
        roles = result.scalars().all()
        return list(roles) if roles else []
    except Exception:
        # Role tables might not exist yet
        return []


def build_user_response(user: User, roles: List[str], org_name: Optional[str] = None) -> UserResponseAuth:
    """Build user response from user model."""
    return UserResponseAuth(
        id=str(user.id),
        email=user.email,
        fullName=getattr(user, 'full_name', None),
        organizationId=str(user.organization_id) if user.organization_id else None,
        organizationName=org_name,
        role=user.role.value.lower() if user.role else None,
        roles=roles,
        isPlatformAdmin=getattr(user, 'is_platform_admin', False),
        isActive=getattr(user, 'is_active', True),
        emailVerified=getattr(user, 'email_verified', False),
        createdAt=user.created_at,
    )


# ============== Endpoints ==============

@router.post("/register", response_model=RegisterResponse)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user with optional organization creation."""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    organization = None
    org_name = None

    # If organization_id provided, verify it exists
    if user_data.organization_id:
        org_result = await db.execute(
            select(Organization).where(Organization.id == uuid.UUID(user_data.organization_id))
        )
        organization = org_result.scalar_one_or_none()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID",
            )
        org_name = organization.name
    # If organization_name provided, create new organization
    elif user_data.organization_name:
        # Check if org with same name exists
        existing_org = await db.execute(
            select(Organization).where(Organization.name == user_data.organization_name)
        )
        if existing_org.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name already exists",
            )

        # Create new organization
        organization = Organization(
            name=user_data.organization_name,
            slug=generate_slug(user_data.organization_name),
        )
        db.add(organization)
        await db.flush()
        org_name = organization.name
    else:
        # No organization provided - create a default one for the user
        default_org_name = f"{user_data.email.split('@')[0]}'s Organization"
        organization = Organization(
            name=default_org_name,
            slug=generate_slug(default_org_name),
        )
        db.add(organization)
        await db.flush()
        org_name = organization.name

    # Determine user role
    role_value = "CREATOR"  # Default
    if user_data.role:
        role_value = user_data.role.upper()

    # First user in org gets ADMIN role
    org_users = await db.execute(
        select(User).where(User.organization_id == organization.id)
    )
    if not org_users.scalars().first():
        role_value = "ADMIN"

    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        organization_id=organization.id,
        role=role_value,
    )

    # Set optional fields if they exist on the model
    if hasattr(user, 'full_name') and user_data.full_name:
        user.full_name = user_data.full_name
    if hasattr(user, 'is_active'):
        user.is_active = True

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Get user roles
    roles = await get_user_roles(db, user)

    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return RegisterResponse(
        user=build_user_response(user, roles, org_name),
        tokens=TokenPair(
            accessToken=access_token,
            refreshToken=refresh_token,
        ),
    )


@router.post("/login", response_model=LoginResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if user is active
    if hasattr(user, 'is_active') and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    if hasattr(user, 'last_login_at'):
        user.last_login_at = datetime.utcnow()
        await db.commit()

    # Get user roles
    roles = await get_user_roles(db, user)

    # Get org name
    org_name = user.organization.name if user.organization else None

    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return LoginResponse(
        user=build_user_response(user, roles, org_name),
        tokens=TokenPair(
            accessToken=access_token,
            refreshToken=refresh_token,
        ),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(data: RefreshTokenRequest):
    """Refresh access token."""
    payload = decode_token(data.refreshToken)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    access_token = create_access_token({"sub": user_id})
    new_refresh_token = create_refresh_token({"sub": user_id})

    return TokenPair(
        accessToken=access_token,
        refreshToken=new_refresh_token,
    )


@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)."""
    return {"message": "Logged out successfully"}


@router.post("/reset-password")
async def reset_password(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Request password reset."""
    # In a real app, send email with reset link
    # For now, just return success
    return {"message": "Password reset email sent"}


@router.get("/me", response_model=UserResponseAuth)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current user info."""
    # Load organization
    org_name = None
    if current_user.organization_id:
        org_result = await db.execute(
            select(Organization).where(Organization.id == current_user.organization_id)
        )
        org = org_result.scalar_one_or_none()
        org_name = org.name if org else None

    # Get user roles
    roles = await get_user_roles(db, current_user)

    return build_user_response(current_user, roles, org_name)
