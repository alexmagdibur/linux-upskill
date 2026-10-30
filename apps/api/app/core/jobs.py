"""Публикация заданий для worker в Redis Streams (формат совпадает с apps/sandbox-worker/worker/jobs.py)."""

from __future__ import annotations

import json
from typing import Any

from .redis import get_redis

STREAM = "upskill:jobs"


async def enqueue(job: dict[str, Any]) -> None:
    await get_redis().xadd(STREAM, {"payload": json.dumps({**job, "attempt": 1})}, maxlen=10000, approximate=True)
