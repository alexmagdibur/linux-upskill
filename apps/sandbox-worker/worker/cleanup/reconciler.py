"""Reconciler: TTL по меткам, удаление осиротевших контейнеров, поиск пропавших runtime."""

from __future__ import annotations

import asyncio
import logging
import time

from worker.api_client import ApiClient
from worker.runtime.base import RuntimeAdapter
from worker.terminal.hub import TerminalHub

log = logging.getLogger("worker.reconciler")

ORPHAN_GRACE_SECONDS = 45


async def reconcile_once(adapter: RuntimeAdapter, api: ApiClient, hub: TerminalHub) -> dict[str, int]:
    now = time.time()
    runtimes = await adapter.list_runtimes()
    removed_expired = removed_orphans = missing = 0

    # 1) TTL — работает даже если API недоступен
    alive = []
    for rt in runtimes:
        if rt.expires_at and rt.expires_at < now:
            hub.drop(rt.runtime_ref)
            await adapter.destroy(rt.runtime_ref)
            removed_expired += 1
        else:
            alive.append(rt)

    # 2) сверка с API (источник истины — PostgreSQL)
    try:
        active = await api.active_runtimes()
    except Exception:  # noqa: BLE001
        log.warning("api unreachable during reconcile", extra={"component": "reconciler"})
        return {"expired": removed_expired, "orphans": 0, "missing": 0}

    present = {rt.session_id for rt in alive}
    for rt in alive:
        if rt.session_id not in active and now - rt.created_at > ORPHAN_GRACE_SECONDS:
            hub.drop(rt.runtime_ref)
            await adapter.destroy(rt.runtime_ref)
            removed_orphans += 1
    for session_id, status in active.items():
        if status in ("READY", "RUNNING") and session_id not in present:
            await api.mark_runtime_missing(session_id)
            missing += 1

    if removed_expired or removed_orphans or missing:
        log.info(
            "reconcile",
            extra={"component": "reconciler", "expired": removed_expired, "orphans": removed_orphans, "missing": missing},
        )
    return {"expired": removed_expired, "orphans": removed_orphans, "missing": missing}


async def reconcile_loop(adapter: RuntimeAdapter, api: ApiClient, hub: TerminalHub, interval: int) -> None:
    while True:
        try:
            await reconcile_once(adapter, api, hub)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("reconcile failed", extra={"component": "reconciler"})
        await asyncio.sleep(interval)
