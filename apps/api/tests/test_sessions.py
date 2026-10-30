"""Интеграционные тесты API на реальных PostgreSQL и Redis. Worker здесь не запускается: его вызовы
(`/internal/v1/*`) выполняет сам тест; настоящую связку с песочницей проверяют worker-тесты и e2e."""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.sessions.lifecycle import sweep_once
from app.modules.sessions.service import now

from .conftest import INTERNAL, TEST_DB, Account, make_settings

ALL_OK = {"answer_path": True, "notes_dir": True}


async def start(acc: Account, lab: str = "linux-001", **headers: str) -> dict:
    r = await acc.post(f"/api/v1/labs/{lab}/sessions", headers=headers)
    assert r.status_code == 202, r.text
    return r.json()


async def internal(client: httpx.AsyncClient, url: str, **kw: object) -> httpx.Response:
    return await client.post(url, headers=INTERNAL, **kw)  # type: ignore[arg-type]


async def make_ready(acc: Account, sid: str) -> None:
    r = await internal(acc.http, f"/internal/v1/sessions/{sid}/provisioned", json={"runtime_ref": f"upskill-{sid}"})
    assert r.json() == {"accepted": True}


async def run_validation(acc: Account, sid: str, results: dict[str, bool]) -> dict:
    r = await acc.post(f"/api/v1/sessions/{sid}/validate")
    assert r.status_code == 202, r.text
    attempt = r.json()["attempt_id"]
    await internal(acc.http, f"/internal/v1/validations/{attempt}/result", json={"results": results, "error_code": None})
    return (await acc.get(f"/api/v1/sessions/{sid}/validations/{attempt}")).json()


async def sql(query: str, **params: object) -> list:
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        res = await conn.execute(text(query), params)
        rows = res.all() if res.returns_rows else []
    await engine.dispose()
    return rows


async def test_catalog_and_lab_card_do_not_leak_internals(make_account) -> None:
    a: Account = await make_account()
    courses = (await a.get("/api/v1/courses")).json()["items"]
    assert courses and courses[0]["id"] == "linux-upskill"
    mods = (await a.get(f"/api/v1/courses/{courses[0]['id']}/modules")).json()["items"]
    assert mods and mods[0]["labs"]
    listing = (await a.get("/api/v1/labs?mode=learn&difficulty=beginner&completed=false")).json()
    assert listing["total"] >= 1
    assert (await a.get("/api/v1/labs?mode=bogus")).status_code == 422
    card = (await a.get("/api/v1/labs/linux-001")).json()
    text_blob = str(card)
    for forbidden in ("validate.sh", "prepare.sh", "image_digest", "sha256", "runtime_ref", "/content/"):
        assert forbidden not in text_blob
    assert card["hints_total"] >= 1 and "hints" not in card
    assert (await a.get("/api/v1/labs/nope-000")).status_code == 404


async def test_create_session_returns_202_and_provisioning(make_account) -> None:
    a: Account = await make_account()
    body = await start(a)
    assert body["status"] == "PROVISIONING" and body["status_url"].endswith(body["session_id"])
    s = (await a.get(body["status_url"])).json()
    assert s["status"] == "PROVISIONING" and "runtime_ref" not in str(s)
    # job попал в очередь Redis
    from redis.asyncio import Redis

    from .conftest import TEST_REDIS

    r = Redis.from_url(TEST_REDIS, decode_responses=True)
    entries = await r.xrange("upskill:jobs")
    await r.aclose()
    assert any(body["session_id"] in e[1]["payload"] and '"provision"' in e[1]["payload"] for e in entries)


async def test_idempotency_key(make_account) -> None:
    a: Account = await make_account()
    key = str(uuid.uuid4())
    first = await start(a, **{"Idempotency-Key": key})
    second = await start(a, **{"Idempotency-Key": key})
    assert first["session_id"] == second["session_id"]
    assert (await sql("SELECT count(*) FROM lab_sessions"))[0][0] == 1
    r = await a.post("/api/v1/labs/linux-002/sessions", headers={"Idempotency-Key": key})
    # лаборатории linux-002 может не быть в каталоге: в обоих случаях повтор ключа с другим телом не создаёт сессию
    assert r.status_code in (409, 404)
    assert (await sql("SELECT count(*) FROM lab_sessions"))[0][0] == 1


async def test_limits_per_user_and_capacity(make_account, client: httpx.AsyncClient) -> None:
    a: Account = await make_account()
    await start(a)
    await start(a)
    r = await a.post("/api/v1/labs/linux-001/sessions")
    assert r.status_code == 429 and r.json()["error"]["code"] == "TOO_MANY_SESSIONS"
    assert (await sql("SELECT count(*) FROM lab_sessions"))[0][0] == 2


async def test_isolation_between_users(make_account) -> None:
    a: Account = await make_account()
    b: Account = await make_account()
    sid = (await start(a))["session_id"]
    await make_ready(a, sid)
    for method, url in (
        ("get", f"/api/v1/sessions/{sid}"),
        ("post", f"/api/v1/sessions/{sid}/validate"),
        ("post", f"/api/v1/sessions/{sid}/reset"),
        ("post", f"/api/v1/sessions/{sid}/terminal-ticket"),
        ("post", f"/api/v1/sessions/{sid}/hints/next"),
        ("delete", f"/api/v1/sessions/{sid}"),
    ):
        r = await getattr(b, method)(url)
        assert r.status_code == 404, (method, url, r.text)
    # сессия A не пострадала
    assert (await a.get(f"/api/v1/sessions/{sid}")).json()["status"] == "READY"
    assert (await b.get("/api/v1/users/me/sessions")).json()["total"] == 0


async def test_internal_api_requires_token(client: httpx.AsyncClient) -> None:
    r = await client.get("/internal/v1/sessions/active")
    assert r.status_code == 403
    r = await client.get("/internal/v1/sessions/active", headers={"X-Internal-Token": "wrong"})
    assert r.status_code == 403
    assert (await client.get("/internal/v1/sessions/active", headers=INTERNAL)).status_code == 200
    assert (await client.get("/metrics")).status_code == 403


async def test_terminal_ticket_rules(make_account) -> None:
    a: Account = await make_account()
    sid = (await start(a))["session_id"]
    r = await a.post(f"/api/v1/sessions/{sid}/terminal-ticket")
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_STATE"  # ещё PROVISIONING
    await make_ready(a, sid)
    t = (await a.post(f"/api/v1/sessions/{sid}/terminal-ticket")).json()
    assert t["expires_in"] <= 30 and len(t["ticket"]) >= 32
    from redis.asyncio import Redis

    from .conftest import TEST_REDIS

    rd = Redis.from_url(TEST_REDIS, decode_responses=True)
    keys = await rd.keys("tt:*")
    assert len(keys) == 1 and t["ticket"] not in keys[0]  # в Redis только хэш
    assert 0 < await rd.ttl(keys[0]) <= 30
    await rd.aclose()


async def test_full_flow_validation_xp_and_idempotent_award(make_account) -> None:
    a: Account = await make_account()
    sid = (await start(a))["session_id"]
    await make_ready(a, sid)

    # неуспех: сессия возвращается в RUNNING, XP нет
    bad = await run_validation(a, sid, {"answer_path": True, "notes_dir": False})
    assert bad["status"] == "FINISHED" and bad["passed"] is False and bad["score"] == 50.0 and bad["xp_awarded"] == 0
    assert (await a.get(f"/api/v1/sessions/{sid}")).json()["status"] == "RUNNING"
    assert "validate.sh" not in str(bad)

    good = await run_validation(a, sid, ALL_OK)
    assert good["passed"] is True and good["score"] == 100.0 and good["xp_awarded"] == 50
    assert (await a.get(f"/api/v1/sessions/{sid}")).json()["status"] == "COMPLETED"
    assert (await a.get("/api/v1/users/me")).json()["total_xp"] == 50

    # повторное прохождение той же лаборатории в новой сессии: XP не начисляется
    sid2 = (await start(a))["session_id"]
    await make_ready(a, sid2)
    again = await run_validation(a, sid2, ALL_OK)
    assert again["passed"] and again["xp_awarded"] == 0
    assert (await a.get("/api/v1/users/me")).json()["total_xp"] == 50
    prog = (await a.get("/api/v1/users/me/progress")).json()
    assert prog["completed_labs"] == 1 and prog["items"][0]["attempts_count"] == 3 and prog["items"][0]["best_score"] == 100.0
    assert len(prog["recent_attempts"]) == 3


async def test_concurrent_validation_requests_create_one_attempt(make_account) -> None:
    a: Account = await make_account()
    sid = (await start(a))["session_id"]
    await make_ready(a, sid)
    results = await asyncio.gather(*[a.post(f"/api/v1/sessions/{sid}/validate") for _ in range(6)])
    codes = sorted(r.status_code for r in results)
    assert codes == [202] + [409] * 5
    assert (await sql("SELECT count(*) FROM validation_attempts"))[0][0] == 1


async def test_concurrent_finalize_awards_xp_once(make_account, client: httpx.AsyncClient) -> None:
    a: Account = await make_account()
    s1 = (await start(a))["session_id"]
    s2 = (await start(a))["session_id"]
    attempts = []
    for sid in (s1, s2):
        await make_ready(a, sid)
        r = await a.post(f"/api/v1/sessions/{sid}/validate")
        attempts.append(r.json()["attempt_id"])
    # две сессии одной лаборатории завершаются одновременно, плюс дубль callback'а worker'а
    await asyncio.gather(
        *[internal(client, f"/internal/v1/validations/{x}/result", json={"results": ALL_OK}) for x in attempts + attempts]
    )
    assert (await sql("SELECT count(*), coalesce(sum(amount),0) FROM xp_transactions"))[0] == (1, 50)
    assert (await a.get("/api/v1/users/me")).json()["total_xp"] == 50


async def test_validate_requires_ready_session_and_hides_failures(make_account) -> None:
    a: Account = await make_account()
    sid = (await start(a))["session_id"]
    r = await a.post(f"/api/v1/sessions/{sid}/validate")  # PROVISIONING
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_STATE"
    await make_ready(a, sid)
    r = await a.post(f"/api/v1/sessions/{sid}/validate")
    attempt = r.json()["attempt_id"]
    # worker сообщил об ошибке инфраструктуры: попытка в ERROR, сессия снова доступна
    await internal(a.http, f"/internal/v1/validations/{attempt}/result", json={"results": {}, "error_code": "VALIDATION_TIMEOUT"})
    v = (await a.get(f"/api/v1/sessions/{sid}/validations/{attempt}")).json()
    assert v["status"] == "ERROR" and v["passed"] is None
    assert (await a.get(f"/api/v1/sessions/{sid}")).json()["status"] == "RUNNING"


async def test_stop_is_idempotent_and_reset_creates_new_session(make_account) -> None:
    a: Account = await make_account()
    sid = (await start(a))["session_id"]
    await make_ready(a, sid)
    r1 = await a.delete(f"/api/v1/sessions/{sid}")
    r2 = await a.delete(f"/api/v1/sessions/{sid}")
    assert r1.status_code == 202 and r1.json()["status"] == "STOPPING"
    assert r2.status_code == 202 and r2.json()["status"] == "STOPPING"  # повтор безопасен
    await internal(a.http, f"/internal/v1/sessions/{sid}/destroyed")
    assert (await a.delete(f"/api/v1/sessions/{sid}")).json()["status"] == "STOPPED"
    assert (await a.post(f"/api/v1/sessions/{sid}/terminal-ticket")).status_code == 409

    sid2 = (await start(a))["session_id"]
    await make_ready(a, sid2)
    r = await a.post(f"/api/v1/sessions/{sid2}/reset")
    assert r.status_code == 202
    new_id = r.json()["session_id"]
    assert new_id != sid2 and r.json()["status"] == "PROVISIONING"
    assert (await a.get(f"/api/v1/sessions/{sid2}")).json()["status"] == "STOPPING"


async def test_hints_unlock_progressively(make_account) -> None:
    a: Account = await make_account()
    sid = (await start(a))["session_id"]
    s = (await a.get(f"/api/v1/sessions/{sid}")).json()
    assert s["hints"] == [] and s["hints_total"] == 2
    s = (await a.post(f"/api/v1/sessions/{sid}/hints/next")).json()
    assert len(s["hints"]) == 1
    for _ in range(3):
        s = (await a.post(f"/api/v1/sessions/{sid}/hints/next")).json()
    assert len(s["hints"]) == 2


async def test_sweeper_expires_ttl_idle_and_stuck_states(make_account) -> None:
    a: Account = await make_account()
    settings = make_settings()
    sid_ttl = (await start(a))["session_id"]
    sid_idle = (await start(a))["session_id"]
    await make_ready(a, sid_ttl)
    await make_ready(a, sid_idle)
    await sql("UPDATE lab_sessions SET expires_at = now() - interval '1 minute' WHERE id = :i", i=uuid.UUID(sid_ttl))
    await sql("UPDATE lab_sessions SET last_activity_at = now() - interval '11 minutes' WHERE id = :i", i=uuid.UUID(sid_idle))

    engine = create_async_engine(TEST_DB)
    async with async_sessionmaker(engine, class_=AsyncSession)() as db:
        counts = await sweep_once(db, settings)
    await engine.dispose()
    assert counts["expired"] == 1 and counts["idle"] == 1
    assert (await a.get(f"/api/v1/sessions/{sid_ttl}")).json()["error_code"] == "TTL_EXPIRED"
    assert (await a.get(f"/api/v1/sessions/{sid_idle}")).json()["status"] == "EXPIRED"
    assert (await a.post(f"/api/v1/sessions/{sid_ttl}/terminal-ticket")).status_code == 409


async def test_sweeper_fails_stuck_provisioning(make_account) -> None:
    a: Account = await make_account()
    sid = (await start(a))["session_id"]
    engine = create_async_engine(TEST_DB)
    async with async_sessionmaker(engine, class_=AsyncSession)() as db:
        counts = await sweep_once(db, make_settings(), at=now() + timedelta(minutes=5))
    await engine.dispose()
    assert counts["provision_timeout"] == 1 or counts["expired"] == 1
    assert (await a.get(f"/api/v1/sessions/{sid}")).json()["status"] in ("FAILED", "EXPIRED")


async def test_sandbox_disabled_mode_returns_503(make_account) -> None:
    from asgi_lifespan import LifespanManager

    from app.main import create_app

    app = create_app(make_settings(sandbox_runtime="disabled"), run_background=False)
    async with LifespanManager(app):
        from .conftest import ORIGIN, PASSWORD

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers={"Origin": ORIGIN}) as c:
            await c.post("/api/v1/auth/register", json={"email": "d@example.com", "password": PASSWORD})
            await c.post("/api/v1/auth/login", json={"email": "d@example.com", "password": PASSWORD})
            r = await c.post("/api/v1/labs/linux-001/sessions", headers={"X-CSRF-Token": c.cookies["upskill_csrf"]})
    assert r.status_code == 503 and r.json()["error"]["code"] == "SANDBOX_DISABLED"
