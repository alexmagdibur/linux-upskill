from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbDep
from app.core.errors import not_found
from app.modules.labs import service as labs_service
from app.modules.labs.models import Lab

from .models import Course, Module

router = APIRouter(tags=["catalog"])


@router.get("/courses")
async def list_courses(db: DbDep, _: CurrentUser) -> dict[str, Any]:
    counts = dict(
        (
            await db.execute(
                select(Module.course_id, func.count(Lab.id))
                .join(Lab, Lab.module_id == Module.id)
                .where(Lab.published.is_(True))
                .group_by(Module.course_id)
            )
        ).all()
    )
    courses = (await db.execute(select(Course).where(Course.published.is_(True)).order_by(Course.position))).scalars()
    return {
        "items": [
            {"id": c.slug, "uuid": str(c.id), "title": c.title, "description": c.description, "labs_count": counts.get(c.id, 0)}
            for c in courses
        ]
    }


@router.get("/courses/{course_id}/modules")
async def course_modules(course_id: str, db: DbDep, user: CurrentUser) -> dict[str, Any]:
    try:
        uid = uuid.UUID(course_id)
        cond = Course.id == uid
    except ValueError:
        cond = Course.slug == course_id
    course = (await db.execute(select(Course).where(cond, Course.published.is_(True)))).scalar_one_or_none()
    if course is None:
        raise not_found("Курс")
    modules = (await db.execute(select(Module).where(Module.course_id == course.id).order_by(Module.position))).scalars().all()
    out = []
    for m in modules:
        items, _total = await labs_service.list_labs(
            db, user.id, mode=None, difficulty=None, completed=None, module=m.slug, limit=100, offset=0
        )
        out.append({"id": m.slug, "uuid": str(m.id), "title": m.title, "description": m.description, "labs": items})
    return {"course": {"id": course.slug, "title": course.title}, "items": out}
