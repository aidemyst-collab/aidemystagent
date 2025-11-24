from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.agent import Agent, AgentExecution
from typing import Dict, Any, List

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get dashboard statistics."""
    
    # Count agents
    agents_count = await db.execute(select(func.count(Agent.id)))
    total_agents = agents_count.scalar() or 0
    
    # Count executions
    exec_count = await db.execute(select(func.count(AgentExecution.id)))
    total_executions = exec_count.scalar() or 0
    
    # Sum tokens
    tokens_sum = await db.execute(select(func.sum(AgentExecution.tokens_used)))
    total_tokens = tokens_sum.scalar() or 0
    
    # Avg execution time
    avg_time = await db.execute(select(func.avg(AgentExecution.execution_time)))
    avg_execution_time = avg_time.scalar() or 0
    
    return {
        "total_agents": total_agents,
        "total_executions": total_executions,
        "total_tokens": int(total_tokens) if total_tokens else 0,
        "avg_execution_time": float(avg_execution_time) if avg_execution_time else 0,
    }


@router.get("/activity")
async def get_recent_activity(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get recent activity."""
    
    result = await db.execute(
        select(AgentExecution)
        .order_by(AgentExecution.created_at.desc())
        .limit(limit)
    )
    executions = result.scalars().all()
    
    activity = []
    for execution in executions:
        agent_result = await db.execute(
            select(Agent).where(Agent.id == execution.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        activity.append({
            "id": str(execution.id),
            "agent_id": str(execution.agent_id),
            "agent_name": agent.name if agent else "Unknown",
            "tokens_used": execution.tokens_used,
            "execution_time": execution.execution_time,
            "created_at": execution.created_at.isoformat() if execution.created_at else None,
        })
    
    return activity
