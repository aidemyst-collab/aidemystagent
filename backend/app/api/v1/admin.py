"""
Platform Administration API endpoints.
Super admin only - manages organizations, subscription plans, and platform-wide operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.user import Organization, User, UserRole
from app.core.security import get_password_hash
from app.models.subscription import SubscriptionPlan
from app.models.organization_usage import OrganizationUsage
from app.models.agent import Agent, AgentExecution
from app.models.deployment import Deployment
from app.models.tool import Tool
from app.api.deps import require_platform_admin


# ============== Schemas ==============

class PlatformStats(BaseModel):
    """Platform-wide statistics."""
    total_organizations: int
    active_organizations: int
    total_users: int
    active_users: int
    total_agents: int
    total_deployments: int
    active_deployments: int
    total_executions: int
    total_tools: int


class OrganizationAdminResponse(BaseModel):
    """Full organization details for admin view."""
    id: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    subscription_status: str
    subscription_plan_name: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    is_active: bool
    user_count: int
    agent_count: int
    deployment_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationAdminListResponse(BaseModel):
    organizations: List[OrganizationAdminResponse]
    total: int


class SubscriptionPlanCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    display_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    max_users: int = Field(default=5, ge=-1)
    max_agents: int = Field(default=10, ge=-1)
    max_deployments: int = Field(default=5, ge=-1)
    max_executions_per_month: int = Field(default=1000, ge=-1)
    max_tools: int = Field(default=20, ge=-1)
    max_credentials: int = Field(default=10, ge=-1)
    features: Optional[Dict[str, Any]] = None
    price_monthly_cents: int = Field(default=0, ge=0)
    price_yearly_cents: int = Field(default=0, ge=0)
    is_public: bool = True
    sort_order: int = Field(default=0, ge=0)


class SubscriptionPlanUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    max_users: Optional[int] = Field(None, ge=-1)
    max_agents: Optional[int] = Field(None, ge=-1)
    max_deployments: Optional[int] = Field(None, ge=-1)
    max_executions_per_month: Optional[int] = Field(None, ge=-1)
    max_tools: Optional[int] = Field(None, ge=-1)
    max_credentials: Optional[int] = Field(None, ge=-1)
    features: Optional[Dict[str, Any]] = None
    price_monthly_cents: Optional[int] = Field(None, ge=0)
    price_yearly_cents: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)


class SubscriptionPlanResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    max_users: int
    max_agents: int
    max_deployments: int
    max_executions_per_month: int
    max_tools: int
    max_credentials: int
    features: Optional[Dict[str, Any]] = None
    price_monthly_cents: int
    price_yearly_cents: int
    is_active: bool
    is_public: bool
    sort_order: int
    organization_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionPlanListResponse(BaseModel):
    plans: List[SubscriptionPlanResponse]
    total: int


class UsageReportResponse(BaseModel):
    organization_id: str
    organization_name: str
    period_start: date
    period_end: date
    users_count: int
    agents_count: int
    deployments_count: int
    executions_count: int
    tokens_used: int
    api_calls_count: int
    total_cost_cents: int


class UsageReportListResponse(BaseModel):
    usage_reports: List[UsageReportResponse]
    total: int


class UserAdminResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    organization_id: str
    organization_name: str
    role: str
    is_platform_admin: bool
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserAdminListResponse(BaseModel):
    users: List[UserAdminResponse]
    total: int


class CreateUserAdminRequest(BaseModel):
    """Request to create a user as admin."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: Optional[str] = Field(None, description="User full name")
    organization_id: UUID = Field(..., description="Organization ID to add user to")
    role: str = Field("creator", description="Legacy role: admin, creator, or viewer")
    is_platform_admin: bool = Field(False, description="Whether user is a platform admin")
    is_active: bool = Field(True, description="Whether user is active")


class OrganizationStatusUpdate(BaseModel):
    """Update organization status."""
    is_active: Optional[bool] = None
    subscription_status: Optional[str] = None
    subscription_plan_id: Optional[UUID] = None


router = APIRouter()


# ============== Platform Statistics ==============

@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Get platform-wide statistics.
    Super admin only.
    """
    # Organizations
    total_orgs = await db.execute(
        select(func.count(Organization.id)).where(Organization.deleted_at.is_(None))
    )
    total_organizations = total_orgs.scalar() or 0

    active_orgs = await db.execute(
        select(func.count(Organization.id)).where(
            Organization.deleted_at.is_(None),
            Organization.is_active == True,
        )
    )
    active_organizations = active_orgs.scalar() or 0

    # Users
    total_users_result = await db.execute(
        select(func.count(User.id)).where(User.deleted_at.is_(None))
    )
    total_users = total_users_result.scalar() or 0

    active_users_result = await db.execute(
        select(func.count(User.id)).where(
            User.deleted_at.is_(None),
            User.is_active == True,
        )
    )
    active_users = active_users_result.scalar() or 0

    # Agents
    total_agents_result = await db.execute(
        select(func.count(Agent.id)).where(Agent.deleted_at.is_(None))
    )
    total_agents = total_agents_result.scalar() or 0

    # Deployments
    total_deployments_result = await db.execute(
        select(func.count(Deployment.id)).where(Deployment.deleted_at.is_(None))
    )
    total_deployments = total_deployments_result.scalar() or 0

    active_deployments_result = await db.execute(
        select(func.count(Deployment.id)).where(
            Deployment.deleted_at.is_(None),
            Deployment.status == "active",
        )
    )
    active_deployments = active_deployments_result.scalar() or 0

    # Executions
    total_executions_result = await db.execute(
        select(func.count(AgentExecution.id))
    )
    total_executions = total_executions_result.scalar() or 0

    # Tools
    total_tools_result = await db.execute(
        select(func.count(Tool.id))
    )
    total_tools = total_tools_result.scalar() or 0

    return PlatformStats(
        total_organizations=total_organizations,
        active_organizations=active_organizations,
        total_users=total_users,
        active_users=active_users,
        total_agents=total_agents,
        total_deployments=total_deployments,
        active_deployments=active_deployments,
        total_executions=total_executions,
        total_tools=total_tools,
    )


# ============== Organization Management ==============

@router.get("/organizations", response_model=OrganizationAdminListResponse)
async def list_all_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    subscription_status: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    List all organizations with detailed stats.
    Super admin only.
    """
    query = select(Organization).where(Organization.deleted_at.is_(None))

    if is_active is not None:
        query = query.where(Organization.is_active == is_active)

    if subscription_status:
        # subscription_status is stored as string in database
        valid_statuses = ['active', 'trial', 'past_due', 'cancelled', 'suspended']
        if subscription_status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid subscription status: {subscription_status}. Valid values: {valid_statuses}",
            )
        query = query.where(Organization.subscription_status == subscription_status.lower())

    if search:
        query = query.where(
            Organization.name.ilike(f"%{search}%") |
            Organization.slug.ilike(f"%{search}%")
        )

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    query = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    organizations = result.scalars().all()

    org_responses = []
    for org in organizations:
        # Get counts
        user_count = await db.execute(
            select(func.count(User.id)).where(
                User.organization_id == org.id,
                User.deleted_at.is_(None),
            )
        )
        agent_count = await db.execute(
            select(func.count(Agent.id)).where(
                Agent.organization_id == org.id,
                Agent.deleted_at.is_(None),
            )
        )
        deployment_count = await db.execute(
            select(func.count(Deployment.id)).where(
                Deployment.organization_id == org.id,
                Deployment.deleted_at.is_(None),
            )
        )

        # Get subscription plan name
        plan_name = None
        if org.subscription_plan_id:
            plan_result = await db.execute(
                select(SubscriptionPlan.display_name).where(
                    SubscriptionPlan.id == org.subscription_plan_id
                )
            )
            plan_name = plan_result.scalar()

        org_responses.append(OrganizationAdminResponse(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            description=org.description,
            subscription_status=org.subscription_status or "trial",
            subscription_plan_name=plan_name,
            trial_ends_at=org.trial_ends_at,
            is_active=org.is_active,
            user_count=user_count.scalar() or 0,
            agent_count=agent_count.scalar() or 0,
            deployment_count=deployment_count.scalar() or 0,
            created_at=org.created_at,
            updated_at=org.updated_at,
        ))

    return OrganizationAdminListResponse(organizations=org_responses, total=total)


@router.patch("/organizations/{organization_id}", response_model=OrganizationAdminResponse)
async def update_organization_status(
    organization_id: UUID,
    update_data: OrganizationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Update organization status (active, subscription status, plan).
    Super admin only.
    """
    result = await db.execute(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.deleted_at.is_(None),
        )
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if update_data.is_active is not None:
        org.is_active = update_data.is_active

    if update_data.subscription_status:
        valid_statuses = ['active', 'trial', 'past_due', 'cancelled', 'suspended']
        status_value = update_data.subscription_status.lower()
        if status_value not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid subscription status: {update_data.subscription_status}. Valid values: {valid_statuses}",
            )
        org.subscription_status = status_value

    if update_data.subscription_plan_id:
        # Verify plan exists
        plan_result = await db.execute(
            select(SubscriptionPlan).where(
                SubscriptionPlan.id == update_data.subscription_plan_id,
                SubscriptionPlan.is_active == True,
            )
        )
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription plan not found",
            )
        org.subscription_plan_id = update_data.subscription_plan_id

    await db.commit()
    await db.refresh(org)

    # Get counts
    user_count = await db.execute(
        select(func.count(User.id)).where(
            User.organization_id == org.id,
            User.deleted_at.is_(None),
        )
    )
    agent_count = await db.execute(
        select(func.count(Agent.id)).where(
            Agent.organization_id == org.id,
            Agent.deleted_at.is_(None),
        )
    )
    deployment_count = await db.execute(
        select(func.count(Deployment.id)).where(
            Deployment.organization_id == org.id,
            Deployment.deleted_at.is_(None),
        )
    )

    # Get subscription plan name
    plan_name = None
    if org.subscription_plan_id:
        plan_result = await db.execute(
            select(SubscriptionPlan.display_name).where(
                SubscriptionPlan.id == org.subscription_plan_id
            )
        )
        plan_name = plan_result.scalar()

    return OrganizationAdminResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        description=org.description,
        subscription_status=org.subscription_status or "trial",
        subscription_plan_name=plan_name,
        trial_ends_at=org.trial_ends_at,
        is_active=org.is_active,
        user_count=user_count.scalar() or 0,
        agent_count=agent_count.scalar() or 0,
        deployment_count=deployment_count.scalar() or 0,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


# ============== Subscription Plan Management ==============

@router.get("/subscription-plans", response_model=SubscriptionPlanListResponse)
async def list_subscription_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
):
    """
    List all subscription plans.
    Super admin only.
    """
    query = select(SubscriptionPlan)

    if not include_inactive:
        query = query.where(SubscriptionPlan.is_active == True)

    query = query.order_by(SubscriptionPlan.sort_order).offset(skip).limit(limit)

    result = await db.execute(query)
    plans = result.scalars().all()

    # Count query
    count_query = select(func.count(SubscriptionPlan.id))
    if not include_inactive:
        count_query = count_query.where(SubscriptionPlan.is_active == True)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    plan_responses = []
    for plan in plans:
        # Get organization count for this plan
        org_count = await db.execute(
            select(func.count(Organization.id)).where(
                Organization.subscription_plan_id == plan.id,
                Organization.deleted_at.is_(None),
            )
        )

        plan_responses.append(SubscriptionPlanResponse(
            id=str(plan.id),
            name=plan.name,
            display_name=plan.display_name,
            description=plan.description,
            max_users=plan.max_users,
            max_agents=plan.max_agents,
            max_deployments=plan.max_deployments,
            max_executions_per_month=plan.max_executions_per_month,
            max_tools=plan.max_tools,
            max_credentials=plan.max_credentials,
            features=plan.features,
            price_monthly_cents=plan.price_monthly_cents,
            price_yearly_cents=plan.price_yearly_cents,
            is_active=plan.is_active,
            is_public=plan.is_public,
            sort_order=plan.sort_order,
            organization_count=org_count.scalar() or 0,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        ))

    return SubscriptionPlanListResponse(plans=plan_responses, total=total)


@router.post("/subscription-plans", response_model=SubscriptionPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription_plan(
    plan_data: SubscriptionPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Create a new subscription plan.
    Super admin only.
    """
    # Check for existing plan with same name
    existing = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.name == plan_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subscription plan with this name already exists",
        )

    plan = SubscriptionPlan(
        name=plan_data.name,
        display_name=plan_data.display_name,
        description=plan_data.description,
        max_users=plan_data.max_users,
        max_agents=plan_data.max_agents,
        max_deployments=plan_data.max_deployments,
        max_executions_per_month=plan_data.max_executions_per_month,
        max_tools=plan_data.max_tools,
        max_credentials=plan_data.max_credentials,
        features=plan_data.features or {},
        price_monthly_cents=plan_data.price_monthly_cents,
        price_yearly_cents=plan_data.price_yearly_cents,
        is_active=True,
        is_public=plan_data.is_public,
        sort_order=plan_data.sort_order,
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return SubscriptionPlanResponse(
        id=str(plan.id),
        name=plan.name,
        display_name=plan.display_name,
        description=plan.description,
        max_users=plan.max_users,
        max_agents=plan.max_agents,
        max_deployments=plan.max_deployments,
        max_executions_per_month=plan.max_executions_per_month,
        max_tools=plan.max_tools,
        max_credentials=plan.max_credentials,
        features=plan.features,
        price_monthly_cents=plan.price_monthly_cents,
        price_yearly_cents=plan.price_yearly_cents,
        is_active=plan.is_active,
        is_public=plan.is_public,
        sort_order=plan.sort_order,
        organization_count=0,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.get("/subscription-plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Get a specific subscription plan.
    Super admin only.
    """
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found",
        )

    # Get organization count
    org_count = await db.execute(
        select(func.count(Organization.id)).where(
            Organization.subscription_plan_id == plan.id,
            Organization.deleted_at.is_(None),
        )
    )

    return SubscriptionPlanResponse(
        id=str(plan.id),
        name=plan.name,
        display_name=plan.display_name,
        description=plan.description,
        max_users=plan.max_users,
        max_agents=plan.max_agents,
        max_deployments=plan.max_deployments,
        max_executions_per_month=plan.max_executions_per_month,
        max_tools=plan.max_tools,
        max_credentials=plan.max_credentials,
        features=plan.features,
        price_monthly_cents=plan.price_monthly_cents,
        price_yearly_cents=plan.price_yearly_cents,
        is_active=plan.is_active,
        is_public=plan.is_public,
        sort_order=plan.sort_order,
        organization_count=org_count.scalar() or 0,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.patch("/subscription-plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def update_subscription_plan(
    plan_id: UUID,
    plan_data: SubscriptionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Update a subscription plan.
    Super admin only.
    """
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found",
        )

    # Update fields
    if plan_data.display_name is not None:
        plan.display_name = plan_data.display_name
    if plan_data.description is not None:
        plan.description = plan_data.description
    if plan_data.max_users is not None:
        plan.max_users = plan_data.max_users
    if plan_data.max_agents is not None:
        plan.max_agents = plan_data.max_agents
    if plan_data.max_deployments is not None:
        plan.max_deployments = plan_data.max_deployments
    if plan_data.max_executions_per_month is not None:
        plan.max_executions_per_month = plan_data.max_executions_per_month
    if plan_data.max_tools is not None:
        plan.max_tools = plan_data.max_tools
    if plan_data.max_credentials is not None:
        plan.max_credentials = plan_data.max_credentials
    if plan_data.features is not None:
        current_features = plan.features or {}
        current_features.update(plan_data.features)
        plan.features = current_features
    if plan_data.price_monthly_cents is not None:
        plan.price_monthly_cents = plan_data.price_monthly_cents
    if plan_data.price_yearly_cents is not None:
        plan.price_yearly_cents = plan_data.price_yearly_cents
    if plan_data.is_active is not None:
        plan.is_active = plan_data.is_active
    if plan_data.is_public is not None:
        plan.is_public = plan_data.is_public
    if plan_data.sort_order is not None:
        plan.sort_order = plan_data.sort_order

    await db.commit()
    await db.refresh(plan)

    # Get organization count
    org_count = await db.execute(
        select(func.count(Organization.id)).where(
            Organization.subscription_plan_id == plan.id,
            Organization.deleted_at.is_(None),
        )
    )

    return SubscriptionPlanResponse(
        id=str(plan.id),
        name=plan.name,
        display_name=plan.display_name,
        description=plan.description,
        max_users=plan.max_users,
        max_agents=plan.max_agents,
        max_deployments=plan.max_deployments,
        max_executions_per_month=plan.max_executions_per_month,
        max_tools=plan.max_tools,
        max_credentials=plan.max_credentials,
        features=plan.features,
        price_monthly_cents=plan.price_monthly_cents,
        price_yearly_cents=plan.price_yearly_cents,
        is_active=plan.is_active,
        is_public=plan.is_public,
        sort_order=plan.sort_order,
        organization_count=org_count.scalar() or 0,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.delete("/subscription-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Deactivate a subscription plan.
    Plans with active organizations cannot be deleted.
    Super admin only.
    """
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found",
        )

    # Check if plan has active organizations
    org_count = await db.execute(
        select(func.count(Organization.id)).where(
            Organization.subscription_plan_id == plan.id,
            Organization.deleted_at.is_(None),
            Organization.is_active == True,
        )
    )
    count = org_count.scalar() or 0

    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete plan with {count} active organizations. Migrate them first.",
        )

    # Deactivate instead of hard delete
    plan.is_active = False
    await db.commit()

    return None


# ============== Usage Reports ==============

@router.get("/usage", response_model=UsageReportListResponse)
async def get_usage_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
    organization_id: Optional[UUID] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
):
    """
    Get usage reports across all organizations.
    Super admin only.
    """
    query = select(OrganizationUsage)

    if organization_id:
        query = query.where(OrganizationUsage.organization_id == organization_id)

    if period_start:
        query = query.where(OrganizationUsage.period_start >= period_start)

    if period_end:
        query = query.where(OrganizationUsage.period_end <= period_end)

    query = query.order_by(OrganizationUsage.period_start.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    usage_records = result.scalars().all()

    # Count query
    count_query = select(func.count(OrganizationUsage.id))
    if organization_id:
        count_query = count_query.where(OrganizationUsage.organization_id == organization_id)
    if period_start:
        count_query = count_query.where(OrganizationUsage.period_start >= period_start)
    if period_end:
        count_query = count_query.where(OrganizationUsage.period_end <= period_end)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    usage_responses = []
    for usage in usage_records:
        # Get organization name
        org_result = await db.execute(
            select(Organization.name).where(Organization.id == usage.organization_id)
        )
        org_name = org_result.scalar() or "Unknown"

        usage_responses.append(UsageReportResponse(
            organization_id=str(usage.organization_id),
            organization_name=org_name,
            period_start=usage.period_start,
            period_end=usage.period_end,
            users_count=usage.users_count,
            agents_count=usage.agents_count,
            deployments_count=usage.deployments_count,
            executions_count=usage.executions_count,
            tokens_used=usage.tokens_used,
            api_calls_count=usage.api_calls_count,
            total_cost_cents=usage.total_cost_cents,
        ))

    return UsageReportListResponse(usage_reports=usage_responses, total=total)


# ============== User Management ==============

@router.get("/users", response_model=UserAdminListResponse)
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
    skip: int = 0,
    limit: int = 100,
    organization_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    is_platform_admin: Optional[bool] = None,
    search: Optional[str] = None,
):
    """
    List all users across all organizations.
    Super admin only.
    """
    query = select(User).where(User.deleted_at.is_(None))

    if organization_id:
        query = query.where(User.organization_id == organization_id)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if is_platform_admin is not None:
        query = query.where(User.is_platform_admin == is_platform_admin)

    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") |
            User.full_name.ilike(f"%{search}%")
        )

    # Count query
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    user_responses = []
    for user in users:
        # Get organization name
        org_result = await db.execute(
            select(Organization.name).where(Organization.id == user.organization_id)
        )
        org_name = org_result.scalar() or "Unknown"

        user_responses.append(UserAdminResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            organization_id=str(user.organization_id),
            organization_name=org_name,
            role=user.role.value if hasattr(user.role, 'value') else str(user.role),
            is_platform_admin=user.is_platform_admin,
            is_active=user.is_active,
            email_verified=user.email_verified,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        ))

    return UserAdminListResponse(users=user_responses, total=total)


@router.post("/users", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    user_data: CreateUserAdminRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Create a new user as platform admin.
    Super admin only.
    """
    # Check if email already exists
    existing_user = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Verify organization exists
    org_result = await db.execute(
        select(Organization).where(
            Organization.id == user_data.organization_id,
            Organization.deleted_at.is_(None),
        )
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Map role string to enum
    role_map = {
        "admin": UserRole.ADMIN,
        "creator": UserRole.CREATOR,
        "viewer": UserRole.VIEWER,
    }
    user_role = role_map.get(user_data.role.lower(), UserRole.CREATOR)

    # Create user
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        organization_id=user_data.organization_id,
        role=user_role,
        is_platform_admin=user_data.is_platform_admin,
        is_active=user_data.is_active,
        email_verified=True,  # Admin-created users are auto-verified
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserAdminResponse(
        id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name,
        organization_id=str(new_user.organization_id),
        organization_name=organization.name,
        role=new_user.role.value if hasattr(new_user.role, 'value') else str(new_user.role),
        is_platform_admin=new_user.is_platform_admin,
        is_active=new_user.is_active,
        email_verified=new_user.email_verified,
        last_login_at=new_user.last_login_at,
        created_at=new_user.created_at,
    )


@router.patch("/users/{user_id}/platform-admin")
async def toggle_platform_admin(
    user_id: UUID,
    is_admin: bool = Query(..., description="Set platform admin status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Grant or revoke platform admin privileges.
    Super admin only.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own platform admin status",
        )

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

    user.is_platform_admin = is_admin
    await db.commit()

    return {"message": f"User platform admin status set to {is_admin}"}


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    is_active: bool = Query(..., description="Set user active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Activate or deactivate a user.
    Super admin only.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

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

    user.is_active = is_active
    await db.commit()

    return {"message": f"User active status set to {is_active}"}
