"""Потребитель Redis Streams: ограниченные повторы с экспоненциальной паузой и dead-letter."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from .runtime.base import RuntimeError_
from .service import WorkerService

log = logging.getLogger("worker.queue")

STREAM = "upskill:jobs"
DLQ = "upskill:jobs:dead"
GROUP = "workers"
JOB_TIMEOUT = {"provision": 90, "validate": 60, "destroy": 30}
# ошибки, при которых повтор бессмысленен
PERMANENT = {"BAD_LAB", "CONTENT_INVALID", "LAB_VERSION_UNAVAILABLE", "IMAGE_NOT_ALLOWED", "IMAGE_MISSING", "IMAGE_MISMATCH"}


class JobConsumer:
    def __init__(self, redis: Redis, service: WorkerService, consumer: str, max_attempts: int) -> None:
        self._r = redis
        self._svc = service
        self._consumer = consumer
        self._max_attempts = max_attempts
        self._tasks: set[asyncio.Task[None]] = set()
        self._stop = asyncio.Event()

    async def _ensure_group(self) -> None:
        with contextlib.suppress(ResponseError):  # BUSYGROUP — группа уже есть
            await self._r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)

    async def run(self) -> None:
        await self._ensure_group()
        last_claim = 0.0
        loop = asyncio.get_running_loop()
        while not self._stop.is_set():
            try:
                resp: Any = await self._r.xreadgroup(GROUP, self._consumer, {STREAM: ">"}, count=10, block=2000)
                for _stream, messages in resp or []:
                    for msg_id, fields in messages:
                        self._spawn(msg_id, fields)
                if loop.time() - last_claim > 30:
                    last_claim = loop.time()
                    await self._claim_stale()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.exception("queue loop error", extra={"component": "queue"})
                await asyncio.sleep(2)
                if "NOGROUP" in str(exc):  # Redis перезапущен/очищен: потерян stream и consumer group
                    with contextlib.suppress(Exception):
                        await self._ensure_group()

    async def _claim_stale(self) -> None:
        # сообщения упавшего consumer'а, не подтверждённые более 2 минут
        res: Any = await self._r.xautoclaim(STREAM, GROUP, self._consumer, min_idle_time=120_000, start_id="0-0", count=10)
        for msg_id, fields in res[1]:
            if fields:
                self._spawn(msg_id, fields)

    def _spawn(self, msg_id: str, fields: dict[str, str]) -> None:
        task = asyncio.create_task(self._handle(msg_id, fields))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _handle(self, msg_id: str, fields: dict[str, str]) -> None:
        try:
            job: dict[str, Any] = json.loads(fields["payload"])
        except (KeyError, ValueError):
            await self._r.xadd(DLQ, {"raw": json.dumps(fields)})
            await self._r.xack(STREAM, GROUP, msg_id)
            return
        attempt = int(job.get("attempt", 1))
        jtype = job.get("type", "")
        log.info("job start", extra={"component": "queue", "session_id": job.get("session_id"), "job": jtype})
        error_code = "JOB_FAILED"
        try:
            handler = {
                "provision": self._svc.provision,
                "validate": self._svc.validate,
                "destroy": self._svc.destroy,
            }[jtype]
            await asyncio.wait_for(handler(job), JOB_TIMEOUT[jtype])
            await self._r.xack(STREAM, GROUP, msg_id)
            return
        except KeyError:
            error_code = "UNKNOWN_JOB"
            attempt = self._max_attempts
        except TimeoutError:
            error_code = "JOB_TIMEOUT"
        except RuntimeError_ as exc:
            error_code = exc.code
            if exc.code in PERMANENT:
                attempt = self._max_attempts
        except Exception:  # noqa: BLE001
            log.exception("job crashed", extra={"component": "queue", "session_id": job.get("session_id")})

        await self._r.xack(STREAM, GROUP, msg_id)
        if attempt >= self._max_attempts:
            log.error("job dead", extra={"component": "queue", "session_id": job.get("session_id"), "error_code": error_code})
            await self._r.xadd(DLQ, {"payload": json.dumps(job), "error_code": error_code}, maxlen=1000, approximate=True)
            if jtype == "provision":  # недопоставленный runtime мог остаться частично созданным
                with contextlib.suppress(Exception):
                    await self._svc.destroy(job)
            with contextlib.suppress(Exception):
                await self._svc.on_job_failed(job, error_code)
            return
        await asyncio.sleep(min(2**attempt, 15))
        job["attempt"] = attempt + 1
        await self._r.xadd(STREAM, {"payload": json.dumps(job)})

    async def stop(self) -> None:
        self._stop.set()
        for t in list(self._tasks):
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
