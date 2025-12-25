from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, JSON, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    config = Column(JSONB, nullable=False)  # Stores nodes, edges, settings
    version = Column(Integer, default=1, nullable=False)
    status = Column(Enum(AgentStatus), default=AgentStatus.DRAFT, nullable=False)

    # Template support
    is_template = Column(Boolean, default=False, nullable=False)
    is_public_template = Column(Boolean, default=False, nullable=False)  # Visible to all orgs
    template_source_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)

    # Tags for categorization and search
    tags = Column(JSONB, default=list)  # e.g., ["customer-support", "sales", "automation"]

    # Additional metadata (using extra_data as attribute to avoid SQLAlchemy reserved word)
    extra_data = Column("metadata", JSONB, default=dict)
    # Example metadata:
    # {
    #   "icon": "robot",
    #   "color": "#3498db",
    #   "estimated_cost_per_run": 0.05,
    #   "avg_execution_time_ms": 2500
    # }

    # Soft delete
    deleted_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="agents")
    creator = relationship("User", back_populates="agents", foreign_keys=[creator_id])
    executions = relationship("AgentExecution", back_populates="agent")
    deployments = relationship("Deployment", back_populates="agent")
    versions = relationship("AgentVersion", back_populates="agent", order_by="desc(AgentVersion.version_number)")
    template_source = relationship("Agent", remote_side=[id], backref="derived_agents")

    __table_args__ = (
        Index('idx_agents_org_status', 'organization_id', 'status'),
        Index('idx_agents_templates', 'is_template', 'is_public_template'),
    )

    def __repr__(self):
        return f"<Agent(name={self.name}, status={self.status})>"


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
