import re
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings


def _fix_ssl(url: str) -> tuple:
    """Strip ssl/sslmode params from URL; return (clean_url, connect_args).
    asyncpg does not accept ssl= or sslmode= as URL parameters — pass ssl=True via connect_args."""
    needs_ssl = bool(re.search(r'ssl(?:mode)?=', url, re.IGNORECASE))
    clean = re.sub(r'[?&]ssl(?:mode)?=[^&]*', '', url, flags=re.IGNORECASE).rstrip('?&')
    return clean, {"ssl": True} if needs_ssl else {}


_db_url, _db_ssl = _fix_ssl(settings.DATABASE_URL)

# Create async engine for main database
engine = create_async_engine(
    _db_url,
    connect_args=_db_ssl,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

# Create async engine for pgvector database
pgvector_engine = create_async_engine(
    settings.PGVECTOR_DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=0,
)

# Create async session factory for main database
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Create async session factory for pgvector database
PgvectorSessionLocal = async_sessionmaker(
    pgvector_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


# Dependency to get main DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Dependency to get pgvector DB session
async def get_pgvector_db():
    async with PgvectorSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
