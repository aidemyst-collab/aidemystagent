"""
API endpoints for user invitations management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import Organization, User, UserRole as UserRoleEnum
from app.models.invitation import Invitation, InvitationStatus
from app.models.role import Role, UserRole
from app.api.deps import get_current_active_user, require_permission, require_org_admin
from app.services.email_service import send_invitation_email


# ============== Schemas ==============

class InvitationCreate(BaseModel):
    email: EmailStr
    role_id: UUID
    message: Optional[str] = Field(None, max_length=500)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationResponse(BaseModel):
    id: str
    email: str
    organization_id: str
    organization_name: str
    role_id: str
    role_name: str
    status: str
    message: Optional[str] = None
    invited_by: Optional[str] = None
    inviter_name: Optional[str] = None
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvitationListResponse(BaseModel):
    invitations: List[InvitationResponse]
    total: int


class AcceptInvitationRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)


class AcceptInvitationResponse(BaseModel):
    message: str
    user_id: str
    organization_id: str
    organization_name: str


router = APIRouter()


# ============== Role Listing for Invitations ==============
# NOTE: This must come BEFORE dynamic routes like /{invitation_id}
# to avoid FastAPI matching "roles" as an invitation_id

@router.get("/roles/available")
async def list_available_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("users:read")),
):
    """
    List roles available for invitations.
    Returns organization roles that can be assigned to new users.
    """
    # Get system roles (excluding super_admin)
    system_roles_query = select(Role).where(
        Role.is_system_role == True,
        Role.name != "super_admin",
    ).order_by(Role.name)

    result = await db.execute(system_roles_query)
    roles = result.scalars().all()

    # Also get custom organization roles if any
    custom_roles_query = select(Role).where(
        Role.organization_id == current_user.organization_id,
        Role.is_system_role == False,
    ).order_by(Role.name)

    custom_result = await db.execute(custom_roles_query)
    custom_roles = custom_result.scalars().all()

    all_roles = list(roles) + list(custom_roles)

    return {
        "roles": [
            {
                "id": str(role.id),
                "name": role.name,
                "display_name": role.display_name,
                "description": role.description,
                "is_system_role": role.is_system_role,
            }
            for role in all_roles
        ]
    }


async def get_invitation_response(
    db: AsyncSession,
    invitation: Invitation
) -> InvitationResponse:
    """Helper to build invitation response with related data."""
    # Get organization name
    org_result = await db.execute(
        select(Organization.name).where(Organization.id == invitation.organization_id)
    )
    org_name = org_result.scalar() or "Unknown"

    # Get role name
    role_result = await db.execute(
        select(Role.display_name).where(Role.id == invitation.role_id)
    )
    role_name = role_result.scalar() or "Unknown"

    # Get inviter name
    inviter_name = None
    if invitation.invited_by:
        inviter_result = await db.execute(
            select(User.full_name, User.email).where(User.id == invitation.invited_by)
        )
        inviter = inviter_result.one_or_none()
        if inviter:
            inviter_name = inviter.full_name or inviter.email

    return InvitationResponse(
        id=str(invitation.id),
        email=invitation.email,
        organization_id=str(invitation.organization_id),
        organization_name=org_name,
        role_id=str(invitation.role_id),
        role_name=role_name,
        status=invitation.status.value,
        message=invitation.message,
        invited_by=str(invitation.invited_by) if invitation.invited_by else None,
        inviter_name=inviter_name,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        created_at=invitation.created_at,
    )


@router.post("", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invitation_data: InvitationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    Send an invitation to join the organization.
    Requires org admin permission.
    """
    email = invitation_data.email.lower().strip()

    # Check if user already exists in the organization
    existing_user = await db.execute(
        select(User).where(
            User.email == email,
            User.organization_id == current_user.organization_id,
            User.deleted_at.is_(None),
        )
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists in the organization",
        )

    # Check for existing pending invitation
    existing_invitation = await db.execute(
        select(Invitation).where(
            Invitation.email == email,
            Invitation.organization_id == current_user.organization_id,
            Invitation.status == InvitationStatus.PENDING,
        )
    )
    if existing_invitation.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email",
        )

    # Verify the role exists and is valid
    role_result = await db.execute(
        select(Role).where(
            Role.id == invitation_data.role_id,
            # Role must be an organization role (not super_admin)
            Role.name != "super_admin",
        )
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found or not assignable",
        )

    # Get org name for the email
    org_result = await db.execute(
        select(Organization.name).where(Organization.id == current_user.organization_id)
    )
    org_name_for_email = org_result.scalar() or "your organization"

    # Create the invitation
    invitation = Invitation.create_invitation(
        organization_id=current_user.organization_id,
        email=email,
        role_id=invitation_data.role_id,
        invited_by=current_user.id,
        message=invitation_data.message,
        expires_in_days=invitation_data.expires_in_days,
    )

    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    # Send invitation email in the background (non-blocking — failure doesn't affect response)
    background_tasks.add_task(
        send_invitation_email,
        to_email=invitation.email,
        inviter_name=current_user.full_name or current_user.email,
        org_name=org_name_for_email,
        role_name=role.display_name,
        token=invitation.token,
        personal_message=invitation_data.message,
    )

    return await get_invitation_response(db, invitation)


@router.get("", response_model=InvitationListResponse)
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("users:read")),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
):
    """
    List invitations for the current user's organization.
    """
    query = select(Invitation).where(
        Invitation.organization_id == current_user.organization_id
    )

    if status_filter:
        try:
            status_enum = InvitationStatus(status_filter)
            query = query.where(Invitation.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}. Valid values: pending, accepted, expired, revoked",
            )

    # Count query
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    query = query.order_by(Invitation.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    invitations = result.scalars().all()

    invitation_responses = []
    for inv in invitations:
        invitation_responses.append(await get_invitation_response(db, inv))

    return InvitationListResponse(invitations=invitation_responses, total=total)


@router.get("/{invitation_id}", response_model=InvitationResponse)
async def get_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("users:read")),
):
    """
    Get a specific invitation by ID.
    """
    result = await db.execute(
        select(Invitation).where(Invitation.id == invitation_id)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Check organization access
    if invitation.organization_id != current_user.organization_id and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this invitation",
        )

    return await get_invitation_response(db, invitation)


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    Revoke a pending invitation.
    Requires org admin permission.
    """
    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.organization_id == current_user.organization_id,
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot revoke invitation with status: {invitation.status.value}",
        )

    invitation.revoke()
    await db.commit()

    return None


@router.post("/{invitation_id}/resend", response_model=InvitationResponse)
async def resend_invitation(
    invitation_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    Resend an invitation by generating a new token and extending expiration.
    Requires org admin permission.
    """
    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.organization_id == current_user.organization_id,
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status not in [InvitationStatus.PENDING, InvitationStatus.EXPIRED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resend invitation with status: {invitation.status.value}",
        )

    # Generate new token and extend expiration
    from datetime import timedelta
    invitation.token = Invitation.generate_token()
    invitation.expires_at = datetime.utcnow() + timedelta(days=7)
    invitation.status = InvitationStatus.PENDING

    await db.commit()
    await db.refresh(invitation)

    # Re-fetch role for display name
    role_for_email_result = await db.execute(
        select(Role).where(Role.id == invitation.role_id)
    )
    role_for_email = role_for_email_result.scalar_one_or_none()

    # Re-fetch org name
    org_for_email_result = await db.execute(
        select(Organization.name).where(Organization.id == invitation.organization_id)
    )
    org_name_for_email = org_for_email_result.scalar() or "your organization"

    background_tasks.add_task(
        send_invitation_email,
        to_email=invitation.email,
        inviter_name=current_user.full_name or current_user.email,
        org_name=org_name_for_email,
        role_name=role_for_email.display_name if role_for_email else "Member",
        token=invitation.token,
        personal_message=None,
    )

    return await get_invitation_response(db, invitation)


# ============== Public Endpoints ==============

@router.get("/verify/{token}")
async def verify_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify an invitation token and return invitation details.
    Public endpoint - no authentication required.
    """
    result = await db.execute(
        select(Invitation).where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token",
        )

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation is no longer valid: {invitation.status.value}",
        )

    if invitation.is_expired:
        invitation.mark_expired()
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    # Get organization and role info
    org_result = await db.execute(
        select(Organization).where(Organization.id == invitation.organization_id)
    )
    org = org_result.scalar_one_or_none()

    role_result = await db.execute(
        select(Role).where(Role.id == invitation.role_id)
    )
    role = role_result.scalar_one_or_none()

    return {
        "email": invitation.email,
        "organization_name": org.name if org else "Unknown",
        "role_name": role.display_name if role else "Unknown",
        "message": invitation.message,
        "expires_at": invitation.expires_at.isoformat(),
    }


@router.post("/accept/{token}", response_model=AcceptInvitationResponse)
async def accept_invitation(
    token: str,
    accept_data: AcceptInvitationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept an invitation and create a new user account.
    Public endpoint - no authentication required.
    """
    result = await db.execute(
        select(Invitation).where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token",
        )

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation is no longer valid: {invitation.status.value}",
        )

    if invitation.is_expired:
        invitation.mark_expired()
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    # Check if user already exists with this email
    existing_user = await db.execute(
        select(User).where(
            User.email == invitation.email,
            User.deleted_at.is_(None),
        )
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Get organization
    org_result = await db.execute(
        select(Organization).where(
            Organization.id == invitation.organization_id,
            Organization.deleted_at.is_(None),
            Organization.is_active == True,
        )
    )
    org = org_result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization is no longer active",
        )

    from app.services.quota_service import check_users_quota
    await check_users_quota(db, invitation.organization_id)

    # Create the new user
    new_user = User(
        email=invitation.email,
        hashed_password=get_password_hash(accept_data.password),
        full_name=accept_data.full_name,
        organization_id=invitation.organization_id,
        role=UserRoleEnum.CREATOR,  # Default legacy role
        is_active=True,
        email_verified=True,  # Consider email verified through invitation
        email_verified_at=datetime.utcnow(),
    )

    db.add(new_user)
    await db.flush()  # Get the user ID

    # Assign the role
    user_role = UserRole(
        user_id=new_user.id,
        role_id=invitation.role_id,
        organization_id=invitation.organization_id,
        assigned_by=invitation.invited_by,
    )
    db.add(user_role)

    # Mark invitation as accepted
    invitation.accept(new_user.id)

    await db.commit()
    await db.refresh(new_user)

    return AcceptInvitationResponse(
        message="Invitation accepted successfully. You can now log in.",
        user_id=str(new_user.id),
        organization_id=str(org.id),
        organization_name=org.name,
    )


