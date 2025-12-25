"""
Organization Usage model for tracking resource consumption
"""
from sqlalchemy import Column, Integer, DateTime, Date, ForeignKey, BigInteger, Numeric, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, date
import uuid

from app.core.database import Base


class OrganizationUsage(Base):
    """
    Tracks resource usage per organization per billing period.
    Used for quota enforcement and billing calculations.
    """
    __tablename__ = "organization_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )

    # Billing period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Resource counts (current snapshot)
    users_count = Column(Integer, default=0, nullable=False)
    agents_count = Column(Integer, default=0, nullable=False)
    deployments_count = Column(Integer, default=0, nullable=False)
    tools_count = Column(Integer, default=0, nullable=False)
    credentials_count = Column(Integer, default=0, nullable=False)

    # Usage metrics (cumulative for the period)
    executions_count = Column(Integer, default=0, nullable=False)
    tokens_used = Column(BigInteger, default=0, nullable=False)
    api_calls_count = Column(Integer, default=0, nullable=False)

    # Cost tracking (in cents)
    llm_cost_cents = Column(Integer, default=0, nullable=False)
    compute_cost_cents = Column(Integer, default=0, nullable=False)
    storage_cost_cents = Column(Integer, default=0, nullable=False)
    total_cost_cents = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="usage_records")

    __table_args__ = (
        UniqueConstraint('organization_id', 'period_start', name='uq_org_usage_period'),
        Index('idx_org_usage_period', 'organization_id', 'period_start'),
    )

    def __repr__(self):
        return f"<OrganizationUsage(org={self.organization_id}, period={self.period_start})>"

    @classmethod
    def get_or_create_current_period(cls, db_session, organization_id: uuid.UUID) -> "OrganizationUsage":
        """Get or create usage record for the current billing period."""
        today = date.today()
        # Use first day of month as period start
        period_start = today.replace(day=1)
        # Last day of month as period end
        if today.month == 12:
            period_end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            period_end = today.replace(month=today.month + 1, day=1)

        # This would be implemented in the service layer
        return cls(
            organization_id=organization_id,
            period_start=period_start,
            period_end=period_end
        )

    def increment_executions(self, count: int = 1) -> None:
        """Increment the execution count."""
        self.executions_count += count

    def increment_tokens(self, tokens: int) -> None:
        """Increment token usage."""
        self.tokens_used += tokens

    def increment_api_calls(self, count: int = 1) -> None:
        """Increment API call count."""
        self.api_calls_count += count

    def update_resource_counts(
        self,
        users: int = None,
        agents: int = None,
        deployments: int = None,
        tools: int = None,
        credentials: int = None
    ) -> None:
        """Update resource count snapshots."""
        if users is not None:
            self.users_count = users
        if agents is not None:
            self.agents_count = agents
        if deployments is not None:
            self.deployments_count = deployments
        if tools is not None:
            self.tools_count = tools
        if credentials is not None:
            self.credentials_count = credentials

    def calculate_total_cost(self) -> int:
        """Calculate and update total cost."""
        self.total_cost_cents = (
            self.llm_cost_cents +
            self.compute_cost_cents +
            self.storage_cost_cents
        )
        return self.total_cost_cents
