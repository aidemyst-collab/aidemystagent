"""
Pydantic schemas for Credential API
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.credential import CredentialProvider


class CredentialBase(BaseModel):
    """Base credential schema"""
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., description="User-friendly name for the credential")
    provider: CredentialProvider = Field(..., description="Provider type (LLM or database/storage)")
    api_base: Optional[str] = Field(None, description="Custom API base URL (for Azure OpenAI or custom endpoints)")
    api_version: Optional[str] = Field(None, description="API version (for Azure OpenAI)")
    organization_key: Optional[str] = Field(None, description="Organization key (for OpenAI)")


class CredentialCreate(CredentialBase):
    """Schema for creating a new credential"""
    api_key: Optional[str] = Field(None, description="API key for LLM providers")

    # Database connection fields
    connection_config: Optional[Dict[str, Any]] = Field(None, description="Connection configuration for database providers")

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v, info):
        provider = info.data.get('provider')
        # Only validate api_key length for LLM providers
        if provider in [CredentialProvider.OPENAI, CredentialProvider.ANTHROPIC,
                       CredentialProvider.GOOGLE, CredentialProvider.AZURE_OPENAI,
                       CredentialProvider.CUSTOM]:
            if not v or len(v) < 10:
                raise ValueError('API key must be at least 10 characters long')
        return v

    @field_validator('connection_config')
    @classmethod
    def validate_connection_config(cls, v, info):
        provider = info.data.get('provider')
        # Require connection_config for database providers
        if provider in [CredentialProvider.REDIS, CredentialProvider.POSTGRESQL, CredentialProvider.MONGODB]:
            if not v:
                raise ValueError('Connection configuration is required for database providers')
        return v


class CredentialUpdate(BaseModel):
    """Schema for updating a credential"""
    name: Optional[str] = None
    api_key: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    organization_key: Optional[str] = None
    is_active: Optional[str] = None

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        if v is not None and len(v) < 10:
            raise ValueError('API key must be at least 10 characters long')
        return v


class CredentialResponse(CredentialBase):
    """Schema for credential response (without exposing full API key)"""
    id: str
    user_id: str
    organization_id: str
    is_active: str
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    api_key_preview: str = Field(..., description="Masked preview of API key")

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @classmethod
    def from_orm_with_preview(cls, credential):
        """Create response with masked API key"""
        data = {
            "id": str(credential.id),
            "user_id": str(credential.user_id),
            "organization_id": str(credential.organization_id),
            "name": credential.name,
            "provider": credential.provider,
            "api_base": credential.api_base,
            "api_version": credential.api_version,
            "organization_key": credential.organization_key,
            "is_active": credential.is_active,
            "created_at": credential.created_at,
            "updated_at": credential.updated_at,
            "last_used_at": credential.last_used_at,
            "api_key_preview": cls._mask_api_key(credential.api_key)
        }
        return cls(**data)

    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        """Mask API key showing only first and last few characters"""
        if len(api_key) <= 12:
            return f"{api_key[:4]}...{api_key[-4:]}"
        return f"{api_key[:8]}...{api_key[-4:]}"


class CredentialListResponse(BaseModel):
    """Schema for list of credentials"""
    credentials: list[CredentialResponse]
    total: int


class CredentialTestRequest(BaseModel):
    """Schema for testing a credential"""
    credential_id: Optional[str] = None  # For testing existing credentials
    provider: CredentialProvider
    api_key: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None


class CredentialTestResponse(BaseModel):
    """Schema for credential test response"""
    success: bool
    message: str
    details: Optional[dict] = None
