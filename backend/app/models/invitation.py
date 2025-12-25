"""
Invitation model for user invitations to organizations
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum
import secrets

from app.core.database import Base


class InvitationStatus(str, enum.Enum):
    """Status of an invitation."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Invitation(Base):
    """
    Invitation for users to join an organization.
    Contains a unique token for accepting the invitation.
    """
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization being invited to
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )

    # Invitee email
    email = Column(String(255), nullable=False, index=True)

    # Role to assign upon acceptance
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False
    )

    # Who sent the invitation
    invited_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Unique token for accepting the invitation
    token = Column(String(255), unique=True, nullable=False, index=True)

    # Status tracking
    status = Column(
        Enum(InvitationStatus),
        default=InvitationStatus.PENDING,
        nullable=False,
        index=True
    )

    # Optional personal message
    message = Column(String(500))

    # Expiration and acceptance timestamps
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime)

    # If accepted, link to the created user
    accepted_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    role = relationship("Role")
    inviter = relationship("User", foreign_keys=[invited_by], back_populates="sent_invitations")
    accepted_user = relationship("User", foreign_keys=[accepted_user_id])

    __table_args__ = (
        # Only one pending invitation per email per organization
        UniqueConstraint(
            'organization_id', 'email',
            name='uq_invitation_org_email',
            # Only apply to pending invitations (handled in application logic)
        ),
        Index('idx_invitation_org_status', 'organization_id', 'status'),
    )

    def __repr__(self):
        return f"<Invitation(email={self.email}, org={self.organization_id}, status={self.status})>"

    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure random token for the invitation."""
        return secrets.token_urlsafe(32)

    @classmethod
    def create_invitation(
        cls,
        organization_id: uuid.UUID,
        email: str,
        role_id: uuid.UUID,
        invited_by: uuid.UUID,
        message: str = None,
        expires_in_days: int = 7
    ) -> "Invitation":
        """Factory method to create a new invitation."""
        return cls(
            organization_id=organization_id,
            email=email.lower().strip(),
            role_id=role_id,
            invited_by=invited_by,
            message=message,
            token=cls.generate_token(),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
            status=InvitationStatus.PENDING
        )

    @property
    def is_expired(self) -> bool:
        """Check if the invitation has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the invitation is still valid (pending and not expired)."""
        return self.status == InvitationStatus.PENDING and not self.is_expired

    def accept(self, user_id: uuid.UUID) -> None:
        """Mark the invitation as accepted."""
        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = datetime.utcnow()
        self.accepted_user_id = user_id

    def revoke(self) -> None:
        """Revoke the invitation."""
        self.status = InvitationStatus.REVOKED

    def mark_expired(self) -> None:
        """Mark the invitation as expired."""
        self.status = InvitationStatus.EXPIRED
