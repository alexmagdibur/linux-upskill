"""Для каждой лаборатории: стартовое состояние воспроизводимо, пустое/неверное решение не проходит,
эталонное и альтернативные решения проходят. Всё выполняется в настоящих песочницах Docker."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from upskill_content import LoadedLab, load_course, load_image_lock, load_lab

from worker.runtime.base import ImageRef, ResourceLimits
from worker.runtime.docker import DockerAdapter
from worker.validation.runner import run_checks

from .conftest import CONTENT, run_as_student

LAB_DIRS = sorted(p for p in (CONTENT / "labs").iterdir() if p.is_dir())


def passed(lab: LoadedLab, results: dict[str, bool]) -> bool:
    return all(results[c.id] for c in lab.manifest.validation.checks if c.required)


async def provision(adapter: DockerAdapter, image: ImageRef, lab: LoadedLab) -> str:
    return await adapter.create(
        str(uuid.uuid4()), image, ResourceLimits(), lab.manifest.runtime.writable_dirs, lab.setup_script, 30
    )


async def attempt(adapter: DockerAdapter, image: ImageRef, lab: LoadedLab, script: str | None) -> dict[str, bool]:
    ref = await provision(adapter, image, lab)
    try:
        if script is not None:
            run_as_student(adapter, ref, script, timeout=25)
        run = await run_checks(adapter, ref, lab)
        assert not run.timed_out
        return run.results
    finally:
        await adapter.destroy(ref)


def test_catalog_has_20_labs_in_three_modules() -> None:
    course = load_course(CONTENT)
    assert [m.slug for m in course.modules] == ["linux-basics", "administration", "incidents"]
    assert [len(m.labs) for m in course.modules] == [8, 7, 5]
    on_disk = {p.name for p in LAB_DIRS}
    assert on_disk == {lab for m in course.modules for lab in m.labs} and len(on_disk) == 20


def test_all_manifests_valid_and_use_allowlisted_images() -> None:
    images = load_image_lock(CONTENT)
    for d in LAB_DIRS:
        lab = load_lab(d)  # строгая схема, 1–3 подсказки, существующие скрипты
        assert lab.manifest.runtime.image in images
        assert (d / "tests" / "solution.sh").is_file() and (d / "tests" / "wrong.sh").is_file(), d.name
        ids = [c.id for c in lab.manifest.validation.checks]
        assert all(f"chk {i} " in lab.validate_script.decode() or f"chk {i}\t" in lab.validate_script.decode() or i in lab.validate_script.decode() for i in ids)


@pytest.mark.parametrize("lab_dir", LAB_DIRS, ids=lambda p: p.name)
async def test_lab_positive_and_negative(adapter: DockerAdapter, image: ImageRef, lab_dir: Path) -> None:
    lab = load_lab(lab_dir)

    baseline = await attempt(adapter, image, lab, None)
    assert not passed(lab, baseline), f"стартовое состояние не должно проходить проверку: {baseline}"

    wrong = await attempt(adapter, image, lab, (lab_dir / "tests" / "wrong.sh").read_text(encoding="utf-8"))
    assert not passed(lab, wrong), f"неверное решение не должно проходить: {wrong}"

    solutions = [lab_dir / "tests" / "solution.sh", *sorted((lab_dir / "tests").glob("alt_*.sh"))]
    for sol in solutions:
        results = await attempt(adapter, image, lab, sol.read_text(encoding="utf-8"))
        assert all(results.values()), f"{sol.name}: решение должно проходить все проверки: {results}"
