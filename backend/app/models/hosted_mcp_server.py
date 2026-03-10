"""
Hosted MCP Server model for managing MCP servers deployed to Azure Container Apps.

Each HostedMCPServer represents an MCP server that is deployed and managed
by AgentStudio on Azure Container Apps.
"""
import enum
from sqlalchemy import Column, String, DateTime, Integer, Numeric, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class HostedMCPServerStatus(str, enum.Enum):
    """Status enum for hosted MCP servers."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETED = "deleted"


class HostedMCPServerSourceType(str, enum.Enum):
    """Source type for the MCP server deployment."""
    REGISTRY = "registry"  # npm package (e.g., @anthropic/mcp-weather)
    GITHUB = "github"      # GitHub repository
    DOCKER = "docker"      # Pre-built Docker image


class HostedMCPServer(Base):
    """
    Represents an MCP Server hosted on Azure Container Apps.

    Example:
        MCP Weather Server
        - source_type: docker
        - source_config: {"image": "ghcr.io/anthropic/mcp-weather:latest"}
        - azure_app_url: https://mcp-weather-123.internal.azurecontainerapps.io
        - status: running
        - discovered_tools: [{"name": "get_weather", "description": "Get weather for a location"}]
    """
    __tablename__ = "hosted_mcp_servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Server Identity
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Source Configuration
    source_type = Column(String(20), nullable=False)  # 'registry', 'github', 'docker'
    source_config = Column(JSON, nullable=False)
    # source_config examples:
    # registry: {"package": "@anthropic/mcp-weather", "version": "latest"}
    # github: {"repo": "user/repo", "branch": "main", "dockerfile_path": "Dockerfile"}
    # docker: {"image": "ghcr.io/user/mcp-server:latest", "registry_credential_id": "optional-id"}

    # Azure Container App Details
    azure_app_name = Column(String(63), nullable=True)  # Container App name (auto-generated)
    azure_app_url = Column(String(255), nullable=True)  # Internal URL
    azure_resource_id = Column(String(500), nullable=True)  # Full Azure resource ID

    # Runtime Configuration
    environment_variables = Column(JSON, default=dict)  # {"KEY": "value" or "{{credential:name}}"}
    port = Column(Integer, default=3000, nullable=False)
    cpu_cores = Column(Numeric(3, 2), default=0.25, nullable=False)  # 0.25 to 4
    memory_gb = Column(Numeric(3, 1), default=0.5, nullable=False)   # 0.5 to 8
    min_replicas = Column(Integer, default=0, nullable=False)  # Scale to zero
    max_replicas = Column(Integer, default=3, nullable=False)

    # Status
    status = Column(String(20), default=HostedMCPServerStatus.PENDING.value, nullable=False, index=True)
    last_health_check = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Discovered Capabilities (populated after deployment)
    discovered_tools = Column(JSON, default=list)
    discovered_resources = Column(JSON, default=list)
    discovered_prompts = Column(JSON, default=list)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    # Relationships
    organization = relationship("Organization", back_populates="hosted_mcp_servers")
    creator = relationship("User", back_populates="hosted_mcp_servers")

    def __repr__(self):
        return f"<HostedMCPServer(id={self.id}, name={self.name}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if server is in an active state."""
        return self.status == HostedMCPServerStatus.RUNNING.value and self.deleted_at is None

    @property
    def tool_count(self) -> int:
        """Return the number of discovered tools."""
        return len(self.discovered_tools) if self.discovered_tools else 0

    @property
    def resource_count(self) -> int:
        """Return the number of discovered resources."""
        return len(self.discovered_resources) if self.discovered_resources else 0

    @property
    def prompt_count(self) -> int:
        """Return the number of discovered prompts."""
        return len(self.discovered_prompts) if self.discovered_prompts else 0

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "creator_id": str(self.creator_id),
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "source_config": self.source_config,
            "azure_app_name": self.azure_app_name,
            "azure_app_url": self.azure_app_url,
            "azure_resource_id": self.azure_resource_id,
            "environment_variables": self.environment_variables or {},
            "port": self.port,
            "cpu_cores": float(self.cpu_cores) if self.cpu_cores else 0.25,
            "memory_gb": float(self.memory_gb) if self.memory_gb else 0.5,
            "min_replicas": self.min_replicas,
            "max_replicas": self.max_replicas,
            "status": self.status,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "error_message": self.error_message,
            "discovered_tools": self.discovered_tools or [],
            "discovered_resources": self.discovered_resources or [],
            "discovered_prompts": self.discovered_prompts or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
