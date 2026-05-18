"""
Platform Admin — Organisation Approval Management API

Prefix: /admin/organizations
All routes require platform-admin access via require_platform_admin.

Implements Milestone 1 RBAC: org approval gate.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
import asyncio
from datetime import datetime
from pydantic import BaseModel

from app.services.system_log_service import system_log

from app.core.database import get_db
from app.models.user import Organization, User
from app.models.role import Role, UserRole as UserRoleAssignment
from app.models.audit_log import AuditLog
from app.api.deps import require_platform_admin

router = APIRouter()


# ============== Schemas ==============

class OrgApprovalAction(BaseModel):
    reason: Optional[str] = None  # required for reject


class OrgAdminListItem(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    approvalStatus: str
    approvalRejectedReason: Optional[str] = None
    approvedAt: Optional[datetime] = None
    userCount: int
    ownerEmail: Optional[str] = None
    createdAt: datetime

    class Config:
        from_attributes = True


class OrgAdminListResponse(BaseModel):
    organizations: List[OrgAdminListItem]
    total: int


# ============== Helper ==============

async def _load_org_or_404(db: AsyncSession, org_id: UUID) -> Organization:
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.deleted_at.is_(None),
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


async def _get_user_count(db: AsyncSession, org_id: UUID) -> int:
    result = await db.execute(
        select(func.count(User.id)).where(
            User.organization_id == org_id,
            User.deleted_at.is_(None),
        )
    )
    return result.scalar() or 0


async def _get_owner_email(db: AsyncSession, org_id: UUID) -> Optional[str]:
    """Return the email of the org_owner user if one exists, else the first user in the org."""
    # Try to find user with org_owner role assignment
    owner_role_result = await db.execute(
        select(User.email)
        .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
        .join(Role, Role.id == UserRoleAssignment.role_id)
        .where(
            UserRoleAssignment.organization_id == org_id,
            Role.name == "org_owner",
            User.deleted_at.is_(None),
        )
        .limit(1)
    )
    email = owner_role_result.scalar_one_or_none()
    if email:
        return email

    # Fallback: first user in the org by creation date
    first_user_result = await db.execute(
        select(User.email)
        .where(
            User.organization_id == org_id,
            User.deleted_at.is_(None),
        )
        .order_by(User.created_at.asc())
        .limit(1)
    )
    return first_user_result.scalar_one_or_none()


async def _build_list_item(db: AsyncSession, org: Organization) -> OrgAdminListItem:
    user_count = await _get_user_count(db, org.id)
    owner_email = await _get_owner_email(db, org.id)
    return OrgAdminListItem(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        approvalStatus=org.approval_status,
        approvalRejectedReason=org.approval_rejected_reason,
        approvedAt=org.approved_at,
        userCount=user_count,
        ownerEmail=owner_email,
        createdAt=org.created_at,
    )


# ============== Endpoints ==============

@router.get("", response_model=OrgAdminListResponse)
async def list_organizations(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by approval status: pending, active, rejected, suspended, or all (default all)",
    ),
    search: Optional[str] = Query(default=None, description="Search by org name or slug"),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_platform_admin),
) -> OrgAdminListResponse:
    """
    List all organisations with optional status filter and search.
    Platform admins only.
    """
    query = select(Organization).where(Organization.deleted_at.is_(None))

    if status_filter and status_filter != "all":
        query = query.where(Organization.approval_status == status_filter)

    if search:
        like_term = f"%{search}%"
        query = query.where(
            (Organization.name.ilike(like_term)) | (Organization.slug.ilike(like_term))
        )

    query = query.order_by(Organization.created_at.desc())
    result = await db.execute(query)
    orgs = result.scalars().all()

    items = []
    for org in orgs:
        items.append(await _build_list_item(db, org))

    return OrgAdminListResponse(organizations=items, total=len(items))


@router.post("/{org_id}/approve", response_model=OrgAdminListItem)
async def approve_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_platform_admin),
) -> OrgAdminListItem:
    """
    Approve a pending organisation.
    Sets approval_status=active, records approved_at and approved_by_id.
    Platform admins only.
    """
    org = await _load_org_or_404(db, org_id)

    old_status = org.approval_status
    org.approval_status = "active"
    org.approved_at = datetime.utcnow()
    org.approved_by_id = admin_user.id
    org.approval_rejected_reason = None  # clear any previous rejection reason

    db.add(AuditLog.create_log(
        action="org.approve",
        resource_type="organization",
        resource_id=str(org.id),
        resource_name=org.name,
        user_id=admin_user.id,
        user_email=admin_user.email,
        organization_id=org.id,
        old_values={"approval_status": old_status},
        new_values={"approval_status": "active"},
    ))

    await db.commit()
    await db.refresh(org)

    asyncio.create_task(system_log(
        "INFO", "admin",
        f"Organisation approved: {org.name}",
        {"org_id": str(org.id), "by": admin_user.email},
        "admin.org_admin",
    ))

    return await _build_list_item(db, org)


@router.post("/{org_id}/reject", response_model=OrgAdminListItem)
async def reject_organization(
    org_id: UUID,
    body: OrgApprovalAction,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_platform_admin),
) -> OrgAdminListItem:
    """
    Reject a pending organisation.
    Reason is required. Sets approval_status=rejected.
    Platform admins only.
    """
    if not body.reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A rejection reason is required",
        )

    org = await _load_org_or_404(db, org_id)

    old_status = org.approval_status
    org.approval_status = "rejected"
    org.approval_rejected_reason = body.reason

    db.add(AuditLog.create_log(
        action="org.reject",
        resource_type="organization",
        resource_id=str(org.id),
        resource_name=org.name,
        user_id=admin_user.id,
        user_email=admin_user.email,
        organization_id=org.id,
        old_values={"approval_status": old_status},
        new_values={"approval_status": "rejected", "reason": body.reason},
    ))

    await db.commit()
    await db.refresh(org)

    asyncio.create_task(system_log(
        "WARNING", "admin",
        f"Organisation rejected: {org.name}",
        {"org_id": str(org.id), "reason": body.reason, "by": admin_user.email},
        "admin.org_admin",
    ))

    return await _build_list_item(db, org)


@router.post("/{org_id}/suspend", response_model=OrgAdminListItem)
async def suspend_organization(
    org_id: UUID,
    body: OrgApprovalAction,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_platform_admin),
) -> OrgAdminListItem:
    """
    Suspend an active organisation.
    Sets approval_status=suspended.
    Platform admins only.
    """
    org = await _load_org_or_404(db, org_id)

    old_status = org.approval_status
    org.approval_status = "suspended"
    if body.reason:
        org.approval_rejected_reason = body.reason

    db.add(AuditLog.create_log(
        action="org.suspend",
        resource_type="organization",
        resource_id=str(org.id),
        resource_name=org.name,
        user_id=admin_user.id,
        user_email=admin_user.email,
        organization_id=org.id,
        old_values={"approval_status": old_status},
        new_values={"approval_status": "suspended"},
        metadata={"reason": body.reason} if body.reason else {},
    ))

    await db.commit()
    await db.refresh(org)

    asyncio.create_task(system_log(
        "WARNING", "admin",
        f"Organisation suspended: {org.name}",
        {"org_id": str(org.id), "reason": body.reason, "by": admin_user.email},
        "admin.org_admin",
    ))

    return await _build_list_item(db, org)


@router.post("/{org_id}/reactivate", response_model=OrgAdminListItem)
async def reactivate_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_platform_admin),
) -> OrgAdminListItem:
    """
    Reactivate a suspended or rejected organisation.
    Sets approval_status=active.
    Platform admins only.
    """
    org = await _load_org_or_404(db, org_id)

    old_status = org.approval_status
    org.approval_status = "active"
    org.approval_rejected_reason = None
    org.approved_at = datetime.utcnow()
    org.approved_by_id = admin_user.id

    db.add(AuditLog.create_log(
        action="org.reactivate",
        resource_type="organization",
        resource_id=str(org.id),
        resource_name=org.name,
        user_id=admin_user.id,
        user_email=admin_user.email,
        organization_id=org.id,
        old_values={"approval_status": old_status},
        new_values={"approval_status": "active"},
    ))

    await db.commit()
    await db.refresh(org)

    asyncio.create_task(system_log(
        "INFO", "admin",
        f"Organisation reactivated: {org.name}",
        {"org_id": str(org.id), "by": admin_user.email},
        "admin.org_admin",
    ))

    return await _build_list_item(db, org)
