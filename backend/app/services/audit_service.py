"""
Audit Service for logging system activities.
Provides centralized audit logging functionality.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.audit_log import AuditLog, AuditAction
from app.models.user import User


class AuditService:
    """Service for creating and managing audit logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        user: Optional[User] = None,
        organization_id: Optional[UUID] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: The action being performed (use AuditAction constants)
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource (optional)
            resource_name: Human-readable name of the resource
            user: The user performing the action
            organization_id: Organization context (defaults to user's org)
            old_values: Previous state for updates
            new_values: New state for creates/updates
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Request correlation ID
            metadata: Additional context
            status: Action status (success, failure, partial)
            error_message: Error details if action failed

        Returns:
            The created AuditLog entry
        """
        audit_log = AuditLog.create_log(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            resource_name=resource_name,
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            organization_id=organization_id or (user.organization_id if user else None),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata=metadata,
            status=status,
            error_message=error_message,
        )

        self.db.add(audit_log)
        # Don't commit here - let the caller manage the transaction
        return audit_log

    async def log_login(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """Log a user login attempt."""
        return await self.log(
            action=AuditAction.USER_LOGIN if success else AuditAction.USER_LOGIN_FAILED,
            resource_type="user",
            resource_id=str(user.id),
            resource_name=user.email,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            status="success" if success else "failure",
            error_message=error_message,
        )

    async def log_logout(
        self,
        user: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log a user logout."""
        return await self.log(
            action=AuditAction.USER_LOGOUT,
            resource_type="user",
            resource_id=str(user.id),
            resource_name=user.email,
            user=user,
            ip_address=ip_address,
        )

    async def log_user_create(
        self,
        created_user: User,
        created_by: Optional[User] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log user creation."""
        return await self.log(
            action=AuditAction.USER_CREATE,
            resource_type="user",
            resource_id=str(created_user.id),
            resource_name=created_user.email,
            user=created_by,
            organization_id=created_user.organization_id,
            new_values={
                "email": created_user.email,
                "full_name": created_user.full_name,
                "role": created_user.role.value if hasattr(created_user.role, 'value') else str(created_user.role),
            },
            ip_address=ip_address,
            metadata=metadata,
        )

    async def log_user_update(
        self,
        user: User,
        updated_by: User,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log user update."""
        return await self.log(
            action=AuditAction.USER_UPDATE,
            resource_type="user",
            resource_id=str(user.id),
            resource_name=user.email,
            user=updated_by,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
        )

    async def log_user_delete(
        self,
        user: User,
        deleted_by: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log user deletion."""
        return await self.log(
            action=AuditAction.USER_DELETE,
            resource_type="user",
            resource_id=str(user.id),
            resource_name=user.email,
            user=deleted_by,
            ip_address=ip_address,
        )

    async def log_agent_create(
        self,
        agent_id: UUID,
        agent_name: str,
        user: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log agent creation."""
        return await self.log(
            action=AuditAction.AGENT_CREATE,
            resource_type="agent",
            resource_id=str(agent_id),
            resource_name=agent_name,
            user=user,
            ip_address=ip_address,
        )

    async def log_agent_update(
        self,
        agent_id: UUID,
        agent_name: str,
        user: User,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log agent update."""
        return await self.log(
            action=AuditAction.AGENT_UPDATE,
            resource_type="agent",
            resource_id=str(agent_id),
            resource_name=agent_name,
            user=user,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
        )

    async def log_agent_delete(
        self,
        agent_id: UUID,
        agent_name: str,
        user: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log agent deletion."""
        return await self.log(
            action=AuditAction.AGENT_DELETE,
            resource_type="agent",
            resource_id=str(agent_id),
            resource_name=agent_name,
            user=user,
            ip_address=ip_address,
        )

    async def log_agent_execute(
        self,
        agent_id: UUID,
        agent_name: str,
        user: User,
        execution_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log agent execution."""
        return await self.log(
            action=AuditAction.AGENT_EXECUTE,
            resource_type="agent",
            resource_id=str(agent_id),
            resource_name=agent_name,
            user=user,
            ip_address=ip_address,
            metadata={
                **(metadata or {}),
                "execution_id": execution_id,
            } if execution_id else metadata,
        )

    async def log_deployment_create(
        self,
        deployment_id: UUID,
        agent_name: str,
        environment: str,
        user: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log deployment creation."""
        return await self.log(
            action=AuditAction.DEPLOYMENT_CREATE,
            resource_type="deployment",
            resource_id=str(deployment_id),
            resource_name=f"{agent_name} ({environment})",
            user=user,
            ip_address=ip_address,
            new_values={"environment": environment},
        )

    async def log_credential_create(
        self,
        credential_id: UUID,
        credential_name: str,
        user: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log credential creation (never log actual credential values)."""
        return await self.log(
            action=AuditAction.CREDENTIAL_CREATE,
            resource_type="credential",
            resource_id=str(credential_id),
            resource_name=credential_name,
            user=user,
            ip_address=ip_address,
        )

    async def log_credential_access(
        self,
        credential_id: UUID,
        credential_name: str,
        user: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log credential access/usage."""
        return await self.log(
            action=AuditAction.CREDENTIAL_ACCESS,
            resource_type="credential",
            resource_id=str(credential_id),
            resource_name=credential_name,
            user=user,
            ip_address=ip_address,
        )

    async def log_role_assign(
        self,
        user: User,
        role_name: str,
        assigned_by: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log role assignment."""
        return await self.log(
            action=AuditAction.ROLE_ASSIGN,
            resource_type="user",
            resource_id=str(user.id),
            resource_name=user.email,
            user=assigned_by,
            new_values={"role": role_name},
            ip_address=ip_address,
        )

    async def log_role_revoke(
        self,
        user: User,
        role_name: str,
        revoked_by: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log role revocation."""
        return await self.log(
            action=AuditAction.ROLE_REVOKE,
            resource_type="user",
            resource_id=str(user.id),
            resource_name=user.email,
            user=revoked_by,
            old_values={"role": role_name},
            ip_address=ip_address,
        )

    async def log_invitation_create(
        self,
        invitation_id: UUID,
        email: str,
        role_name: str,
        user: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log invitation creation."""
        return await self.log(
            action=AuditAction.INVITATION_CREATE,
            resource_type="invitation",
            resource_id=str(invitation_id),
            resource_name=email,
            user=user,
            new_values={"role": role_name, "email": email},
            ip_address=ip_address,
        )

    async def log_invitation_accept(
        self,
        invitation_id: UUID,
        email: str,
        created_user: User,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log invitation acceptance."""
        return await self.log(
            action=AuditAction.INVITATION_ACCEPT,
            resource_type="invitation",
            resource_id=str(invitation_id),
            resource_name=email,
            user=created_user,
            ip_address=ip_address,
            metadata={"accepted_by": email},
        )

    async def log_org_update(
        self,
        org_id: UUID,
        org_name: str,
        user: User,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log organization update."""
        return await self.log(
            action=AuditAction.ORG_UPDATE,
            resource_type="organization",
            resource_id=str(org_id),
            resource_name=org_name,
            user=user,
            organization_id=org_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
        )

    async def log_subscription_change(
        self,
        org_id: UUID,
        org_name: str,
        user: User,
        old_plan: Optional[str],
        new_plan: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log subscription plan change."""
        return await self.log(
            action=AuditAction.ORG_SUBSCRIPTION_CHANGE,
            resource_type="organization",
            resource_id=str(org_id),
            resource_name=org_name,
            user=user,
            organization_id=org_id,
            old_values={"subscription_plan": old_plan},
            new_values={"subscription_plan": new_plan},
            ip_address=ip_address,
        )


def get_audit_service(db: AsyncSession) -> AuditService:
    """Factory function to get an AuditService instance."""
    return AuditService(db)
