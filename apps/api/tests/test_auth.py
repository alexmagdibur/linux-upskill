from __future__ import annotations

import httpx

from .conftest import ORIGIN, PASSWORD


async def test_register_login_me_logout(client: httpx.AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json={"email": "A@Example.com", "password": PASSWORD, "display_name": "Ann"})
    assert r.status_code == 201 and r.json()["email"] == "a@example.com" and "password" not in r.text

    assert (await client.get("/api/v1/users/me")).status_code == 401

    r = await client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 200
    set_cookie = " ".join(r.headers.get_list("set-cookie")).lower()
    assert "upskill_access" in set_cookie and "httponly" in set_cookie and "samesite=lax" in set_cookie

    me = await client.get("/api/v1/users/me")
    assert me.status_code == 200 and me.json()["total_xp"] == 0

    csrf = {"X-CSRF-Token": client.cookies["upskill_csrf"]}
    assert (await client.post("/api/v1/auth/logout", headers=csrf)).status_code == 204
    assert (await client.get("/api/v1/users/me")).status_code == 401


async def test_duplicate_email_and_bad_credentials(client: httpx.AsyncClient) -> None:
    body = {"email": "dup@example.com", "password": PASSWORD}
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 201
    r = await client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "EMAIL_TAKEN"

    r = await client.post("/api/v1/auth/login", json={"email": "dup@example.com", "password": "wrong-password"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "INVALID_CREDENTIALS"
    r = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "INVALID_CREDENTIALS"  # без утечки существования


async def test_weak_password_rejected_with_uniform_error(client: httpx.AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json={"email": "x@example.com", "password": "short"})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR" and "message" in err and "details" in err


async def test_refresh_rotation_and_reuse_detection(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json={"email": "r@example.com", "password": PASSWORD})
    await client.post("/api/v1/auth/login", json={"email": "r@example.com", "password": PASSWORD})
    old_refresh = client.cookies.get("upskill_refresh", path="/api/v1/auth")
    csrf = {"X-CSRF-Token": client.cookies["upskill_csrf"]}

    assert (await client.post("/api/v1/auth/refresh", headers=csrf)).status_code == 200
    new_refresh = client.cookies.get("upskill_refresh", path="/api/v1/auth")
    assert new_refresh and new_refresh != old_refresh

    # злоумышленник воспроизводит старый (уже ротированный) refresh-токен
    attacker = httpx.AsyncClient(transport=client._transport, base_url="http://test", headers={"Origin": ORIGIN})  # noqa: SLF001
    attacker.cookies.set("upskill_refresh", old_refresh, path="/api/v1/auth")
    attacker.cookies.set("upskill_csrf", "x")
    r = await attacker.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "x"})
    assert r.status_code == 401
    await attacker.aclose()

    # всё семейство отозвано: легитимный токен тоже больше не работает
    csrf = {"X-CSRF-Token": client.cookies["upskill_csrf"]}
    assert (await client.post("/api/v1/auth/refresh", headers=csrf)).status_code == 401
    assert (await client.get("/api/v1/users/me")).status_code == 401


async def test_refresh_token_stored_only_as_hash(client: httpx.AsyncClient) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from .conftest import TEST_DB

    await client.post("/api/v1/auth/register", json={"email": "h@example.com", "password": PASSWORD})
    await client.post("/api/v1/auth/login", json={"email": "h@example.com", "password": PASSWORD})
    token = client.cookies.get("upskill_refresh", path="/api/v1/auth")
    engine = create_async_engine(TEST_DB)
    async with engine.connect() as conn:
        hashes = (await conn.execute(text("SELECT token_hash FROM auth_sessions"))).scalars().all()
        pw = (await conn.execute(text("SELECT password_hash FROM users"))).scalars().one()
    await engine.dispose()
    assert token not in hashes and len(hashes[0]) == 64
    assert pw.startswith("$argon2id$")


async def test_csrf_and_origin_protection(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json={"email": "c@example.com", "password": PASSWORD})
    await client.post("/api/v1/auth/login", json={"email": "c@example.com", "password": PASSWORD})

    r = await client.post("/api/v1/labs/linux-001/sessions")  # cookie есть, CSRF-заголовка нет
    assert r.status_code == 403 and r.json()["error"]["code"] == "CSRF_FAILED"

    csrf = {"X-CSRF-Token": client.cookies["upskill_csrf"], "Origin": "https://evil.example"}
    r = await client.post("/api/v1/labs/linux-001/sessions", headers=csrf)
    assert r.status_code == 403 and r.json()["error"]["code"] == "CSRF_ORIGIN"


async def test_rate_limiter_blocks_after_limit(client: httpx.AsyncClient) -> None:
    import pytest

    from app.core.config import set_settings
    from app.core.errors import AppError
    from app.core.ratelimit import hit

    from .conftest import make_settings

    set_settings(make_settings(rate_limit_enabled=True))
    try:
        for _ in range(3):
            await hit("t:key", 3, 60)
        with pytest.raises(AppError) as exc:
            await hit("t:key", 3, 60)
        assert exc.value.code == "RATE_LIMITED" and exc.value.status == 429
    finally:
        set_settings(make_settings())
