from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, Any, Dict, List
from app.models.agent import AgentStatus


class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None


class AgentCreate(AgentBase):
    config: Dict[str, Any]


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[AgentStatus] = None


class AgentResponse(AgentBase):
    id: UUID4
    organization_id: UUID4
    creator_id: UUID4
    config: Dict[str, Any]
    version: int
    status: AgentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    total: int
    agents: List[AgentResponse]


class AgentExecutionCreate(BaseModel):
    input: Dict[str, Any]


class AgentExecutionResponse(BaseModel):
    id: UUID4
    agent_id: UUID4
    user_id: UUID4
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    tokens_used: int
    execution_time: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
