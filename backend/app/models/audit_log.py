"""
Audit Log model for tracking all system activities
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class AuditLog(Base):
    """
    Audit log for tracking all significant system activities.
    Provides compliance and security monitoring capabilities.
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization context (NULL for platform-level actions)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)

    # Who performed the action (NULL for system actions or deleted users)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String(255))  # Store email in case user is deleted

    # Action details
    action = Column(String(100), nullable=False, index=True)
    # Example actions:
    # - user.login, user.logout, user.login_failed
    # - user.create, user.update, user.delete
    # - agent.create, agent.update, agent.delete, agent.deploy
    # - org.update, org.subscription_changed
    # - credential.create, credential.delete
    # - role.assign, role.revoke

    # Resource information
    resource_type = Column(String(50), nullable=False, index=True)
    # e.g., 'user', 'agent', 'tool', 'credential', 'deployment', 'organization'

    resource_id = Column(String(100))  # UUID or identifier of affected resource
    resource_name = Column(String(255))  # Human-readable name for easier auditing

    # Change tracking
    old_values = Column(JSONB)  # Previous state (for updates)
    new_values = Column(JSONB)  # New state (for creates/updates)

    # Request context
    ip_address = Column(INET)
    user_agent = Column(Text)
    request_id = Column(String(100))  # For correlating with request logs

    # Additional metadata (using extra_data as attribute to avoid SQLAlchemy reserved word)
    extra_data = Column("metadata", JSONB, default=dict)
    # Example metadata:
    # {
    #   "reason": "User requested deletion",
    #   "triggered_by": "api",
    #   "duration_ms": 150
    # }

    # Status of the action
    status = Column(String(20), default="success")  # success, failure, partial

    # Error information if action failed
    error_message = Column(Text)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_org_created', 'organization_id', 'created_at'),
        Index('idx_audit_user_created', 'user_id', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_action_created', 'action', 'created_at'),
    )

    def __repr__(self):
        return f"<AuditLog(action={self.action}, resource={self.resource_type}:{self.resource_id})>"

    @classmethod
    def create_log(
        cls,
        action: str,
        resource_type: str,
        resource_id: str = None,
        resource_name: str = None,
        user_id: str = None,
        user_email: str = None,
        organization_id: str = None,
        old_values: dict = None,
        new_values: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        request_id: str = None,
        metadata: dict = None,
        status: str = "success",
        error_message: str = None
    ) -> "AuditLog":
        """Factory method to create an audit log entry."""
        return cls(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            resource_name=resource_name,
            user_id=user_id,
            user_email=user_email,
            organization_id=organization_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            extra_data=metadata or {},
            status=status,
            error_message=error_message
        )


# Common audit action constants
class AuditAction:
    """Constants for audit log actions."""

    # User actions
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_LOGIN_FAILED = "user.login_failed"
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_INVITE = "user.invite"
    USER_PASSWORD_CHANGE = "user.password_change"
    USER_PASSWORD_RESET = "user.password_reset"

    # Organization actions
    ORG_CREATE = "org.create"
    ORG_UPDATE = "org.update"
    ORG_DELETE = "org.delete"
    ORG_SUBSCRIPTION_CHANGE = "org.subscription_change"

    # Agent actions
    AGENT_CREATE = "agent.create"
    AGENT_UPDATE = "agent.update"
    AGENT_DELETE = "agent.delete"
    AGENT_DEPLOY = "agent.deploy"
    AGENT_EXECUTE = "agent.execute"
    AGENT_VERSION_CREATE = "agent.version_create"
    AGENT_VERSION_RESTORE = "agent.version_restore"

    # Tool actions
    TOOL_CREATE = "tool.create"
    TOOL_UPDATE = "tool.update"
    TOOL_DELETE = "tool.delete"
    TOOL_EXECUTE = "tool.execute"

    # Credential actions
    CREDENTIAL_CREATE = "credential.create"
    CREDENTIAL_UPDATE = "credential.update"
    CREDENTIAL_DELETE = "credential.delete"
    CREDENTIAL_ACCESS = "credential.access"

    # Deployment actions
    DEPLOYMENT_CREATE = "deployment.create"
    DEPLOYMENT_UPDATE = "deployment.update"
    DEPLOYMENT_DELETE = "deployment.delete"
    DEPLOYMENT_START = "deployment.start"
    DEPLOYMENT_STOP = "deployment.stop"

    # Role actions
    ROLE_CREATE = "role.create"
    ROLE_UPDATE = "role.update"
    ROLE_DELETE = "role.delete"
    ROLE_ASSIGN = "role.assign"
    ROLE_REVOKE = "role.revoke"

    # Invitation actions
    INVITATION_CREATE = "invitation.create"
    INVITATION_ACCEPT = "invitation.accept"
    INVITATION_REVOKE = "invitation.revoke"
    INVITATION_EXPIRE = "invitation.expire"
