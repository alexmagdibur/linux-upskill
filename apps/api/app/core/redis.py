from __future__ import annotations

from redis.asyncio import Redis

from .config import Settings

_client: Redis | None = None


def init_redis(settings: Settings) -> Redis:
    global _client
    _client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def get_redis() -> Redis:
    if _client is None:
        raise RuntimeError("Redis не инициализирован")
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
