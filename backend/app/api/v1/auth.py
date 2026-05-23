from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid
import asyncio
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
import re

from app.services.system_log_service import system_log

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    create_impersonation_token,
    decode_token,
)
from app.models.user import User, Organization
from app.models.audit_log import AuditLog, AuditAction
from app.api.deps import get_current_active_user, require_platform_admin, get_impersonation_context

router = APIRouter()


# ============== Schemas ==============

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    role: Optional[str] = None
    # Organisation profile
    website: Optional[str] = None
    phone_number: Optional[str] = None
    country: Optional[str] = None
    industry: str = "Other"
    employee_count: str = "1-10"
    intended_use_case: Optional[str] = None


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
    # Org approval gate status — "pending", "active", "rejected", "suspended"
    orgApprovalStatus: Optional[str] = None
    # Products the organisation is subscribed to — e.g. ["agentstudio", "demystrag", "mock_api"]
    products: List[str] = []
    # Impersonation context — only populated when the caller uses an impersonation token
    isImpersonated: bool = False
    impersonatedBy: Optional[str] = None  # Admin user ID that started the session

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
    """Get user's role display names from UserRole table."""
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
        return []


async def get_primary_role_name(db: AsyncSession, user: User) -> str:
    """Get user's primary RBAC role name (e.g. 'developer', 'org_admin') for JWT claim."""
    try:
        from app.models.role import UserRole, Role
        result = await db.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
            .limit(1)
        )
        role_name = result.scalar_one_or_none()
        return role_name or (user.role.value.lower() if user.role else "viewer")
    except Exception:
        return user.role.value.lower() if user.role else "viewer"


def build_token_claims(user: User, org: Organization, plan, role_name: str) -> dict:
    """
    Build enriched JWT claims from user, org and subscription plan.
    Called at login and refresh so sub-apps can authorise without querying AgentStudio.
    """
    products = ["agentstudio"]
    plan_limits = {
        "max_users": 5,
        "max_documents": 100,
        "max_storage_mb": 1000,
        "max_collections": 5,
        "embedding_providers": ["openai"],
    }

    if plan:
        features = plan.features or {}
        if plan.has_feature("has_demystrag"):
            products.append("demystrag")
        if plan.has_feature("has_mock_api"):
            products.append("mock_api")
        plan_limits = {
            "max_users": plan.max_users,
            "max_documents": features.get("demystrag_max_documents", 100),
            "max_storage_mb": features.get("demystrag_max_storage_mb", 1000),
            "max_collections": features.get("demystrag_max_collections", 5),
            "embedding_providers": features.get("demystrag_embedding_providers", ["openai"]),
        }

    return {
        "sub": str(user.id),
        "email": user.email,
        "full_name": getattr(user, "full_name", None),
        "org_id": str(org.id),
        "org_name": org.name,
        "org_slug": org.slug or "",
        "org_role": role_name,
        "is_platform_admin": bool(getattr(user, "is_platform_admin", False)),
        "products": products,
        "plan_limits": {
            **plan_limits,
            # demystrag_ prefixed aliases — DemystRAG reads these keys
            "demystrag_max_documents": plan_limits.get("max_documents", 100),
            "demystrag_max_storage_mb": plan_limits.get("max_storage_mb", 1000),
        },
    }


async def assign_role_to_user(db: AsyncSession, user_id: uuid.UUID, role_name: str, organization_id: uuid.UUID) -> bool:
    """Assign a role to a user in the user_roles table."""
    try:
        from app.models.role import UserRole, Role

        # Find the role by name
        result = await db.execute(
            select(Role).where(
                Role.name == role_name,
                Role.organization_id.is_(None),  # System roles have no org_id
                Role.is_system_role == True
            )
        )
        role = result.scalar_one_or_none()

        if not role:
            return False

        # Create user role assignment
        user_role = UserRole(
            user_id=user_id,
            role_id=role.id,
            organization_id=organization_id,
        )
        db.add(user_role)
        return True
    except Exception as e:
        print(f"Error assigning role: {e}")
        return False


def build_user_response(
    user: User,
    roles: List[str],
    org_name: Optional[str] = None,
    org_approval_status: Optional[str] = None,
    products: Optional[List[str]] = None,
) -> UserResponseAuth:
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
        orgApprovalStatus=org_approval_status,
        products=products or [],
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

        # Create new organization — starts PENDING until a platform admin approves it
        organization = Organization(
            name=user_data.organization_name,
            slug=generate_slug(user_data.organization_name),
            approval_status="pending",
            website=user_data.website,
            phone_number=user_data.phone_number,
            country=user_data.country,
            industry=user_data.industry,
            employee_count=user_data.employee_count,
            intended_use_case=user_data.intended_use_case,
        )
        db.add(organization)
        await db.flush()
        org_name = organization.name
    else:
        # No organization provided - create a default one for the user (also starts PENDING)
        default_org_name = f"{user_data.email.split('@')[0]}'s Organization"
        organization = Organization(
            name=default_org_name,
            slug=generate_slug(default_org_name),
            approval_status="pending",
            website=user_data.website,
            phone_number=user_data.phone_number,
            country=user_data.country,
            industry=user_data.industry,
            employee_count=user_data.employee_count,
            intended_use_case=user_data.intended_use_case,
        )
        db.add(organization)
        await db.flush()
        org_name = organization.name

    # Determine user role
    role_value = "CREATOR"  # Default legacy role
    rbac_role_name = "developer"  # Default RBAC role
    if user_data.role:
        role_value = user_data.role.upper()

    # First user in org gets ADMIN/org_owner role
    org_users = await db.execute(
        select(User).where(User.organization_id == organization.id)
    )
    if not org_users.scalars().first():
        role_value = "ADMIN"
        rbac_role_name = "org_owner"

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
    await db.flush()  # Flush to get user.id

    # Assign RBAC role to user
    await assign_role_to_user(db, user.id, rbac_role_name, organization.id)

    await db.commit()
    await db.refresh(user)

    asyncio.create_task(system_log(
        "INFO", "auth",
        f"New user registered: {user.email}",
        {"organization": org_name, "role": rbac_role_name},
        "auth.register",
    ))

    # Get user roles for response
    roles = await get_user_roles(db, user)

    # Capture org approval status to include in response
    org_approval_status = getattr(organization, 'approval_status', None)

    # New org has no subscription plan yet — build_token_claims uses defaults
    claims = build_token_claims(user, organization, plan=None, role_name=rbac_role_name)
    access_token = create_access_token(claims)
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return RegisterResponse(
        user=build_user_response(user, roles, org_name, org_approval_status, claims.get("products")),
        tokens=TokenPair(
            accessToken=access_token,
            refreshToken=refresh_token,
        ),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Login user."""
    # Get client info for audit
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.organization).selectinload(Organization.subscription_plan)
        )
        .where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        # Log failed login attempt
        audit_log = AuditLog.create_log(
            action=AuditAction.USER_LOGIN_FAILED,
            resource_type="user",
            resource_id=str(user.id) if user else None,
            resource_name=credentials.email,
            user_id=user.id if user else None,
            user_email=credentials.email,
            organization_id=user.organization_id if user else None,
            ip_address=client_ip,
            user_agent=user_agent,
            status="failure",
            error_message="Invalid credentials",
            metadata={"reason": "invalid_password" if user else "user_not_found"},
        )
        db.add(audit_log)
        await db.commit()

        asyncio.create_task(system_log(
            "WARNING", "auth",
            f"Login failed: {credentials.email}",
            {"reason": "invalid_password" if user else "user_not_found", "ip": client_ip},
            "auth.login",
        ))

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if user is active
    if hasattr(user, 'is_active') and not user.is_active:
        # Log failed login due to deactivation
        audit_log = AuditLog.create_log(
            action=AuditAction.USER_LOGIN_FAILED,
            resource_type="user",
            resource_id=str(user.id),
            resource_name=user.email,
            user_id=user.id,
            user_email=user.email,
            organization_id=user.organization_id,
            ip_address=client_ip,
            user_agent=user_agent,
            status="failure",
            error_message="Account deactivated",
            metadata={"reason": "account_deactivated"},
        )
        db.add(audit_log)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Org approval gate — platform admins bypass
    is_platform_admin = bool(getattr(user, "is_platform_admin", False))
    if not is_platform_admin and user.organization:
        approval_status = getattr(user.organization, "approval_status", "active")
        if approval_status == "pending":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your organisation is pending approval. You will be notified when access is granted.",
            )
        elif approval_status in ("rejected", "suspended"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: organisation is {approval_status}.",
            )

    # Update last login
    if hasattr(user, 'last_login_at'):
        user.last_login_at = datetime.utcnow()

    # Log successful login
    audit_log = AuditLog.create_log(
        action=AuditAction.USER_LOGIN,
        resource_type="user",
        resource_id=str(user.id),
        resource_name=user.email,
        user_id=user.id,
        user_email=user.email,
        organization_id=user.organization_id,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success",
        metadata={"login_method": "email_password"},
    )
    db.add(audit_log)
    await db.commit()

    asyncio.create_task(system_log(
        "INFO", "auth",
        f"User logged in: {user.email}",
        {"organization": user.organization.name if user.organization else None, "ip": client_ip},
        "auth.login",
    ))

    # Get user roles
    roles = await get_user_roles(db, user)
    role_name = await get_primary_role_name(db, user)

    # Get org name and approval status
    org = user.organization
    org_name = org.name if org else None
    org_approval_status = getattr(org, 'approval_status', None) if org else None
    plan = org.subscription_plan if org else None

    # Create enriched tokens
    claims = build_token_claims(user, org, plan, role_name) if org else {"sub": str(user.id)}
    access_token = create_access_token(claims)
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return LoginResponse(
        user=build_user_response(user, roles, org_name, org_approval_status, claims.get("products")),
        tokens=TokenPair(
            accessToken=access_token,
            refreshToken=refresh_token,
        ),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token with re-derived enriched claims."""
    payload = decode_token(data.refreshToken)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.organization).selectinload(Organization.subscription_plan)
        )
        .where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user or not getattr(user, "is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    org = user.organization
    plan = org.subscription_plan if org else None
    role_name = await get_primary_role_name(db, user)

    claims = build_token_claims(user, org, plan, role_name) if org else {"sub": str(user.id)}
    access_token = create_access_token(claims)
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenPair(
        accessToken=access_token,
        refreshToken=new_refresh_token,
    )


@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Logout user."""
    # Get client info for audit
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Log logout
    audit_log = AuditLog.create_log(
        action=AuditAction.USER_LOGOUT,
        resource_type="user",
        resource_id=str(current_user.id),
        resource_name=current_user.email,
        user_id=current_user.id,
        user_email=current_user.email,
        organization_id=current_user.organization_id,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success",
    )
    db.add(audit_log)
    await db.commit()

    return {"message": "Logged out successfully"}


class ImpersonateResponse(BaseModel):
    accessToken: str
    targetUser: UserResponseAuth


# /impersonate/end must be defined BEFORE /impersonate/{user_id} so FastAPI
# doesn't treat the literal string "end" as a user_id path segment.
@router.post("/impersonate/end")
async def end_impersonation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    impersonated_by: Optional[str] = Depends(get_impersonation_context),
):
    """
    End an active impersonation session.
    The client is responsible for restoring the real admin token after calling this.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    db.add(AuditLog.create_log(
        action=AuditAction.IMPERSONATE_END,
        resource_type="user",
        resource_id=str(current_user.id),
        resource_name=current_user.email,
        user_id=current_user.id,
        user_email=current_user.email,
        organization_id=current_user.organization_id,
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={"admin_user_id": impersonated_by},
    ))
    await db.commit()
    return {"message": "Impersonation ended"}


@router.post("/impersonate/{user_id}", response_model=ImpersonateResponse)
async def impersonate_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_platform_admin),
    current_impersonation: Optional[str] = Depends(get_impersonation_context),
):
    """
    Platform Admin only: start impersonating a user for troubleshooting.
    Issues a 30-minute impersonation token scoped to the target user.
    Blocked if the caller is already using an impersonation token.
    """
    if current_impersonation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot impersonate while already in an impersonation session. End the current session first.",
        )

    # Load target user
    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == target_uuid, User.deleted_at.is_(None))
    )
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Platform admins cannot impersonate other platform admins
    if target_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate another Platform Admin",
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    token = create_impersonation_token(str(target_user.id), str(admin_user.id))

    db.add(AuditLog.create_log(
        action=AuditAction.IMPERSONATE_START,
        resource_type="user",
        resource_id=str(target_user.id),
        resource_name=target_user.email,
        user_id=admin_user.id,
        user_email=admin_user.email,
        organization_id=target_user.organization_id,
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={
            "admin_user_id": str(admin_user.id),
            "admin_email": admin_user.email,
            "target_user_id": str(target_user.id),
            "target_email": target_user.email,
        },
    ))
    await db.commit()

    roles = await get_user_roles(db, target_user)
    org_name = target_user.organization.name if target_user.organization else None
    target_response = UserResponseAuth(
        **build_user_response(target_user, roles, org_name).model_dump(),
        isImpersonated=True,
        impersonatedBy=str(admin_user.id),
    )

    return ImpersonateResponse(accessToken=token, targetUser=target_response)


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
    impersonated_by: Optional[str] = Depends(get_impersonation_context),
):
    """Get current user info. Includes impersonation context when applicable."""
    org_name = None
    org_approval_status = None
    if current_user.organization_id:
        org_result = await db.execute(
            select(Organization).where(Organization.id == current_user.organization_id)
        )
        org = org_result.scalar_one_or_none()
        if org:
            org_name = org.name
            org_approval_status = getattr(org, 'approval_status', None)

    roles = await get_user_roles(db, current_user)
    role_name = await get_primary_role_name(db, current_user)

    products_list: List[str] = []
    if current_user.organization_id:
        org_result2 = await db.execute(
            select(Organization).where(Organization.id == current_user.organization_id)
        )
        org2 = org_result2.scalar_one_or_none()
        if org2:
            plan2 = org2.subscription_plan if org2 else None
            claims2 = build_token_claims(current_user, org2, plan2, role_name)
            products_list = claims2.get("products", [])

    base = build_user_response(current_user, roles, org_name, org_approval_status, products_list)

    return UserResponseAuth(
        **base.model_dump(),
        isImpersonated=impersonated_by is not None,
        impersonatedBy=impersonated_by,
    )


@router.post("/repair-my-roles")
async def repair_current_user_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Self-service endpoint to repair missing RBAC role assignments.
    Call this if you're getting 403 errors on endpoints you should have access to.
    """
    from app.models.role import UserRole as UserRoleAssignment, Role
    from sqlalchemy import func

    # Check if user already has role assignments
    existing_roles = await db.execute(
        select(UserRoleAssignment).where(UserRoleAssignment.user_id == current_user.id)
    )
    existing = existing_roles.scalars().all()

    if existing:
        roles = await get_user_roles(db, current_user)
        return {
            "message": "User already has role assignments",
            "roles": roles,
            "repaired": False
        }

    # Map legacy roles to RBAC roles
    legacy_to_rbac = {
        "ADMIN": "org_admin",
        "CREATOR": "developer",
        "VIEWER": "viewer",
    }

    # Get the legacy role value
    legacy_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role).upper()
    rbac_role_name = legacy_to_rbac.get(legacy_role, "developer")

    # Check if this is the only user in their org - they should be org_owner
    org_users_count = await db.execute(
        select(func.count(User.id)).where(
            User.organization_id == current_user.organization_id,
            User.deleted_at.is_(None),
        )
    )
    count = org_users_count.scalar() or 0

    # If only user in org and they're an admin, make them org_owner
    if count == 1 and legacy_role == "ADMIN":
        rbac_role_name = "org_owner"

    # Find the role
    role_result = await db.execute(
        select(Role).where(
            Role.name == rbac_role_name,
            Role.organization_id.is_(None),
            Role.is_system_role == True
        )
    )
    role = role_result.scalar_one_or_none()

    if not role:
        return {
            "message": f"Role '{rbac_role_name}' not found in database. Please contact administrator.",
            "repaired": False,
            "error": True
        }

    # Create user role assignment
    user_role_assignment = UserRoleAssignment(
        user_id=current_user.id,
        role_id=role.id,
        organization_id=current_user.organization_id,
    )
    db.add(user_role_assignment)
    await db.commit()

    # Get updated roles
    roles = await get_user_roles(db, current_user)

    return {
        "message": f"Successfully assigned role: {role.display_name}",
        "roles": roles,
        "repaired": True,
        "assigned_role": role.display_name
    }
