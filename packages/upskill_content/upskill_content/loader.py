"""Загрузка доверенного контента с диска: манифесты, скрипты, подсказки, курсы."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .manifest import LabManifest


class ContentError(Exception):
    pass


@dataclass(frozen=True)
class LoadedLab:
    manifest: LabManifest
    directory: Path
    content_hash: str
    setup_script: bytes
    validate_script: bytes
    exercise_script: bytes | None = None


class ModuleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    title: str
    description: str
    labs: list[str]


class CourseSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    title: str
    description: str
    modules: list[ModuleSpec]


def _tree_hash(directory: Path) -> str:
    h = hashlib.sha256()
    # порядок — по POSIX-пути побайтово: сортировка Path зависит от ОС (на Windows регистронезависимая)
    entries = ((p.relative_to(directory).as_posix(), p) for p in directory.rglob("*") if p.is_file())
    files = sorted(entries, key=lambda t: t[0].encode())
    for rel, path in files:
        if rel.startswith("tests/"):  # тесты не входят в неизменяемую версию
            continue
        h.update(rel.encode())
        h.update(b"\0")
        h.update(path.read_bytes().replace(b"\r\n", b"\n"))
        h.update(b"\0")
    return h.hexdigest()


def _safe_file(base: Path, rel: str) -> Path:
    path = (base / rel).resolve()
    if base.resolve() not in path.parents or not path.is_file():
        raise ContentError(f"{base.name}: файл {rel} не найден или вне каталога лаборатории")
    return path


def load_lab(lab_dir: Path) -> LoadedLab:
    manifest_path = lab_dir / "manifest.yaml"
    if not manifest_path.is_file():
        raise ContentError(f"{lab_dir.name}: нет manifest.yaml")
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest = LabManifest.model_validate(raw)
    except (yaml.YAMLError, ValidationError) as exc:
        raise ContentError(f"{lab_dir.name}: некорректный манифест: {exc}") from exc
    if manifest.id != lab_dir.name:
        raise ContentError(f"{lab_dir.name}: id в манифесте ({manifest.id}) не совпадает с именем каталога")

    hints_path = lab_dir / "hints" / "hints.yaml"
    hints = list(manifest.hints)
    if hints_path.is_file():
        data = yaml.safe_load(hints_path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise ContentError(f"{lab_dir.name}: hints.yaml должен быть списком строк")
        hints = data
    if not 1 <= len(hints) <= 3:
        raise ContentError(f"{lab_dir.name}: нужно 1–3 подсказки, найдено {len(hints)}")
    manifest = manifest.model_copy(update={"hints": hints})

    setup = _safe_file(lab_dir, manifest.setup.script).read_bytes().replace(b"\r\n", b"\n")
    validate = _safe_file(lab_dir, manifest.validation.script).read_bytes().replace(b"\r\n", b"\n")
    exercise = None
    if manifest.validation.exercise_script:
        exercise = _safe_file(lab_dir, manifest.validation.exercise_script).read_bytes().replace(b"\r\n", b"\n")
    return LoadedLab(manifest, lab_dir, _tree_hash(lab_dir), setup, validate, exercise)


def load_course(content_root: Path, slug: str = "linux-upskill") -> CourseSpec:
    path = content_root / "courses" / slug / "course.yaml"
    try:
        return CourseSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ContentError(f"course {slug}: {exc}") from exc


def load_image_lock(content_root: Path) -> dict[str, dict[str, str]]:
    """Allowlist образов: логическое имя -> {tag, id}. Генерируется `make images`."""
    path = content_root / "images.lock.json"
    if not path.is_file():
        raise ContentError("content/images.lock.json не найден: выполните `make images`")
    data = json.loads(path.read_text(encoding="utf-8"))
    for name, entry in data.items():
        if not str(entry.get("id", "")).startswith("sha256:") or "REPLACE" in entry["id"].upper():
            raise ContentError(f"images.lock.json: некорректный id для {name}")
    return data
