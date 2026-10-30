from __future__ import annotations

import asyncio
import hmac
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text

from app.core.config import Settings, get_settings, set_settings
from app.core.deps import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER, REFRESH_COOKIE
from app.core.errors import error_body, install_error_handlers
from app.core.logging import request_id_var, setup_logging
from app.core.redis import close_redis, get_redis, init_redis
from app.db.session import close_db, init_db, sessionmaker
from app.modules.auth.router import router as auth_router
from app.modules.courses.router import router as courses_router
from app.modules.internal.router import router as internal_router
from app.modules.labs.router import router as labs_router
from app.modules.sessions.lifecycle import sweeper_loop
from app.modules.sessions.router import router as sessions_router
from app.modules.users.router import router as users_router
from app.websocket.terminal import router as ws_router

log = logging.getLogger("app")
HTTP_REQUESTS = Counter("upskill_http_requests_total", "HTTP-запросы", ["method", "status"])
HTTP_LATENCY = Histogram("upskill_http_request_seconds", "Латентность HTTP", ["method"])
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_EXEMPT = {"/api/v1/auth/register", "/api/v1/auth/login"}


def create_app(settings: Settings | None = None, *, run_background: bool = True) -> FastAPI:
    settings = settings or get_settings()
    set_settings(settings)
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        set_settings(settings)
        init_db(settings.database_url)
        init_redis(settings)
        task = asyncio.create_task(sweeper_loop(settings)) if run_background else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await close_redis()
            await close_db()

    app = FastAPI(
        title="Linux Upskill API",
        version="0.1.0",
        description="API платформы Linux Upskill: каталог лабораторий, песочницы, проверка, прогресс.",
        lifespan=lifespan,
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request_id_var.set(rid)
        path = request.url.path
        if request.method in UNSAFE and path.startswith("/api/"):
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") not in settings.allowed_origins:
                return JSONResponse(error_body("CSRF_ORIGIN", "Недопустимый Origin запроса"), status_code=403)
            has_cookie = any(c in request.cookies for c in (ACCESS_COOKIE, REFRESH_COOKIE))
            if has_cookie and path not in CSRF_EXEMPT:
                cookie, header = request.cookies.get(CSRF_COOKIE, ""), request.headers.get(CSRF_HEADER, "")
                if not cookie or not hmac.compare_digest(cookie, header):
                    return JSONResponse(error_body("CSRF_FAILED", "Отсутствует или неверен CSRF-токен"), status_code=403)
        started = time.perf_counter()
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        route = request.scope.get("route")
        if route is not None and not path.startswith("/health"):
            HTTP_REQUESTS.labels(request.method, str(response.status_code)).inc()
            HTTP_LATENCY.labels(request.method).observe(time.perf_counter() - started)
        return response

    prefix = "/api/v1"
    for r in (auth_router, users_router, courses_router, labs_router, sessions_router):
        app.include_router(r, prefix=prefix)
    app.include_router(internal_router)
    app.include_router(ws_router)

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def ready(response: Response) -> dict[str, object]:
        checks = {"database": False, "redis": False}
        try:
            async with sessionmaker()() as db:
                await db.execute(text("SELECT 1"))
            checks["database"] = True
        except Exception:  # noqa: BLE001
            pass
        try:
            checks["redis"] = bool(await get_redis().ping())
        except Exception:  # noqa: BLE001
            pass
        if not all(checks.values()):
            response.status_code = 503
        return {"status": "ready" if all(checks.values()) else "degraded", **checks, "sandbox": settings.sandbox_runtime}

    @app.get("/metrics", include_in_schema=False)
    async def metrics(request: Request) -> Response:
        # метрики не публикуются через proxy; для скрейпа — внутренний токен
        supplied = request.headers.get("x-internal-token") or request.headers.get("authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(supplied, settings.internal_token):
            return JSONResponse(error_body("FORBIDDEN", "Доступ запрещён"), status_code=403)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
