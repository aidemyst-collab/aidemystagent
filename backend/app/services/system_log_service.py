"""
System log service — write structured logs to the database and clean old entries.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging_config import logger
from app.models.system_log import SystemLog


async def system_log(
    level: str,
    category: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
) -> None:
    """Write a structured log entry to the database. Never raises."""
    try:
        async with AsyncSessionLocal() as db:
            entry = SystemLog(
                level=level.upper(),
                category=category,
                message=message,
                details=details or {},
                source=source,
            )
            db.add(entry)
            await db.commit()
    except Exception as exc:
        logger.error(f"Failed to write system log: {exc}")


async def cleanup_old_logs(days: int = 30) -> int:
    """Delete log entries older than `days` days. Returns deleted count."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(SystemLog).where(SystemLog.created_at < cutoff)
            )
            await db.commit()
            deleted = result.rowcount
            if deleted:
                logger.info(f"System log cleanup: deleted {deleted} entries older than {days} days")
            return deleted
    except Exception as exc:
        logger.error(f"System log cleanup failed: {exc}")
        return 0


async def log_cleanup_loop(interval_hours: int = 24, retention_days: int = 30) -> None:
    """Background task: runs cleanup every `interval_hours` hours indefinitely."""
    while True:
        await asyncio.sleep(interval_hours * 3600)
        await cleanup_old_logs(days=retention_days)
