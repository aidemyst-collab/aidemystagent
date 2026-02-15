from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from app.models.deployment import DeploymentStatus, DeploymentEnvironment


class DeploymentBase(BaseModel):
    """Base deployment schema."""
    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT
    config: Dict[str, Any] = Field(default_factory=dict)


class DeploymentCreate(DeploymentBase):
    """Schema for creating a deployment."""
    agent_id: UUID
    version: str


class DeploymentUpdate(BaseModel):
    """Schema for updating a deployment."""
    status: Optional[DeploymentStatus] = None
    endpoint_url: Optional[str] = None
    error_message: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class DeploymentResponse(DeploymentBase):
    """Schema for deployment response."""
    id: UUID
    agent_id: UUID
    agent_name: Optional[str] = None
    version: str
    status: DeploymentStatus
    endpoint_url: Optional[str] = None
    voice_webhook_url: Optional[str] = None
    api_key: Optional[str] = None
    error_message: Optional[str] = None
    deployed_by: UUID
    deployed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeploymentList(BaseModel):
    """Schema for deployment list response."""
    deployments: list[DeploymentResponse]
    total: int


class DeploymentExport(BaseModel):
    """Schema for exporting full deployment with agent workflow."""
    id: UUID
    agent_id: UUID
    agent_name: str
    agent_description: Optional[str] = None
    version: str
    environment: DeploymentEnvironment
    status: DeploymentStatus
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None
    deployed_at: Optional[datetime] = None
    created_at: datetime

    # Deployment config
    deployment_config: Dict[str, Any] = Field(default_factory=dict)

    # Agent workflow (nodes and edges)
    workflow: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full agent workflow with nodes and edges"
    )

    class Config:
        from_attributes = True
