"""Для каждой лаборатории-«машины» (runtime.type: lxd): стартовое состояние и неверное решение не проходят,
эталонное и альтернативные решения проходят. Всё в настоящих учебных машинах на LXD-хосте."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest
from upskill_content import LoadedLab, load_image_lock, load_lab

from worker.runtime.base import ImageRef, ResourceLimits
from worker.runtime.lxd import LXDAdapter
from worker.validation.runner import run_checks

from .conftest import CONTENT
from .test_lxd import _lxd_adapter, _reachable

LXD_DIRS = sorted(
    p for p in (CONTENT / "labs").iterdir() if p.is_dir() and (load_lab(p).manifest.runtime or None) and load_lab(p).manifest.runtime.type == "lxd"  # type: ignore[union-attr]
)

pytestmark = pytest.mark.skipif(not _reachable(), reason="LXD-хост (LXD_SSH_HOST) не настроен или недоступен")

_SEM = asyncio.Semaphore(2)  # одновременно не больше двух машин на небольшой VM (5 ГиБ ОЗУ)


def passed(lab: LoadedLab, results: dict[str, bool]) -> bool:
    assert lab.manifest.validation is not None
    return all(results[c.id] for c in lab.manifest.validation.checks if c.required)


async def attempt(adapter: LXDAdapter, image: ImageRef, lab: LoadedLab, script: str | None) -> dict[str, bool]:
    async with _SEM:
        assert lab.manifest.runtime is not None
        ref = await adapter.create(str(uuid.uuid4()), image, ResourceLimits(ttl_seconds=900), [], lab.setup_script, 90)
        try:
            if script is not None:
                await adapter.exercise(ref, script.encode(), 60)
            run = await run_checks(adapter, ref, lab)
            assert not run.timed_out
            return run.results
        finally:
            await adapter.destroy(ref)


def test_lxd_catalog_is_not_empty() -> None:
    assert LXD_DIRS, "ожидаются лаборатории на учебной машине"
    for d in LXD_DIRS:
        lab = load_lab(d)
        assert lab.manifest.availability == "available" and lab.manifest.runtime.image == "ubuntu-systemd"  # type: ignore[union-attr]
        assert (d / "tests" / "solution.sh").is_file() and (d / "tests" / "wrong.sh").is_file(), d.name
        assert all(c.id in lab.validate_script.decode() for c in lab.manifest.validation.checks), d.name  # type: ignore[union-attr]


@pytest.mark.parametrize("lab_dir", LXD_DIRS, ids=lambda p: p.name)
async def test_lxd_lab_positive_and_negative(lab_dir: Path) -> None:
    adapter = _lxd_adapter()
    assert adapter is not None
    e = load_image_lock(CONTENT)["ubuntu-systemd"]
    image = ImageRef(e["tag"], e["id"])
    lab = load_lab(lab_dir)
    solutions = [lab_dir / "tests" / "solution.sh", *sorted((lab_dir / "tests").glob("alt_*.sh"))]
    scripts: list[str | None] = [None, (lab_dir / "tests" / "wrong.sh").read_text(encoding="utf-8")]
    scripts += [s.read_text(encoding="utf-8") for s in solutions]
    results = await asyncio.gather(*(attempt(adapter, image, lab, s) for s in scripts))
    baseline, wrong, *good = results
    assert not passed(lab, baseline), f"стартовое состояние не должно проходить: {baseline}"
    assert not passed(lab, wrong), f"неверное решение не должно проходить: {wrong}"
    for sol, res in zip(solutions, good, strict=True):
        assert all(res.values()), f"{sol.name}: решение должно проходить все проверки: {res}"
