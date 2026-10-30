"""WebSocket-шлюз терминала: браузер <-> API <-> (внутренний WS) worker <-> PTY в песочнице."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import uuid

import websockets
from fastapi import APIRouter, WebSocket
from prometheus_client import Counter, Gauge
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.deps import ACCESS_COOKIE, user_from_access_token
from app.core.redis import get_redis
from app.db.session import sessionmaker
from app.modules.sessions import states as st
from app.modules.sessions.models import LabSession
from app.modules.sessions.service import now, transition

log = logging.getLogger("app.ws")
router = APIRouter()

WS_ACTIVE = Gauge("upskill_ws_connections", "Активные терминальные WebSocket")
WS_DISCONNECTS = Counter("upskill_ws_disconnects_total", "Закрытые терминальные WebSocket", ["reason"])
MAX_INPUT_FRAME = 64 * 1024
ACTIVITY_THROTTLE = 15.0

CLOSE_UNAUTHORIZED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_NOT_FOUND = 4404
CLOSE_EXPIRED = 4410
CLOSE_UNAVAILABLE = 4503


def _worker_ws_url(base: str, session_id: str) -> str:
    return base.replace("https://", "wss://").replace("http://", "ws://").rstrip("/") + f"/terminal/{session_id}"


async def _authorize(ws: WebSocket, session_id: uuid.UUID) -> uuid.UUID | None:
    """Origin + cookie-сессия + одноразовый ticket, привязанный к user_id и session_id. Возвращает user_id."""
    settings = get_settings()
    origin = (ws.headers.get("origin") or "").rstrip("/")
    if origin not in settings.allowed_origins:
        await ws.close(code=CLOSE_FORBIDDEN)
        return None
    ticket = ws.query_params.get("ticket", "")
    if not ticket:
        await ws.close(code=CLOSE_UNAUTHORIZED)
        return None
    # GETDEL: ticket одноразовый, повторное использование невозможно
    stored = await get_redis().getdel(f"tt:{hashlib.sha256(ticket.encode()).hexdigest()}")
    async with sessionmaker()() as db:
        user = await user_from_access_token(db, settings, ws.cookies.get(ACCESS_COOKIE))
        if user is None:
            await ws.close(code=CLOSE_UNAUTHORIZED)
            return None
        if stored != f"{user.id}:{session_id}":
            await ws.close(code=CLOSE_FORBIDDEN)
            return None
        row = (
            await db.execute(select(LabSession).where(LabSession.id == session_id, LabSession.user_id == user.id))
        ).scalar_one_or_none()
        if row is None:
            await ws.close(code=CLOSE_NOT_FOUND)
            return None
        if row.status not in st.TERMINAL_USABLE:
            await ws.close(code=CLOSE_EXPIRED)
            return None
        if row.status == st.READY:
            await transition(db, session_id, st.RUNNING, sources=frozenset({st.READY}))
            await db.commit()
        return user.id


@router.websocket("/api/v1/sessions/{session_id}/terminal")
async def terminal(ws: WebSocket, session_id: uuid.UUID) -> None:
    settings = get_settings()
    user_id = await _authorize(ws, session_id)
    if user_id is None:
        return
    try:
        upstream = await websockets.connect(
            _worker_ws_url(settings.worker_url, str(session_id)),
            additional_headers={"X-Internal-Token": settings.internal_token},
            max_size=2**20,
            open_timeout=10,
            ping_interval=20,
        )
    except Exception:  # noqa: BLE001
        log.warning("worker unavailable", extra={"session_id": str(session_id), "error_code": "WORKER_UNAVAILABLE"})
        await ws.close(code=CLOSE_UNAVAILABLE)
        return

    await ws.accept()
    WS_ACTIVE.inc()
    reason = "client"
    loop = asyncio.get_running_loop()
    last_activity = 0.0

    async def touch() -> None:
        nonlocal last_activity
        if loop.time() - last_activity < ACTIVITY_THROTTLE:
            return
        last_activity = loop.time()
        async with sessionmaker()() as db:
            await db.execute(update(LabSession).where(LabSession.id == session_id).values(last_activity_at=now()))
            await db.commit()

    async def client_to_worker() -> None:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                return
            if msg.get("bytes") is not None:
                data = msg["bytes"]
                if len(data) > MAX_INPUT_FRAME:
                    await ws.send_text(json.dumps({"type": "error", "code": "frame_too_large"}))
                    continue
                await upstream.send(data)
                await touch()
            elif msg.get("text") is not None:
                try:
                    ctl = json.loads(msg["text"])
                except ValueError:
                    continue
                kind = ctl.get("type")
                if kind == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
                elif kind == "resize":
                    cols, rows = int(ctl.get("cols", 80)), int(ctl.get("rows", 24))
                    await upstream.send(json.dumps({"type": "resize", "cols": cols, "rows": rows}))

    async def worker_to_client() -> None:
        async for frame in upstream:
            if isinstance(frame, bytes):
                await ws.send_bytes(frame)
            else:
                await ws.send_text(frame)

    async def watch_session() -> None:
        nonlocal reason
        while True:
            await asyncio.sleep(5)
            async with sessionmaker()() as db:
                status = (await db.execute(select(LabSession.status).where(LabSession.id == session_id))).scalar_one_or_none()
            if status not in st.TERMINAL_USABLE:
                reason = "session_expired"
                await ws.send_text(json.dumps({"type": "session_expired", "status": status}))
                return

    tasks = [asyncio.create_task(t()) for t in (client_to_worker, worker_to_client, watch_session)]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        with contextlib.suppress(Exception):
            await upstream.close()
        with contextlib.suppress(Exception):
            await ws.close(code=CLOSE_EXPIRED if reason == "session_expired" else 1000)
        WS_ACTIVE.dec()
        WS_DISCONNECTS.labels(reason).inc()
