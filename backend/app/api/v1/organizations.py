"""
API endpoints for organization management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.user import Organization, User
from app.api.deps import get_current_active_user, require_permission
from pydantic import BaseModel, Field
import re


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from organization name."""
    slug = name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug[:100]


# Schemas
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    subscription_status: str
    trial_ends_at: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user_count: int = 0

    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    organizations: List[OrganizationResponse]
    total: int


class OrganizationSummary(BaseModel):
    """Minimal org info for public listing during registration."""
    id: str
    name: str
    slug: Optional[str] = None

    class Config:
        from_attributes = True


class OrganizationSummaryListResponse(BaseModel):
    organizations: List[OrganizationSummary]
    total: int


router = APIRouter()


@router.get("/public", response_model=OrganizationSummaryListResponse)
async def list_organizations_public(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    List all active organizations (public endpoint for registration).
    Returns minimal information only.
    """
    query = select(Organization).where(
        Organization.is_active == True,
        Organization.deleted_at.is_(None),
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    organizations = result.scalars().all()

    # Get total count
    count_query = select(func.count(Organization.id)).where(
        Organization.is_active == True,
        Organization.deleted_at.is_(None),
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    org_responses = [
        OrganizationSummary(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
        ) for org in organizations
    ]

    return OrganizationSummaryListResponse(organizations=org_responses, total=total)


@router.get("/", response_model=OrganizationListResponse)
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("organizations:read")),
    skip: int = 0,
    limit: int = 100,
):
    """
    List organizations.
    - Platform admins see all organizations
    - Regular users see only their organization
    """
    if current_user.is_platform_admin:
        # Platform admins can see all organizations
        query = select(Organization).where(
            Organization.deleted_at.is_(None),
        ).offset(skip).limit(limit)

        count_query = select(func.count(Organization.id)).where(
            Organization.deleted_at.is_(None),
        )
    else:
        # Regular users only see their own organization
        query = select(Organization).where(
            Organization.id == current_user.organization_id,
            Organization.deleted_at.is_(None),
        )

        count_query = select(func.count(Organization.id)).where(
            Organization.id == current_user.organization_id,
            Organization.deleted_at.is_(None),
        )

    result = await db.execute(query)
    organizations = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get user counts for each organization
    org_responses = []
    for org in organizations:
        user_count_query = select(func.count(User.id)).where(
            User.organization_id == org.id,
            User.deleted_at.is_(None),
        )
        user_count_result = await db.execute(user_count_query)
        user_count = user_count_result.scalar() or 0

        org_responses.append(OrganizationResponse(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            description=org.description,
            logo_url=org.logo_url,
            subscription_status=org.subscription_status or "trial",
            trial_ends_at=org.trial_ends_at,
            settings=org.settings,
            is_active=org.is_active,
            created_at=org.created_at,
            updated_at=org.updated_at,
            user_count=user_count,
        ))

    return OrganizationListResponse(organizations=org_responses, total=total)


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the current user's organization details.
    """
    result = await db.execute(
        select(Organization).where(
            Organization.id == current_user.organization_id,
            Organization.deleted_at.is_(None),
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Get user count
    user_count_query = select(func.count(User.id)).where(
        User.organization_id == organization.id,
        User.deleted_at.is_(None),
    )
    user_count_result = await db.execute(user_count_query)
    user_count = user_count_result.scalar() or 0

    return OrganizationResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        logo_url=organization.logo_url,
        subscription_status=organization.subscription_status or "trial",
        trial_ends_at=organization.trial_ends_at,
        settings=organization.settings,
        is_active=organization.is_active,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        user_count=user_count,
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("organizations:read")),
):
    """
    Get a specific organization by ID.
    - Platform admins can access any organization
    - Regular users can only access their own organization
    """
    result = await db.execute(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.deleted_at.is_(None),
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check access
    if not current_user.is_platform_admin and organization.id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this organization",
        )

    # Get user count
    user_count_query = select(func.count(User.id)).where(
        User.organization_id == organization.id,
        User.deleted_at.is_(None),
    )
    user_count_result = await db.execute(user_count_query)
    user_count = user_count_result.scalar() or 0

    return OrganizationResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        logo_url=organization.logo_url,
        subscription_status=organization.subscription_status or "trial",
        trial_ends_at=organization.trial_ends_at,
        settings=organization.settings,
        is_active=organization.is_active,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        user_count=user_count,
    )


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new organization (public endpoint for registration).
    Note: In production, this might be restricted or require additional validation.
    """
    # Generate slug if not provided
    slug = org_data.slug or generate_slug(org_data.name)

    # Check if organization with same name or slug exists
    existing_name = await db.execute(
        select(Organization).where(
            Organization.name == org_data.name,
            Organization.deleted_at.is_(None),
        )
    )
    if existing_name.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this name already exists",
        )

    existing_slug = await db.execute(
        select(Organization).where(
            Organization.slug == slug,
            Organization.deleted_at.is_(None),
        )
    )
    if existing_slug.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this slug already exists",
        )

    # Create new organization
    new_organization = Organization(
        name=org_data.name,
        slug=slug,
        description=org_data.description,
        logo_url=org_data.logo_url,
        settings=org_data.settings or {},
        subscription_status="trial",
        is_active=True,
    )

    db.add(new_organization)
    await db.commit()
    await db.refresh(new_organization)

    return OrganizationResponse(
        id=str(new_organization.id),
        name=new_organization.name,
        slug=new_organization.slug,
        description=new_organization.description,
        logo_url=new_organization.logo_url,
        subscription_status=new_organization.subscription_status or "trial",
        trial_ends_at=new_organization.trial_ends_at,
        settings=new_organization.settings,
        is_active=new_organization.is_active,
        created_at=new_organization.created_at,
        updated_at=new_organization.updated_at,
        user_count=0,
    )


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    org_data: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("organizations:update")),
):
    """
    Update an organization.
    - Platform admins can update any organization
    - Org owners/admins can update their own organization
    """
    result = await db.execute(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.deleted_at.is_(None),
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check access - platform admins or same org
    if not current_user.is_platform_admin and organization.id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this organization",
        )

    # Update fields
    if org_data.name is not None:
        # Check for name uniqueness
        existing = await db.execute(
            select(Organization).where(
                Organization.name == org_data.name,
                Organization.id != organization_id,
                Organization.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An organization with this name already exists",
            )
        organization.name = org_data.name

    if org_data.slug is not None:
        # Check for slug uniqueness
        existing = await db.execute(
            select(Organization).where(
                Organization.slug == org_data.slug,
                Organization.id != organization_id,
                Organization.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An organization with this slug already exists",
            )
        organization.slug = org_data.slug

    if org_data.description is not None:
        organization.description = org_data.description

    if org_data.logo_url is not None:
        organization.logo_url = org_data.logo_url

    if org_data.settings is not None:
        # Merge settings instead of replacing
        current_settings = organization.settings or {}
        current_settings.update(org_data.settings)
        organization.settings = current_settings

    await db.commit()
    await db.refresh(organization)

    # Get user count
    user_count_query = select(func.count(User.id)).where(
        User.organization_id == organization.id,
        User.deleted_at.is_(None),
    )
    user_count_result = await db.execute(user_count_query)
    user_count = user_count_result.scalar() or 0

    return OrganizationResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        logo_url=organization.logo_url,
        subscription_status=organization.subscription_status or "trial",
        trial_ends_at=organization.trial_ends_at,
        settings=organization.settings,
        is_active=organization.is_active,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        user_count=user_count,
    )


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("organizations:delete")),
):
    """
    Soft delete an organization (platform admins only).
    Organizations with active users cannot be deleted.
    """
    # Only platform admins can delete organizations
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform administrators can delete organizations",
        )

    result = await db.execute(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.deleted_at.is_(None),
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check if organization has active users
    user_count_query = select(func.count(User.id)).where(
        User.organization_id == organization.id,
        User.deleted_at.is_(None),
        User.is_active == True,
    )
    user_count_result = await db.execute(user_count_query)
    user_count = user_count_result.scalar() or 0

    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete organization with {user_count} active users. Deactivate users first.",
        )

    # Soft delete
    organization.deleted_at = datetime.utcnow()
    organization.is_active = False
    await db.commit()

    return None


@router.post("/{organization_id}/suspend", response_model=OrganizationResponse)
async def suspend_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("organizations:update")),
):
    """
    Suspend an organization (platform admins only).
    Suspended organizations cannot access the platform.
    """
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform administrators can suspend organizations",
        )

    result = await db.execute(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.deleted_at.is_(None),
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    organization.subscription_status = "suspended"
    organization.is_active = False
    await db.commit()
    await db.refresh(organization)

    # Get user count
    user_count_query = select(func.count(User.id)).where(
        User.organization_id == organization.id,
        User.deleted_at.is_(None),
    )
    user_count_result = await db.execute(user_count_query)
    user_count = user_count_result.scalar() or 0

    return OrganizationResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        logo_url=organization.logo_url,
        subscription_status=organization.subscription_status or "trial",
        trial_ends_at=organization.trial_ends_at,
        settings=organization.settings,
        is_active=organization.is_active,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        user_count=user_count,
    )


@router.post("/{organization_id}/activate", response_model=OrganizationResponse)
async def activate_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("organizations:update")),
):
    """
    Activate a suspended organization (platform admins only).
    """
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform administrators can activate organizations",
        )

    result = await db.execute(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.deleted_at.is_(None),
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    organization.subscription_status = "active"
    organization.is_active = True
    await db.commit()
    await db.refresh(organization)

    # Get user count
    user_count_query = select(func.count(User.id)).where(
        User.organization_id == organization.id,
        User.deleted_at.is_(None),
    )
    user_count_result = await db.execute(user_count_query)
    user_count = user_count_result.scalar() or 0

    return OrganizationResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        logo_url=organization.logo_url,
        subscription_status=organization.subscription_status or "trial",
        trial_ends_at=organization.trial_ends_at,
        settings=organization.settings,
        is_active=organization.is_active,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        user_count=user_count,
    )
