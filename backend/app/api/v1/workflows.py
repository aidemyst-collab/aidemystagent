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
    get_effective_organization_id,
)

router = APIRouter()


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:create")),
):
    """Create a new workflow."""
    # Using Agent model to store workflow data
    # This maintains backward compatibility with existing database schema
    workflow = Agent(
        name=workflow_data.name,
        description=workflow_data.description,
        config=workflow_data.config,
        organization_id=effective_org_id,
        creator_id=current_user.id,
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)

    return WorkflowResponse.model_validate(workflow)


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:read")),
):
    """List all workflows for the effective organization (supports admin org switching)."""
    # Filter by effective organization (switched org for platform admins, or user's org)
    query = (
        select(Agent)
        .where(
            Agent.organization_id == effective_org_id,
            Agent.deleted_at.is_(None),
        )
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    workflows = result.scalars().all()

    # Get total count
    count_query = select(func.count(Agent.id)).where(
        Agent.organization_id == effective_org_id,
        Agent.deleted_at.is_(None),
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return WorkflowListResponse(
        total=total,
        workflows=[WorkflowResponse.model_validate(workflow) for workflow in workflows],
    )


@router.get("/list", response_model=dict)
async def list_workflows_for_selector(
    exclude_id: str = None,
    search: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:read")),
):
    """
    Get list of workflows for the Execute Workflow node selector.
    Returns minimal data needed for selection dropdown.
    """
    from sqlalchemy import or_

    # Build base query
    query = select(Agent).where(
        Agent.organization_id == effective_org_id,
        Agent.deleted_at.is_(None),
    )

    # Exclude specific workflow (to prevent recursion)
    if exclude_id:
        try:
            exclude_uuid = UUID(exclude_id)
            query = query.where(Agent.id != exclude_uuid)
        except (ValueError, TypeError):
            pass  # Invalid UUID, skip exclusion

    # Search filter
    if search:
        query = query.where(
            or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%"),
            )
        )

    # Order by most recently updated
    query = query.order_by(Agent.updated_at.desc()).limit(100)

    result = await db.execute(query)
    workflows = result.scalars().all()

    return {
        "workflows": [
            {
                "id": str(workflow.id),
                "name": workflow.name,
                "description": workflow.description or "",
                "status": workflow.status.value if workflow.status else "draft",
            }
            for workflow in workflows
        ]
    }


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
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

    # Check organization access (using effective org for platform admin switching)
    if workflow.organization_id != effective_org_id:
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
    effective_org_id: UUID = Depends(get_effective_organization_id),
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

    # Check organization access (using effective org for platform admin switching)
    if workflow.organization_id != effective_org_id:
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
    effective_org_id: UUID = Depends(get_effective_organization_id),
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

    # Check organization access (using effective org for platform admin switching)
    if workflow.organization_id != effective_org_id:
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
    effective_org_id: UUID = Depends(get_effective_organization_id),
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

    # Check organization access (using effective org for platform admin switching)
    if workflow.organization_id != effective_org_id:
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


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: UUID,
    request: dict,
    db: AsyncSession = Depends(get_db),
    pgvector_db: AsyncSession = Depends(get_pgvector_db),
    redis: any = Depends(get_redis),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
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

    # Check organization access (using effective org for platform admin switching)
    if workflow.organization_id != effective_org_id:
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
    input_mode = request.get("input_mode") or request.get("mode", "chat")
    session_id = request.get("session_id")

    execution_result = await engine.execute_agent(
        agent_config=workflow.config,
        user_input=user_input,
        input_mode=input_mode,
        session_id=session_id,
        organization_id=effective_org_id,
        workflow_id=workflow_id
    )

    execution_time = int((time.time() - start_time) * 1000)  # milliseconds

    # Extract token usage
    llm_usage = execution_result.get("llm_usage") or {}
    tokens_used = llm_usage.get("total_tokens", 0)

    # Create execution record (with session tracking for conversation auditing)
    execution = AgentExecution(
        agent_id=workflow_id,
        user_id=current_user.id,
        organization_id=effective_org_id,  # Use effective org for org-level queries
        input={
            "raw_input": user_input,
            "mode": input_mode,
            "session_id": execution_result.get("session_id"),  # Track conversation session
            "processed_input": execution_result.get("processed_input"),
            "node_inputs": execution_result.get("node_inputs", {}),  # Track node-level inputs
        },
        output={
            "result": execution_result.get("output"),
            "llm_usage": execution_result.get("llm_usage"),
            "llm_cost": execution_result.get("llm_cost"),
            "node_outputs": execution_result.get("node_outputs", {}),  # Track node-level outputs
            "execution_trace": execution_result.get("execution_trace", []),  # Track execution path
        },
        tokens_used=tokens_used,
        execution_time=execution_time,
    )
    db.add(execution)

    # Note: Workflow executions are tracked in agent_executions table, not audit_logs
    # Audit logs are reserved for user security events (login, logout, CRUD operations)

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
        "audio_data": execution_result.get("audio_data"),
        "audio_format": execution_result.get("audio_format"),
        "twiml_response": execution_result.get("twiml_response"),
        "audio_transcript": execution_result.get("audio_transcript"),
        # Session info for multi-turn conversations
        "session_id": execution_result.get("session_id"),  # Return for conversation continuity
    }


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:read")),
    skip: int = 0,
    limit: int = 50,
    session_id: str = None,
):
    """List execution history for a workflow, optionally filtered by session."""
    from app.models.agent import AgentExecution

    # Verify workflow access
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

    # Check organization access (using effective org for platform admin switching)
    if workflow.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workflow",
        )

    # Build query
    query = select(AgentExecution).where(AgentExecution.agent_id == workflow_id)

    # Filter by session_id if provided
    if session_id:
        # Use JSON path to filter by session_id in input JSONB
        query = query.where(
            AgentExecution.input["session_id"].astext == session_id
        )

    # Get total count
    count_query = select(func.count(AgentExecution.id)).where(AgentExecution.agent_id == workflow_id)
    if session_id:
        count_query = count_query.where(AgentExecution.input["session_id"].astext == session_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(AgentExecution.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    executions = result.scalars().all()

    return {
        "total": total,
        "executions": [
            {
                "id": str(e.id),
                "session_id": e.input.get("session_id") if e.input else None,
                "input": e.input,
                "output": e.output,
                "tokens_used": e.tokens_used,
                "execution_time": e.execution_time,
                "created_at": e.created_at.isoformat(),
            }
            for e in executions
        ],
    }


@router.get("/executions/all")
async def list_organization_executions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("analytics:read")),
    skip: int = 0,
    limit: int = 50,
    workflow_id: UUID = None,
    user_id: UUID = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """List all workflow executions for the effective organization with filtering."""
    from app.models.agent import AgentExecution

    # Build query - filter by effective organization (supports admin org switching)
    query = select(AgentExecution).where(
        AgentExecution.organization_id == effective_org_id
    )

    # Apply filters
    if workflow_id:
        query = query.where(AgentExecution.agent_id == workflow_id)
    if user_id:
        query = query.where(AgentExecution.user_id == user_id)
    if start_date:
        query = query.where(AgentExecution.created_at >= start_date)
    if end_date:
        query = query.where(AgentExecution.created_at <= end_date)

    # Get total count
    count_query = select(func.count(AgentExecution.id)).where(
        AgentExecution.organization_id == effective_org_id
    )
    if workflow_id:
        count_query = count_query.where(AgentExecution.agent_id == workflow_id)
    if user_id:
        count_query = count_query.where(AgentExecution.user_id == user_id)
    if start_date:
        count_query = count_query.where(AgentExecution.created_at >= start_date)
    if end_date:
        count_query = count_query.where(AgentExecution.created_at <= end_date)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results with agent info
    query = (
        query
        .join(Agent, AgentExecution.agent_id == Agent.id)
        .add_columns(Agent.name.label("workflow_name"))
        .order_by(AgentExecution.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    return {
        "total": total,
        "executions": [
            {
                "id": str(row[0].id),
                "workflow_id": str(row[0].agent_id),
                "workflow_name": row[1],
                "user_id": str(row[0].user_id),
                "session_id": row[0].input.get("session_id") if row[0].input else None,
                "input": row[0].input,
                "output": row[0].output,
                "tokens_used": row[0].tokens_used,
                "execution_time": row[0].execution_time,
                "created_at": row[0].created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.get("/{workflow_id}/sessions")
async def list_workflow_sessions(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:read")),
    skip: int = 0,
    limit: int = 50,
):
    """List unique sessions for a workflow with execution counts."""
    from app.models.agent import AgentExecution
    from sqlalchemy import distinct, desc

    # Verify workflow access
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

    # Check organization access (using effective org for platform admin switching)
    if workflow.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workflow",
        )

    # Query to get unique sessions with stats
    # Using raw SQL for JSON aggregation since SQLAlchemy JSONB handling varies
    query = """
        SELECT
            input->>'session_id' as session_id,
            COUNT(*) as execution_count,
            SUM(tokens_used) as total_tokens,
            SUM(execution_time) as total_execution_time,
            MIN(created_at) as first_execution,
            MAX(created_at) as last_execution
        FROM agent_executions
        WHERE agent_id = :workflow_id
          AND input->>'session_id' IS NOT NULL
        GROUP BY input->>'session_id'
        ORDER BY MAX(created_at) DESC
        OFFSET :skip
        LIMIT :limit
    """

    from sqlalchemy import text
    result = await db.execute(
        text(query),
        {"workflow_id": str(workflow_id), "skip": skip, "limit": limit}
    )
    sessions = result.fetchall()

    # Get total unique sessions count
    count_query = """
        SELECT COUNT(DISTINCT input->>'session_id')
        FROM agent_executions
        WHERE agent_id = :workflow_id
          AND input->>'session_id' IS NOT NULL
    """
    count_result = await db.execute(text(count_query), {"workflow_id": str(workflow_id)})
    total = count_result.scalar() or 0

    return {
        "total": total,
        "sessions": [
            {
                "session_id": row[0],
                "execution_count": row[1],
                "total_tokens": row[2] or 0,
                "total_execution_time_ms": row[3] or 0,
                "first_execution": row[4].isoformat() if row[4] else None,
                "last_execution": row[5].isoformat() if row[5] else None,
            }
            for row in sessions
        ],
    }
