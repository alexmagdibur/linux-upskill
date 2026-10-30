"""Фиксированное окно в Redis. При недоступности Redis лимитер пропускает запрос (fail-open) и пишет лог."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request

from .config import get_settings
from .errors import AppError
from .redis import get_redis

log = logging.getLogger("app.ratelimit")


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def hit(key: str, limit: int, window_seconds: int) -> None:
    if not get_settings().rate_limit_enabled:
        return
    try:
        r = get_redis()
        k = f"rl:{key}"
        n = await r.incr(k)
        if n == 1:
            await r.expire(k, window_seconds)
        if n > limit:
            ttl = await r.ttl(k)
            raise AppError("RATE_LIMITED", "Слишком много запросов, попробуйте позже", 429, {"retry_after": max(ttl, 1)})
    except AppError:
        raise
    except Exception:  # noqa: BLE001
        log.warning("rate limiter unavailable", extra={"component": "ratelimit"})


def ip_limit(name: str, limit: int, window: int) -> Callable[[Request], Awaitable[None]]:
    async def dep(request: Request) -> None:
        await hit(f"{name}:ip:{client_ip(request)}", limit, window)

    return dep
