from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import asyncio

from app.core.database import get_db
from app.models.agent import Agent, AgentExecution
from app.services.langgraph_engine import LangGraphEngine

router = APIRouter()
engine = LangGraphEngine()


class ExecuteRequest(BaseModel):
    """Request model for agent execution."""
    input: str
    stream: bool = False


class ExecuteResponse(BaseModel):
    """Response model for agent execution."""
    execution_id: UUID
    output: Optional[str]
    execution_path: list
    tokens_used: int
    execution_time: int


@router.post("/{agent_id}")
async def execute_agent(
    agent_id: UUID,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute an agent (non-streaming)."""

    # Get agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Execute agent
    import time
    start_time = time.time()

    execution_result = await engine.execute_agent(
        agent_config=agent.config,
        user_input=request.input
    )

    execution_time = int((time.time() - start_time) * 1000)  # milliseconds

    # Create execution record
    execution = AgentExecution(
        agent_id=agent_id,
        user_id=agent.creator_id,  # TODO: Get from current user
        input={"query": request.input},
        output={"result": execution_result.get("output")},
        tokens_used=0,  # TODO: Track actual tokens
        execution_time=execution_time,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    return ExecuteResponse(
        execution_id=execution.id,
        output=execution_result.get("output"),
        execution_path=execution_result.get("execution_path", []),
        tokens_used=0,
        execution_time=execution_time,
    )


@router.post("/{agent_id}/stream")
async def execute_agent_stream(
    agent_id: UUID,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute an agent with streaming response."""

    # Get agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    async def generate():
        """Generate streaming response."""
        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'message': 'Execution started'})}\n\n"

        # Execute agent
        execution_result = await engine.execute_agent(
            agent_config=agent.config,
            user_input=request.input
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

    return {
        "id": execution.id,
        "agent_id": execution.agent_id,
        "input": execution.input,
        "output": execution.output,
        "tokens_used": execution.tokens_used,
        "execution_time": execution.execution_time,
        "created_at": execution.created_at,
    }
