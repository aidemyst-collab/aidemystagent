from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class AgentStatus(str, enum.Enum):
    DRAFT = "draft"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    config = Column(JSON, nullable=False)  # Stores nodes, edges, settings
    version = Column(Integer, default=1, nullable=False)
    status = Column(Enum(AgentStatus), default=AgentStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="agents")
    creator = relationship("User", back_populates="agents", foreign_keys=[creator_id])
    executions = relationship("AgentExecution", back_populates="agent")


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    input = Column(JSON, nullable=False)
    output = Column(JSON)
    tokens_used = Column(Integer, default=0)
    execution_time = Column(Integer)  # in milliseconds
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="executions")
