import redis.asyncio as redis
import json
import logging
from api.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, url: str):
        try:
            self.client = redis.from_url(url, decode_responses=True)
            logger.info("Successfully connected to Redis.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    async def get(self, key: str):
        if not self.client:
            return None
        try:
            value = await self.client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Failed to get key '{key}' from Redis: {e}")
            return None

    async def set(self, key: str, value, ttl_seconds: int):
        if not self.client:
            return
        try:
            await self.client.set(key, json.dumps(value), ex=ttl_seconds)
        except Exception as e:
            logger.error(f"Failed to set key '{key}' in Redis: {e}")

redis_client = RedisClient(url=settings.REDIS_URL)
