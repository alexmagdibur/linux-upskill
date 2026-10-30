"""Импорт доверенного контента (content/) в БД. Выполняется при деплое, не через публичный API.

    python -m app.seed [--content-dir DIR] [--allow-mutation]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from upskill_content import ContentError, LoadedLab, load_course, load_image_lock, load_lab

from app.core.config import get_settings
from app.db import models  # noqa: F401
from app.db.session import close_db, init_db, sessionmaker
from app.modules.courses.models import Course, Module
from app.modules.labs.models import Lab, LabVersion


def public_json(lab: LoadedLab) -> dict[str, object]:
    m = lab.manifest
    return {
        "lesson": m.lesson,
        "stage": m.stage,
        "topic": m.topic,
        "theory": m.theory,
        "prediction": m.prediction,
        "criterion": m.criterion,
        "followups": m.followups,
        "availability": m.availability,
        "unavailable_reason": m.unavailable_reason,
        "objectives": m.objectives,
        "skills": m.skills,
        "task": m.task,
        "hints": m.hints,
        "base_xp": m.reward.base_xp,
        "timeout_seconds": m.runtime.timeout_seconds if m.runtime else 0,
        "checks": [c.model_dump() for c in m.validation.checks] if m.validation else [],
    }


async def seed(db: AsyncSession, content_dir: Path, allow_mutation: bool = False) -> dict[str, int]:
    images = load_image_lock(content_dir)
    course_spec = load_course(content_dir)
    stats = {"labs": 0, "versions_created": 0, "versions_unchanged": 0}

    course = (await db.execute(select(Course).where(Course.slug == course_spec.slug))).scalar_one_or_none()
    if course is None:
        course = Course(slug=course_spec.slug, title=course_spec.title, description=course_spec.description)
        db.add(course)
    course.title, course.description, course.published, course.position = course_spec.title, course_spec.description, True, 0
    await db.flush()

    lab_pos = 0
    for mpos, mspec in enumerate(course_spec.modules):
        module = (
            await db.execute(select(Module).where(Module.course_id == course.id, Module.slug == mspec.slug))
        ).scalar_one_or_none()
        if module is None:
            module = Module(course_id=course.id, slug=mspec.slug, title=mspec.title)
            db.add(module)
        module.title, module.description, module.position = mspec.title, mspec.description, mpos
        await db.flush()

        for lab_slug in mspec.labs:
            lab_pos += 1
            loaded = load_lab(content_dir / "labs" / lab_slug)
            m = loaded.manifest
            if m.runtime is None:  # недоступная лаборатория: исполняемой части нет
                image = {"id": "n/a"}
            else:
                image = images.get(m.runtime.image)
                if image is None:
                    raise ContentError(f"{lab_slug}: образ {m.runtime.image} отсутствует в images.lock.json")
            lab = (await db.execute(select(Lab).where(Lab.slug == lab_slug))).scalar_one_or_none()
            if lab is None:
                lab = Lab(module_id=module.id, slug=lab_slug, title=m.title, mode=m.mode, difficulty=m.difficulty,
                          estimated_minutes=m.estimated_minutes)
                db.add(lab)
            lab.module_id, lab.title, lab.description = module.id, m.title, m.description
            lab.mode, lab.difficulty, lab.estimated_minutes = m.mode, m.difficulty, m.estimated_minutes
            lab.position, lab.published = lab_pos, True
            lab.lesson_number, lab.topic, lab.task_type = m.lesson, m.topic, m.task_type
            lab.environment, lab.availability, lab.unavailable_reason = m.environment, m.availability, m.unavailable_reason
            await db.flush()
            stats["labs"] += 1

            existing = (
                await db.execute(select(LabVersion).where(LabVersion.lab_id == lab.id, LabVersion.version == m.version))
            ).scalar_one_or_none()
            ref = f"labs/{lab_slug}@v{m.version}#{loaded.content_hash}"
            if existing is None:
                db.add(LabVersion(lab_id=lab.id, version=m.version, manifest_ref=ref, content_hash=loaded.content_hash,
                                  image_digest=image["id"], public_json=public_json(loaded), published_at=datetime.now(UTC)))
                stats["versions_created"] += 1
            elif existing.content_hash != loaded.content_hash or existing.image_digest != image["id"]:
                if not allow_mutation:
                    raise ContentError(
                        f"{lab_slug}: содержимое или образ изменились, но version={m.version} уже опубликована. "
                        "Увеличьте version в manifest.yaml (или используйте --allow-mutation только в разработке)."
                    )
                existing.manifest_ref, existing.content_hash, existing.image_digest = ref, loaded.content_hash, image["id"]
                existing.public_json = public_json(loaded)
                stats["versions_created"] += 1
            else:
                stats["versions_unchanged"] += 1
    # задания, исключённые из курса, снимаем с публикации (история попыток и XP сохраняются)
    in_course = {slug for m in course_spec.modules for slug in m.labs}
    for gone in (await db.execute(select(Lab).where(Lab.published.is_(True), Lab.slug.not_in(in_course)))).scalars():
        gone.published = False
        stats["unpublished"] = stats.get("unpublished", 0) + 1
    # модули, исчезнувшие из course.yaml и оставшиеся без лабораторий, убираем
    keep = {m.slug for m in course_spec.modules}
    for stale in (await db.execute(select(Module).where(Module.course_id == course.id))).scalars():
        if stale.slug not in keep and not (await db.execute(select(Lab.id).where(Lab.module_id == stale.id).limit(1))).first():
            await db.delete(stale)
    await db.commit()
    return stats


async def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-dir", type=Path, default=get_settings().content_dir)
    parser.add_argument("--allow-mutation", action="store_true")
    args = parser.parse_args()
    init_db()
    try:
        async with sessionmaker()() as db:
            stats = await seed(db, args.content_dir, args.allow_mutation or get_settings().env in ("dev", "test"))
    except ContentError as exc:
        print(f"ОШИБКА КОНТЕНТА: {exc}", file=sys.stderr)
        return 1
    finally:
        await close_db()
    print(f"seed ok: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
