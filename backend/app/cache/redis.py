import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def cache_get(key: str) -> str | None:
    client = get_redis()
    return await client.get(key)


async def cache_set(key: str, value: str, ttl: int | None = None) -> None:
    client = get_redis()
    expire = ttl if ttl is not None else settings.cache_ttl
    await client.setex(key, expire, value)


async def cache_delete(key: str) -> None:
    client = get_redis()
    await client.delete(key)
