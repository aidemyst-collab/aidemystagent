"""Redis client for caching and session management."""

import redis.asyncio as aioredis
from typing import Optional
import os


class RedisClient:
    """Redis client singleton."""

    _instance: Optional[aioredis.Redis] = None
    _binary_instance: Optional[aioredis.Redis] = None

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
    async def get_binary_client(cls) -> aioredis.Redis:
        """Get or create Redis client for binary data (no decoding).

        Returns:
            aioredis.Redis: Async Redis client for binary data
        """
        if cls._binary_instance is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            cls._binary_instance = await aioredis.from_url(
                redis_url,
                decode_responses=False
            )
        return cls._binary_instance

    @classmethod
    async def close(cls):
        """Close Redis connections."""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
        if cls._binary_instance:
            await cls._binary_instance.close()
            cls._binary_instance = None


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


async def get_redis_binary() -> aioredis.Redis:
    """Dependency for getting Redis client for binary data.

    Returns:
        aioredis.Redis: Async Redis client without response decoding
    """
    return await RedisClient.get_binary_client()
