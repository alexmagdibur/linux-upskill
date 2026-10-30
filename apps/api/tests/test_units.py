"""Юнит-тесты: оценивание, автомат состояний, манифесты."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from upskill_content import ContentError, LabManifest, load_lab
from upskill_content.manifest import RuntimeSpec

from app.modules.sessions import states as st
from app.modules.validation.scoring import compute_score

CHECKS = [
    {"id": "a", "weight": 2, "required": True, "pass_message": "ok-a", "fail_message": "no-a"},
    {"id": "b", "weight": 1, "required": True, "pass_message": "ok-b", "fail_message": "no-b"},
    {"id": "c", "weight": 1, "required": False, "pass_message": "ok-c", "fail_message": "no-c"},
]
CONTENT = Path(__file__).resolve().parents[3] / "content" / "labs"


def test_score_all_passed() -> None:
    score, passed, public = compute_score(CHECKS, {"a": True, "b": True, "c": True})
    assert score == Decimal("100.00") and passed
    assert [p["message"] for p in public] == ["ok-a", "ok-b", "ok-c"]


def test_score_weighted_formula() -> None:
    score, passed, _ = compute_score(CHECKS, {"a": True, "b": False, "c": True})
    assert score == Decimal("75.00")  # 100 * (2+1) / 4
    assert not passed  # required b провален


def test_optional_check_failure_still_passes() -> None:
    score, passed, _ = compute_score(CHECKS, {"a": True, "b": True, "c": False})
    assert score == Decimal("75.00") and passed


def test_missing_results_are_failures() -> None:
    score, passed, _ = compute_score(CHECKS, {})
    assert score == Decimal("0.00") and not passed


def test_state_machine_rules() -> None:
    assert st.can_transition(st.PROVISIONING, st.READY)
    assert st.can_transition(st.RUNNING, st.VALIDATING)
    assert st.can_transition(st.VALIDATING, st.RUNNING) and st.can_transition(st.VALIDATING, st.COMPLETED)
    assert st.can_transition(st.STOPPING, st.STOPPED)
    for terminal in (st.COMPLETED, st.STOPPED, st.FAILED, st.EXPIRED):
        assert not any(st.can_transition(terminal, dst) for dst in st.TRANSITIONS)
    assert not st.can_transition(st.READY, st.COMPLETED)
    for active in st.ACTIVE:
        assert st.can_transition(active, st.EXPIRED) and st.can_transition(active, st.STOPPING)


def _manifest(**over: object) -> dict[str, object]:
    base: dict[str, object] = dict(
        schema_version=1, id="linux-999", version=1, title="t", mode="practice", difficulty="junior", estimated_minutes=5,
        description="d", objectives=["o"], task="t", runtime={"type": "container", "image": "ubuntu-basic"},
        validation={"checks": [{"id": "check_x", "title": "t", "pass_message": "p", "fail_message": "f"}]}, reward={"base_xp": 10},
    )
    base.update(over)
    return base


def test_manifest_valid() -> None:
    assert LabManifest.model_validate(_manifest()).runtime.image == "ubuntu-basic"


def test_manifest_rejects_digest_placeholder_and_registry_refs() -> None:
    with pytest.raises(ValidationError):
        RuntimeSpec(image="linuxdojo/ubuntu-basic@sha256:REPLACE_WITH_REAL_DIGEST")
    with pytest.raises(ValidationError):
        LabManifest.model_validate(_manifest(runtime={"type": "container", "image": "evil.example/registry:latest"}))


def test_manifest_rejects_unknown_fields_and_bad_values() -> None:
    with pytest.raises(ValidationError):
        LabManifest.model_validate(_manifest(privileged=True))
    with pytest.raises(ValidationError):
        LabManifest.model_validate(_manifest(mode="exam"))
    with pytest.raises(ValidationError):
        LabManifest.model_validate(_manifest(validation={"checks": []}))


@pytest.mark.parametrize("bad", ["/etc", "/root/x", "/var/log/../etc", "/srv/", "relative/path", "/usr/bin/x"])
def test_writable_dirs_allowlist(bad: str) -> None:
    with pytest.raises(ValidationError):
        RuntimeSpec(image="ubuntu-basic", writable_dirs=[bad])


def test_load_lab_requires_hints_and_matching_id(tmp_path: Path) -> None:
    with pytest.raises(ContentError):
        load_lab(tmp_path)
    assert load_lab(CONTENT / "linux-001").manifest.id == "linux-001"


def test_content_hash_is_platform_independent_and_ignores_tests(tmp_path: Path) -> None:
    """Хэш версии не зависит от ОС (порядок файлов — побайтовый по POSIX-пути; CRLF нормализуется; tests/ не входит)."""
    from upskill_content.loader import _tree_hash

    (tmp_path / "README.md").write_bytes(b"x\r\n")
    (tmp_path / "checks").mkdir()
    (tmp_path / "checks" / "validate.sh").write_bytes(b"y\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "solution.sh").write_bytes(b"secret solution")
    h1 = _tree_hash(tmp_path)
    (tmp_path / "tests" / "solution.sh").write_bytes(b"changed")
    (tmp_path / "README.md").write_bytes(b"x\n")
    assert _tree_hash(tmp_path) == h1
    # зафиксированное значение для порядка «README.md» перед «checks/…» (как на Linux), одинаковое на всех ОС
    import hashlib

    expected = hashlib.sha256(b"README.md\0x\n\0checks/validate.sh\0y\n\0").hexdigest()
    assert h1 == expected
