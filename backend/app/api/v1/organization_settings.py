"""
API endpoints for organization settings management.

Provides dedicated endpoints for managing organization-level settings including:
- Guardrails configuration (enforced and defaults)
- LLM defaults
- Security settings
- General preferences
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.user import Organization, User
from app.api.deps import get_current_active_user, require_permission
from app.schemas.organization_settings import (
    OrganizationSettings,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdate,
    OrganizationGuardrailsConfig,
    GuardrailsOnlyResponse,
    GuardrailsOnlyUpdate,
    merge_settings,
    get_default_settings,
)

router = APIRouter()


async def get_organization_by_id(
    organization_id: str,
    db: AsyncSession,
    current_user: User,
) -> Organization:
    """Helper to get organization with permission check."""
    try:
        org_uuid = UUID(organization_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID format"
        )

    # Get the organization
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_uuid,
            Organization.deleted_at.is_(None),
        )
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check if user belongs to this organization or is admin
    if str(current_user.organization_id) != organization_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization's settings"
        )

    return org


@router.get("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get organization settings.

    Returns the complete settings object including guardrails, LLM defaults,
    security settings, and general preferences.
    """
    org = await get_organization_by_id(organization_id, db, current_user)

    # Get settings from the organization's settings JSONB field
    settings_dict = org.settings or {}

    # Merge with defaults to ensure all fields exist
    default_settings = get_default_settings()
    merged = merge_settings(default_settings, settings_dict)

    # Parse into the structured schema
    settings = OrganizationSettings.model_validate(merged)

    return OrganizationSettingsResponse(
        organizationId=str(org.id),
        organizationName=org.name,
        settings=settings,
        updatedAt=org.updated_at,
        updatedBy=None,  # TODO: Track who last updated settings
    )


@router.patch("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def update_organization_settings(
    organization_id: str,
    updates: OrganizationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update organization settings.

    Partial update - only provided fields will be updated.
    Requires admin role within the organization.
    """
    # Check permission - only admins or creators can update settings
    if current_user.role not in ["admin", "creator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or creators can update organization settings"
        )

    org = await get_organization_by_id(organization_id, db, current_user)

    # Get current settings
    current_settings = org.settings or {}
    default_settings = get_default_settings()
    merged_current = merge_settings(default_settings, current_settings)

    # Apply updates
    updates_dict = updates.model_dump(by_alias=True, exclude_none=True)
    new_settings = merge_settings(merged_current, updates_dict)

    # Update the organization
    org.settings = new_settings
    org.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(org)

    # Return the updated settings
    settings = OrganizationSettings.model_validate(new_settings)

    return OrganizationSettingsResponse(
        organizationId=str(org.id),
        organizationName=org.name,
        settings=settings,
        updatedAt=org.updated_at,
        updatedBy=str(current_user.id),
    )


@router.get("/{organization_id}/settings/guardrails", response_model=GuardrailsOnlyResponse)
async def get_organization_guardrails(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get organization guardrails configuration only.

    Returns the guardrails configuration including enforced rules,
    defaults, and global settings.
    """
    org = await get_organization_by_id(organization_id, db, current_user)

    settings_dict = org.settings or {}
    default_settings = get_default_settings()
    merged = merge_settings(default_settings, settings_dict)

    guardrails = OrganizationGuardrailsConfig.model_validate(
        merged.get("guardrails", {})
    )

    return GuardrailsOnlyResponse(
        organizationId=str(org.id),
        guardrails=guardrails,
        updatedAt=org.updated_at,
    )


@router.patch("/{organization_id}/settings/guardrails", response_model=GuardrailsOnlyResponse)
async def update_organization_guardrails(
    organization_id: str,
    updates: GuardrailsOnlyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update organization guardrails configuration only.

    Partial update - only provided fields will be updated.
    Requires admin role within the organization.
    """
    if current_user.role not in ["admin", "creator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or creators can update guardrails settings"
        )

    org = await get_organization_by_id(organization_id, db, current_user)

    # Get current settings
    current_settings = org.settings or {}
    default_settings = get_default_settings()
    merged_current = merge_settings(default_settings, current_settings)

    # Get current guardrails
    current_guardrails = merged_current.get("guardrails", {})

    # Apply updates
    updates_dict = updates.model_dump(by_alias=True, exclude_none=True)
    new_guardrails = merge_settings(current_guardrails, updates_dict)

    # Update in the settings
    merged_current["guardrails"] = new_guardrails
    org.settings = merged_current
    org.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(org)

    guardrails = OrganizationGuardrailsConfig.model_validate(new_guardrails)

    return GuardrailsOnlyResponse(
        organizationId=str(org.id),
        guardrails=guardrails,
        updatedAt=org.updated_at,
    )


@router.get("/current/settings", response_model=OrganizationSettingsResponse)
async def get_current_organization_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get settings for the current user's organization.

    Convenience endpoint that uses the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    return await get_organization_settings(
        str(current_user.organization_id),
        db,
        current_user,
    )


@router.patch("/current/settings", response_model=OrganizationSettingsResponse)
async def update_current_organization_settings(
    updates: OrganizationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update settings for the current user's organization.

    Convenience endpoint that uses the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    return await update_organization_settings(
        str(current_user.organization_id),
        updates,
        db,
        current_user,
    )


@router.get("/current/settings/guardrails", response_model=GuardrailsOnlyResponse)
async def get_current_organization_guardrails(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get guardrails for the current user's organization.

    Convenience endpoint that uses the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    return await get_organization_guardrails(
        str(current_user.organization_id),
        db,
        current_user,
    )
