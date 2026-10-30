from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbDep
from app.modules.auth.schemas import UserOut
from app.modules.labs.models import Lab, LabVersion
from app.modules.progress import service as progress_service
from app.modules.sessions.models import LabSession

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def me(user: CurrentUser, db: DbDep) -> dict[str, Any]:
    data = UserOut.model_validate(user).model_dump(mode="json")
    data["total_xp"] = await progress_service.total_xp(db, user.id)
    return data


@router.get("/me/progress")
async def my_progress(user: CurrentUser, db: DbDep) -> dict[str, Any]:
    return await progress_service.progress_overview(db, user.id)


@router.get("/me/sessions")
async def my_sessions(
    user: CurrentUser,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    base = select(LabSession).where(LabSession.user_id == user.id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            select(LabSession, Lab.slug, Lab.title)
            .join(LabVersion, LabVersion.id == LabSession.lab_version_id)
            .join(Lab, Lab.id == LabVersion.lab_id)
            .where(LabSession.user_id == user.id)
            .order_by(LabSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return {
        "items": [
            {
                "session_id": str(s.id),
                "lab_id": slug,
                "lab_title": title,
                "status": s.status,
                "created_at": s.created_at,
                "finished_at": s.finished_at,
            }
            for s, slug, title in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
