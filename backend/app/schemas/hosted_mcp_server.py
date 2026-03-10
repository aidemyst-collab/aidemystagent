"""
Pydantic schemas for Hosted MCP Servers

Hosted MCP Servers are MCP servers deployed to Azure Container Apps
and managed by AgentStudio.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from enum import Enum


class HostedMCPServerStatus(str, Enum):
    """Status of a hosted MCP server."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETED = "deleted"


class HostedMCPServerSourceType(str, Enum):
    """Source type for MCP server deployment."""
    REGISTRY = "registry"  # npm package (e.g., @anthropic/mcp-weather)
    GITHUB = "github"      # GitHub repository
    DOCKER = "docker"      # Pre-built Docker image


# ==============================================================================
# Source Configuration Schemas
# ==============================================================================

class RegistrySourceConfig(BaseModel):
    """Configuration for deploying from npm registry."""
    package: str = Field(..., min_length=1, description="npm package name (e.g., @anthropic/mcp-weather)")
    version: str = Field(default="latest", description="Package version (default: latest)")


class GitHubSourceConfig(BaseModel):
    """Configuration for deploying from GitHub repository."""
    repo: str = Field(..., min_length=1, description="GitHub repo (e.g., user/repo)")
    branch: str = Field(default="main", description="Branch to build from")
    dockerfile_path: str = Field(default="Dockerfile", description="Path to Dockerfile")


class DockerSourceConfig(BaseModel):
    """Configuration for deploying from Docker image."""
    image: str = Field(..., min_length=1, description="Docker image URL (e.g., ghcr.io/user/mcp-server:latest)")
    registry_credential_id: Optional[str] = Field(None, description="Credential ID for private registry")


# ==============================================================================
# Discovered Capability Schemas
# ==============================================================================

class DiscoveredTool(BaseModel):
    """A tool discovered from an MCP server."""
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None


class DiscoveredResource(BaseModel):
    """A resource discovered from an MCP server."""
    uri: str
    name: Optional[str] = None
    description: Optional[str] = None
    mime_type: Optional[str] = None


class DiscoveredPrompt(BaseModel):
    """A prompt discovered from an MCP server."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


# ==============================================================================
# Hosted MCP Server Schemas
# ==============================================================================

class HostedMCPServerBase(BaseModel):
    """Base schema for Hosted MCP Server."""
    name: str = Field(..., min_length=1, max_length=100, description="Server display name")
    description: Optional[str] = Field(None, max_length=500, description="Server description")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate server name."""
        if not v.strip():
            raise ValueError('Server name cannot be empty')
        # Name should be alphanumeric with hyphens (for Azure Container Apps naming)
        cleaned = v.strip()
        if len(cleaned) > 100:
            raise ValueError('Server name cannot exceed 100 characters')
        return cleaned


class HostedMCPServerCreate(HostedMCPServerBase):
    """Schema for creating a hosted MCP server."""
    source_type: HostedMCPServerSourceType = Field(..., description="Source type for deployment")
    source_config: Dict[str, Any] = Field(..., description="Source-specific configuration")
    environment_variables: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Environment variables (use {{credential:name}} for secret refs)"
    )
    port: int = Field(default=3000, ge=1, le=65535, description="Container port")
    cpu_cores: float = Field(default=0.25, ge=0.25, le=4, description="CPU cores (0.25 to 4)")
    memory_gb: float = Field(default=0.5, ge=0.5, le=8, description="Memory in GB (0.5 to 8)")
    min_replicas: int = Field(default=0, ge=0, le=10, description="Minimum replicas (0 for scale-to-zero)")
    max_replicas: int = Field(default=3, ge=1, le=10, description="Maximum replicas")

    @field_validator('source_config')
    @classmethod
    def validate_source_config(cls, v: Dict[str, Any], info) -> Dict[str, Any]:
        """Validate source config based on source_type."""
        # Note: Full validation happens in the API layer with source_type context
        if not v:
            raise ValueError('Source configuration cannot be empty')
        return v

    @field_validator('max_replicas')
    @classmethod
    def validate_replicas(cls, v: int, info) -> int:
        """Ensure max_replicas >= min_replicas."""
        min_replicas = info.data.get('min_replicas', 0)
        if v < min_replicas:
            raise ValueError('max_replicas must be >= min_replicas')
        return v


class HostedMCPServerUpdate(BaseModel):
    """Schema for updating a hosted MCP server."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    environment_variables: Optional[Dict[str, str]] = None
    cpu_cores: Optional[float] = Field(None, ge=0.25, le=4)
    memory_gb: Optional[float] = Field(None, ge=0.5, le=8)
    min_replicas: Optional[int] = Field(None, ge=0, le=10)
    max_replicas: Optional[int] = Field(None, ge=1, le=10)


class HostedMCPServerResponse(BaseModel):
    """Schema for hosted MCP server response."""
    id: UUID
    organization_id: UUID
    creator_id: UUID
    name: str
    description: Optional[str]
    source_type: str
    source_config: Dict[str, Any]
    azure_app_name: Optional[str]
    azure_app_url: Optional[str]
    azure_resource_id: Optional[str]
    environment_variables: Dict[str, str]
    port: int
    cpu_cores: float
    memory_gb: float
    min_replicas: int
    max_replicas: int
    status: str
    last_health_check: Optional[datetime]
    error_message: Optional[str]
    discovered_tools: List[Dict[str, Any]]
    discovered_resources: List[Dict[str, Any]]
    discovered_prompts: List[Dict[str, Any]]
    tool_count: int
    resource_count: int
    prompt_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HostedMCPServerListResponse(BaseModel):
    """Schema for listing hosted MCP servers."""
    servers: List[HostedMCPServerResponse]
    total: int


class HostedMCPServerSummary(BaseModel):
    """Lightweight server summary."""
    id: UUID
    name: str
    description: Optional[str]
    source_type: str
    status: str
    azure_app_url: Optional[str]
    tool_count: int
    resource_count: int
    prompt_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# Operation Schemas
# ==============================================================================

class HostedMCPServerLogs(BaseModel):
    """Schema for container logs response."""
    logs: str
    timestamp: datetime


class HostedMCPServerDiscoveryResponse(BaseModel):
    """Schema for capability discovery response."""
    tools: List[DiscoveredTool]
    resources: List[DiscoveredResource]
    prompts: List[DiscoveredPrompt]
    discovered_at: datetime


class ToolExecuteRequest(BaseModel):
    """Schema for executing a tool on a hosted MCP server."""
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolExecuteResponse(BaseModel):
    """Schema for tool execution result."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


# ==============================================================================
# Status Update Schemas (Internal)
# ==============================================================================

class HostedMCPServerStatusUpdate(BaseModel):
    """Schema for internal status updates."""
    status: HostedMCPServerStatus
    azure_app_name: Optional[str] = None
    azure_app_url: Optional[str] = None
    azure_resource_id: Optional[str] = None
    error_message: Optional[str] = None


class HostedMCPServerCapabilitiesUpdate(BaseModel):
    """Schema for updating discovered capabilities."""
    discovered_tools: List[Dict[str, Any]]
    discovered_resources: List[Dict[str, Any]]
    discovered_prompts: List[Dict[str, Any]]
