"""Внутренний API для worker. Не должен публиковаться через reverse proxy (см. infra/proxy)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from app.core.deps import DbDep, require_internal
from app.modules.sessions import service as sessions
from app.modules.sessions import states as st
from app.modules.sessions.models import LabSession
from app.modules.validation import service as validation
from app.modules.validation.models import ValidationAttempt

router = APIRouter(prefix="/internal/v1", tags=["internal"], dependencies=[Depends(require_internal)], include_in_schema=False)


class Provisioned(BaseModel):
    runtime_ref: str = Field(max_length=200)


class Failed(BaseModel):
    error_code: str = Field(max_length=64)


class ValidationResult(BaseModel):
    results: dict[str, bool] = Field(default_factory=dict)
    error_code: str | None = Field(default=None, max_length=64)


@router.post("/sessions/{session_id}/provisioned")
async def provisioned(session_id: uuid.UUID, body: Provisioned, db: DbDep) -> dict[str, bool]:
    s = await sessions.transition(
        db, session_id, st.READY, sources=frozenset({st.PROVISIONING}), runtime_ref=body.runtime_ref,
        started_at=sessions.now(),
    )
    await db.commit()
    return {"accepted": s is not None}


@router.post("/sessions/{session_id}/failed")
async def failed(session_id: uuid.UUID, body: Failed, db: DbDep) -> dict[str, bool]:
    s = await sessions.transition(
        db, session_id, st.FAILED, sources=st.ACTIVE, error_code=body.error_code, finished_at=sessions.now()
    )
    if s is not None:
        await db.execute(
            update(ValidationAttempt)
            .where(ValidationAttempt.session_id == session_id, ValidationAttempt.status == "PENDING")
            .values(status="ERROR", error_code=body.error_code, finished_at=sessions.now())
        )
    await db.commit()
    if s is not None:
        await sessions.enqueue_destroy(session_id)
    return {"accepted": s is not None}


@router.post("/sessions/{session_id}/destroyed")
async def destroyed(session_id: uuid.UUID, db: DbDep) -> dict[str, bool]:
    s = await sessions.transition(db, session_id, st.STOPPED, sources=frozenset({st.STOPPING}))
    await db.commit()
    return {"accepted": s is not None}


@router.post("/validations/{attempt_id}/result")
async def validation_result(attempt_id: uuid.UUID, body: ValidationResult, db: DbDep) -> dict[str, Any]:
    attempt = await validation.finalize_attempt(db, attempt_id, body.results, body.error_code)
    return {"accepted": attempt is not None}


@router.get("/sessions/active")
async def active(db: DbDep) -> dict[str, Any]:
    rows = (
        await db.execute(select(LabSession.id, LabSession.status).where(LabSession.status.in_(list(st.RUNTIME_HOLDING))))
    ).all()
    return {"items": [{"session_id": str(i), "status": s} for i, s in rows]}
