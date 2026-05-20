from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio
import os

# Import your models
from app.core.database import Base
from app.models.user import User, Organization
from app.models.agent import Agent, AgentExecution
from app.models.tool import Tool, ToolExecution
from app.models.deployment import Deployment
from app.models.version import AgentVersion
from app.models.credential import Credential
from app.models.mcp_server import MCPServer
from app.models.dynamic_mcp_server import DynamicMCPServer
from app.models.hosted_mcp_server import HostedMCPServer
from app.models.system_log import SystemLog

# Alembic Config object
config = context.config

# Override sqlalchemy.url with DATABASE_URL environment variable if available
_raw_db_url = os.getenv("DATABASE_URL", "")

def _normalise_db_url(url: str) -> str:
    """Fix URL for asyncpg: strip trailing whitespace, normalise sslmode → ssl."""
    import re
    url = url.strip()
    return re.sub(r'([?&])sslmode=', r'\1ssl=', url, flags=re.IGNORECASE)

database_url = _normalise_db_url(_raw_db_url) if _raw_db_url else ""
if database_url:
    # Escape % so ConfigParser doesn't treat %xx as interpolation sequences
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    section = config.get_section(config.config_ini_section, {})
    if database_url:
        section["sqlalchemy.url"] = database_url
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
