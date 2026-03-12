"""
MCP Server model for managing MCP server registry
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgENUM
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class MCPServerStatus(str, enum.Enum):
    """Status of an MCP server."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class MCPTransportType(str, enum.Enum):
    """Transport type for MCP server connection."""
    SSE = "sse"
    HTTP = "http"
    STDIO = "stdio"


# Define PostgreSQL ENUM types explicitly with create_type=False
# Types are created by Alembic migrations, not SQLAlchemy
mcp_transport_enum = PgENUM(
    "sse", "http", "stdio",
    name="mcptransporttype",
    create_type=False
)

mcp_status_enum = PgENUM(
    "active", "inactive", "error",
    name="mcpserverstatus",
    create_type=False
)


class MCPServer(Base):
    """
    Stores MCP server configurations for centralized management.
    Users can register MCP servers here instead of entering URLs per tool.
    """
    __tablename__ = "mcp_servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Server identification
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)

    # Connection details
    server_url = Column(String(500), nullable=False)
    transport_type = Column(mcp_transport_enum, default="sse", nullable=False)

    # Optional credential for authentication
    credential_id = Column(String, ForeignKey("credentials.id"), nullable=True)

    # Status and health
    status = Column(mcp_status_enum, default="active", nullable=False)
    last_health_check = Column(DateTime, nullable=True)
    last_error = Column(String(1000), nullable=True)

    # Discovered capabilities (cached)
    discovered_tools = Column(JSON, default=list)  # List of tool names/schemas
    discovered_resources = Column(JSON, default=list)  # List of resource URIs
    discovered_prompts = Column(JSON, default=list)  # List of prompt names

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="mcp_servers")
    creator = relationship("User", back_populates="mcp_servers")
    credential = relationship("Credential", back_populates="mcp_servers")

    def __repr__(self):
        return f"<MCPServer(id={self.id}, name={self.name}, status={self.status})>"
