import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Ensure the app lifespan has started.")
    return _redis_client


async def init_redis() -> None:
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def cache_get(key: str) -> str | None:
    return await get_redis().get(key)


async def cache_set(key: str, value: str, ttl: int | None = None) -> None:
    expire = ttl if ttl is not None else settings.cache_ttl
    await get_redis().setex(key, expire, value)


async def cache_delete(key: str) -> None:
    await get_redis().delete(key)
