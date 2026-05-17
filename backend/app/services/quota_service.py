"""
Quota enforcement service.
Checks org subscription plan limits before resource creation.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import date
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.user import Organization
from app.models.subscription import SubscriptionPlan
from app.models.agent import Agent, AgentExecution
from app.models.tool import Tool, ToolStatus
from app.models.credential import Credential
from app.models.deployment import Deployment, DeploymentStatus
from app.core.logging_config import logger


async def _get_plan(db: AsyncSession, org_id: UUID) -> Optional[SubscriptionPlan]:
    """Get the subscription plan for an org. Returns 'free' plan as fallback."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if org and org.subscription_plan_id:
        plan_result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == org.subscription_plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        if plan:
            return plan

    # Fallback to free plan
    free_result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.name == "free")
    )
    return free_result.scalar_one_or_none()


def _quota_exceeded_error(resource: str, limit: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=f"quota_exceeded:{resource}:{limit}",
    )


async def check_agents_quota(db: AsyncSession, org_id: UUID) -> None:
    plan = await _get_plan(db, org_id)
    if not plan or plan.max_agents == -1:
        return
    count_result = await db.execute(
        select(func.count(Agent.id)).where(
            Agent.organization_id == org_id,
            Agent.deleted_at.is_(None),
        )
    )
    count = count_result.scalar() or 0
    if count >= plan.max_agents:
        raise _quota_exceeded_error("agents", plan.max_agents)


async def check_deployments_quota(db: AsyncSession, org_id: UUID) -> None:
    plan = await _get_plan(db, org_id)
    if not plan or plan.max_deployments == -1:
        return
    count_result = await db.execute(
        select(func.count(Deployment.id)).where(
            Deployment.organization_id == org_id,
            Deployment.status == DeploymentStatus.ACTIVE,
            Deployment.deleted_at.is_(None),
        )
    )
    count = count_result.scalar() or 0
    if count >= plan.max_deployments:
        raise _quota_exceeded_error("deployments", plan.max_deployments)


async def check_tools_quota(db: AsyncSession, org_id: UUID) -> None:
    plan = await _get_plan(db, org_id)
    if not plan or plan.max_tools == -1:
        return
    count_result = await db.execute(
        select(func.count(Tool.id)).where(
            Tool.organization_id == org_id,
            Tool.status == ToolStatus.ACTIVE,
        )
    )
    count = count_result.scalar() or 0
    if count >= plan.max_tools:
        raise _quota_exceeded_error("tools", plan.max_tools)


async def check_credentials_quota(db: AsyncSession, org_id: UUID) -> None:
    plan = await _get_plan(db, org_id)
    if not plan or plan.max_credentials == -1:
        return
    count_result = await db.execute(
        select(func.count(Credential.id)).where(
            Credential.organization_id == org_id,
        )
    )
    count = count_result.scalar() or 0
    if count >= plan.max_credentials:
        raise _quota_exceeded_error("credentials", plan.max_credentials)


async def check_executions_quota(db: AsyncSession, org_id: UUID) -> None:
    """Check monthly execution quota."""
    plan = await _get_plan(db, org_id)
    if not plan or plan.max_executions_per_month == -1:
        return
    today = date.today()
    period_start = today.replace(day=1)
    count_result = await db.execute(
        select(func.count(AgentExecution.id)).where(
            AgentExecution.organization_id == org_id,
            AgentExecution.created_at >= period_start,
        )
    )
    count = count_result.scalar() or 0
    if count >= plan.max_executions_per_month:
        raise _quota_exceeded_error("executions", plan.max_executions_per_month)


async def check_users_quota(db: AsyncSession, org_id: UUID) -> None:
    """Check user quota (called when accepting invitation)."""
    from app.models.user import User
    plan = await _get_plan(db, org_id)
    if not plan or plan.max_users == -1:
        return
    count_result = await db.execute(
        select(func.count(User.id)).where(
            User.organization_id == org_id,
            User.deleted_at.is_(None),
            User.is_active == True,
        )
    )
    count = count_result.scalar() or 0
    if count >= plan.max_users:
        raise _quota_exceeded_error("users", plan.max_users)


async def get_usage_summary(db: AsyncSession, org_id: UUID) -> Dict[str, Any]:
    """
    Return current usage vs plan limits for an organization.
    Used by GET /organizations/me/usage
    """
    from app.models.user import User
    try:
        plan = await _get_plan(db, org_id)
        today = date.today()
        period_start = today.replace(day=1)

        # Count all resources
        agents = (await db.execute(
            select(func.count(Agent.id)).where(
                Agent.organization_id == org_id,
                Agent.deleted_at.is_(None),
            )
        )).scalar() or 0

        users = (await db.execute(
            select(func.count(User.id)).where(
                User.organization_id == org_id,
                User.deleted_at.is_(None),
                User.is_active == True,
            )
        )).scalar() or 0

        deployments = (await db.execute(
            select(func.count(Deployment.id)).where(
                Deployment.organization_id == org_id,
                Deployment.status == DeploymentStatus.ACTIVE,
                Deployment.deleted_at.is_(None),
            )
        )).scalar() or 0

        tools = (await db.execute(
            select(func.count(Tool.id)).where(
                Tool.organization_id == org_id,
                Tool.status == ToolStatus.ACTIVE,
            )
        )).scalar() or 0

        credentials = (await db.execute(
            select(func.count(Credential.id)).where(
                Credential.organization_id == org_id,
            )
        )).scalar() or 0

        executions_this_month = (await db.execute(
            select(func.count(AgentExecution.id)).where(
                AgentExecution.organization_id == org_id,
                AgentExecution.created_at >= period_start,
            )
        )).scalar() or 0

        def quota_item(current: int, limit: int) -> dict:
            pct = round((current / limit * 100), 1) if limit > 0 and limit != -1 else 0
            return {"current": current, "limit": limit, "percentage": pct, "unlimited": limit == -1}

        plan_info = {
            "name": plan.name if plan else "free",
            "display_name": plan.display_name if plan else "Free",
            "features": plan.features if plan else {},
        } if plan else {"name": "free", "display_name": "Free", "features": {}}

        return {
            "plan": plan_info,
            "usage": {
                "agents": quota_item(agents, plan.max_agents if plan else 5),
                "users": quota_item(users, plan.max_users if plan else 3),
                "deployments": quota_item(deployments, plan.max_deployments if plan else 2),
                "tools": quota_item(tools, plan.max_tools if plan else 10),
                "credentials": quota_item(credentials, plan.max_credentials if plan else 5),
                "executions_this_month": quota_item(
                    executions_this_month,
                    plan.max_executions_per_month if plan else 500,
                ),
            },
        }

    except Exception as exc:
        logger.error(f"Error fetching usage summary for org {org_id}: {exc}")
        return {
            "plan": {"name": "free", "display_name": "Free", "features": {}},
            "usage": {
                "agents": {"current": 0, "limit": 5, "percentage": 0, "unlimited": False},
                "users": {"current": 0, "limit": 3, "percentage": 0, "unlimited": False},
                "deployments": {"current": 0, "limit": 2, "percentage": 0, "unlimited": False},
                "tools": {"current": 0, "limit": 10, "percentage": 0, "unlimited": False},
                "credentials": {"current": 0, "limit": 5, "percentage": 0, "unlimited": False},
                "executions_this_month": {"current": 0, "limit": 500, "percentage": 0, "unlimited": False},
            },
        }
