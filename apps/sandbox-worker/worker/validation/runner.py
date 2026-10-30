"""Запуск проверки: (необязательный) exercise от имени student, затем независимый validator."""

from __future__ import annotations

from dataclasses import dataclass

from upskill_content import LoadedLab

from worker.runtime.base import RuntimeAdapter


@dataclass
class CheckRun:
    results: dict[str, bool]
    timed_out: bool


def parse_check_output(stdout: str, declared: list[str]) -> dict[str, bool]:
    """Строки `PASS <id>` / `FAIL <id>`. Неизвестные id игнорируются, отсутствующие = провал; побеждает последняя."""
    results = dict.fromkeys(declared, False)
    for line in stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] in ("PASS", "FAIL") and parts[1] in results:
            results[parts[1]] = parts[0] == "PASS"
    return results


async def run_checks(adapter: RuntimeAdapter, runtime_ref: str, lab: LoadedLab) -> CheckRun:
    declared = [c.id for c in lab.manifest.validation.checks]
    spec = lab.manifest.validation
    assert spec is not None
    if lab.exercise_script:
        await adapter.exercise(runtime_ref, lab.exercise_script, spec.exercise_timeout_seconds)
    if spec.reboot_before_validate:
        await adapter.reboot(runtime_ref)
    ctx = await adapter.snapshot_or_inspect(runtime_ref, lab.validate_script, lab.manifest.validation.timeout_seconds)
    if ctx.timed_out:
        return CheckRun(dict.fromkeys(declared, False), True)
    return CheckRun(parse_check_output(ctx.stdout, declared), False)
