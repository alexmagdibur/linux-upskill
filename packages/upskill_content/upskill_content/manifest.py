"""Строгая схема manifest.yaml (schema_version: 1)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Mode = Literal["learn", "practice", "incident"]
Difficulty = Literal["beginner", "junior", "middle"]

_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,40}$")
_CHECK_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
_ALLOWED_WRITABLE_PREFIXES = ("/var/log/", "/srv/", "/opt/", "/var/lib/", "/etc/")
MAX_WRITABLE_DIRS = 4


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuntimeSpec(_Strict):
    type: Literal["container"] = "container"
    # логическое имя образа из content/images.lock.json (не ссылка на реестр)
    image: str = Field(pattern=r"^[a-z][a-z0-9-]{1,40}$")
    timeout_seconds: int = Field(default=1800, ge=60, le=3600)
    # дополнительные записываемые tmpfs-каталоги (rootfs контейнера read-only)
    writable_dirs: list[str] = Field(default_factory=list)

    @field_validator("image")
    @classmethod
    def _no_placeholder(cls, v: str) -> str:
        if "REPLACE_WITH" in v.upper():
            raise ValueError("image содержит placeholder")
        return v

    @field_validator("writable_dirs")
    @classmethod
    def _check_dirs(cls, v: list[str]) -> list[str]:
        if len(v) > MAX_WRITABLE_DIRS:
            raise ValueError(f"не более {MAX_WRITABLE_DIRS} writable_dirs")
        for d in v:
            parts = d.split("/")
            if (
                not d.startswith(_ALLOWED_WRITABLE_PREFIXES)
                or ".." in parts
                or d.endswith("/")
                or "//" in d
                or len(parts) < 3
            ):
                raise ValueError(f"недопустимый writable_dir: {d}")
        return v


class SetupSpec(_Strict):
    script: str = "setup/prepare.sh"


class CheckSpec(_Strict):
    id: str
    title: str
    pass_message: str
    fail_message: str
    weight: float = Field(default=1.0, gt=0)
    required: bool = True

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not _CHECK_ID_RE.match(v):
            raise ValueError("недопустимый id проверки")
        return v


class ValidationSpec(_Strict):
    type: Literal["script"] = "script"
    script: str = "checks/validate.sh"
    # необязательный скрипт, который запускается ОТ ИМЕНИ student перед проверкой (например, запуск написанного
    # пользователем скрипта); пользовательский код никогда не исполняется в контексте validator
    exercise_script: str | None = None
    timeout_seconds: int = Field(default=15, ge=1, le=60)
    checks: list[CheckSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> ValidationSpec:
        ids = [c.id for c in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("дублирующиеся id проверок")
        return self


class RewardSpec(_Strict):
    base_xp: int = Field(ge=0, le=1000)


class LabManifest(_Strict):
    schema_version: Literal[1]
    id: str
    version: int = Field(ge=1)
    title: str
    mode: Mode
    difficulty: Difficulty
    estimated_minutes: int = Field(ge=1, le=120)
    description: str
    skills: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(min_length=1)
    task: str  # markdown-текст задания для Workspace
    runtime: RuntimeSpec
    setup: SetupSpec = SetupSpec()
    validation: ValidationSpec
    hints: list[str] = Field(default_factory=list)
    reward: RewardSpec

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("недопустимый id лаборатории")
        return v
