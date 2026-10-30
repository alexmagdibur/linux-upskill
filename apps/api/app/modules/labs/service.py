from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errors import not_found
from app.modules.courses.models import Course, Module
from app.modules.progress.models import UserProgress

from .models import Lab, LabVersion


def _is_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def resolve_lab(db: AsyncSession, lab_ref: str, *, published_only: bool = True) -> Lab:
    """lab_ref — slug (linux-001) или UUID."""
    stmt = select(Lab)
    uid = _is_uuid(lab_ref)
    stmt = stmt.where(Lab.id == uid) if uid else stmt.where(Lab.slug == lab_ref)
    if published_only:
        stmt = stmt.where(Lab.published.is_(True))
    lab = (await db.execute(stmt)).scalar_one_or_none()
    if lab is None:
        raise not_found("Лаборатория")
    return lab


async def latest_version(db: AsyncSession, lab_id: uuid.UUID) -> LabVersion:
    v = (
        await db.execute(
            select(LabVersion)
            .where(LabVersion.lab_id == lab_id, LabVersion.published_at.is_not(None))
            .order_by(LabVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if v is None:
        raise not_found("Версия лаборатории")
    return v


def lab_summary(lab: Lab, module: Module, base_xp: int, progress: UserProgress | None) -> dict[str, Any]:
    return {
        "id": lab.slug,
        "uuid": str(lab.id),
        "title": lab.title,
        "description": lab.description,
        "mode": lab.mode,
        "difficulty": lab.difficulty,
        "estimated_minutes": lab.estimated_minutes,
        "module": {"slug": module.slug, "title": module.title},
        "base_xp": base_xp,
        "completed": bool(progress and progress.completed_at),
        "best_score": float(progress.best_score) if progress else None,
        "attempts_count": progress.attempts_count if progress else 0,
    }


def _labs_query(user_id: uuid.UUID) -> Any:
    newer = aliased(LabVersion)
    return (
        select(Lab, Module, LabVersion, UserProgress)
        .join(Module, Module.id == Lab.module_id)
        .join(Course, Course.id == Module.course_id)
        .join(
            LabVersion,
            (LabVersion.lab_id == Lab.id)
            & LabVersion.published_at.is_not(None)
            & ~exists().where(
                (newer.lab_id == Lab.id) & newer.published_at.is_not(None) & (newer.version > LabVersion.version)
            ),
        )
        .outerjoin(UserProgress, (UserProgress.lab_id == Lab.id) & (UserProgress.user_id == user_id))
        .where(Lab.published.is_(True), Course.published.is_(True))
    )


async def list_labs(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    mode: str | None,
    difficulty: str | None,
    completed: bool | None,
    module: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    stmt = _labs_query(user_id)
    if mode:
        stmt = stmt.where(Lab.mode == mode)
    if difficulty:
        stmt = stmt.where(Lab.difficulty == difficulty)
    if module:
        stmt = stmt.where(Module.slug == module)
    if completed is True:
        stmt = stmt.where(UserProgress.completed_at.is_not(None))
    elif completed is False:
        stmt = stmt.where(UserProgress.completed_at.is_(None))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.order_by(Module.position, Lab.position).limit(limit).offset(offset))).all()
    items = [lab_summary(lab, mod, ver.public_json["base_xp"], prog) for lab, mod, ver, prog in rows]
    return items, total


async def lab_card(db: AsyncSession, user_id: uuid.UUID, lab_ref: str) -> dict[str, Any]:
    lab = await resolve_lab(db, lab_ref)
    row = (await db.execute(_labs_query(user_id).where(Lab.id == lab.id))).first()
    if row is None:
        raise not_found("Лаборатория")
    lab, module, version, progress = row
    pub = version.public_json
    card = lab_summary(lab, module, pub["base_xp"], progress)
    card.update(
        {
            "objectives": pub["objectives"],
            "skills": pub["skills"],
            "hints_total": len(pub["hints"]),
            "checks": [c["title"] for c in pub["checks"]],
            "version": version.version,
        }
    )
    return card
