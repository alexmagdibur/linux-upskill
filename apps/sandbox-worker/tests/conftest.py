from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import docker
import pytest
import pytest_asyncio
from upskill_content import load_image_lock

from worker.runtime.base import ImageRef, ResourceLimits
from worker.runtime.docker import LABEL_MANAGED, DockerAdapter

ROOT = Path(__file__).resolve().parents[3]
CONTENT = ROOT / "content"


def docker_available() -> bool:
    try:
        docker.from_env().ping()
        return True
    except Exception:  # noqa: BLE001
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if docker_available():
        return
    skip = pytest.mark.skip(reason="Docker daemon недоступен: интеграционные тесты песочницы пропущены")
    for item in items:
        item.add_marker(skip)


@pytest.fixture(scope="session")
def image() -> ImageRef:
    entry = load_image_lock(CONTENT)["ubuntu-basic"]
    return ImageRef(entry["tag"], entry["id"])


@pytest.fixture(scope="session")
def adapter() -> DockerAdapter:
    return DockerAdapter()


@pytest_asyncio.fixture
async def sandbox(adapter: DockerAdapter, image: ImageRef) -> AsyncIterator[str]:
    sid = str(uuid.uuid4())
    ref = await adapter.create(sid, image, ResourceLimits(), ["/var/log/app"], b"mkdir -p ~/w && echo seed > ~/w/f.txt\n", 20)
    yield ref
    await adapter.destroy(ref)


def run_as_student(adapter: DockerAdapter, ref: str, script: str, timeout: int = 20) -> tuple[int, str]:
    """Выполнить произвольный скрипт внутри песочницы от имени student (как это сделал бы пользователь)."""
    container = adapter._client.containers.get(ref)  # noqa: SLF001
    code, out = adapter._run_script(container, script.encode(), "student", "/home/student", timeout)  # noqa: SLF001
    return code, out.decode(errors="replace")


@pytest.fixture(autouse=True, scope="session")
def no_leftovers():
    yield
    if docker_available():
        client = docker.from_env()
        leaked = client.containers.list(all=True, filters={"label": f"{LABEL_MANAGED}=true"})
        for c in leaked:
            c.remove(force=True)
        assert not leaked, f"тесты оставили контейнеры: {[c.name for c in leaked]}"
