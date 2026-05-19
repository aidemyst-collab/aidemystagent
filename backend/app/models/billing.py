"""
Stripe billing models for AgentStudio.

OrgSubscription  — one per Organisation; tracks Stripe customer/subscription IDs and plan state.
StripeWebhookEvent — idempotency store; prevents duplicate webhook processing.
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from datetime import datetime
import uuid

from app.core.database import Base


class OrgSubscription(Base):
    __tablename__ = "org_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Stripe identifiers
    stripe_customer_id = Column(String(100), nullable=True, index=True)
    stripe_subscription_id = Column(String(100), nullable=True, index=True)
    stripe_price_id = Column(String(100), nullable=True)

    # Plan state (mirrors what's in Organization.subscription_plan + status)
    plan = Column(String(50), default="free", nullable=False)
    status = Column(String(50), default="trialing", nullable=False)

    # Billing period
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)

    # Dunning
    payment_failure_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Adds `organization.org_subscription` (uselist=False — one-to-one)
    organization = relationship(
        "Organization",
        backref=backref("org_subscription", uselist=False),
    )

    def __repr__(self):
        return f"<OrgSubscription(org={self.organization_id}, plan={self.plan}, status={self.status})>"


class StripeWebhookEvent(Base):
    """Idempotency store — one row per Stripe event ID."""
    __tablename__ = "stripe_webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stripe_event_id = Column(String(100), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(Text, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
