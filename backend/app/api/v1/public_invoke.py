"""
Public Invoke Router - Organization-scoped deployment invocations.

This router handles public API calls to deployed agents using organization slugs.
URL Pattern: /orgs/{org_slug}/deployments/{deployment_id}/invoke

Authentication is via deployment API key (not user JWT).
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, Field
import time

from app.core.database import get_db, get_pgvector_db
from app.core.redis_client import get_redis
from app.models.deployment import Deployment, DeploymentStatus
from app.models.agent import Agent, AgentExecution
from app.models.user import Organization
import redis.asyncio as aioredis

router = APIRouter()


class PublicInvokeRequest(BaseModel):
    """Request model for public deployment invocation."""
    input: Union[str, Dict[str, Any], Any] = Field(
        ...,
        description="Input for the agent. Can be a string or JSON object"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation history"
    )
    node_inputs: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional node-specific inputs"
    )


class PublicInvokeResponse(BaseModel):
    """Response model for public deployment invocation."""
    output: Optional[str] = None
    execution_id: Optional[str] = None
    execution_path: List[str] = []
    tokens_used: int = 0
    execution_time_ms: int = 0
    session_id: Optional[str] = None


@router.post(
    "/orgs/{org_slug}/deployments/{deployment_id}/invoke",
    response_model=PublicInvokeResponse,
    tags=["public"],
    summary="Invoke a deployed agent",
    description="Public endpoint to invoke a deployed agent using API key authentication."
)
async def invoke_deployment_public(
    org_slug: str,
    deployment_id: UUID,
    request: PublicInvokeRequest,
    authorization: str = Header(..., description="API Key: Bearer sk-xxx"),
    db: AsyncSession = Depends(get_db),
    pgvector_db: AsyncSession = Depends(get_pgvector_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Invoke a deployed agent using organization slug and API key.

    This is the public endpoint for external applications to call deployed agents.
    Authentication is via the deployment's API key (not user JWT).

    URL Pattern: /orgs/{org_slug}/deployments/{deployment_id}/invoke

    Usage:
    ```
    curl -X POST "https://api.agentstudio.io/orgs/acme-corp/deployments/{deployment_id}/invoke" \\
      -H "Authorization: Bearer sk-your-api-key" \\
      -H "Content-Type: application/json" \\
      -d '{"input": "Your query here"}'
    ```
    """
    start_time = time.time()

    # 1. Validate organization exists
    org_result = await db.execute(
        select(Organization).where(
            Organization.slug == org_slug,
            Organization.deleted_at.is_(None),
            Organization.is_active == True,
        )
    )
    organization = org_result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_slug}' not found",
        )

    # 2. Extract and validate API key
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header. Use: Bearer sk-xxx",
        )

    api_key = authorization[7:]  # Remove "Bearer " prefix

    # 3. Find deployment by ID and verify it belongs to this organization
    deployment_result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.organization_id == organization.id,
            Deployment.deleted_at.is_(None),
        )
    )
    deployment = deployment_result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found in this organization",
        )

    # 4. Validate API key
    if deployment.api_key != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # 5. Check deployment status
    if deployment.status != DeploymentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deployment is not active. Current status: {deployment.status}",
        )

    # 6. Get the agent
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
            detail="Agent associated with this deployment not found",
        )

    # 7. Execute the agent
    try:
        from app.services.langgraph_engine import LangGraphEngine
        engine = LangGraphEngine(
            db=db,
            pgvector_db=pgvector_db,
            redis_client=redis,
        )

        # Prepare input
        if isinstance(request.input, str):
            agent_input = {"query": request.input}
        else:
            agent_input = request.input

        # Add node inputs if provided
        if request.node_inputs:
            agent_input["node_inputs"] = request.node_inputs

        # Execute
        result = await engine.execute_agent(
            agent_config=agent.config,
            input_data=agent_input,
            session_id=request.session_id,
        )

        execution_time_ms = int((time.time() - start_time) * 1000)

        # 8. Record execution (optional - for analytics)
        execution = AgentExecution(
            agent_id=agent.id,
            user_id=deployment.deployed_by,  # Use deployer as user
            organization_id=organization.id,
            input={"query": request.input, "session_id": request.session_id},
            output=result,
            tokens_used=result.get("tokens_used", 0) if isinstance(result, dict) else 0,
            execution_time=execution_time_ms,
        )
        db.add(execution)
        await db.commit()
        await db.refresh(execution)

        # 9. Return response
        return PublicInvokeResponse(
            output=result.get("output") if isinstance(result, dict) else str(result),
            execution_id=str(execution.id),
            execution_path=result.get("execution_path", []) if isinstance(result, dict) else [],
            tokens_used=result.get("tokens_used", 0) if isinstance(result, dict) else 0,
            execution_time_ms=execution_time_ms,
            session_id=request.session_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )


@router.get(
    "/orgs/{org_slug}/deployments/{deployment_id}/health",
    tags=["public"],
    summary="Check deployment health",
)
async def check_deployment_health(
    org_slug: str,
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a deployment is healthy and accepting requests.
    This endpoint does not require authentication.
    """
    # Validate organization
    org_result = await db.execute(
        select(Organization).where(
            Organization.slug == org_slug,
            Organization.deleted_at.is_(None),
            Organization.is_active == True,
        )
    )
    organization = org_result.scalar_one_or_none()

    if not organization:
        return {"status": "error", "message": "Organization not found"}

    # Find deployment
    deployment_result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.organization_id == organization.id,
            Deployment.deleted_at.is_(None),
        )
    )
    deployment = deployment_result.scalar_one_or_none()

    if not deployment:
        return {"status": "error", "message": "Deployment not found"}

    return {
        "status": "healthy" if deployment.status == DeploymentStatus.ACTIVE else "unhealthy",
        "deployment_status": deployment.status.value if deployment.status else "unknown",
        "organization": org_slug,
    }
