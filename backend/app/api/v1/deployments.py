from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List
from uuid import UUID
from datetime import datetime
import secrets

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.deployment import Deployment, DeploymentStatus, DeploymentEnvironment
from app.models.agent import Agent, AgentExecution
from app.models.user import User
from app.services.langgraph_engine import LangGraphEngine
import redis.asyncio as aioredis
import time
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentUpdate,
    DeploymentResponse,
    DeploymentList,
)
from app.api.deps import (
    get_current_active_user,
    require_permission,
    get_effective_organization_id,
)

router = APIRouter()


@router.post("", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    deployment: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("deployments:create")),
):
    """Create a new deployment for an agent."""
    # Verify agent exists and user has access
    result = await db.execute(
        select(Agent).where(
            Agent.id == deployment.agent_id,
            Agent.deleted_at.is_(None),
        )
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

    # Generate API key for the deployment
    api_key = f"sk-{secrets.token_urlsafe(32)}"

    # Create deployment (endpoint_url will be set after we have the deployment ID)
    db_deployment = Deployment(
        agent_id=deployment.agent_id,
        organization_id=effective_org_id,
        version=deployment.version,
        environment=deployment.environment,
        status=DeploymentStatus.PENDING,
        endpoint_url="",  # Will be updated after commit
        api_key=api_key,
        config=deployment.config,
        deployed_by=current_user.id,
    )

    db.add(db_deployment)
    await db.commit()
    await db.refresh(db_deployment)

    # Now update endpoint URL with the actual deployment ID
    db_deployment.endpoint_url = f"/api/v1/deployments/{db_deployment.id}/invoke"

    # Simulate deployment (in real implementation, this would trigger async job)
    db_deployment.status = DeploymentStatus.ACTIVE
    db_deployment.deployed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_deployment)

    return db_deployment


@router.get("", response_model=DeploymentList)
async def list_deployments(
    agent_id: UUID = None,
    environment: DeploymentEnvironment = None,
    status_filter: DeploymentStatus = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("deployments:read")),
):
    """List all deployments with optional filters (scoped to effective organization)."""
    from sqlalchemy import or_

    # Base query with effective organization scoping
    # Include deployments with matching org_id OR NULL org_id (legacy deployments via agent)
    query = (
        select(Deployment)
        .outerjoin(Agent, Deployment.agent_id == Agent.id)
        .where(
            or_(
                Deployment.organization_id == effective_org_id,
                # Include legacy deployments (NULL org_id) if agent belongs to effective org
                (Deployment.organization_id.is_(None)) & (Agent.organization_id == effective_org_id)
            ),
            Deployment.deleted_at.is_(None),
        )
        .order_by(desc(Deployment.created_at))
    )

    if agent_id:
        query = query.where(Deployment.agent_id == agent_id)
    if environment:
        query = query.where(Deployment.environment == environment)
    if status_filter:
        query = query.where(Deployment.status == status_filter)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    deployments = result.scalars().all()

    # Get total count with same filters
    count_query = (
        select(func.count(Deployment.id))
        .select_from(Deployment)
        .outerjoin(Agent, Deployment.agent_id == Agent.id)
        .where(
            or_(
                Deployment.organization_id == effective_org_id,
                (Deployment.organization_id.is_(None)) & (Agent.organization_id == effective_org_id)
            ),
            Deployment.deleted_at.is_(None),
        )
    )
    if agent_id:
        count_query = count_query.where(Deployment.agent_id == agent_id)
    if environment:
        count_query = count_query.where(Deployment.environment == environment)
    if status_filter:
        count_query = count_query.where(Deployment.status == status_filter)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return DeploymentList(deployments=deployments, total=total)


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("deployments:read")),
):
    """Get a specific deployment by ID."""
    result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.deleted_at.is_(None),
        )
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    # Check organization access (using effective org for platform admin switching)
    if deployment.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this deployment",
        )

    return deployment


@router.patch("/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: UUID,
    update: DeploymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("deployments:update")),
):
    """Update a deployment."""
    result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.deleted_at.is_(None),
        )
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    # Check organization access (using effective org for platform admin switching)
    if deployment.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this deployment",
        )

    # Update fields
    if update.status is not None:
        deployment.status = update.status
    if update.endpoint_url is not None:
        deployment.endpoint_url = update.endpoint_url
    if update.error_message is not None:
        deployment.error_message = update.error_message
    if update.config is not None:
        deployment.config = update.config

    await db.commit()
    await db.refresh(deployment)

    return deployment


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("deployments:delete")),
):
    """Delete/stop a deployment (soft delete)."""
    result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.deleted_at.is_(None),
        )
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    # Check organization access (using effective org for platform admin switching)
    # Handle deployments created before organization_id was added (NULL org_id)
    if deployment.organization_id is not None and deployment.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this deployment",
        )

    # If deployment has no org_id, check via agent's organization
    if deployment.organization_id is None:
        agent_result = await db.execute(
            select(Agent).where(Agent.id == deployment.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent and agent.organization_id != effective_org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this deployment",
            )

    # Soft delete
    deployment.status = DeploymentStatus.STOPPED
    deployment.deleted_at = datetime.utcnow()
    await db.commit()


@router.post("/{deployment_id}/stop", response_model=DeploymentResponse)
async def stop_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("deployments:update")),
):
    """Stop a running deployment."""
    result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.deleted_at.is_(None),
        )
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    # Check organization access (using effective org for platform admin switching)
    if deployment.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this deployment",
        )

    if deployment.status != DeploymentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deployment is not active",
        )

    deployment.status = DeploymentStatus.STOPPED
    await db.commit()
    await db.refresh(deployment)

    return deployment


@router.post("/{deployment_id}/restart", response_model=DeploymentResponse)
async def restart_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("deployments:update")),
):
    """Restart a stopped deployment."""
    result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.deleted_at.is_(None),
        )
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    # Check organization access (using effective org for platform admin switching)
    if deployment.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this deployment",
        )

    if deployment.status not in [DeploymentStatus.STOPPED, DeploymentStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deployment cannot be restarted",
        )

    deployment.status = DeploymentStatus.DEPLOYING
    await db.commit()

    # Simulate deployment
    deployment.status = DeploymentStatus.ACTIVE
    deployment.deployed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(deployment)

    return deployment


# ============================================
# Public Invoke Endpoint (API Key Authentication)
# ============================================

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union, List
from fastapi import Header


class InvokeRequest(BaseModel):
    """Request model for deployment invocation."""
    input: Union[str, Dict[str, Any], Any] = Field(
        ...,
        description="Input for the agent. Can be a string or JSON object"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation history"
    )


class InvokeResponse(BaseModel):
    """Response model for deployment invocation."""
    output: Optional[str]
    execution_id: Optional[UUID] = None
    execution_path: List[str] = []
    tokens_used: int = 0
    execution_time: int = 0


@router.post("/{deployment_or_agent_id}/invoke", response_model=InvokeResponse)
async def invoke_deployment(
    deployment_or_agent_id: UUID,
    request: InvokeRequest,
    authorization: str = Header(..., description="API Key: Bearer sk-xxx"),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Invoke a deployed agent using API key authentication.

    This is the public endpoint for external applications to call deployed agents.
    Authentication is via the deployment's API key (not user JWT).

    The ID can be either a deployment_id or agent_id (for backwards compatibility).

    Usage:
    ```
    curl -X POST "https://api.example.com/api/v1/deployments/{deployment_id}/invoke" \\
      -H "Authorization: Bearer sk-your-api-key" \\
      -H "Content-Type: application/json" \\
      -d '{"input": "Your query here"}'
    ```
    """
    # Extract API key from Authorization header
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header. Use: Bearer sk-xxx",
        )

    api_key = authorization[7:]  # Remove "Bearer " prefix

    # Try to find deployment by ID first
    result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_or_agent_id,
            Deployment.deleted_at.is_(None),
        )
    )
    deployment = result.scalar_one_or_none()

    # If not found by deployment_id, try to find by agent_id (backwards compatibility)
    if not deployment:
        result = await db.execute(
            select(Deployment).where(
                Deployment.agent_id == deployment_or_agent_id,
                Deployment.deleted_at.is_(None),
                Deployment.status == DeploymentStatus.ACTIVE,
            ).order_by(desc(Deployment.created_at)).limit(1)
        )
        deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    # Validate API key
    if deployment.api_key != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Check deployment is active
    if deployment.status != DeploymentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deployment is not active. Current status: {deployment.status.value}",
        )

    # Get the agent
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == deployment.agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    agent = agent_result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Execute the agent
    start_time = time.time()

    engine = LangGraphEngine(db=db, redis_client=redis)

    # Prepare input with session_id if provided
    agent_input = request.input
    if request.session_id:
        if isinstance(agent_input, dict):
            agent_input["session_id"] = request.session_id
        elif isinstance(agent_input, str):
            agent_input = {
                "message": agent_input,
                "session_id": request.session_id
            }

    try:
        execution_result = await engine.execute_agent(
            agent_config=agent.config,
            user_input=agent_input,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )

    execution_time = int((time.time() - start_time) * 1000)  # milliseconds

    # Extract token usage
    llm_usage = execution_result.get("llm_usage") or {}
    tokens_used = llm_usage.get("total_tokens", 0)

    # Create execution record for tracking
    execution = AgentExecution(
        agent_id=agent.id,
        user_id=deployment.deployed_by,  # Use the deployer as the user
        organization_id=deployment.organization_id,
        input={
            "raw_input": request.input if isinstance(request.input, (str, dict, list)) else str(request.input),
            "deployment_id": str(deployment.id),
            "via": "deployment_invoke",
        },
        output={
            "result": execution_result.get("output"),
            "llm_usage": execution_result.get("llm_usage"),
        },
        tokens_used=tokens_used,
        execution_time=execution_time,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    return InvokeResponse(
        output=execution_result.get("output"),
        execution_id=execution.id,
        execution_path=execution_result.get("execution_path", []),
        tokens_used=tokens_used,
        execution_time=execution_time,
    )
