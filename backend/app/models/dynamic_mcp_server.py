"""
Dynamic MCP Server model for grouping tools under a single API server.

Each DynamicMCPServer represents an API that exposes multiple tools.
Tools within a server share the same base URL, credentials, and default headers.
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class DynamicMCPServer(Base):
    """
    Represents a Dynamic MCP Server that groups multiple tools.

    Example:
        Weather API Server
        - base_url: https://api.openweathermap.org/data/2.5
        - credential: OpenWeather API Key
        - tools:
            - get_current_weather (GET /weather)
            - get_forecast (GET /forecast)
            - get_alerts (GET /alerts/{region})
    """
    __tablename__ = "dynamic_mcp_servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Server identification
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)

    # API configuration (shared by all tools)
    base_url = Column(String(500), nullable=False)  # e.g., "https://api.example.com/v1"

    # Authentication (shared credential for all tools)
    credential_id = Column(String, ForeignKey("credentials.id"), nullable=True)

    # Default request configuration
    default_headers = Column(JSON, default=dict)  # Default headers for all tools
    timeout_seconds = Column(Integer, default=30)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="dynamic_mcp_servers")
    creator = relationship("User", back_populates="dynamic_mcp_servers")
    credential = relationship("Credential", back_populates="dynamic_mcp_servers")
    tools = relationship(
        "DynamicMCPTool",
        back_populates="server",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<DynamicMCPServer(id={self.id}, name={self.name}, base_url={self.base_url})>"

    @property
    def tool_count(self) -> int:
        """Return the number of tools in this server."""
        return len(self.tools) if self.tools else 0

    @property
    def active_tool_count(self) -> int:
        """Return the number of active tools in this server."""
        if not self.tools:
            return 0
        return sum(1 for tool in self.tools if tool.is_active)

    def to_mcp_server_schema(self) -> dict:
        """
        Convert to schema for the Dynamic MCP Server runtime.

        Returns format with all tools included.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "base_url": self.base_url,
            "credential_id": self.credential_id,
            "default_headers": self.default_headers or {},
            "timeout_seconds": self.timeout_seconds,
            "is_active": self.is_active,
            "tools": [
                tool.to_mcp_tool_schema()
                for tool in (self.tools or [])
                if tool.is_active
            ]
        }
