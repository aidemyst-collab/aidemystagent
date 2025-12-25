import enum
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, Enum, DateTime, JSON, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class DeploymentStatus(str, enum.Enum):
    """Deployment status enum."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    FAILED = "failed"
    STOPPED = "stopped"


class DeploymentEnvironment(str, enum.Enum):
    """Deployment environment enum."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Deployment(Base):
    """Deployment model representing an agent deployment."""
    __tablename__ = "deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization reference for direct scoping
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    environment = Column(Enum(DeploymentEnvironment), nullable=False, default=DeploymentEnvironment.DEVELOPMENT)
    status = Column(Enum(DeploymentStatus), nullable=False, default=DeploymentStatus.PENDING)
    endpoint_url = Column(String(500), nullable=True)
    api_key = Column(String(255), nullable=True)
    config = Column(JSONB, nullable=False, default=dict)
    error_message = Column(Text, nullable=True)
    deployed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deployed_at = Column(DateTime, nullable=True)

    # Metadata for tracking (using extra_data as attribute to avoid SQLAlchemy reserved word)
    extra_data = Column("metadata", JSONB, default=dict)
    # Example extra_data:
    # {
    #   "replicas": 1,
    #   "memory_limit": "512Mi",
    #   "cpu_limit": "500m",
    #   "auto_scaling": false
    # }

    # Soft delete
    deleted_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    agent = relationship("Agent", back_populates="deployments")
    deployer = relationship("User")

    __table_args__ = (
        Index('idx_deployments_org_env', 'organization_id', 'environment'),
        Index('idx_deployments_agent_status', 'agent_id', 'status'),
    )

    def __repr__(self):
        return f"<Deployment(agent={self.agent_id}, env={self.environment}, status={self.status})>"
