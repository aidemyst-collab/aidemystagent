"""
Pydantic schemas for MCP Server management
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class MCPServerStatus(str, Enum):
    """Status of an MCP server."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class MCPTransportType(str, Enum):
    """Transport type for MCP server connection."""
    SSE = "sse"
    HTTP = "http"
    STDIO = "stdio"


class MCPToolSchema(BaseModel):
    """Schema for a discovered MCP tool."""
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None


class MCPResourceSchema(BaseModel):
    """Schema for a discovered MCP resource."""
    uri: str
    name: Optional[str] = None
    description: Optional[str] = None
    mime_type: Optional[str] = None


class MCPPromptSchema(BaseModel):
    """Schema for a discovered MCP prompt."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class MCPServerCreate(BaseModel):
    """Schema for creating a new MCP server."""
    name: str = Field(..., min_length=1, max_length=100, description="Display name for the server")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    server_url: str = Field(..., min_length=1, max_length=500, description="MCP server URL (e.g., http://localhost:3000/sse)")
    transport_type: MCPTransportType = Field(default=MCPTransportType.SSE, description="Transport protocol")
    credential_id: Optional[str] = Field(None, description="Optional credential ID for authentication")

    @validator('name')
    def validate_name(cls, v):
        """Validate server name format."""
        if not v.strip():
            raise ValueError('Server name cannot be empty')
        return v.strip()

    @validator('server_url')
    def validate_server_url(cls, v):
        """Validate server URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Server URL must start with http:// or https://')
        return v.strip()


class MCPServerUpdate(BaseModel):
    """Schema for updating an MCP server."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    server_url: Optional[str] = Field(None, min_length=1, max_length=500)
    transport_type: Optional[MCPTransportType] = None
    credential_id: Optional[str] = None
    status: Optional[MCPServerStatus] = None

    @validator('server_url')
    def validate_server_url(cls, v):
        """Validate server URL format if provided."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Server URL must start with http:// or https://')
        return v.strip() if v else v


class MCPServerResponse(BaseModel):
    """Schema for MCP server response."""
    id: UUID
    organization_id: UUID
    creator_id: UUID
    name: str
    description: Optional[str]
    server_url: str
    transport_type: MCPTransportType
    credential_id: Optional[str]
    status: MCPServerStatus
    last_health_check: Optional[datetime]
    last_error: Optional[str]
    discovered_tools: List[Dict[str, Any]]
    discovered_resources: List[Dict[str, Any]]
    discovered_prompts: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPServerListResponse(BaseModel):
    """Schema for listing MCP servers."""
    servers: List[MCPServerResponse]
    total: int


class MCPServerTestRequest(BaseModel):
    """Schema for testing MCP server connection."""
    server_url: Optional[str] = Field(None, description="Override server URL for testing")
    auth_token: Optional[str] = Field(None, description="Override auth token for testing")


class MCPServerTestResponse(BaseModel):
    """Schema for MCP server test result."""
    success: bool
    message: str
    response_time_ms: Optional[int] = None
    server_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MCPServerDiscoveryResponse(BaseModel):
    """Schema for MCP server discovery result."""
    success: bool
    tools: List[MCPToolSchema]
    resources: List[MCPResourceSchema]
    prompts: List[MCPPromptSchema]
    error: Optional[str] = None


class MCPServerHealthResponse(BaseModel):
    """Schema for MCP server health check result."""
    server_id: UUID
    status: MCPServerStatus
    last_check: datetime
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
