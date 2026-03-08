"""
Dynamic MCP Tool model for storing tool definitions within a Dynamic MCP Server.

Each tool belongs to a DynamicMCPServer and inherits its base_url and credentials.
Tools only define the path, method, and parameters - the server handles the rest.
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class DynamicMCPTool(Base):
    """
    Stores tool definitions for a Dynamic MCP Server.

    Each tool belongs to a server and uses relative paths.
    Example:
        Server: https://api.weather.com/v1
        Tool: get_weather
            path: /current
            method: GET
            → Full URL: https://api.weather.com/v1/current
    """
    __tablename__ = "dynamic_mcp_tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parent server relationship
    server_id = Column(UUID(as_uuid=True), ForeignKey("dynamic_mcp_servers.id"), nullable=False)

    # Tool identification
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)

    # Endpoint configuration (relative to server base_url)
    path = Column(String(500), nullable=False)  # e.g., "/weather" or "/users/{user_id}"
    method = Column(String(10), nullable=False, default="GET")  # GET, POST, PUT, PATCH, DELETE

    # Parameters schema (JSON array of ToolParameter)
    parameters = Column(JSON, default=list)

    # Request configuration (overrides server defaults if set)
    headers = Column(JSON, default=dict)  # Additional headers (merged with server defaults)
    query_params = Column(JSON, default=dict)  # Static query parameters
    body_template = Column(JSON, default=dict)  # Body template for POST/PUT/PATCH

    # Response handling
    response_path = Column(String(200), nullable=True)  # JSON path to extract (e.g., "data.items")

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    server = relationship("DynamicMCPServer", back_populates="tools")

    def __repr__(self):
        return f"<DynamicMCPTool(id={self.id}, name={self.name}, path={self.path})>"

    def to_mcp_tool_schema(self) -> dict:
        """
        Convert to MCP tool schema format for the Dynamic MCP Server runtime.

        Returns format compatible with FastMCP tool registration.
        The _config includes server information for execution.
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
            # Internal metadata for execution (includes server info)
            "_config": {
                "tool_id": str(self.id),
                "server_id": str(self.server_id),
                "path": self.path,
                "method": self.method,
                "headers": self.headers or {},
                "query_params": self.query_params or {},
                "body_template": self.body_template or {},
                "response_path": self.response_path,
            }
        }

    def get_full_url(self, base_url: str) -> str:
        """
        Get the full URL for this tool by combining server base_url and tool path.

        Args:
            base_url: The server's base URL

        Returns:
            Full URL string
        """
        # Ensure base_url doesn't end with / and path starts with /
        base = base_url.rstrip("/")
        path = self.path if self.path.startswith("/") else f"/{self.path}"
        return f"{base}{path}"
