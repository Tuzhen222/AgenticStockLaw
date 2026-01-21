"""
Redis Client - Connection management for Redis.
"""
import os
import logging
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Singleton instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create async Redis client."""
    global _redis_client
    
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info(f"Connected to Redis at {redis_url}")
    
    return _redis_client


async def close_redis_client():
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")
