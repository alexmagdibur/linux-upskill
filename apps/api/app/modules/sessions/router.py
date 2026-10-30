from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Header, Response, status

from app.core.deps import CurrentUser, DbDep, SettingsDep
from app.core.ratelimit import hit
from app.modules.validation import service as validation

from . import service

router = APIRouter(tags=["sessions"])


@router.post("/labs/{lab_id}/sessions", status_code=status.HTTP_202_ACCEPTED)
async def create_session(
    lab_id: str,
    db: DbDep,
    user: CurrentUser,
    settings: SettingsDep,
    idempotency_key: Annotated[str | None, Header(max_length=128)] = None,
) -> dict[str, Any]:
    await hit(f"create-session:{user.id}", 10, 60)
    session, _created = await service.create_session(db, settings, user, lab_id, idempotency_key)
    return service.accepted_view(session)


@router.get("/sessions/{session_id}")
async def get_session(session_id: uuid.UUID, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    s, v, lab = await service.get_owned(db, user, session_id)
    return service.session_view(s, v, lab, await service.last_attempt(db, s.id))


@router.post("/sessions/{session_id}/validate", status_code=status.HTTP_202_ACCEPTED)
async def validate(session_id: uuid.UUID, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    await hit(f"validate:{user.id}", 20, 60)
    attempt = await validation.request_validation(db, user, session_id)
    return {
        "attempt_id": str(attempt.id),
        "status": attempt.status,
        "status_url": f"/api/v1/sessions/{session_id}/validations/{attempt.id}",
    }


@router.get("/sessions/{session_id}/validations/{attempt_id}")
async def get_validation(session_id: uuid.UUID, attempt_id: uuid.UUID, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    return validation.attempt_view(await validation.get_attempt(db, user, session_id, attempt_id))


@router.post("/sessions/{session_id}/reset", status_code=status.HTTP_202_ACCEPTED)
async def reset(session_id: uuid.UUID, db: DbDep, user: CurrentUser, settings: SettingsDep) -> dict[str, Any]:
    await hit(f"create-session:{user.id}", 10, 60)
    return service.accepted_view(await service.reset_session(db, settings, user, session_id))


@router.delete("/sessions/{session_id}")
async def stop(session_id: uuid.UUID, db: DbDep, user: CurrentUser, response: Response) -> dict[str, Any]:
    s = await service.stop_session(db, user, session_id)
    response.status_code = status.HTTP_202_ACCEPTED if s.status == "STOPPING" else status.HTTP_200_OK
    return {"session_id": str(s.id), "status": s.status}


@router.post("/sessions/{session_id}/hints/next")
async def next_hint(session_id: uuid.UUID, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    return await service.unlock_hint(db, user, session_id)


@router.post("/sessions/{session_id}/terminal-ticket")
async def terminal_ticket(session_id: uuid.UUID, db: DbDep, user: CurrentUser, settings: SettingsDep) -> dict[str, Any]:
    await hit(f"ticket:{user.id}", 60, 60)
    return await service.issue_ticket(db, settings, user, session_id)
