"""RuntimeAdapter — граница между оркестрацией и конкретным runtime (Docker сегодня, VM завтра)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResourceLimits:
    cpu: float = 0.5
    memory: str = "256m"
    pids: int = 128
    home_size_mb: int = 48
    tmp_size_mb: int = 16
    ttl_seconds: int = 1800


@dataclass(frozen=True)
class ImageRef:
    tag: str
    image_id: str  # content-addressed sha256:... из images.lock.json


@dataclass
class ValidationContext:
    stdout: str
    exit_code: int
    timed_out: bool = False


@dataclass
class RuntimeInfo:
    runtime_ref: str
    session_id: str
    expires_at: float
    created_at: float
    running: bool
    extra: dict[str, str] = field(default_factory=dict)


class PTYStream(ABC):
    """Двунаправленный поток байтов интерактивного shell."""

    @abstractmethod
    def read_blocking(self) -> bytes:
        """Блокирующее чтение (вызывается из потока). b'' означает EOF."""

    @abstractmethod
    def write_blocking(self, data: bytes) -> None: ...

    @abstractmethod
    def resize_blocking(self, cols: int, rows: int) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class RuntimeError_(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


class RuntimeAdapter(ABC):
    @abstractmethod
    async def create(
        self,
        session_id: str,
        image: ImageRef,
        limits: ResourceLimits,
        writable_dirs: list[str],
        setup_script: bytes,
        setup_timeout: int,
    ) -> str:
        """Создать изолированное окружение, выполнить доверенный setup, вернуть runtime_ref."""

    @abstractmethod
    async def attach_terminal(self, runtime_ref: str) -> PTYStream: ...

    @abstractmethod
    async def resize_terminal(self, runtime_ref: str, cols: int, rows: int) -> None: ...

    @abstractmethod
    async def snapshot_or_inspect(
        self, runtime_ref: str, validator_script: bytes, timeout: int
    ) -> ValidationContext:
        """Независимо от пользовательского shell выполнить доверенный проверяющий скрипт."""

    @abstractmethod
    async def exercise(self, runtime_ref: str, script: bytes, timeout: int) -> ValidationContext:
        """Выполнить доверенный сценарий-«прогон» от имени ученика (вывод игнорируется проверкой)."""

    async def reboot(self, runtime_ref: str) -> None:
        """Перезагрузить учебную машину и дождаться загрузки (только runtime с настоящим init)."""
        raise RuntimeError_("REBOOT_UNSUPPORTED", "этот runtime не поддерживает перезагрузку")

    @abstractmethod
    async def destroy(self, runtime_ref: str) -> None: ...

    @abstractmethod
    async def is_alive(self, runtime_ref: str) -> bool: ...

    @abstractmethod
    async def list_runtimes(self) -> list[RuntimeInfo]: ...
