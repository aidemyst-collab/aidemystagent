"""
Credential model for storing LLM provider API keys
"""
from sqlalchemy import Column, String, Enum as SQLEnum, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
import json

from app.core.database import Base


class CredentialProvider(str, enum.Enum):
    """Supported LLM providers, database/storage systems, voice providers, and messaging providers"""
    # LLM Providers
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    CUSTOM = "custom"
    # Database/Storage Systems
    REDIS = "redis"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    # Voice Providers
    TWILIO = "twilio"
    ETISALAT = "etisalat"
    # Messaging Providers
    WHATSAPP_META = "whatsapp_meta"


class Credential(Base):
    """
    Stores encrypted credentials for LLM providers and database/storage systems
    Each user/organization can have multiple credentials for different providers

    For LLM providers: api_key stores the actual API key
    For database systems: api_key stores JSON-serialized connection details
    """
    __tablename__ = "credentials"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    name = Column(String, nullable=False)  # User-friendly name (e.g., "My OpenAI Key", "Production Redis")
    provider = Column(SQLEnum(CredentialProvider, values_callable=lambda x: [e.value for e in x]), nullable=False)

    # Encrypted credential data (API key for LLM, JSON connection details for databases)
    api_key = Column(String, nullable=False)

    # Additional configuration for specific providers
    api_base = Column(String, nullable=True)  # For Azure OpenAI or custom endpoints
    api_version = Column(String, nullable=True)  # For Azure OpenAI
    organization_key = Column(String, nullable=True)  # For OpenAI organization

    # Metadata
    is_active = Column(String, default="active")  # active, inactive
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="credentials")
    organization = relationship("Organization", back_populates="credentials")
    mcp_servers = relationship("MCPServer", back_populates="credential")
    dynamic_mcp_servers = relationship("DynamicMCPServer", back_populates="credential")

    @property
    def decrypted_value(self):
        """
        Returns the decrypted credential value.
        For config-based providers (Twilio, Etisalat, WhatsApp, databases), parses JSON.
        For LLM providers, returns the API key string.
        """
        config_providers = [
            CredentialProvider.TWILIO,
            CredentialProvider.ETISALAT,
            CredentialProvider.WHATSAPP_META,
            CredentialProvider.REDIS,
            CredentialProvider.POSTGRESQL,
            CredentialProvider.MONGODB,
        ]

        if self.provider in config_providers:
            try:
                return json.loads(self.api_key)
            except (json.JSONDecodeError, TypeError):
                return self.api_key
        return self.api_key

    def __repr__(self):
        return f"<Credential(id={self.id}, name={self.name}, provider={self.provider})>"
