from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.labs.models import Lab
from app.modules.sessions.models import LabSession
from app.modules.validation.models import ValidationAttempt

from .models import UserProgress, XpTransaction


async def total_xp(db: AsyncSession, user_id: uuid.UUID) -> int:
    return (
        await db.execute(select(func.coalesce(func.sum(XpTransaction.amount), 0)).where(XpTransaction.user_id == user_id))
    ).scalar_one()


async def progress_overview(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(UserProgress, Lab).join(Lab, Lab.id == UserProgress.lab_id).where(UserProgress.user_id == user_id)
            .order_by(UserProgress.completed_at.desc().nullslast())
        )
    ).all()
    runnable = select(func.count()).select_from(Lab).where(Lab.published.is_(True), Lab.availability == "available")
    labs_total = (await db.execute(runnable)).scalar_one()
    recent = (
        await db.execute(
            select(ValidationAttempt, LabSession)
            .join(LabSession, LabSession.id == ValidationAttempt.session_id)
            .where(LabSession.user_id == user_id)
            .order_by(ValidationAttempt.created_at.desc())
            .limit(10)
        )
    ).all()
    lab_ids = {s.lab_version_id for _a, s in recent}
    slugs: dict[uuid.UUID, str] = {}
    if lab_ids:
        from app.modules.labs.models import LabVersion

        slugs = dict(
            (
                await db.execute(
                    select(LabVersion.id, Lab.slug).join(Lab, Lab.id == LabVersion.lab_id).where(LabVersion.id.in_(lab_ids))
                )
            ).all()
        )
    return {
        "total_xp": await total_xp(db, user_id),
        "completed_labs": sum(1 for p, _ in rows if p.completed_at),
        "labs_total": labs_total,
        "items": [
            {
                "lab_id": lab.slug,
                "title": lab.title,
                "best_score": float(p.best_score),
                "attempts_count": p.attempts_count,
                "completed_at": p.completed_at,
            }
            for p, lab in rows
        ],
        "recent_attempts": [
            {
                "attempt_id": str(a.id),
                "session_id": str(s.id),
                "lab_id": slugs.get(s.lab_version_id),
                "passed": a.passed,
                "score": float(a.score) if a.score is not None else None,
                "status": a.status,
                "created_at": a.created_at,
            }
            for a, s in recent
        ],
    }
