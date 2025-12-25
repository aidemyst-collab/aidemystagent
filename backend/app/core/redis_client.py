"""Redis client for caching and session management."""

import redis.asyncio as aioredis
from typing import Optional
import os


class RedisClient:
    """Redis client singleton."""

    _instance: Optional[aioredis.Redis] = None

    @classmethod
    async def get_client(cls) -> aioredis.Redis:
        """Get or create Redis client instance.

        Returns:
            aioredis.Redis: Async Redis client
        """
        if cls._instance is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            cls._instance = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return cls._instance

    @classmethod
    async def close(cls):
        """Close Redis connection."""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


async def get_redis() -> aioredis.Redis:
    """Dependency for getting Redis client.

    Returns:
        aioredis.Redis: Async Redis client

    Usage:
        @app.get("/example")
        async def example(redis: aioredis.Redis = Depends(get_redis)):
            await redis.set("key", "value")
    """
    return await RedisClient.get_client()
