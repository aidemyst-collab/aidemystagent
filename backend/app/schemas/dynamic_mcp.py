"""
Pydantic schemas for Dynamic MCP Servers and Tools

Dynamic MCP Servers are API-based tool servers created via UI.
Each server contains multiple tools that share the same base URL and credentials.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class HTTPMethod(str, Enum):
    """HTTP methods for tool API calls."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ParameterType(str, Enum):
    """Parameter types for tool inputs."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


# ==============================================================================
# Tool Parameter Schema
# ==============================================================================

class ToolParameter(BaseModel):
    """Schema for a tool parameter definition."""
    name: str = Field(..., min_length=1, max_length=50, description="Parameter name")
    type: ParameterType = Field(default=ParameterType.STRING, description="Parameter data type")
    description: Optional[str] = Field(None, max_length=200, description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    enum: Optional[List[str]] = Field(None, description="Allowed values for enum types")


# ==============================================================================
# Dynamic MCP Tool Schemas
# ==============================================================================

class DynamicMCPToolBase(BaseModel):
    """Base schema for Dynamic MCP Tool."""
    name: str = Field(..., min_length=1, max_length=100, description="Tool name (used by LLM)")
    description: str = Field(..., min_length=1, max_length=500, description="Tool description (used by LLM to decide when to use)")
    path: str = Field(..., min_length=1, max_length=500, description="API path relative to server base URL (e.g., /weather or /users/{id})")
    method: HTTPMethod = Field(default=HTTPMethod.GET, description="HTTP method")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Input parameters for the tool")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Additional headers (merged with server defaults)")
    query_params: Optional[Dict[str, str]] = Field(default_factory=dict, description="Static query parameters")
    body_template: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Body template for POST/PUT/PATCH")
    response_path: Optional[str] = Field(None, max_length=200, description="JSON path to extract from response (e.g., data.items)")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tool name format (snake_case recommended)."""
        if not v.strip():
            raise ValueError('Tool name cannot be empty')
        # Allow alphanumeric and underscores
        cleaned = v.strip().lower().replace(' ', '_')
        if not cleaned.replace('_', '').isalnum():
            raise ValueError('Tool name can only contain letters, numbers, and underscores')
        return cleaned

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate tool path format."""
        if not v.strip():
            raise ValueError('Path cannot be empty')
        path = v.strip()
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        return path


class DynamicMCPToolCreate(DynamicMCPToolBase):
    """Schema for creating a tool within a server."""
    pass


class DynamicMCPToolUpdate(BaseModel):
    """Schema for updating a tool."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    path: Optional[str] = Field(None, min_length=1, max_length=500)
    method: Optional[HTTPMethod] = None
    parameters: Optional[List[ToolParameter]] = None
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    body_template: Optional[Dict[str, Any]] = None
    response_path: Optional[str] = None
    is_active: Optional[bool] = None


class DynamicMCPToolResponse(BaseModel):
    """Schema for tool response."""
    id: UUID
    server_id: UUID
    name: str
    description: str
    path: str
    method: str
    parameters: List[Dict[str, Any]]
    headers: Optional[Dict[str, str]]
    query_params: Optional[Dict[str, str]]
    body_template: Optional[Dict[str, Any]]
    response_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# Dynamic MCP Server Schemas
# ==============================================================================

class DynamicMCPServerBase(BaseModel):
    """Base schema for Dynamic MCP Server."""
    name: str = Field(..., min_length=1, max_length=100, description="Server display name")
    description: Optional[str] = Field(None, max_length=500, description="Server description")
    base_url: str = Field(..., min_length=1, max_length=500, description="Base URL for all tools (e.g., https://api.example.com/v1)")
    credential_id: Optional[str] = Field(None, description="Credential ID for authentication")
    default_headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Default headers for all tools")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate server name."""
        if not v.strip():
            raise ValueError('Server name cannot be empty')
        return v.strip()

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format."""
        if not v.strip():
            raise ValueError('Base URL cannot be empty')
        url = v.strip().rstrip('/')  # Remove trailing slash
        if not url.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return url


class DynamicMCPServerCreate(DynamicMCPServerBase):
    """Schema for creating a server with tools."""
    tools: List[DynamicMCPToolCreate] = Field(default_factory=list, description="Initial tools for this server")


class DynamicMCPServerUpdate(BaseModel):
    """Schema for updating a server."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    credential_id: Optional[str] = None
    default_headers: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    is_active: Optional[bool] = None

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate base URL format if provided."""
        if v is None:
            return v
        url = v.strip().rstrip('/')
        if not url.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return url


class DynamicMCPServerResponse(BaseModel):
    """Schema for server response with tools."""
    id: UUID
    organization_id: UUID
    creator_id: UUID
    name: str
    description: Optional[str]
    base_url: str
    credential_id: Optional[str]
    default_headers: Optional[Dict[str, str]]
    timeout_seconds: int
    is_active: bool
    tools: List[DynamicMCPToolResponse]
    tool_count: int
    active_tool_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DynamicMCPServerListResponse(BaseModel):
    """Schema for listing servers."""
    servers: List[DynamicMCPServerResponse]
    total: int


class DynamicMCPServerSummary(BaseModel):
    """Lightweight server summary (without full tool details)."""
    id: UUID
    name: str
    description: Optional[str]
    base_url: str
    is_active: bool
    tool_count: int
    active_tool_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# Internal Schemas (for Dynamic MCP Server runtime)
# ==============================================================================

class DynamicMCPServerInternal(BaseModel):
    """Schema for internal API - includes all info needed by Dynamic MCP Server runtime."""
    id: str
    name: str
    description: Optional[str]
    base_url: str
    credential_id: Optional[str]
    organization_id: str
    default_headers: Dict[str, str]
    timeout_seconds: int
    is_active: bool
    tools: List[Dict[str, Any]]  # Full tool schemas with _config


class DynamicMCPServersInternalResponse(BaseModel):
    """Response for internal API listing all servers with tools."""
    servers: List[DynamicMCPServerInternal]
    total: int


# ==============================================================================
# Tool Execution Schemas
# ==============================================================================

class ToolExecuteRequest(BaseModel):
    """Schema for testing/executing a tool."""
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolExecuteResponse(BaseModel):
    """Schema for tool execution result."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
