from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError, not_found
from app.core.jobs import enqueue
from app.core.redis import get_redis
from app.core.security import sha256_hex
from app.modules.labs import service as labs_service
from app.modules.labs.models import Lab, LabVersion
from app.modules.users.models import User
from app.modules.validation.models import ValidationAttempt

from . import states as st
from .models import IdempotencyKey, LabSession

log = logging.getLogger("app.sessions")
IDEMPOTENCY_TTL = timedelta(hours=24)


def now() -> datetime:
    return datetime.now(UTC)


# ----------------------------------------------------------------- transitions
async def transition(
    db: AsyncSession, session_id: uuid.UUID, dst: str, *, sources: frozenset[str] | None = None, **values: Any
) -> LabSession | None:
    """Атомарный переход: UPDATE ... WHERE status IN (...) RETURNING. None — если текущий статус не допускает переход."""
    src = sources or st.sources_for(dst)
    stmt = (
        update(LabSession)
        .where(LabSession.id == session_id, LabSession.status.in_(src))
        .values(status=dst, **values)
        .returning(LabSession)
        .execution_options(synchronize_session=False, populate_existing=True)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def enqueue_destroy(session_id: uuid.UUID) -> None:
    try:
        await enqueue({"type": "destroy", "session_id": str(session_id)})
    except Exception:  # noqa: BLE001 — ресурсы всё равно уберёт reconciler по TTL/сверке
        log.exception("destroy enqueue failed", extra={"session_id": str(session_id), "component": "sessions"})


# --------------------------------------------------------------------- queries
async def get_owned(db: AsyncSession, user: User, session_id: uuid.UUID) -> tuple[LabSession, LabVersion, Lab]:
    row = (
        await db.execute(
            select(LabSession, LabVersion, Lab)
            .join(LabVersion, LabVersion.id == LabSession.lab_version_id)
            .join(Lab, Lab.id == LabVersion.lab_id)
            .where(LabSession.id == session_id, LabSession.user_id == user.id)
        )
    ).first()
    if row is None:  # чужая и несуществующая сессии неразличимы
        raise not_found("Сессия")
    return row[0], row[1], row[2]


async def last_attempt(db: AsyncSession, session_id: uuid.UUID) -> ValidationAttempt | None:
    return (
        await db.execute(
            select(ValidationAttempt).where(ValidationAttempt.session_id == session_id)
            .order_by(ValidationAttempt.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()


def session_view(s: LabSession, v: LabVersion, lab: Lab, attempt: ValidationAttempt | None) -> dict[str, Any]:
    pub = v.public_json
    return {
        "session_id": str(s.id),
        "status": s.status,
        "expires_at": s.expires_at,
        "created_at": s.created_at,
        "started_at": s.started_at,
        "finished_at": s.finished_at,
        "error_code": s.error_code,
        "lab": {
            "id": lab.slug,
            "title": lab.title,
            "mode": lab.mode,
            "difficulty": lab.difficulty,
            "estimated_minutes": lab.estimated_minutes,
            "base_xp": pub["base_xp"],
        },
        "task": pub["task"],
        "theory": pub.get("theory"),
        "prediction": pub.get("prediction"),
        "criterion": pub.get("criterion"),
        "objectives": pub["objectives"],
        "checks": [c["title"] for c in pub["checks"]],
        "hints_total": len(pub["hints"]),
        "hints": pub["hints"][: s.hints_used],
        "last_attempt": (
            {"attempt_id": str(attempt.id), "status": attempt.status, "passed": attempt.passed,
             "score": float(attempt.score) if attempt.score is not None else None}
            if attempt else None
        ),
    }


def accepted_view(s: LabSession) -> dict[str, Any]:
    return {
        "session_id": str(s.id),
        "status": s.status,
        "expires_at": s.expires_at,
        "status_url": f"/api/v1/sessions/{s.id}",
    }


# ---------------------------------------------------------------------- create
_ENV_TITLES = {
    "V": "учебная VM (root, systemd, ядро, диски)",
    "N": "несколько узлов (сеть, кластер)",
    "D": "VM с container runtime",
}


def _ensure_runnable(lab: Lab) -> None:
    """Лаборатории, требующие VM/кластер, только описаны: запустить их в контейнерной песочнице небезопасно."""
    if lab.availability != "available":
        raise AppError(
            "LAB_UNAVAILABLE",
            "Эта лаборатория требует окружения, которое пока недоступно: " + _ENV_TITLES.get(lab.environment or "", "VM-runtime"),
            409,
            {"environment": lab.environment, "reason": lab.unavailable_reason},
        )


async def _insert_session(db: AsyncSession, settings: Settings, user: User, lab: Lab, version: LabVersion) -> LabSession:
    if settings.sandbox_runtime == "disabled":
        raise AppError("SANDBOX_DISABLED", "Песочницы отключены в конфигурации сервера", 503)
    # сериализуем проверку лимитов, чтобы параллельные запросы не превысили ёмкость
    await db.execute(text("SELECT pg_advisory_xact_lock(727001)"))
    holding = list(st.RUNTIME_HOLDING)
    total = (await db.execute(select(func.count()).select_from(LabSession).where(LabSession.status.in_(holding)))).scalar_one()
    if total >= settings.sandbox_max_concurrent:
        raise AppError("CAPACITY_EXCEEDED", "Все песочницы заняты, попробуйте через несколько минут", 503)
    mine = (
        await db.execute(
            select(func.count()).select_from(LabSession).where(LabSession.user_id == user.id, LabSession.status.in_(holding))
        )
    ).scalar_one()
    if mine >= settings.sandbox_per_user_limit:
        raise AppError("TOO_MANY_SESSIONS", "Достигнут лимит активных лабораторий, остановите одну из них", 429)
    ttl = min(settings.sandbox_ttl_seconds, int(version.public_json["timeout_seconds"]))
    session = LabSession(
        user_id=user.id,
        lab_version_id=version.id,
        status=st.PROVISIONING,
        expires_at=now() + timedelta(seconds=ttl),
        last_activity_at=now(),
    )
    db.add(session)
    await db.flush()
    return session


async def _dispatch_provision(db: AsyncSession, session: LabSession, lab: Lab, version: LabVersion, ttl: int) -> None:
    try:
        await enqueue(
            {
                "type": "provision",
                "session_id": str(session.id),
                "lab_slug": lab.slug,
                "version": version.version,
                "content_hash": version.content_hash,
                "ttl_seconds": ttl,
            }
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("provision enqueue failed", extra={"session_id": str(session.id), "component": "sessions"})
        await transition(db, session.id, st.FAILED, error_code="QUEUE_UNAVAILABLE", finished_at=now())
        await db.commit()
        raise AppError("SERVICE_UNAVAILABLE", "Очередь заданий недоступна, попробуйте позже", 503) from exc


async def create_session(
    db: AsyncSession, settings: Settings, user: User, lab_ref: str, idempotency_key: str | None
) -> tuple[LabSession, bool]:
    """Возвращает (сессия, создана_новая)."""
    lab = await labs_service.resolve_lab(db, lab_ref)
    _ensure_runnable(lab)
    version = await labs_service.latest_version(db, lab.id)
    req_hash = sha256_hex(f"create:{lab.slug}")

    if idempotency_key:
        existing = (
            await db.execute(
                select(IdempotencyKey).where(IdempotencyKey.user_id == user.id, IdempotencyKey.key == idempotency_key)
            )
        ).scalar_one_or_none()
        if existing and now() - existing.created_at < IDEMPOTENCY_TTL:
            if existing.request_hash != req_hash:
                raise AppError("IDEMPOTENCY_CONFLICT", "Idempotency-Key уже использован с другим запросом", 409)
            s = (await db.execute(select(LabSession).where(LabSession.id == existing.session_id))).scalar_one()
            return s, False
        if existing:
            await db.delete(existing)
            await db.flush()

    session = await _insert_session(db, settings, user, lab, version)
    if idempotency_key:
        db.add(IdempotencyKey(user_id=user.id, key=idempotency_key, request_hash=req_hash, session_id=session.id))
    try:
        await db.commit()
    except IntegrityError as exc:  # гонка двух запросов с одним ключом
        await db.rollback()
        raise AppError("IDEMPOTENCY_CONFLICT", "Запрос с этим Idempotency-Key уже обрабатывается", 409) from exc
    ttl = int((session.expires_at - now()).total_seconds())
    await _dispatch_provision(db, session, lab, version, ttl)
    return session, True


# ----------------------------------------------------------------- operations
async def stop_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> LabSession:
    s, _v, _lab = await get_owned(db, user, session_id)
    if s.status not in st.ACTIVE:
        return s  # идемпотентно: STOPPING/STOPPED/EXPIRED/FAILED/COMPLETED остаются как есть
    updated = await transition(
        db, s.id, st.STOPPING, sources=st.ACTIVE, finished_at=now(), error_code=None
    )
    await db.commit()
    if updated is not None:
        await enqueue_destroy(s.id)
        return updated
    await db.refresh(s)
    return s


async def reset_session(db: AsyncSession, settings: Settings, user: User, session_id: uuid.UUID) -> LabSession:
    old, version_old, lab = await get_owned(db, user, session_id)
    if old.status in st.ACTIVE:
        await transition(db, old.id, st.STOPPING, sources=st.ACTIVE, finished_at=now())
    version = await labs_service.latest_version(db, lab.id)
    # освободить слот старой сессии до проверки лимитов нельзя без commit, поэтому считаем её как удерживающую
    new = await _insert_session_after_stop(db, settings, user, lab, version, old.id)
    await db.commit()
    await enqueue_destroy(old.id)
    ttl = int((new.expires_at - now()).total_seconds())
    await _dispatch_provision(db, new, lab, version, ttl)
    return new


async def _insert_session_after_stop(
    db: AsyncSession, settings: Settings, user: User, lab: Lab, version: LabVersion, old_id: uuid.UUID
) -> LabSession:
    if settings.sandbox_runtime == "disabled":
        raise AppError("SANDBOX_DISABLED", "Песочницы отключены в конфигурации сервера", 503)
    await db.execute(text("SELECT pg_advisory_xact_lock(727001)"))
    holding = list(st.RUNTIME_HOLDING)
    # старая сессия в STOPPING освобождает «логический» слот: её runtime уничтожается сразу после commit
    base = LabSession.status.in_(holding) & (LabSession.id != old_id)
    total = (await db.execute(select(func.count()).select_from(LabSession).where(base))).scalar_one()
    if total >= settings.sandbox_max_concurrent:
        raise AppError("CAPACITY_EXCEEDED", "Все песочницы заняты, попробуйте через несколько минут", 503)
    mine = (
        await db.execute(select(func.count()).select_from(LabSession).where(base, LabSession.user_id == user.id))
    ).scalar_one()
    if mine >= settings.sandbox_per_user_limit:
        raise AppError("TOO_MANY_SESSIONS", "Достигнут лимит активных лабораторий, остановите одну из них", 429)
    ttl = min(settings.sandbox_ttl_seconds, int(version.public_json["timeout_seconds"]))
    s = LabSession(user_id=user.id, lab_version_id=version.id, status=st.PROVISIONING,
                   expires_at=now() + timedelta(seconds=ttl), last_activity_at=now())
    db.add(s)
    await db.flush()
    return s


async def unlock_hint(db: AsyncSession, user: User, session_id: uuid.UUID) -> dict[str, Any]:
    s, v, lab = await get_owned(db, user, session_id)
    total = len(v.public_json["hints"])
    if s.status in st.ACTIVE and s.hints_used < total:
        await db.execute(
            update(LabSession).where(LabSession.id == s.id, LabSession.hints_used < total)
            .values(hints_used=LabSession.hints_used + 1)
        )
        await db.commit()
        await db.refresh(s)
    return session_view(s, v, lab, await last_attempt(db, s.id))


# ---------------------------------------------------------------------- ticket
async def issue_ticket(db: AsyncSession, settings: Settings, user: User, session_id: uuid.UUID) -> dict[str, Any]:
    s, _v, _lab = await get_owned(db, user, session_id)
    if s.status not in st.TERMINAL_USABLE:
        raise AppError("INVALID_STATE", "Терминал доступен только для готовой лаборатории", 409, {"status": s.status})
    ticket = secrets.token_urlsafe(32)
    ttl = settings.terminal_ticket_ttl_seconds
    await get_redis().set(f"tt:{hashlib.sha256(ticket.encode()).hexdigest()}", f"{user.id}:{s.id}", ex=ttl)
    return {"ticket": ticket, "expires_in": ttl, "ws_path": f"/api/v1/sessions/{s.id}/terminal"}
