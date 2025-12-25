from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from uuid import UUID
from datetime import datetime

from app.core.database import get_db, get_pgvector_db
from app.core.redis_client import get_redis
from app.models.agent import Agent, AgentStatus
from app.models.user import User
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowDeployResponse,
)
from app.api.deps import (
    get_current_active_user,
    require_permission,
)

router = APIRouter()


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:create")),
):
    """Create a new workflow."""
    # Using Agent model to store workflow data
    # This maintains backward compatibility with existing database schema
    workflow = Agent(
        name=workflow_data.name,
        description=workflow_data.description,
        config=workflow_data.config,
        organization_id=current_user.organization_id,
        creator_id=current_user.id,
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
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:read")),
):
    """List all workflows for the user's organization."""
    # Filter by organization - only show workflows in user's org
    query = (
        select(Agent)
        .where(
            Agent.organization_id == current_user.organization_id,
            Agent.deleted_at.is_(None),
        )
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    workflows = result.scalars().all()

    # Get total count
    count_query = select(func.count(Agent.id)).where(
        Agent.organization_id == current_user.organization_id,
        Agent.deleted_at.is_(None),
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return WorkflowListResponse(
        total=total,
        workflows=[WorkflowResponse.model_validate(workflow) for workflow in workflows],
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:read")),
):
    """Get workflow by ID."""
    result = await db.execute(
        select(Agent).where(
            Agent.id == workflow_id,
            Agent.deleted_at.is_(None),
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Check organization access
    if workflow.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workflow",
        )

    return WorkflowResponse.model_validate(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    workflow_data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:update")),
):
    """Update a workflow."""
    result = await db.execute(
        select(Agent).where(
            Agent.id == workflow_id,
            Agent.deleted_at.is_(None),
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Check organization access
    if workflow.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workflow",
        )

    # Check if user can update (owner or has update permission)
    if workflow.creator_id != current_user.id and not current_user.is_platform_admin:
        # Non-owners need agents:update:any permission (checked by middleware)
        pass

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
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:delete")),
):
    """Delete a workflow (soft delete)."""
    result = await db.execute(
        select(Agent).where(
            Agent.id == workflow_id,
            Agent.deleted_at.is_(None),
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Check organization access
    if workflow.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workflow",
        )

    # Check if user can delete (owner or has delete permission)
    if workflow.creator_id != current_user.id and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can delete this workflow",
        )

    # Soft delete
    workflow.deleted_at = datetime.utcnow()
    await db.commit()

    return None


@router.post("/{workflow_id}/deploy", response_model=WorkflowDeployResponse)
async def deploy_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:deploy")),
):
    """Deploy a workflow."""
    result = await db.execute(
        select(Agent).where(
            Agent.id == workflow_id,
            Agent.deleted_at.is_(None),
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Check organization access
    if workflow.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workflow",
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


@router.post("/{workflow_id}/execute/")
async def execute_workflow(
    workflow_id: UUID,
    request: dict,
    db: AsyncSession = Depends(get_db),
    pgvector_db: AsyncSession = Depends(get_pgvector_db),
    redis: any = Depends(get_redis),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:execute")),
):
    """Execute a workflow."""
    from app.services.langgraph_engine import LangGraphEngine
    from app.models.agent import AgentExecution
    import time

    result = await db.execute(
        select(Agent).where(
            Agent.id == workflow_id,
            Agent.deleted_at.is_(None),
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Check organization access
    if workflow.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workflow",
        )

    # Execute workflow
    start_time = time.time()

    # Create engine instance with database sessions and Redis client
    engine = LangGraphEngine(db=db, pgvector_db=pgvector_db, redis_client=redis)

    # Get input from request
    user_input = request.get("input", "")

    execution_result = await engine.execute_agent(
        agent_config=workflow.config,
        user_input=user_input,
        input_mode=request.get("mode")
    )

    execution_time = int((time.time() - start_time) * 1000)  # milliseconds

    # Extract token usage
    llm_usage = execution_result.get("llm_usage") or {}
    tokens_used = llm_usage.get("total_tokens", 0)

    # Create execution record
    execution = AgentExecution(
        agent_id=workflow_id,
        user_id=current_user.id,
        input={
            "raw_input": user_input,
            "mode": request.get("mode", "chat"),
            "processed_input": execution_result.get("processed_input"),
        },
        output={
            "result": execution_result.get("output"),
            "llm_usage": execution_result.get("llm_usage"),
            "llm_cost": execution_result.get("llm_cost"),
        },
        tokens_used=tokens_used,
        execution_time=execution_time,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    return {
        "execution_id": str(execution.id),
        "output": execution_result.get("output"),
        "execution_path": execution_result.get("execution_path", []),
        "execution_trace": execution_result.get("execution_trace", []),
        "node_outputs": execution_result.get("node_outputs", {}),
        "tokens_used": tokens_used,
        "execution_time": execution_time,
        "input_metadata": execution_result.get("input_metadata"),
        "processed_input": execution_result.get("processed_input"),
    }
