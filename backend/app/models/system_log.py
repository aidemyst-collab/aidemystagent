from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.core.database import Base


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(String(10), nullable=False, index=True)       # INFO WARNING ERROR CRITICAL
    category = Column(String(50), nullable=False, index=True)    # auth deployment admin system
    message = Column(Text, nullable=False)
    details = Column(JSONB, default=dict)
    source = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<SystemLog(level={self.level}, category={self.category}, message={self.message[:50]})>"
