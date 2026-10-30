from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    new_opaque_token,
    sha256_hex,
    verify_password,
)
from app.modules.users.models import User

from .models import AuthSession

_DUMMY_HASH = hash_password("dummy-password-for-timing")


def set_auth_cookies(response: Response, settings: Settings, access: str, refresh: str) -> None:
    common = {"httponly": True, "secure": settings.cookie_secure, "samesite": "lax"}
    response.set_cookie(ACCESS_COOKIE, access, max_age=settings.access_ttl_seconds, path="/", **common)  # type: ignore[arg-type]
    response.set_cookie(
        REFRESH_COOKIE, refresh, max_age=settings.refresh_ttl_seconds, path="/api/v1/auth", **common  # type: ignore[arg-type]
    )
    response.set_cookie(
        CSRF_COOKIE,
        new_opaque_token(),
        max_age=settings.refresh_ttl_seconds,
        path="/",
        httponly=False,  # читается фронтендом и отправляется в заголовке (double-submit)
        secure=settings.cookie_secure,
        samesite="lax",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")


async def register(db: AsyncSession, email: str, password: str, display_name: str | None) -> User:
    user = User(email=email.lower(), password_hash=hash_password(password), display_name=display_name)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError("EMAIL_TAKEN", "Пользователь с таким email уже зарегистрирован", 409) from exc
    return user


async def _issue(db: AsyncSession, settings: Settings, user: User, family_id: uuid.UUID) -> tuple[str, str, AuthSession]:
    refresh = new_opaque_token()
    auth = AuthSession(
        user_id=user.id,
        family_id=family_id,
        token_hash=sha256_hex(refresh),
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.refresh_ttl_seconds),
    )
    db.add(auth)
    await db.flush()
    return create_access_token(settings, user.id, family_id), refresh, auth


async def login(db: AsyncSession, settings: Settings, email: str, password: str) -> tuple[User, str, str]:
    user = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
    # одинаковая работа для существующего и несуществующего пользователя
    ok = verify_password(user.password_hash if user else _DUMMY_HASH, password)
    if user is None or not ok:
        raise AppError("INVALID_CREDENTIALS", "Неверный email или пароль", 401)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    access, refresh, _ = await _issue(db, settings, user, uuid.uuid4())
    await db.commit()
    return user, access, refresh


async def refresh(db: AsyncSession, settings: Settings, token: str | None) -> tuple[User, str, str]:
    if not token:
        raise AppError("UNAUTHORIZED", "Требуется вход в систему", 401)
    auth = (
        await db.execute(select(AuthSession).where(AuthSession.token_hash == sha256_hex(token)).with_for_update())
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if auth is None or auth.expires_at < now:
        raise AppError("UNAUTHORIZED", "Сессия истекла, войдите заново", 401)
    if auth.revoked_at is not None:
        # повторное использование уже ротированного токена: отзываем всё семейство
        await db.execute(
            update(AuthSession).where(AuthSession.family_id == auth.family_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        raise AppError("UNAUTHORIZED", "Сессия отозвана, войдите заново", 401)
    user = (await db.execute(select(User).where(User.id == auth.user_id))).scalar_one()
    access, new_refresh, new_auth = await _issue(db, settings, user, auth.family_id)
    auth.revoked_at = now
    auth.replaced_by = new_auth.id
    await db.commit()
    return user, access, new_refresh


async def logout(db: AsyncSession, token: str | None) -> None:
    if not token:
        return
    auth = (await db.execute(select(AuthSession).where(AuthSession.token_hash == sha256_hex(token)))).scalar_one_or_none()
    if auth is not None:
        await db.execute(
            update(AuthSession).where(AuthSession.family_id == auth.family_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await db.commit()
