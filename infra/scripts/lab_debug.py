"""Отладка задания на учебной машине: поднимает машину, применяет скрипт и показывает вывод проверки.

    python infra/scripts/lab_debug.py ld-123 solution [--root "команда от root после решения"]

Режимы скрипта: solution | wrong | none | путь к файлу. Машина удаляется в конце.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "sandbox-worker"))
sys.path.insert(0, str(ROOT / "packages" / "upskill_content"))

from tests.conftest import CONTENT  # noqa: E402
from tests.test_lxd import _lxd_adapter  # noqa: E402
from upskill_content import load_image_lock, load_lab  # noqa: E402
from worker.runtime.base import ImageRef, ResourceLimits  # noqa: E402


async def main() -> None:
    lab_id, mode = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "none"
    extra = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else None
    adapter = _lxd_adapter()
    assert adapter is not None
    d = CONTENT / "labs" / lab_id
    lab = load_lab(d)
    e = load_image_lock(CONTENT)["ubuntu-systemd"]
    try:
        ref = await adapter.create(str(uuid.uuid4()), ImageRef(e["tag"], e["id"]), ResourceLimits(ttl_seconds=900), [], lab.setup_script, 40)
    except Exception as exc:
        print("SETUP ERROR:", getattr(exc, "code", ""), getattr(exc, "message", exc))
        return
    try:
        if mode in ("solution", "wrong"):
            script = (d / "tests" / f"{mode}.sh").read_bytes()
        elif mode != "none":
            script = Path(mode).read_bytes()
        else:
            script = b""
        if script:
            ctx = await adapter.exercise(ref, script, 90)
            print("--- exercise ---\n", ctx.stdout[-1500:])
        if lab.exercise_script:
            ctx = await adapter.exercise(ref, lab.exercise_script, lab.manifest.validation.exercise_timeout_seconds)
            print("--- lab exercise ---\n", ctx.stdout[-1500:])
        if lab.manifest.validation.reboot_before_validate:
            await adapter.reboot(ref)
        if extra:
            ctx = await adapter.snapshot_or_inspect(ref, extra.encode(), 60)
            print("--- root ---\n", ctx.stdout[-3000:])
        ctx = await adapter.snapshot_or_inspect(ref, lab.validate_script, lab.manifest.validation.timeout_seconds)
        print("--- validate ---\n", ctx.stdout[-2000:])
    finally:
        await adapter.destroy(ref)


if __name__ == "__main__":
    asyncio.run(main())
