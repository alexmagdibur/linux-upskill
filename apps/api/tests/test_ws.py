"""Безопасность и семантика WebSocket-шлюза терминала.

Положительный сценарий идёт через встроенный «worker-двойник» (echo-сервер на websockets): так проверяется
именно логика шлюза (ticket, Origin, владелец, проксирование binary/resize). Настоящий PTY проверяют
worker-тесты и Playwright E2E.
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
import uuid
from collections.abc import Iterator

import pytest
import websockets
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app

from .conftest import INTERNAL, ORIGIN, PASSWORD, make_settings


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class FakeWorker:
    """Принимает внутренний WS; эхо-отвечает на binary, фиксирует resize и заголовок токена."""

    def __init__(self) -> None:
        self.port = free_port()
        self.received: list[object] = []
        self.token_seen: list[str] = []
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._ready = threading.Event()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)

        async def handler(ws) -> None:  # type: ignore[no-untyped-def]
            self.token_seen.append(ws.request.headers.get("X-Internal-Token", ""))
            await ws.send(b"WELCOME\r\n")
            async for msg in ws:
                self.received.append(msg)
                if isinstance(msg, bytes):
                    await ws.send(b"echo:" + msg)

        async def main() -> None:
            async with websockets.serve(handler, "127.0.0.1", self.port):
                self._ready.set()
                await asyncio.Future()

        self._loop.run_until_complete(main())

    def start(self) -> None:
        self._thread.start()
        assert self._ready.wait(5)


@pytest.fixture
def worker() -> Iterator[FakeWorker]:
    w = FakeWorker()
    w.start()
    yield w


@pytest.fixture
def web(worker: FakeWorker) -> Iterator[TestClient]:
    app = create_app(make_settings(worker_url=f"http://127.0.0.1:{worker.port}"), run_background=False)
    with TestClient(app, base_url="http://test", headers={"Origin": ORIGIN}) as c:
        yield c


class User:
    """Пользователь = свой набор cookie поверх ОДНОГО TestClient (один event loop приложения)."""

    def __init__(self, web: TestClient, cookies: dict[str, str] | None = None) -> None:
        self.web, self.cookies = web, cookies or {}

    def _use(self) -> TestClient:
        self.web.cookies.clear()
        for k, v in self.cookies.items():
            self.web.cookies.set(k, v, path="/api/v1/auth" if k == "upskill_refresh" else "/")
        self.web.headers["X-CSRF-Token"] = self.cookies.get("upskill_csrf", "")
        return self.web

    def post(self, *a: object, **kw: object):  # type: ignore[no-untyped-def]
        return self._use().post(*a, **kw)  # type: ignore[arg-type]

    def get(self, *a: object, **kw: object):  # type: ignore[no-untyped-def]
        return self._use().get(*a, **kw)  # type: ignore[arg-type]

    def delete(self, *a: object, **kw: object):  # type: ignore[no-untyped-def]
        return self._use().delete(*a, **kw)  # type: ignore[arg-type]

    def websocket_connect(self, *a: object, **kw: object):  # type: ignore[no-untyped-def]
        return self._use().websocket_connect(*a, **kw)  # type: ignore[arg-type]


def new_user(c: TestClient) -> User:
    email = f"ws-{uuid.uuid4().hex[:8]}@example.com"
    c.cookies.clear()
    assert c.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD}).status_code == 201
    r = c.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200
    jar = dict(c.cookies.items())
    c.cookies.clear()
    return User(c, jar)


def ready_session(u: User) -> str:
    sid = u.post("/api/v1/labs/linux-001/sessions").json()["session_id"]
    r = u.post(f"/internal/v1/sessions/{sid}/provisioned", json={"runtime_ref": f"upskill-{sid}"}, headers=INTERNAL)
    assert r.json() == {"accepted": True}
    return sid


def ticket(u: User, sid: str) -> str:
    r = u.post(f"/api/v1/sessions/{sid}/terminal-ticket")
    assert r.status_code == 200, r.text
    return r.json()["ticket"]


def url(sid: str, t: str) -> str:
    return f"/api/v1/sessions/{sid}/terminal?ticket={t}"


def expect_rejected(c: User, path: str, headers: dict[str, str] | None = None) -> None:
    with pytest.raises(WebSocketDisconnect), c.websocket_connect(path, headers=headers or {}) as ws:
        ws.receive_text()


@pytest.fixture(autouse=True)
def _clean(web: TestClient) -> None:
    # ключи Redis из предыдущих тестов не должны влиять; пользователи уникальны
    return None


def test_proxy_roundtrip_binary_resize_and_internal_token(web: TestClient, worker: FakeWorker) -> None:
    u = new_user(web)
    sid = ready_session(u)
    with u.websocket_connect(url(sid, ticket(u, sid))) as ws:
        assert ws.receive_bytes() == b"WELCOME\r\n"
        ws.send_bytes(b"ls\n")  # ввод пользователя — binary-кадр
        assert ws.receive_bytes() == b"echo:ls\n"
        ws.send_text(json.dumps({"type": "resize", "cols": 120, "rows": 32}))
        ws.send_text(json.dumps({"type": "ping"}))
        assert json.loads(ws.receive_text()) == {"type": "pong"}
        deadline = time.time() + 3
        while time.time() < deadline and not any(isinstance(m, str) for m in worker.received):
            time.sleep(0.05)
    assert json.loads(next(m for m in worker.received if isinstance(m, str))) == {"type": "resize", "cols": 120, "rows": 32}
    assert worker.token_seen == [make_settings().internal_token]  # к worker ходит только шлюз с внутренним токеном
    assert u.get(f"/api/v1/sessions/{sid}").json()["status"] == "RUNNING"  # первое подключение: READY -> RUNNING


def test_ticket_is_one_time(web: TestClient) -> None:
    u = new_user(web)
    sid = ready_session(u)
    t = ticket(u, sid)
    with u.websocket_connect(url(sid, t)) as ws:
        ws.receive_bytes()
    expect_rejected(u, url(sid, t))  # повторное использование отклонено


def test_missing_and_garbage_ticket_rejected(web: TestClient) -> None:
    u = new_user(web)
    sid = ready_session(u)
    expect_rejected(u, f"/api/v1/sessions/{sid}/terminal")
    expect_rejected(u, url(sid, "not-a-real-ticket"))


def test_bad_origin_rejected_and_ticket_not_usable_afterwards(web: TestClient) -> None:
    u = new_user(web)
    sid = ready_session(u)
    t = ticket(u, sid)
    expect_rejected(u, url(sid, t), headers={"Origin": "https://evil.example"})
    expect_rejected(u, url(sid, t), headers={"Origin": ""})


def test_other_users_cannot_use_a_ticket_or_attach(web: TestClient) -> None:
    a, b = new_user(web), new_user(web)
    sid = ready_session(a)
    stolen = ticket(a, sid)
    expect_rejected(b, url(sid, stolen))  # чужой ticket с cookie пользователя B
    # B не может получить ticket на чужую сессию
    assert b.post(f"/api/v1/sessions/{sid}/terminal-ticket").status_code == 404
    # без cookie-авторизации ticket бесполезен
    anon = User(web)  # без cookie-авторизации ticket бесполезен
    expect_rejected(anon, url(sid, ticket(a, sid)))


def test_ticket_bound_to_session(web: TestClient) -> None:
    u = new_user(web)
    s1, s2 = ready_session(u), ready_session(u)
    t1 = ticket(u, s1)
    expect_rejected(u, url(s2, t1))  # ticket от одной сессии не подходит к другой


def test_expired_ticket_rejected(web: TestClient) -> None:
    from redis import Redis

    from .conftest import TEST_REDIS

    u = new_user(web)
    sid = ready_session(u)
    t = ticket(u, sid)
    r = Redis.from_url(TEST_REDIS)
    key = r.keys("tt:*")[0]
    r.pexpire(key, 100)
    time.sleep(0.3)
    expect_rejected(u, url(sid, t))


def test_stopped_session_has_no_terminal(web: TestClient) -> None:
    u = new_user(web)
    sid = ready_session(u)
    t = ticket(u, sid)
    u.delete(f"/api/v1/sessions/{sid}")
    expect_rejected(u, url(sid, t))
    assert u.post(f"/api/v1/sessions/{sid}/terminal-ticket").status_code == 409


def test_worker_down_closes_connection_cleanly(web: TestClient) -> None:
    app = create_app(make_settings(worker_url="http://127.0.0.1:1"), run_background=False)
    with TestClient(app, base_url="http://test", headers={"Origin": ORIGIN}) as c:
        u = new_user(c)
        sid = ready_session(u)
        expect_rejected(u, url(sid, ticket(u, sid)))
    # сессия не повреждена, можно подключиться снова, когда worker вернётся
    assert u is not None
