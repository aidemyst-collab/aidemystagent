from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, Any, Dict, List
from app.models.agent import AgentStatus


class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None


class WorkflowCreate(WorkflowBase):
    config: Dict[str, Any]  # Contains: nodes, edges, executionSettings


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[AgentStatus] = None


class WorkflowResponse(WorkflowBase):
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


class WorkflowListResponse(BaseModel):
    total: int
    workflows: List[WorkflowResponse]


class WorkflowDeployResponse(BaseModel):
    id: UUID4
    status: str
    endpoint: str
    deployedAt: datetime


class WorkflowExecutionCreate(BaseModel):
    input: Dict[str, Any]


class WorkflowExecutionResponse(BaseModel):
    id: UUID4
    workflow_id: UUID4
    user_id: UUID4
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    tokens_used: int
    execution_time: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
