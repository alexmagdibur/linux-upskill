from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.models import AuthSession
from app.modules.users.models import User

from .config import Settings, get_settings
from .errors import AppError
from .security import decode_access_token

ACCESS_COOKIE = "upskill_access"
REFRESH_COOKIE = "upskill_refresh"
CSRF_COOKIE = "upskill_csrf"
CSRF_HEADER = "x-csrf-token"

DbDep = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def user_from_access_token(db: AsyncSession, settings: Settings, token: str | None) -> User | None:
    if not token:
        return None
    claims = decode_access_token(settings, token)
    if not claims:
        return None
    try:
        user_id, sid = uuid.UUID(claims["sub"]), uuid.UUID(claims["sid"])
    except ValueError:
        return None
    row = (
        await db.execute(
            select(User, AuthSession)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(User.id == user_id, AuthSession.family_id == sid)
            .order_by(AuthSession.created_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    user, auth = row
    # сессия отозвана при выходе (revoked без replaced_by) или семейство скомпрометировано
    if auth.revoked_at is not None and auth.replaced_by is None:
        return None
    if auth.expires_at < datetime.now(UTC):
        return None
    return user


async def get_current_user(request: Request, db: DbDep, settings: SettingsDep) -> User:
    user = await user_from_access_token(db, settings, request.cookies.get(ACCESS_COOKIE))
    if user is None:
        raise AppError("UNAUTHORIZED", "Требуется вход в систему", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_internal(request: Request, settings: SettingsDep) -> None:
    import hmac

    token = request.headers.get("x-internal-token", "")
    if not hmac.compare_digest(token, settings.internal_token):
        raise AppError("FORBIDDEN", "Доступ запрещён", 403)
