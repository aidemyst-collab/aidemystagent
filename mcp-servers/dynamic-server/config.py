"""
Configuration for Dynamic MCP Server
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Dynamic MCP Server settings."""

    # AgentStudio API configuration
    AGENTSTUDIO_API_URL: str = "http://localhost:8000"
    MCP_INTERNAL_API_KEY: str = "dev-internal-key"

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 3000
    DEBUG: bool = False

    # Redis for token caching
    REDIS_URL: Optional[str] = None

    # Tool refresh interval (seconds)
    TOOL_REFRESH_INTERVAL: int = 60

    # Request timeouts
    DEFAULT_TIMEOUT: int = 30
    MAX_TIMEOUT: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
