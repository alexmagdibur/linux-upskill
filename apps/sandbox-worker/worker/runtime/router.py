"""RuntimeRouter: один интерфейс RuntimeAdapter поверх нескольких runtime (Docker-контейнеры и LXD-машины).

Тип runtime при создании берётся из манифеста лаборатории; для уже существующей сессии адаптер определяется по
имени runtime_ref (запоминается при создании, при промахе — опросом адаптеров). `destroy` идемпотентно вызывается у всех.
"""

from __future__ import annotations

import asyncio

from .base import ImageRef, PTYStream, ResourceLimits, RuntimeAdapter, RuntimeError_, RuntimeInfo, ValidationContext


class RuntimeRouter(RuntimeAdapter):
    def __init__(self, adapters: dict[str, RuntimeAdapter]) -> None:
        self._adapters = adapters  # {"container": DockerAdapter, "lxd": LXDAdapter}
        self._by_ref: dict[str, RuntimeAdapter] = {}

    def has(self, runtime_type: str) -> bool:
        return runtime_type in self._adapters

    def remember(self, ref: str, adapter: RuntimeAdapter) -> None:
        self._by_ref[ref] = adapter

    def for_type(self, runtime_type: str) -> RuntimeAdapter:
        adapter = self._adapters.get(runtime_type)
        if adapter is None:
            raise RuntimeError_("RUNTIME_DISABLED", f"runtime '{runtime_type}' не настроен на этом worker")
        return adapter

    async def _resolve(self, ref: str) -> RuntimeAdapter:
        cached = self._by_ref.get(ref)
        if cached is not None:
            return cached
        for adapter in self._adapters.values():
            if await adapter.is_alive(ref):
                self._by_ref[ref] = adapter
                return adapter
        raise RuntimeError_("RUNTIME_GONE")

    async def create(
        self, session_id: str, image: ImageRef, limits: ResourceLimits, writable_dirs: list[str],
        setup_script: bytes, setup_timeout: int, *, runtime_type: str = "container",
    ) -> str:
        adapter = self.for_type(runtime_type)
        ref = await adapter.create(session_id, image, limits, writable_dirs, setup_script, setup_timeout)
        self._by_ref[ref] = adapter
        return ref

    async def attach_terminal(self, runtime_ref: str) -> PTYStream:
        return await (await self._resolve(runtime_ref)).attach_terminal(runtime_ref)

    async def resize_terminal(self, runtime_ref: str, cols: int, rows: int) -> None:
        await (await self._resolve(runtime_ref)).resize_terminal(runtime_ref, cols, rows)

    async def snapshot_or_inspect(self, runtime_ref: str, validator_script: bytes, timeout: int) -> ValidationContext:
        return await (await self._resolve(runtime_ref)).snapshot_or_inspect(runtime_ref, validator_script, timeout)

    async def exercise(self, runtime_ref: str, script: bytes, timeout: int) -> ValidationContext:
        return await (await self._resolve(runtime_ref)).exercise(runtime_ref, script, timeout)

    async def reboot(self, runtime_ref: str) -> None:
        await (await self._resolve(runtime_ref)).reboot(runtime_ref)

    async def destroy(self, runtime_ref: str) -> None:
        self._by_ref.pop(runtime_ref, None)
        await asyncio.gather(*(a.destroy(runtime_ref) for a in self._adapters.values()))

    async def is_alive(self, runtime_ref: str) -> bool:
        results = await asyncio.gather(*(a.is_alive(runtime_ref) for a in self._adapters.values()))
        return any(results)

    async def list_runtimes(self) -> list[RuntimeInfo]:
        lists = await asyncio.gather(*(a.list_runtimes() for a in self._adapters.values()))
        return [r for lst in lists for r in lst]

    async def gc(self) -> None:
        for adapter in self._adapters.values():
            gc = getattr(adapter, "gc_networks", None)
            if gc is not None:
                await gc()

    def close(self) -> None:
        for adapter in self._adapters.values():
            close = getattr(adapter, "close", None)
            if close is not None:
                close()
