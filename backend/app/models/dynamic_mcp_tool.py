"""
Dynamic MCP Tool model for storing tool definitions used by the Dynamic MCP Server.

These tools are created via UI and exposed by the Dynamic MCP Server.
The server reads these definitions and makes actual API calls on behalf of agents.
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class DynamicMCPTool(Base):
    """
    Stores tool definitions for the Dynamic MCP Server.

    When an agent calls a tool, the Dynamic MCP Server:
    1. Looks up this definition by name
    2. Fetches the credential (if specified)
    3. Makes the actual API call
    4. Returns the result to the agent

    The LLM never sees the actual credentials - only tool name and parameters.
    """
    __tablename__ = "dynamic_mcp_tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Tool identification
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)

    # API configuration
    api_endpoint = Column(String(1000), nullable=False)
    method = Column(String(10), nullable=False, default="GET")  # GET, POST, PUT, PATCH, DELETE

    # Parameters schema (JSON array of ToolParameter)
    parameters = Column(JSON, default=list)

    # Request configuration
    headers = Column(JSON, default=dict)  # Custom headers
    query_params = Column(JSON, default=dict)  # Static query parameters
    body_template = Column(JSON, default=dict)  # Body template for POST/PUT/PATCH

    # Authentication (credential reference - NOT the actual secret)
    credential_id = Column(String, ForeignKey("credentials.id"), nullable=True)

    # Response handling
    response_path = Column(String(200), nullable=True)  # JSON path to extract
    response_template = Column(String(1000), nullable=True)  # Template to format response

    # Timeout and retry
    timeout_seconds = Column(Integer, default=30)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="dynamic_mcp_tools")
    creator = relationship("User", back_populates="dynamic_mcp_tools")
    credential = relationship("Credential", back_populates="dynamic_mcp_tools")

    def __repr__(self):
        return f"<DynamicMCPTool(id={self.id}, name={self.name}, endpoint={self.api_endpoint})>"

    def to_mcp_tool_schema(self) -> dict:
        """
        Convert to MCP tool schema format for the Dynamic MCP Server.

        Returns format compatible with FastMCP tool registration.
        """
        # Build input schema from parameters
        properties = {}
        required = []

        for param in (self.parameters or []):
            param_name = param.get("name")
            param_type = param.get("type", "string")

            # Map to JSON Schema types
            json_type = {
                "string": "string",
                "number": "number",
                "integer": "integer",
                "boolean": "boolean",
                "array": "array",
                "object": "object",
            }.get(param_type, "string")

            properties[param_name] = {
                "type": json_type,
                "description": param.get("description", ""),
            }

            if param.get("default") is not None:
                properties[param_name]["default"] = param.get("default")

            if param.get("enum"):
                properties[param_name]["enum"] = param.get("enum")

            if param.get("required"):
                required.append(param_name)

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
            # Internal metadata for execution
            "_config": {
                "tool_id": str(self.id),
                "organization_id": str(self.organization_id),
                "api_endpoint": self.api_endpoint,
                "method": self.method,
                "headers": self.headers or {},
                "query_params": self.query_params or {},
                "body_template": self.body_template or {},
                "credential_id": self.credential_id,
                "response_path": self.response_path,
                "response_template": self.response_template,
                "timeout_seconds": self.timeout_seconds,
            }
        }
