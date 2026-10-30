"""Бизнес-логика worker: provision / validate / destroy над RuntimeAdapter."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from upskill_content import ContentError, LoadedLab, load_image_lock, load_lab

from .api_client import ApiClient
from .config import WorkerSettings
from .runtime.base import ImageRef, ResourceLimits, RuntimeAdapter, RuntimeError_
from .terminal.hub import TerminalHub
from .validation.runner import run_checks

log = logging.getLogger("worker.service")

_SAFE_SLUG = re.compile(r"^[a-z][a-z0-9-]{2,40}$")
_SAFE_UUID = re.compile(r"^[0-9a-f-]{36}$")


def runtime_ref_for(session_id: str) -> str:
    if not _SAFE_UUID.match(session_id):
        raise ValueError("bad session id")
    return f"upskill-{session_id}"


class WorkerService:
    def __init__(self, settings: WorkerSettings, adapter: RuntimeAdapter, api: ApiClient, hub: TerminalHub) -> None:
        self.settings = settings
        self.adapter = adapter
        self.api = api
        self.hub = hub
        self._slots = asyncio.Semaphore(settings.sandbox_max_concurrent)
        self.stats = {"provisioned": 0, "provision_failed": 0, "validations": 0, "destroyed": 0}

    # ------------------------------------------------------------------ content
    def _load(self, slug: str, version: int, content_hash: str) -> LoadedLab:
        if not _SAFE_SLUG.match(slug):
            raise RuntimeError_("BAD_LAB")
        try:
            lab = load_lab(self.settings.content_dir / "labs" / slug)
        except ContentError as exc:
            log.error("content error", extra={"error_code": "CONTENT_INVALID"})
            raise RuntimeError_("CONTENT_INVALID", str(exc)) from exc
        # сессия привязана к неизменяемой версии: worker держит только текущую версию контента
        if lab.manifest.version != version or lab.content_hash != content_hash:
            raise RuntimeError_("LAB_VERSION_UNAVAILABLE")
        return lab

    def _image(self, logical: str, runtime_type: str = "container") -> ImageRef:
        lock = load_image_lock(self.settings.content_dir)
        entry = lock.get(logical)
        kind = "lxd" if entry and entry.get("runtime") == "lxd" else "container"
        if not entry or kind != runtime_type:  # образ другого runtime подсунуть нельзя
            raise RuntimeError_("IMAGE_NOT_ALLOWED")
        return ImageRef(entry["tag"], entry["id"])

    # --------------------------------------------------------------- operations
    async def provision(self, job: dict[str, Any]) -> None:
        session_id = job["session_id"]
        lab = self._load(job["lab_slug"], int(job["version"]), job["content_hash"])
        runtime = lab.manifest.runtime
        assert runtime is not None
        image = self._image(runtime.image, runtime.type)
        s = self.settings
        limits = ResourceLimits(
            cpu=s.sandbox_cpu_limit,
            memory=s.sandbox_memory_limit,
            pids=s.sandbox_pids_limit,
            home_size_mb=s.sandbox_home_size_mb,
            tmp_size_mb=s.sandbox_tmp_size_mb,
            ttl_seconds=min(int(job.get("ttl_seconds", s.sandbox_ttl_seconds)), lab.manifest.runtime.timeout_seconds),
        )
        async with self._slots:
            adapter = self.adapter.for_type(runtime.type) if hasattr(self.adapter, "for_type") else self.adapter
            setup_timeout = 90 if runtime.type == "lxd" else 30  # машины с systemd готовятся дольше контейнера
            ref = await adapter.create(session_id, image, limits, runtime.writable_dirs, lab.setup_script, setup_timeout)
            if hasattr(self.adapter, "remember"):
                self.adapter.remember(ref, adapter)
        accepted = await self.api.provisioned(session_id, ref)
        if not accepted:
            await self.destroy({"session_id": session_id})
            return
        self.stats["provisioned"] += 1

    async def destroy(self, job: dict[str, Any]) -> None:
        ref = runtime_ref_for(job["session_id"])
        self.hub.drop(ref)
        await self.adapter.destroy(ref)
        self.stats["destroyed"] += 1
        try:
            await self.api.destroyed(job["session_id"])
        except Exception:  # noqa: BLE001 — API сам переведёт STOPPING -> STOPPED по таймауту
            log.warning("destroyed callback failed", extra={"session_id": job["session_id"]})

    async def validate(self, job: dict[str, Any]) -> None:
        lab = self._load(job["lab_slug"], int(job["version"]), job["content_hash"])
        ref = runtime_ref_for(job["session_id"])
        declared = [c.id for c in lab.manifest.validation.checks]
        try:
            run = await run_checks(self.adapter, ref, lab)
        except RuntimeError_ as exc:
            await self.api.validation_result(job["attempt_id"], dict.fromkeys(declared, False), exc.code)
            return
        if run.timed_out:
            await self.api.validation_result(job["attempt_id"], dict.fromkeys(declared, False), "VALIDATION_TIMEOUT")
            return
        self.stats["validations"] += 1
        await self.api.validation_result(job["attempt_id"], run.results, None)

    async def on_job_failed(self, job: dict[str, Any], error_code: str) -> None:
        """Вызывается, когда задача исчерпала попытки."""
        if job["type"] == "provision":
            self.stats["provision_failed"] += 1
            await self.api.provision_failed(job["session_id"], error_code)
        elif job["type"] == "validate":
            await self.api.validation_result(job["attempt_id"], {}, error_code)
