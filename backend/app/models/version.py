from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class AgentVersion(Base):
    """Agent version model for version control."""
    __tablename__ = "agent_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    version_tag = Column(String, nullable=True)  # e.g., "v1.0.0", "stable", "beta"
    config = Column(JSON, nullable=False)  # Snapshot of agent config at this version
    description = Column(String, nullable=True)
    changelog = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="versions")
    creator = relationship("User")
