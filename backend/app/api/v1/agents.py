from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.agent import Agent, AgentStatus
from app.models.user import User
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
)
from app.api.deps import (
    get_current_active_user,
    get_permission_service,
    require_permission,
    get_effective_organization_id,
)
from app.services.permission_service import PermissionService

router = APIRouter()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:create")),
):
    """Create a new agent."""
    agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        config=agent_data.config,
        organization_id=effective_org_id,
        creator_id=current_user.id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return AgentResponse.model_validate(agent)


@router.get("", response_model=AgentListResponse)
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[AgentStatus] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:read")),
):
    """List all agents for the effective organization (supports admin org switching)."""
    # Base query - filter by effective organization and exclude soft-deleted
    query = (
        select(Agent)
        .where(Agent.organization_id == effective_org_id)
        .where(Agent.deleted_at.is_(None))
    )

    # Apply filters
    if status_filter:
        query = query.where(Agent.status == status_filter)

    if search:
        query = query.where(
            Agent.name.ilike(f"%{search}%") |
            Agent.description.ilike(f"%{search}%")
        )

    # Get total count
    count_query = (
        select(func.count(Agent.id))
        .where(Agent.organization_id == effective_org_id)
        .where(Agent.deleted_at.is_(None))
    )
    if status_filter:
        count_query = count_query.where(Agent.status == status_filter)
    if search:
        count_query = count_query.where(
            Agent.name.ilike(f"%{search}%") |
            Agent.description.ilike(f"%{search}%")
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(Agent.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    agents = result.scalars().all()

    return AgentListResponse(
        total=total,
        agents=[AgentResponse.model_validate(agent) for agent in agents],
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:read")),
):
    """Get agent by ID."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.deleted_at.is_(None))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check organization access (using effective org for platform admin switching)
    if agent.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    return AgentResponse.model_validate(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """Update an agent."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.deleted_at.is_(None))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check organization access (using effective org for platform admin switching)
    if agent.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    # Check permission - either agents:update for any agent, or agents:update:own for own agents
    can_update = await permission_service.can_access_resource(
        current_user,
        "agents",
        "update",
        agent.organization_id,
        agent.creator_id
    )
    if not can_update:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: cannot update this agent",
        )

    # Update fields
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.description is not None:
        agent.description = agent_data.description
    if agent_data.config is not None:
        agent.config = agent_data.config
    if agent_data.status is not None:
        agent.status = agent_data.status

    await db.commit()
    await db.refresh(agent)

    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    permission_service: PermissionService = Depends(get_permission_service),
):
    """Delete an agent (soft delete)."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.deleted_at.is_(None))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check organization access (using effective org for platform admin switching)
    if agent.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    # Check permission - either agents:delete for any agent, or agents:delete:own for own agents
    can_delete = await permission_service.can_access_resource(
        current_user,
        "agents",
        "delete",
        agent.organization_id,
        agent.creator_id
    )
    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: cannot delete this agent",
        )

    # Soft delete instead of hard delete
    agent.deleted_at = datetime.utcnow()
    await db.commit()

    return None


@router.post("/{agent_id}/deploy")
async def deploy_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("deployments:create")),
):
    """Deploy an agent."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.deleted_at.is_(None))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check organization access (using effective org for platform admin switching)
    if agent.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    agent.status = AgentStatus.DEPLOYED
    agent.version += 1
    await db.commit()

    return {"message": "Agent deployed successfully", "version": agent.version}


@router.post("/{agent_id}/test")
async def test_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:execute")),
):
    """Test an agent."""
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.deleted_at.is_(None))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check organization access (using effective org for platform admin switching)
    if agent.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    # TODO: Implement agent execution
    return {"message": "Agent test endpoint - not yet implemented"}
