from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbDep

from . import service

router = APIRouter(tags=["catalog"])


@router.get("/labs")
async def list_labs(
    db: DbDep,
    user: CurrentUser,
    mode: Literal["learn", "practice", "incident"] | None = None,
    difficulty: Literal["beginner", "junior", "middle", "senior"] | None = None,
    completed: bool | None = None,
    module: Annotated[str | None, Query(max_length=64)] = None,
    availability: Literal["available", "unavailable"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    items, total = await service.list_labs(
        db, user.id, mode=mode, difficulty=difficulty, completed=completed, module=module, limit=limit, offset=offset,
        availability=availability,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/labs/{lab_id}")
async def get_lab(lab_id: str, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    return await service.lab_card(db, user.id, lab_id)
