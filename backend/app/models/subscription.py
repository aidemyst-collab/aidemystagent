"""
Subscription Plan model for multi-tenant billing
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class SubscriptionPlan(Base):
    """
    Subscription plans for organizations.
    Defines quotas, features, and pricing for each tier.
    """
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)  # e.g., 'free', 'starter', 'professional', 'enterprise'
    display_name = Column(String(100), nullable=False)  # e.g., 'Free', 'Starter', 'Professional', 'Enterprise'
    description = Column(Text)

    # Quotas (-1 means unlimited)
    max_users = Column(Integer, default=5, nullable=False)
    max_agents = Column(Integer, default=10, nullable=False)
    max_deployments = Column(Integer, default=5, nullable=False)
    max_executions_per_month = Column(Integer, default=1000, nullable=False)
    max_tools = Column(Integer, default=20, nullable=False)
    max_credentials = Column(Integer, default=10, nullable=False)

    # Features as JSON for flexibility
    features = Column(JSONB, default=dict, nullable=False)
    # Example features:
    # {
    #   "custom_tools": true,
    #   "api_access": true,
    #   "sso": false,
    #   "priority_support": false,
    #   "custom_branding": false,
    #   "audit_logs": true,
    #   "advanced_analytics": false
    # }

    # Pricing (in cents to avoid floating point issues)
    price_monthly_cents = Column(Integer, default=0)  # 0 for free tier
    price_yearly_cents = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)  # False for custom enterprise plans

    # Metadata
    sort_order = Column(Integer, default=0)  # For display ordering
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organizations = relationship("Organization", back_populates="subscription_plan")

    def __repr__(self):
        return f"<SubscriptionPlan(name={self.name}, max_users={self.max_users})>"

    def has_feature(self, feature_name: str) -> bool:
        """Check if plan has a specific feature."""
        return self.features.get(feature_name, False) if self.features else False

    def is_within_quota(self, quota_name: str, current_count: int) -> bool:
        """Check if current count is within the quota limit."""
        limit = getattr(self, quota_name, 0)
        if limit == -1:  # Unlimited
            return True
        return current_count < limit
