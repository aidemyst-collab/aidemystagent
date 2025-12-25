from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ToolType(str, enum.Enum):
    BUILT_IN = "built-in"
    API = "api"
    CUSTOM = "custom"
    MCP = "mcp"


class ToolVisibility(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    ORGANIZATION = "organization"


class ToolStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class Tool(Base):
    __tablename__ = "tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    type = Column(Enum(ToolType), nullable=False)
    config = Column(JSON, nullable=False)  # Tool-specific configuration
    visibility = Column(Enum(ToolVisibility), default=ToolVisibility.PRIVATE, nullable=False)
    status = Column(Enum(ToolStatus), default=ToolStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    executions = relationship("ToolExecution", back_populates="tool")


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("agent_executions.id"))
    input = Column(JSON, nullable=False)
    output = Column(JSON)
    status = Column(String, nullable=False)  # success, failed, timeout
    error_message = Column(String)
    execution_time = Column(Integer)  # in milliseconds
    cost = Column(Integer)  # in cents
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tool = relationship("Tool", back_populates="executions")
