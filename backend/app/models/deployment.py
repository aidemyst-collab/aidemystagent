import enum
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, Enum, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
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
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    version = Column(String, nullable=False)
    environment = Column(Enum(DeploymentEnvironment), nullable=False, default=DeploymentEnvironment.DEVELOPMENT)
    status = Column(Enum(DeploymentStatus), nullable=False, default=DeploymentStatus.PENDING)
    endpoint_url = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    config = Column(JSON, nullable=False, default={})
    error_message = Column(Text, nullable=True)
    deployed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deployed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="deployments")
    deployer = relationship("User")
