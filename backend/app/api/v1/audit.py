"""
API endpoints for audit log management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field
import csv
import io
import json

from app.core.database import get_db
from app.models.audit_log import AuditLog, AuditAction
from app.models.user import User
from app.api.deps import get_current_active_user, require_permission


# ============== Schemas ==============

class AuditLogResponse(BaseModel):
    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    audit_logs: List[AuditLogResponse]
    total: int


class AuditLogSummary(BaseModel):
    action: str
    count: int
    last_occurrence: datetime


class AuditSummaryResponse(BaseModel):
    total_logs: int
    logs_by_action: List[AuditLogSummary]
    logs_by_resource_type: Dict[str, int]
    logs_by_status: Dict[str, int]
    recent_users: List[str]


router = APIRouter()


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("audit:read")),
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    user_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
):
    """
    List audit logs for the current user's organization.
    Platform admins can see all logs.
    """
    # Base query
    if current_user.is_platform_admin:
        query = select(AuditLog)
    else:
        query = select(AuditLog).where(
            AuditLog.organization_id == current_user.organization_id
        )

    # Apply filters
    if action:
        query = query.where(AuditLog.action == action)

    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    if status_filter:
        query = query.where(AuditLog.status == status_filter)

    if start_date:
        query = query.where(AuditLog.created_at >= start_date)

    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    if search:
        query = query.where(
            or_(
                AuditLog.action.ilike(f"%{search}%"),
                AuditLog.resource_name.ilike(f"%{search}%"),
                AuditLog.user_email.ilike(f"%{search}%"),
            )
        )

    # Count query
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    log_responses = [
        AuditLogResponse(
            id=str(log.id),
            organization_id=str(log.organization_id) if log.organization_id else None,
            user_id=str(log.user_id) if log.user_id else None,
            user_email=log.user_email,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            resource_name=log.resource_name,
            old_values=log.old_values,
            new_values=log.new_values,
            ip_address=str(log.ip_address) if log.ip_address else None,
            user_agent=log.user_agent,
            status=log.status,
            error_message=log.error_message,
            extra_data=log.extra_data,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return AuditLogListResponse(audit_logs=log_responses, total=total)


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("audit:read")),
):
    """
    Get a specific audit log entry.
    """
    result = await db.execute(
        select(AuditLog).where(AuditLog.id == log_id)
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )

    # Check access
    if not current_user.is_platform_admin and log.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this audit log",
        )

    return AuditLogResponse(
        id=str(log.id),
        organization_id=str(log.organization_id) if log.organization_id else None,
        user_id=str(log.user_id) if log.user_id else None,
        user_email=log.user_email,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        resource_name=log.resource_name,
        old_values=log.old_values,
        new_values=log.new_values,
        ip_address=str(log.ip_address) if log.ip_address else None,
        user_agent=log.user_agent,
        status=log.status,
        error_message=log.error_message,
        extra_data=log.extra_data,
        created_at=log.created_at,
    )


@router.get("/summary", response_model=AuditSummaryResponse)
async def get_audit_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("audit:read")),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Get a summary of audit logs.
    """
    # Base filter
    if current_user.is_platform_admin:
        base_filter = True
    else:
        base_filter = AuditLog.organization_id == current_user.organization_id

    date_filter = True
    if start_date:
        date_filter = and_(date_filter, AuditLog.created_at >= start_date)
    if end_date:
        date_filter = and_(date_filter, AuditLog.created_at <= end_date)

    # Total count
    total_query = select(func.count(AuditLog.id))
    if not current_user.is_platform_admin:
        total_query = total_query.where(base_filter)
    if start_date or end_date:
        total_query = total_query.where(date_filter)
    total_result = await db.execute(total_query)
    total_logs = total_result.scalar() or 0

    # Logs by action
    action_query = (
        select(
            AuditLog.action,
            func.count(AuditLog.id).label("count"),
            func.max(AuditLog.created_at).label("last_occurrence"),
        )
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
        .limit(20)
    )
    if not current_user.is_platform_admin:
        action_query = action_query.where(base_filter)
    if start_date or end_date:
        action_query = action_query.where(date_filter)
    action_result = await db.execute(action_query)
    logs_by_action = [
        AuditLogSummary(action=row[0], count=row[1], last_occurrence=row[2])
        for row in action_result.all()
    ]

    # Logs by resource type
    resource_query = (
        select(
            AuditLog.resource_type,
            func.count(AuditLog.id).label("count"),
        )
        .group_by(AuditLog.resource_type)
    )
    if not current_user.is_platform_admin:
        resource_query = resource_query.where(base_filter)
    if start_date or end_date:
        resource_query = resource_query.where(date_filter)
    resource_result = await db.execute(resource_query)
    logs_by_resource_type = {row[0]: row[1] for row in resource_result.all()}

    # Logs by status
    status_query = (
        select(
            AuditLog.status,
            func.count(AuditLog.id).label("count"),
        )
        .group_by(AuditLog.status)
    )
    if not current_user.is_platform_admin:
        status_query = status_query.where(base_filter)
    if start_date or end_date:
        status_query = status_query.where(date_filter)
    status_result = await db.execute(status_query)
    logs_by_status = {row[0]: row[1] for row in status_result.all()}

    # Recent unique users
    users_query = (
        select(AuditLog.user_email)
        .where(AuditLog.user_email.isnot(None))
        .distinct()
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    if not current_user.is_platform_admin:
        users_query = users_query.where(base_filter)
    if start_date or end_date:
        users_query = users_query.where(date_filter)
    users_result = await db.execute(users_query)
    recent_users = [row[0] for row in users_result.all()]

    return AuditSummaryResponse(
        total_logs=total_logs,
        logs_by_action=logs_by_action,
        logs_by_resource_type=logs_by_resource_type,
        logs_by_status=logs_by_status,
        recent_users=recent_users,
    )


@router.get("/export")
async def export_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("audit:read")),
    format: str = Query("csv", enum=["csv", "json"]),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(10000, le=50000),
):
    """
    Export audit logs as CSV or JSON.
    """
    # Base query
    if current_user.is_platform_admin:
        query = select(AuditLog)
    else:
        query = select(AuditLog).where(
            AuditLog.organization_id == current_user.organization_id
        )

    # Apply filters
    if action:
        query = query.where(AuditLog.action == action)

    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    if start_date:
        query = query.where(AuditLog.created_at >= start_date)

    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    query = query.order_by(AuditLog.created_at.desc()).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    if format == "csv":
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "ID", "Timestamp", "Action", "Resource Type", "Resource ID",
            "Resource Name", "User Email", "IP Address", "Status", "Error Message"
        ])

        # Data rows
        for log in logs:
            writer.writerow([
                str(log.id),
                log.created_at.isoformat(),
                log.action,
                log.resource_type,
                log.resource_id or "",
                log.resource_name or "",
                log.user_email or "",
                str(log.ip_address) if log.ip_address else "",
                log.status,
                log.error_message or "",
            ])

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )

    else:  # JSON
        log_data = [
            {
                "id": str(log.id),
                "timestamp": log.created_at.isoformat(),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "resource_name": log.resource_name,
                "user_email": log.user_email,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "status": log.status,
                "error_message": log.error_message,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "metadata": log.extra_data,
            }
            for log in logs
        ]

        json_output = json.dumps(log_data, indent=2, default=str)

        return StreamingResponse(
            iter([json_output]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )


@router.get("/actions")
async def list_audit_actions(
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("audit:read")),
):
    """
    List all available audit action types.
    """
    actions = {
        "user": [
            AuditAction.USER_LOGIN,
            AuditAction.USER_LOGOUT,
            AuditAction.USER_LOGIN_FAILED,
            AuditAction.USER_CREATE,
            AuditAction.USER_UPDATE,
            AuditAction.USER_DELETE,
            AuditAction.USER_INVITE,
            AuditAction.USER_PASSWORD_CHANGE,
            AuditAction.USER_PASSWORD_RESET,
        ],
        "organization": [
            AuditAction.ORG_CREATE,
            AuditAction.ORG_UPDATE,
            AuditAction.ORG_DELETE,
            AuditAction.ORG_SUBSCRIPTION_CHANGE,
        ],
        "agent": [
            AuditAction.AGENT_CREATE,
            AuditAction.AGENT_UPDATE,
            AuditAction.AGENT_DELETE,
            AuditAction.AGENT_DEPLOY,
            AuditAction.AGENT_EXECUTE,
            AuditAction.AGENT_VERSION_CREATE,
            AuditAction.AGENT_VERSION_RESTORE,
        ],
        "tool": [
            AuditAction.TOOL_CREATE,
            AuditAction.TOOL_UPDATE,
            AuditAction.TOOL_DELETE,
            AuditAction.TOOL_EXECUTE,
        ],
        "credential": [
            AuditAction.CREDENTIAL_CREATE,
            AuditAction.CREDENTIAL_UPDATE,
            AuditAction.CREDENTIAL_DELETE,
            AuditAction.CREDENTIAL_ACCESS,
        ],
        "deployment": [
            AuditAction.DEPLOYMENT_CREATE,
            AuditAction.DEPLOYMENT_UPDATE,
            AuditAction.DEPLOYMENT_DELETE,
            AuditAction.DEPLOYMENT_START,
            AuditAction.DEPLOYMENT_STOP,
        ],
        "role": [
            AuditAction.ROLE_CREATE,
            AuditAction.ROLE_UPDATE,
            AuditAction.ROLE_DELETE,
            AuditAction.ROLE_ASSIGN,
            AuditAction.ROLE_REVOKE,
        ],
        "invitation": [
            AuditAction.INVITATION_CREATE,
            AuditAction.INVITATION_ACCEPT,
            AuditAction.INVITATION_REVOKE,
            AuditAction.INVITATION_EXPIRE,
        ],
    }

    return {"actions": actions}


@router.get("/resource-types")
async def list_resource_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("audit:read")),
):
    """
    List all resource types that have audit logs.
    """
    if current_user.is_platform_admin:
        query = select(AuditLog.resource_type).distinct()
    else:
        query = select(AuditLog.resource_type).where(
            AuditLog.organization_id == current_user.organization_id
        ).distinct()

    result = await db.execute(query)
    resource_types = [row[0] for row in result.all()]

    return {"resource_types": resource_types}
