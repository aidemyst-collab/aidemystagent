from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class ToolType(str, Enum):
    BUILT_IN = "built-in"
    CUSTOM = "custom"
    API = "api"
    MCP = "mcp"


class ToolVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    ORGANIZATION = "organization"


class ToolStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class ToolConfigBase(BaseModel):
    """Base configuration for tools."""
    parameters: Dict[str, Any] = Field(default_factory=dict)


class CustomToolConfig(ToolConfigBase):
    """Configuration for custom code tools."""
    language: str = Field(..., description="Programming language (python, javascript, typescript)")
    code: str = Field(..., description="The code to execute")


class APIToolConfig(ToolConfigBase):
    """Configuration for API integration tools."""
    api: Dict[str, Any] = Field(
        ...,
        description="API configuration including endpoint, method, auth"
    )


class MCPToolConfig(ToolConfigBase):
    """Configuration for MCP (Model Context Protocol) tools."""
    mcp_type: str = Field(..., description="MCP type: resource, prompt, or tool")
    resource_uri: str = Field(..., description="Resource URI pattern")
    mcp_server_url: Optional[str] = Field(None, description="Optional custom MCP server URL")


class ToolParameterType(str, Enum):
    """Parameter types for dynamic tools."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""
    name: str = Field(..., min_length=1, max_length=50, description="Parameter name")
    type: ToolParameterType = Field(default=ToolParameterType.STRING, description="Parameter type")
    description: Optional[str] = Field(None, max_length=200, description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value")
    enum: Optional[List[str]] = Field(None, description="Allowed values for enum")


class HTTPMethod(str, Enum):
    """HTTP methods for API tools."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ToolCreate(BaseModel):
    """Schema for creating a new tool."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    type: ToolType
    config: Dict[str, Any] = Field(..., description="Tool-specific configuration")
    visibility: ToolVisibility = ToolVisibility.PRIVATE
    status: ToolStatus = ToolStatus.ACTIVE

    @validator('name')
    def validate_name(cls, v):
        """Validate tool name format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Tool name must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()

    @validator('config')
    def validate_config(cls, v, values):
        """Validate config based on tool type."""
        tool_type = values.get('type')

        if not v:
            raise ValueError('Config cannot be empty')

        # Ensure parameters exist
        if 'parameters' not in v:
            v['parameters'] = {}

        # Type-specific validation
        if tool_type == ToolType.CUSTOM:
            if 'code' not in v or 'language' not in v:
                raise ValueError('Custom tools must have "code" and "language" in config')
            if v['language'] not in ['python', 'javascript', 'typescript']:
                raise ValueError('Invalid language for custom tool')

        elif tool_type == ToolType.API:
            if 'api' not in v:
                raise ValueError('API tools must have "api" configuration')
            api_config = v['api']
            required_fields = ['endpoint', 'method', 'auth_type']
            if not all(field in api_config for field in required_fields):
                raise ValueError(f'API config must contain: {", ".join(required_fields)}')

        elif tool_type == ToolType.MCP:
            if 'mcp_type' not in v or 'resource_uri' not in v:
                raise ValueError('MCP tools must have "mcp_type" and "resource_uri" in config')
            if v['mcp_type'] not in ['resource', 'prompt', 'tool']:
                raise ValueError('Invalid MCP type')

        return v


class ToolUpdate(BaseModel):
    """Schema for updating a tool."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    config: Optional[Dict[str, Any]] = None
    visibility: Optional[ToolVisibility] = None
    status: Optional[ToolStatus] = None


class ToolResponse(BaseModel):
    """Schema for tool response."""
    id: UUID
    organization_id: UUID
    creator_id: UUID
    name: str
    description: str
    type: ToolType
    config: Dict[str, Any]
    visibility: ToolVisibility
    status: ToolStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    """Schema for listing tools."""
    tools: List[ToolResponse]
    total: int


class ToolExecuteRequest(BaseModel):
    """Request model for tool execution."""
    input_data: Dict[str, Any]


class ToolExecuteResponse(BaseModel):
    """Response model for tool execution."""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: Optional[int] = None  # in milliseconds
