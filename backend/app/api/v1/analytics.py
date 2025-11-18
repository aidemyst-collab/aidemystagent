from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.core.database import get_db
from app.models.agent import Agent, AgentExecution

router = APIRouter()


@router.get("/analytics")
async def get_analytics(
    agent_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get analytics data for agents and executions."""

    # Build base query for executions
    executions_query = select(AgentExecution)

    if agent_id:
        executions_query = executions_query.where(AgentExecution.agent_id == agent_id)
    if start_date:
        executions_query = executions_query.where(AgentExecution.created_at >= start_date)
    if end_date:
        executions_query = executions_query.where(AgentExecution.created_at <= end_date)

    # Total agents
    agents_result = await db.execute(select(func.count(Agent.id)))
    total_agents = agents_result.scalar() or 0

    # Total executions
    executions_count_result = await db.execute(
        select(func.count(AgentExecution.id)).select_from(
            executions_query.subquery()
        )
    )
    total_executions = executions_count_result.scalar() or 0

    # Average execution time
    avg_time_result = await db.execute(
        select(func.avg(AgentExecution.execution_time)).select_from(
            executions_query.subquery()
        )
    )
    avg_execution_time = avg_time_result.scalar() or 0

    # Success rate (executions with output)
    success_result = await db.execute(
        select(func.count(AgentExecution.id))
        .select_from(executions_query.subquery())
        .where(AgentExecution.output.isnot(None))
    )
    successful_executions = success_result.scalar() or 0
    success_rate = (
        (successful_executions / total_executions * 100)
        if total_executions > 0
        else 0
    )

    # Executions by agent
    executions_by_agent_query = (
        select(
            Agent.name,
            func.count(AgentExecution.id).label("count")
        )
        .join(AgentExecution, Agent.id == AgentExecution.agent_id)
        .group_by(Agent.name)
        .order_by(func.count(AgentExecution.id).desc())
        .limit(10)
    )

    if start_date:
        executions_by_agent_query = executions_by_agent_query.where(
            AgentExecution.created_at >= start_date
        )
    if end_date:
        executions_by_agent_query = executions_by_agent_query.where(
            AgentExecution.created_at <= end_date
        )

    executions_by_agent_result = await db.execute(executions_by_agent_query)
    executions_by_agent = [
        {"agent_name": row[0], "count": row[1]}
        for row in executions_by_agent_result.all()
    ]

    # Executions over time (last 7 days)
    executions_over_time_query = (
        select(
            func.date(AgentExecution.created_at).label("date"),
            func.count(AgentExecution.id).label("count")
        )
        .group_by(func.date(AgentExecution.created_at))
        .order_by(func.date(AgentExecution.created_at).desc())
        .limit(7)
    )

    if agent_id:
        executions_over_time_query = executions_over_time_query.where(
            AgentExecution.agent_id == agent_id
        )

    executions_over_time_result = await db.execute(executions_over_time_query)
    executions_over_time = [
        {"date": str(row[0]), "count": row[1]}
        for row in executions_over_time_result.all()
    ]

    return {
        "total_agents": total_agents,
        "total_executions": total_executions,
        "avg_execution_time": round(float(avg_execution_time), 2),
        "success_rate": round(success_rate, 2),
        "executions_by_agent": executions_by_agent,
        "executions_over_time": executions_over_time,
    }
