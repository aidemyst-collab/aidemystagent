from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.agent import Agent, AgentStatus
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
)

router = APIRouter()


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new agent."""
    # TODO: Get current user from auth
    # For now, using mock values
    org_id = "00000000-0000-0000-0000-000000000000"
    creator_id = "00000000-0000-0000-0000-000000000000"

    agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        config=agent_data.config,
        organization_id=org_id,
        creator_id=creator_id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return AgentResponse.model_validate(agent)


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all agents."""
    # TODO: Filter by organization
    result = await db.execute(select(Agent).offset(skip).limit(limit))
    agents = result.scalars().all()

    total_result = await db.execute(select(Agent))
    total = len(total_result.scalars().all())

    return AgentListResponse(
        total=total,
        agents=[AgentResponse.model_validate(agent) for agent in agents],
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return AgentResponse.model_validate(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
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
async def delete_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    await db.delete(agent)
    await db.commit()

    return None


@router.post("/{agent_id}/deploy")
async def deploy_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Deploy an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    agent.status = AgentStatus.DEPLOYED
    agent.version += 1
    await db.commit()

    return {"message": "Agent deployed successfully", "version": agent.version}


@router.post("/{agent_id}/test")
async def test_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Test an agent."""
    # TODO: Implement agent execution
    return {"message": "Agent test endpoint - not yet implemented"}
