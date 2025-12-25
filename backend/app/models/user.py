from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """Legacy role enum - kept for backward compatibility during migration."""
    ADMIN = "admin"
    CREATOR = "creator"
    VIEWER = "viewer"


class SubscriptionStatus(str, enum.Enum):
    """Organization subscription status."""
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"

    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup."""
        if isinstance(value, str):
            # Try lowercase match
            for member in cls:
                if member.value == value.lower():
                    return member
        return None


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True)  # URL-friendly identifier
    description = Column(Text)
    logo_url = Column(String(500))

    # Subscription
    subscription_plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=True)
    # Using String to match migration - stored as lowercase values like 'active', 'trial'
    subscription_status = Column(String(20), default="trial", nullable=False)
    trial_ends_at = Column(DateTime)

    # Settings stored as JSON for flexibility
    settings = Column(JSONB, default=dict)
    # Example settings:
    # {
    #   "default_llm_provider": "openai",
    #   "default_model": "gpt-4",
    #   "allowed_domains": ["@company.com"],
    #   "require_2fa": false,
    #   "timezone": "UTC"
    # }

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Soft delete
    deleted_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization")
    agents = relationship("Agent", back_populates="organization")
    credentials = relationship("Credential", back_populates="organization")
    subscription_plan = relationship("SubscriptionPlan", back_populates="organizations")
    custom_roles = relationship("Role", back_populates="organization")
    user_role_assignments = relationship("UserRole", back_populates="organization")
    invitations = relationship("Invitation", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")
    usage_records = relationship("OrganizationUsage", back_populates="organization")

    def __repr__(self):
        return f"<Organization(name={self.name}, slug={self.slug})>"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Legacy role field - kept for backward compatibility during migration
    role = Column(Enum(UserRole), default=UserRole.CREATOR, nullable=False)

    # Profile information
    full_name = Column(String(255))
    avatar_url = Column(String(500))

    # Platform admin flag (for super admin quick check)
    is_platform_admin = Column(Boolean, default=False, nullable=False)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime)

    # Security
    password_changed_at = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime)
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(45))  # IPv6 max length

    # Additional metadata (using extra_data as attribute to avoid SQLAlchemy reserved word)
    extra_data = Column("metadata", JSONB, default=dict)

    # Soft delete
    deleted_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    agents = relationship("Agent", back_populates="creator", foreign_keys="Agent.creator_id")
    credentials = relationship("Credential", back_populates="user")
    user_roles = relationship("UserRole", back_populates="user", foreign_keys="UserRole.user_id")
    sent_invitations = relationship("Invitation", back_populates="inviter", foreign_keys="Invitation.invited_by")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(email={self.email}, org={self.organization_id})>"

    @property
    def is_locked(self) -> bool:
        """Check if the account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def increment_failed_login(self, max_attempts: int = 5, lockout_minutes: int = 30) -> None:
        """Increment failed login counter and lock if threshold reached."""
        from datetime import timedelta
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)

    def reset_failed_logins(self) -> None:
        """Reset failed login counter after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_login(self, ip_address: str = None) -> None:
        """Record successful login."""
        self.last_login_at = datetime.utcnow()
        if ip_address:
            self.last_login_ip = ip_address
        self.reset_failed_logins()
