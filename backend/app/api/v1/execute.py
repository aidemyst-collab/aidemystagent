from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union, List
import json
import asyncio

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.agent import Agent, AgentExecution
from app.models.user import User
from app.services.langgraph_engine import LangGraphEngine
from app.api.deps import (
    get_current_active_user,
    require_permission,
    get_effective_organization_id,
)
import redis.asyncio as aioredis

router = APIRouter()


class ExecuteRequest(BaseModel):
    """Request model for agent execution."""
    input: Union[str, Dict[str, Any], Any] = Field(
        ...,
        description="Input for the agent. Can be a string (chat mode), JSON object (json mode), or form data (form mode)"
    )
    stream: bool = False
    mode: Optional[str] = Field(
        None,
        description="Optional mode override (chat, json, form). If not provided, uses INPUT node configuration"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation history (memory feature)"
    )


class ExecuteResponse(BaseModel):
    """Response model for agent execution."""
    execution_id: UUID
    output: Optional[str]
    execution_path: list
    execution_trace: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed execution trace with input/output for each node"
    )
    node_outputs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Output data from each node for reference"
    )
    tokens_used: int
    execution_time: int
    input_metadata: Optional[Dict[str, Any]] = None
    processed_input: Optional[Dict[str, Any]] = None


@router.post("/{agent_id}")
async def execute_agent(
    agent_id: UUID,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:execute")),
):
    """Execute an agent (non-streaming)."""

    # Get agent
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
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

    # Execute agent
    import time
    start_time = time.time()

    # Create engine instance with database session and Redis client
    engine = LangGraphEngine(db=db, redis_client=redis)

    # Prepare input with session_id if provided
    agent_input = request.input
    if request.session_id:
        if isinstance(agent_input, dict):
            agent_input["session_id"] = request.session_id
        elif isinstance(agent_input, str):
            # For string inputs, we'll pass session_id separately
            # It will be picked up by the MEMORY node
            agent_input = {
                "message": agent_input,
                "session_id": request.session_id
            }

    execution_result = await engine.execute_agent(
        agent_config=agent.config,
        user_input=agent_input,
        input_mode=request.mode
    )

    execution_time = int((time.time() - start_time) * 1000)  # milliseconds

    # Extract token usage
    llm_usage = execution_result.get("llm_usage") or {}
    tokens_used = llm_usage.get("total_tokens", 0)

    # Create execution record
    execution = AgentExecution(
        agent_id=agent_id,
        user_id=current_user.id,
        input={
            "raw_input": request.input if isinstance(request.input, (str, dict, list)) else str(request.input),
            "mode": request.mode or "chat",
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

    return ExecuteResponse(
        execution_id=execution.id,
        output=execution_result.get("output"),
        execution_path=execution_result.get("execution_path", []),
        execution_trace=execution_result.get("execution_trace", []),
        node_outputs=execution_result.get("node_outputs", {}),
        tokens_used=tokens_used,
        execution_time=execution_time,
        input_metadata=execution_result.get("input_metadata"),
        processed_input=execution_result.get("processed_input"),
    )


@router.post("/{agent_id}/stream")
async def execute_agent_stream(
    agent_id: UUID,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:execute")),
):
    """Execute an agent with streaming response."""

    # Get agent
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
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

    async def generate():
        """Generate streaming response."""
        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'message': 'Execution started'})}\n\n"

        # Create engine instance with database session and Redis client
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

        # Execute agent
        execution_result = await engine.execute_agent(
            agent_config=agent.config,
            user_input=agent_input,
            input_mode=request.mode
        )

        # Stream execution path
        for step in execution_result.get("execution_path", []):
            yield f"data: {json.dumps({'type': 'step', 'node': step})}\n\n"
            await asyncio.sleep(0.1)  # Small delay for demo

        # Send final output
        output = execution_result.get("output", "")
        if output:
            # Stream output word by word for demo
            words = output.split()
            for word in words:
                yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
                await asyncio.sleep(0.05)

        # Send completion event
        yield f"data: {json.dumps({'type': 'complete', 'message': 'Execution completed'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/{execution_id}/status")
async def get_execution_status(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("agents:read")),
):
    """Get execution status."""
    result = await db.execute(
        select(AgentExecution).where(AgentExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    # Check if user has access to this execution
    if execution.user_id != current_user.id:
        # Check if agent belongs to effective org (supports platform admin switching)
        agent_result = await db.execute(
            select(Agent).where(Agent.id == execution.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if not agent or agent.organization_id != effective_org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this execution",
            )

    return {
        "id": execution.id,
        "agent_id": execution.agent_id,
        "input": execution.input,
        "output": execution.output,
        "tokens_used": execution.tokens_used,
        "execution_time": execution.execution_time,
        "created_at": execution.created_at,
    }
