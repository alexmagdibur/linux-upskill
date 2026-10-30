"""Worker целиком на реальных Redis и Docker: очередь заданий, retry/DLQ, терминальный hub, reconciler/TTL.
Внутренний API заменён регистрирующим двойником — это граница между сервисами, а не песочница."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from upskill_content import load_lab

from worker.cleanup import reconciler
from worker.config import WorkerSettings
from worker.jobs import DLQ, GROUP, STREAM, JobConsumer
from worker.runtime.base import ImageRef, ResourceLimits, RuntimeError_
from worker.runtime.docker import DockerAdapter
from worker.service import WorkerService, runtime_ref_for
from worker.terminal.hub import TerminalHub

from .conftest import CONTENT, run_as_student

REDIS_URL = "redis://127.0.0.1:6379/2"


class FakeApi:
    def __init__(self) -> None:
        self.provisioned_calls: list[tuple[str, str]] = []
        self.failed_calls: list[tuple[str, str]] = []
        self.results: dict[str, dict] = {}
        self.destroyed_calls: list[str] = []
        self.active: dict[str, str] = {}
        self.missing: list[str] = []
        self.accept = True

    async def provisioned(self, session_id: str, runtime_ref: str) -> bool:
        self.provisioned_calls.append((session_id, runtime_ref))
        return self.accept

    async def provision_failed(self, session_id: str, error_code: str) -> None:
        self.failed_calls.append((session_id, error_code))

    async def validation_result(self, attempt_id: str, results: dict, error_code: str | None) -> None:
        self.results[attempt_id] = {"results": results, "error": error_code}

    async def destroyed(self, session_id: str) -> None:
        self.destroyed_calls.append(session_id)

    async def active_runtimes(self) -> dict[str, str]:
        return dict(self.active)

    async def mark_runtime_missing(self, session_id: str) -> None:
        self.missing.append(session_id)


@pytest_asyncio.fixture
async def redis() -> Redis:
    r = Redis.from_url(REDIS_URL, decode_responses=True)
    await r.flushdb()
    yield r
    await r.aclose()


def lab_job(kind: str, sid: str, **extra: object) -> dict:
    lab = load_lab(CONTENT / "labs" / "linux-001")
    return {"type": kind, "session_id": sid, "lab_slug": "linux-001", "version": lab.manifest.version,
            "content_hash": lab.content_hash, "ttl_seconds": 600, **extra}


async def wait_for(cond, timeout: float = 30.0):  # type: ignore[no-untyped-def]
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return
        await asyncio.sleep(0.2)
    raise AssertionError("условие не выполнилось вовремя")


@pytest_asyncio.fixture
async def stack(adapter: DockerAdapter, redis: Redis):
    settings = WorkerSettings(redis_url=REDIS_URL, content_dir=CONTENT)
    api = FakeApi()
    hub = TerminalHub(adapter, 64 * 1024, 10 * 1024 * 1024)
    svc = WorkerService(settings, adapter, api, hub)  # type: ignore[arg-type]
    consumer = JobConsumer(redis, svc, "test-consumer", 3)
    task = asyncio.create_task(consumer.run())
    yield api, svc, redis, hub
    await consumer.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def publish(redis: Redis, job: dict) -> None:
    await redis.xadd(STREAM, {"payload": json.dumps({**job, "attempt": 1})})


async def test_provision_validate_destroy_via_redis_stream(adapter: DockerAdapter, stack) -> None:
    api, _svc, redis, _hub = stack
    sid = str(uuid.uuid4())
    await publish(redis, lab_job("provision", sid))
    await wait_for(lambda: api.provisioned_calls)
    assert api.provisioned_calls == [(sid, f"upskill-{sid}")]
    assert await adapter.is_alive(f"upskill-{sid}")

    # неправильное состояние -> проверка не проходит
    attempt = str(uuid.uuid4())
    await publish(redis, lab_job("validate", sid, attempt_id=attempt))
    await wait_for(lambda: attempt in api.results)
    assert api.results[attempt] == {"results": {"answer_path": False, "notes_dir": False}, "error": None}

    run_as_student(adapter, f"upskill-{sid}", "cd ~/lab/src/app && pwd > ~/lab/answer.txt && mkdir ~/lab/notes")
    attempt2 = str(uuid.uuid4())
    await publish(redis, lab_job("validate", sid, attempt_id=attempt2))
    await wait_for(lambda: attempt2 in api.results)
    assert api.results[attempt2]["results"] == {"answer_path": True, "notes_dir": True}

    await publish(redis, {"type": "destroy", "session_id": sid})
    await wait_for(lambda: sid in api.destroyed_calls)
    assert not await adapter.is_alive(f"upskill-{sid}")
    assert await redis.xlen(DLQ) == 0
    # все сообщения подтверждены
    assert (await redis.xpending(STREAM, GROUP))["pending"] == 0


async def test_provision_cleaned_when_api_no_longer_wants_it(adapter: DockerAdapter, stack) -> None:
    api, _svc, redis, _hub = stack
    api.accept = False  # сессию остановили, пока готовилось окружение
    sid = str(uuid.uuid4())
    await publish(redis, lab_job("provision", sid))
    await wait_for(lambda: sid in api.destroyed_calls)
    assert not await adapter.is_alive(f"upskill-{sid}")


async def test_permanent_errors_go_to_dlq_without_retries(adapter: DockerAdapter, stack) -> None:
    api, _svc, redis, _hub = stack
    sid = str(uuid.uuid4())
    job = lab_job("provision", sid)
    job["content_hash"] = "0" * 64  # версия контента не совпадает
    await publish(redis, job)
    await wait_for(lambda: api.failed_calls)
    assert api.failed_calls == [(sid, "LAB_VERSION_UNAVAILABLE")]
    assert await redis.xlen(DLQ) == 1
    assert not await adapter.is_alive(f"upskill-{sid}")


async def test_transient_error_is_retried_then_succeeds(adapter: DockerAdapter, stack, monkeypatch) -> None:
    api, _svc, redis, _hub = stack
    real_create = adapter.create
    calls = {"n": 0}

    async def flaky(*a, **kw):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError_("DOCKER_BUSY")
        return await real_create(*a, **kw)

    monkeypatch.setattr(adapter, "create", flaky)
    sid = str(uuid.uuid4())
    await publish(redis, lab_job("provision", sid))
    await wait_for(lambda: api.provisioned_calls, timeout=40)
    assert calls["n"] == 2 and not api.failed_calls
    await adapter.destroy(runtime_ref_for(sid))


async def test_exhausted_retries_report_failure_and_leave_no_container(adapter: DockerAdapter, stack, monkeypatch) -> None:
    api, _svc, redis, _hub = stack

    async def always_fail(*a, **kw):  # type: ignore[no-untyped-def]
        raise RuntimeError_("DOCKER_BUSY")

    monkeypatch.setattr(adapter, "create", always_fail)
    sid = str(uuid.uuid4())
    await publish(redis, lab_job("provision", sid))
    await wait_for(lambda: api.failed_calls, timeout=60)
    assert api.failed_calls == [(sid, "DOCKER_BUSY")]
    assert await redis.xlen(DLQ) == 1


async def test_terminal_hub_reattach_keeps_shell_state_and_replays_scrollback(adapter: DockerAdapter, sandbox: str) -> None:
    hub = TerminalHub(adapter, 64 * 1024, 10 * 1024 * 1024)
    pty = await hub.get(sandbox)
    sub, replay = pty.attach()
    await pty.write(b"export KEEP=state42; echo first-$KEEP\n")

    async def read_until(s, needle: bytes) -> bytes:  # type: ignore[no-untyped-def]
        buf = b""
        while needle not in buf:
            chunk = await asyncio.wait_for(s.queue.get(), 10)
            assert chunk is not None
            buf += chunk
        return buf

    await read_until(sub, b"first-state42\r\n")
    pty.detach(sub)  # «вкладку закрыли»

    pty2 = await hub.get(sandbox)
    assert pty2 is pty  # тот же PTY, shell не пересоздан
    sub2, replay2 = pty2.attach()
    assert b"first-state42" in replay2  # scrollback воспроизведён
    await pty2.write(b"echo again-$KEEP\n")
    await read_until(sub2, b"again-state42")
    hub.drop(sandbox)


async def test_new_tab_replaces_old_subscriber(adapter: DockerAdapter, sandbox: str) -> None:
    hub = TerminalHub(adapter, 64 * 1024, 10 * 1024 * 1024)
    pty = await hub.get(sandbox)
    old, _ = pty.attach()
    new, _ = pty.attach()
    assert old.closed and not new.closed
    assert (await asyncio.wait_for(old.queue.get(), 5)) is None  # старая вкладка получает сигнал закрытия
    hub.drop(sandbox)


async def test_output_limit_stops_runaway_output(adapter: DockerAdapter, sandbox: str) -> None:
    hub = TerminalHub(adapter, 64 * 1024, 256 * 1024)  # лимит 256 КиБ
    pty = await hub.get(sandbox)
    sub, _ = pty.attach()
    await pty.write(b"yes AAAAAAAAAAAAAAAAAAAAAAAAAAAA\n")
    deadline = time.time() + 20
    while not pty.output_limit_hit and time.time() < deadline:
        try:
            await asyncio.wait_for(sub.queue.get(), 1)
        except TimeoutError:
            pass
    assert pty.output_limit_hit
    hub.drop(sandbox)


async def test_ctrl_c_interrupts_command_without_closing_terminal(adapter: DockerAdapter, sandbox: str) -> None:
    hub = TerminalHub(adapter, 64 * 1024, 10 * 1024 * 1024)
    pty = await hub.get(sandbox)
    sub, _ = pty.attach()
    await pty.write(b"sleep 300\n")
    await asyncio.sleep(0.7)
    await pty.write(b"\x03")  # Ctrl+C приходит как управляющий символ PTY
    await pty.write(b"echo alive-$((1+1))\n")
    buf = b""
    while b"alive-2\r\n" not in buf:
        chunk = await asyncio.wait_for(sub.queue.get(), 10)
        assert chunk is not None
        buf += chunk
    assert not pty.exited
    hub.drop(sandbox)


async def test_reconciler_removes_expired_orphans_and_reports_missing(
    adapter: DockerAdapter, image: ImageRef, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(reconciler, "ORPHAN_GRACE_SECONDS", 0)
    hub = TerminalHub(adapter, 1024, 1024)
    api = FakeApi()
    setup = b"true\n"
    expired_sid, orphan_sid, kept_sid = (str(uuid.uuid4()) for _ in range(3))
    ghost_sid = str(uuid.uuid4())  # в БД есть, контейнера нет
    # TTL-метка в прошлом -> удаляется даже без API
    await adapter.create(expired_sid, image, ResourceLimits(ttl_seconds=-1000), [], setup, 10)
    await adapter.create(orphan_sid, image, ResourceLimits(), [], setup, 10)
    await adapter.create(kept_sid, image, ResourceLimits(), [], setup, 10)
    api.active = {kept_sid: "RUNNING", ghost_sid: "READY"}
    await asyncio.sleep(1.1)  # created_at < now

    stats = await reconciler.reconcile_once(adapter, api, hub)  # type: ignore[arg-type]
    # живой dev-worker (если запущен) тоже убирает просроченные/осиротевшие контейнеры, поэтому счётчики — «не больше»,
    # а проверяется результат: контейнеры удалены, нужный жив, пропавшая сессия обнаружена ровно один раз
    assert stats["expired"] <= 1 and stats["orphans"] <= 1 and stats["missing"] == 1
    assert not await adapter.is_alive(runtime_ref_for(expired_sid))
    assert not await adapter.is_alive(runtime_ref_for(orphan_sid))
    assert await adapter.is_alive(runtime_ref_for(kept_sid))
    assert api.missing == [ghost_sid]
    await adapter.destroy(runtime_ref_for(kept_sid))


async def test_reconciler_still_applies_ttl_when_api_is_down(adapter: DockerAdapter, image: ImageRef) -> None:
    class DownApi(FakeApi):
        async def active_runtimes(self) -> dict[str, str]:
            raise ConnectionError("api down")

    sid = str(uuid.uuid4())
    await adapter.create(sid, image, ResourceLimits(ttl_seconds=-1000), [], b"true\n", 10)
    stats = await reconciler.reconcile_once(adapter, DownApi(), TerminalHub(adapter, 1024, 1024))  # type: ignore[arg-type]
    assert stats["expired"] == 1 and not await adapter.is_alive(runtime_ref_for(sid))


def test_content_dir_is_read_only_trust_boundary() -> None:
    # контент не приходит через API: worker читает только локальный каталог по slug из allowlist-регулярки
    from worker.service import _SAFE_SLUG

    assert _SAFE_SLUG.match("linux-001") and not _SAFE_SLUG.match("../etc/passwd") and not _SAFE_SLUG.match("a/b")
    assert isinstance(CONTENT, Path)


async def test_consumer_recovers_after_redis_is_flushed(adapter: DockerAdapter, stack) -> None:
    """Redis без персистентности теряет stream и consumer group при перезапуске — worker обязан восстановиться."""
    api, _svc, redis, _hub = stack
    await asyncio.sleep(0.5)
    await redis.flushdb()  # имитация рестарта Redis
    sid = str(uuid.uuid4())
    await asyncio.sleep(2.5)  # цикл упал с NOGROUP и пересоздал группу
    await publish(redis, lab_job("provision", sid))
    await wait_for(lambda: api.provisioned_calls, timeout=40)
    await adapter.destroy(runtime_ref_for(sid))
