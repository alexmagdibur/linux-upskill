from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, not_found
from app.core.jobs import enqueue
from app.modules.labs.models import Lab, LabVersion
from app.modules.progress.models import UserProgress, XpTransaction
from app.modules.sessions import service as sessions
from app.modules.sessions import states as st
from app.modules.sessions.models import LabSession
from app.modules.users.models import User

from .models import ValidationAttempt
from .scoring import compute_score

log = logging.getLogger("app.validation")
COMPLETED_GRACE = timedelta(minutes=2)


def attempt_view(a: ValidationAttempt) -> dict[str, Any]:
    return {
        "attempt_id": str(a.id),
        "status": a.status,
        "passed": a.passed,
        "score": float(a.score) if a.score is not None else None,
        "checks": a.checks_json or [],
        "error_code": a.error_code,
        "xp_awarded": a.xp_awarded,
    }


async def request_validation(db: AsyncSession, user: User, session_id: uuid.UUID) -> ValidationAttempt:
    s, v, lab = await sessions.get_owned(db, user, session_id)
    if s.status == st.VALIDATING:
        raise AppError("VALIDATION_IN_PROGRESS", "Проверка уже выполняется", 409)
    if s.status not in st.TERMINAL_USABLE:
        raise AppError("INVALID_STATE", "Проверка недоступна в текущем состоянии сессии", 409, {"status": s.status})
    # атомарный переход: параллельный запрос не пройдёт WHERE status IN (...)
    moved = await sessions.transition(db, s.id, st.VALIDATING, sources=st.TERMINAL_USABLE, last_activity_at=sessions.now())
    if moved is None:
        await db.rollback()
        raise AppError("VALIDATION_IN_PROGRESS", "Проверка уже выполняется", 409)
    attempt = ValidationAttempt(session_id=s.id, status="PENDING")
    db.add(attempt)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError("VALIDATION_IN_PROGRESS", "Проверка уже выполняется", 409) from exc
    try:
        await enqueue(
            {
                "type": "validate",
                "session_id": str(s.id),
                "attempt_id": str(attempt.id),
                "lab_slug": lab.slug,
                "version": v.version,
                "content_hash": v.content_hash,
            }
        )
    except Exception:  # noqa: BLE001
        log.exception("validate enqueue failed", extra={"session_id": str(s.id), "component": "validation"})
        await finalize_attempt(db, attempt.id, {}, "QUEUE_UNAVAILABLE")
        raise AppError("SERVICE_UNAVAILABLE", "Очередь заданий недоступна, попробуйте позже", 503) from None
    return attempt


async def get_attempt(db: AsyncSession, user: User, session_id: uuid.UUID, attempt_id: uuid.UUID) -> ValidationAttempt:
    await sessions.get_owned(db, user, session_id)
    a = (
        await db.execute(
            select(ValidationAttempt).where(ValidationAttempt.id == attempt_id, ValidationAttempt.session_id == session_id)
        )
    ).scalar_one_or_none()
    if a is None:
        raise not_found("Проверка")
    return a


async def finalize_attempt(
    db: AsyncSession, attempt_id: uuid.UUID, results: dict[str, bool], error_code: str | None
) -> ValidationAttempt | None:
    """Идемпотентно завершает проверку; прогресс и XP пишутся в одной транзакции."""
    now = datetime.now(UTC)
    attempt = (
        await db.execute(select(ValidationAttempt).where(ValidationAttempt.id == attempt_id).with_for_update())
    ).scalar_one_or_none()
    if attempt is None or attempt.status != "PENDING":
        await db.rollback()
        return attempt
    session = (await db.execute(select(LabSession).where(LabSession.id == attempt.session_id).with_for_update())).scalar_one()
    version = (await db.execute(select(LabVersion).where(LabVersion.id == session.lab_version_id))).scalar_one()
    lab = (await db.execute(select(Lab).where(Lab.id == version.lab_id))).scalar_one()

    if error_code:
        attempt.status, attempt.error_code, attempt.finished_at = "ERROR", error_code, now
        if session.status == st.VALIDATING:
            session.status = st.RUNNING
        await db.commit()
        return attempt

    score, passed, public = compute_score(version.public_json["checks"], results)
    attempt.status, attempt.score, attempt.passed, attempt.checks_json, attempt.finished_at = (
        "FINISHED", score, passed, public, now,
    )

    # строка прогресса создаётся идемпотентно и блокируется: конкурентные завершения сериализуются
    await db.execute(
        pg_insert(UserProgress).values(user_id=session.user_id, lab_id=lab.id, best_score=0, attempts_count=0)
        .on_conflict_do_nothing(index_elements=["user_id", "lab_id"])
    )
    progress = (
        await db.execute(
            select(UserProgress).where(UserProgress.user_id == session.user_id, UserProgress.lab_id == lab.id).with_for_update()
        )
    ).scalar_one()
    progress.attempts_count += 1
    if score > progress.best_score:
        progress.best_score = score

    destroy_after = False
    if passed and session.status == st.VALIDATING:
        session.status, session.finished_at = st.COMPLETED, now
        destroy_after = True
        if progress.completed_at is None:
            progress.completed_at = now
            xp = int(version.public_json["base_xp"])
            res = await db.execute(
                pg_insert(XpTransaction)
                .values(user_id=session.user_id, session_id=session.id, amount=xp, reason=f"lab_first_completion:{lab.slug}")
                .on_conflict_do_nothing()
            )
            if res.rowcount:  # type: ignore[attr-defined]
                attempt.xp_awarded = xp
    elif session.status == st.VALIDATING:
        session.status = st.RUNNING
    await db.commit()
    if destroy_after:
        await sessions.enqueue_destroy(session.id)  # окружение больше не нужно; результат уже сохранён
    return attempt
