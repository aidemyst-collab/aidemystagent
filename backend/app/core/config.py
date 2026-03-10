from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AgentStudio"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Server
    API_V1_PREFIX: str = "/api/v1"
    API_BASE_URL: str = ""  # e.g., "https://api.agentstudio.io" - used for deployment URLs
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentstudio"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 0

    # RAG / pgvector Database (separate database for vector storage)
    PGVECTOR_DATABASE_URL: str = "postgresql+asyncpg://demystrag_user:demystrag_password@localhost:5433/demystrag"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600

    # JWT - IMPORTANT: SECRET_KEY must be set via environment variable for production
    # to maintain token validity across restarts
    SECRET_KEY: str = os.getenv("SECRET_KEY", "agentstudio-dev-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours (was 15 minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days (was 7 days)

    # LLM Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "https://agentstudio365.com",
        "https://agentstudio-d4f3fbfnc0ejhghq.z02.azurefd.net"
    ]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # File Reader Settings
    FILE_READER_ALLOWED_DIRS: List[str] = ["/var/data", "./data", "./uploads"]
    FILE_READER_MAX_FILE_SIZE_MB: int = 10
    FILE_READER_FOLLOW_SYMLINKS: bool = False
    FILE_READER_ALLOW_HIDDEN_FILES: bool = False
    FILE_READER_TIMEOUT_SECONDS: int = 30

    # Voice Webhook Security Settings
    VOICE_WEBHOOK_IP_WHITELIST: bool = True  # Enable IP whitelisting for voice webhooks
    VOICE_WEBHOOK_BASIC_AUTH: bool = False  # Enable Basic Auth for voice webhooks (requires per-deployment config)
    VOICE_WEBHOOK_SIGNATURE_REQUIRED: bool = True  # Require webhook signature validation

    # Azure Container Apps Settings (for Hosted MCP Servers)
    AZURE_SUBSCRIPTION_ID: str = ""
    AZURE_RESOURCE_GROUP: str = "agentstudio-rg"
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_TENANT_ID: str = ""
    ACR_LOGIN_SERVER: str = "agentstudioacr.azurecr.io"
    ACR_USERNAME: str = ""
    ACR_PASSWORD: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
