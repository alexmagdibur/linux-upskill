"""Точка входа worker: потребитель очереди, reconciler и внутренний терминальный WS-сервер."""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from redis.asyncio import Redis

from .api_client import ApiClient
from .cleanup.reconciler import reconcile_loop
from .config import WorkerSettings, get_settings
from .jobs import JobConsumer
from .logging_setup import setup_logging
from .runtime.base import RuntimeAdapter, RuntimeError_
from .runtime.router import RuntimeRouter
from .service import WorkerService, runtime_ref_for
from .terminal.hub import TerminalHub

log = logging.getLogger("worker.main")

ACTIVE_RUNTIMES = Gauge("upskill_worker_runtimes", "Количество управляемых контейнеров")


def build_adapter(settings: WorkerSettings) -> RuntimeRouter | None:
    if settings.sandbox_runtime == "disabled":
        return None  # SANDBOX_RUNTIME=disabled — песочницы выключены
    adapters: dict[str, RuntimeAdapter] = {}
    if settings.sandbox_runtime == "docker":
        from .runtime.docker import DockerAdapter

        adapters["container"] = DockerAdapter()
    if settings.lxd_ssh_host:
        from .runtime.lxd import LXDAdapter

        adapters["lxd"] = LXDAdapter(
            settings.lxd_ssh_host, settings.lxd_ssh_user, settings.lxd_ssh_key, settings.lxd_ssh_port
        )
    return RuntimeRouter(adapters) if adapters else None


def create_app(settings: WorkerSettings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        adapter = build_adapter(settings)
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        api = ApiClient(settings)
        app.state.settings = settings
        app.state.adapter = adapter
        app.state.redis = redis
        tasks: list[asyncio.Task[None]] = []
        consumer = None
        if adapter is None:
            log.warning("SANDBOX_RUNTIME=disabled: worker не принимает задания")
        else:
            hub = TerminalHub(adapter, settings.sandbox_scrollback_bytes, settings.sandbox_max_output_bytes)
            service = WorkerService(settings, adapter, api, hub)
            consumer = JobConsumer(redis, service, settings.worker_consumer_name, settings.job_max_attempts)
            app.state.hub = hub
            app.state.service = service
            tasks.append(asyncio.create_task(consumer.run()))
            tasks.append(asyncio.create_task(reconcile_loop(adapter, api, hub, settings.reconcile_interval_seconds)))
        try:
            yield
        finally:
            if consumer:
                await consumer.stop()
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await api.aclose()
            await redis.aclose()
            if adapter is not None and hasattr(adapter, "close"):
                adapter.close()

    app = FastAPI(title="Linux Upskill sandbox worker", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready(response: Response) -> dict[str, object]:
        checks: dict[str, object] = {"redis": False, "runtime": False}
        with contextlib.suppress(Exception):
            checks["redis"] = bool(await app.state.redis.ping())
        adapter = app.state.adapter
        if adapter is not None:
            with contextlib.suppress(Exception):
                await adapter.list_runtimes()
                checks["runtime"] = True
        if not all(checks.values()):
            response.status_code = 503
        return checks

    @app.get("/metrics")
    async def metrics(request: Request) -> Response:
        supplied = request.headers.get("x-internal-token") or request.headers.get("authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(supplied, settings.internal_token):
            return Response(status_code=403)
        adapter = app.state.adapter
        if adapter is not None:
            with contextlib.suppress(Exception):
                ACTIVE_RUNTIMES.set(len(await adapter.list_runtimes()))
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.websocket("/terminal/{session_id}")
    async def terminal(ws: WebSocket, session_id: str) -> None:
        token = ws.headers.get("x-internal-token", "")
        if not hmac.compare_digest(token, settings.internal_token) or app.state.adapter is None:
            await ws.close(code=4403)
            return
        try:
            ref = runtime_ref_for(session_id)
            pty = await app.state.hub.get(ref)
        except (ValueError, RuntimeError_):
            await ws.close(code=4404)
            return
        await ws.accept()
        sub, replay = pty.attach()
        if replay:
            await ws.send_bytes(replay)

        async def pump_out() -> None:
            while True:
                chunk = await sub.queue.get()
                if chunk is None or sub.closed and chunk is None:
                    break
                await ws.send_bytes(chunk)
            if pty.output_limit_hit:
                await ws.send_text(json.dumps({"type": "error", "code": "output_limit"}))
            elif pty.exited:
                await ws.send_text(json.dumps({"type": "shell_exited"}))
            else:
                await ws.send_text(json.dumps({"type": "error", "code": "terminal_replaced"}))

        async def pump_in() -> None:
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    return
                if msg.get("bytes") is not None:
                    await pty.write(msg["bytes"])
                elif msg.get("text") is not None:
                    try:
                        ctl = json.loads(msg["text"])
                    except ValueError:
                        continue
                    if ctl.get("type") == "resize":
                        cols, rows = int(ctl.get("cols", 80)), int(ctl.get("rows", 24))
                        await pty.resize(max(20, min(cols, 500)), max(5, min(rows, 200)))

        out_task = asyncio.create_task(pump_out())
        in_task = asyncio.create_task(pump_in())
        try:
            await asyncio.wait({out_task, in_task}, return_when=asyncio.FIRST_COMPLETED)
        except WebSocketDisconnect:
            pass
        finally:
            for t in (out_task, in_task):
                t.cancel()
            await asyncio.gather(out_task, in_task, return_exceptions=True)
            pty.detach(sub)
            with contextlib.suppress(Exception):
                await ws.close()

    return app


def run() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run(create_app(s), host=s.worker_host, port=s.worker_port, log_config=None)


if __name__ == "__main__":
    run()
