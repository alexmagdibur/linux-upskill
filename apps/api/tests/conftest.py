from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import ROOT, Settings
from app.main import create_app

TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://upskill:upskill@127.0.0.1:15432/upskill_test")
TEST_REDIS = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379/1")
ORIGIN = "http://localhost:5173"
PASSWORD = "correct-horse-battery"
API_DIR = Path(__file__).resolve().parents[1]


def make_settings(**overrides: object) -> Settings:
    base = dict(
        env="test", database_url=TEST_DB, redis_url=TEST_REDIS, rate_limit_enabled=False, public_origin=ORIGIN,
        sandbox_max_concurrent=10, sandbox_per_user_limit=2, content_dir=ROOT / "content",
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Миграции Alembic применяются на чистую тестовую БД (проверка воспроизводимости схемы)."""
    env = dict(os.environ, ALEMBIC_DATABASE_URL=TEST_DB)
    for args in (["downgrade", "base"], ["upgrade", "head"]):
        subprocess.run([sys.executable, "-m", "alembic", *args], cwd=API_DIR, env=env, check=True, capture_output=True)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seeded(migrated_database: None) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.seed import seed

    engine = create_async_engine(TEST_DB)
    async with async_sessionmaker(engine, class_=AsyncSession)() as db:
        await seed(db, ROOT / "content", allow_mutation=True)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_state(seeded: None) -> AsyncIterator[None]:
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users CASCADE"))
    await engine.dispose()
    r = Redis.from_url(TEST_REDIS)
    await r.flushdb()
    await r.aclose()
    yield


@pytest_asyncio.fixture
async def app_ctx() -> AsyncIterator[Callable[..., object]]:
    yield make_settings


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(make_settings(), run_background=False)
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", headers={"Origin": ORIGIN}) as c:
            yield c


class Account:
    def __init__(self, http: httpx.AsyncClient, email: str) -> None:
        self.http, self.email = http, email

    @property
    def csrf(self) -> dict[str, str]:
        return {"X-CSRF-Token": self.http.cookies.get("upskill_csrf", "")}

    async def post(self, url: str, **kw: object) -> httpx.Response:
        headers = {**self.csrf, **kw.pop("headers", {})}  # type: ignore[arg-type]
        return await self.http.post(url, headers=headers, **kw)  # type: ignore[arg-type]

    async def delete(self, url: str) -> httpx.Response:
        return await self.http.delete(url, headers=self.csrf)

    async def get(self, url: str, **kw: object) -> httpx.Response:
        return await self.http.get(url, **kw)  # type: ignore[arg-type]


@pytest_asyncio.fixture
async def make_account(client: httpx.AsyncClient) -> AsyncIterator[Callable[[], object]]:
    """Фабрика независимых пользователей со своими cookie-jar."""
    created: list[httpx.AsyncClient] = []
    transport = client._transport  # noqa: SLF001

    async def factory() -> Account:
        c = httpx.AsyncClient(transport=transport, base_url="http://test", headers={"Origin": ORIGIN})
        created.append(c)
        email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        r = await c.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
        assert r.status_code == 201, r.text
        r = await c.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return Account(c, email)

    yield factory  # type: ignore[misc]
    for c in created:
        await c.aclose()


INTERNAL = {"X-Internal-Token": "dev-internal-token-change-me"}
