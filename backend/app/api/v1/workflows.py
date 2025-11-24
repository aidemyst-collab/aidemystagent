from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.agent import Agent, AgentStatus
from app.models.user import User
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowDeployResponse,
)

router = APIRouter()


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow."""
    # TODO: Get current user from auth
    # For now, get first user from database
    user_result = await db.execute(select(User).limit(1))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No users found. Please create a user first.",
        )

    org_id = user.organization_id
    creator_id = user.id

    # Using Agent model to store workflow data
    # This maintains backward compatibility with existing database schema
    workflow = Agent(
        name=workflow_data.name,
        description=workflow_data.description,
        config=workflow_data.config,
        organization_id=org_id,
        creator_id=creator_id,
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)

    return WorkflowResponse.model_validate(workflow)


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all workflows."""
    # TODO: Filter by organization
    result = await db.execute(select(Agent).offset(skip).limit(limit))
    workflows = result.scalars().all()

    total_result = await db.execute(select(Agent))
    total = len(total_result.scalars().all())

    return WorkflowListResponse(
        total=total,
        workflows=[WorkflowResponse.model_validate(workflow) for workflow in workflows],
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get workflow by ID."""
    result = await db.execute(select(Agent).where(Agent.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return WorkflowResponse.model_validate(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    workflow_data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a workflow."""
    result = await db.execute(select(Agent).where(Agent.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Update fields
    if workflow_data.name is not None:
        workflow.name = workflow_data.name
    if workflow_data.description is not None:
        workflow.description = workflow_data.description
    if workflow_data.config is not None:
        workflow.config = workflow_data.config
    if workflow_data.status is not None:
        workflow.status = workflow_data.status

    await db.commit()
    await db.refresh(workflow)

    return WorkflowResponse.model_validate(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a workflow."""
    result = await db.execute(select(Agent).where(Agent.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    await db.delete(workflow)
    await db.commit()

    return None


@router.post("/{workflow_id}/deploy", response_model=WorkflowDeployResponse)
async def deploy_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)):
    """Deploy a workflow."""
    result = await db.execute(select(Agent).where(Agent.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    workflow.status = AgentStatus.DEPLOYED
    workflow.version += 1
    await db.commit()
    await db.refresh(workflow)

    # Generate endpoint URL
    endpoint = f"https://api.example.com/v1/workflows/{workflow_id}/execute"

    return WorkflowDeployResponse(
        id=workflow.id,
        status="deployed",
        endpoint=endpoint,
        deployedAt=datetime.utcnow(),
    )


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Execute a workflow."""
    result = await db.execute(select(Agent).where(Agent.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # TODO: Implement workflow execution logic
    return {"message": "Workflow execution - not yet implemented", "workflow_id": str(workflow_id)}
