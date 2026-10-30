"""Фоновая уборка: TTL, idle, зависшие PROVISIONING/VALIDATING/STOPPING. Источник истины — PostgreSQL."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from prometheus_client import Gauge
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.session import sessionmaker
from app.modules.validation.models import ValidationAttempt

from . import service
from . import states as st
from .models import LabSession

log = logging.getLogger("app.lifecycle")
SESSIONS_GAUGE = Gauge("upskill_sessions", "Сессии по статусам", ["status"])
STOPPING_GRACE = timedelta(seconds=60)


async def sweep_once(db: AsyncSession, settings: Settings, at: datetime | None = None) -> dict[str, int]:
    now = at or service.now()
    to_destroy: list[uuid.UUID] = []
    counts = {"expired": 0, "idle": 0, "provision_timeout": 0, "validation_timeout": 0, "stopped": 0}

    # 1) истёк TTL
    ids = (
        await db.execute(
            update(LabSession)
            .where(LabSession.status.in_(list(st.ACTIVE)), LabSession.expires_at < now)
            .values(status=st.EXPIRED, finished_at=now, error_code="TTL_EXPIRED")
            .returning(LabSession.id)
        )
    ).scalars().all()
    to_destroy += ids
    counts["expired"] = len(ids)

    # 2) простой без активности терминала
    idle_before = now - timedelta(seconds=settings.sandbox_idle_seconds)
    last = func.coalesce(LabSession.last_activity_at, LabSession.started_at, LabSession.created_at)
    ids = (
        await db.execute(
            update(LabSession)
            .where(LabSession.status.in_([st.READY, st.RUNNING]), last < idle_before)
            .values(status=st.EXPIRED, finished_at=now, error_code="IDLE_TIMEOUT")
            .returning(LabSession.id)
        )
    ).scalars().all()
    to_destroy += ids
    counts["idle"] = len(ids)

    # 3) provisioning завис
    prov_before = now - timedelta(seconds=settings.provisioning_timeout_seconds)
    ids = (
        await db.execute(
            update(LabSession)
            .where(LabSession.status.in_([st.CREATED, st.PROVISIONING]), LabSession.created_at < prov_before)
            .values(status=st.FAILED, finished_at=now, error_code="PROVISION_TIMEOUT")
            .returning(LabSession.id)
        )
    ).scalars().all()
    to_destroy += ids
    counts["provision_timeout"] = len(ids)

    # 4) проверка зависла — вернуть сессию в RUNNING, попытку пометить ошибкой
    val_before = now - timedelta(seconds=settings.validating_timeout_seconds)
    stuck = (
        await db.execute(
            update(ValidationAttempt)
            .where(ValidationAttempt.status == "PENDING", ValidationAttempt.created_at < val_before)
            .values(status="ERROR", error_code="VALIDATION_TIMEOUT", finished_at=now)
            .returning(ValidationAttempt.session_id)
        )
    ).scalars().all()
    if stuck:
        await db.execute(
            update(LabSession).where(LabSession.id.in_(stuck), LabSession.status == st.VALIDATING).values(status=st.RUNNING)
        )
    counts["validation_timeout"] = len(stuck)

    # 5) cleanup не подтвердился — считаем остановленной (reconciler worker добьёт остатки)
    ids = (
        await db.execute(
            update(LabSession)
            .where(LabSession.status == st.STOPPING, LabSession.finished_at < now - STOPPING_GRACE)
            .values(status=st.STOPPED)
            .returning(LabSession.id)
        )
    ).scalars().all()
    to_destroy += ids
    counts["stopped"] = len(ids)

    await db.commit()
    for sid in to_destroy:
        await service.enqueue_destroy(sid)
    return counts


async def refresh_gauges(db: AsyncSession) -> None:
    rows = dict((await db.execute(select(LabSession.status, func.count()).group_by(LabSession.status))).all())
    for status in (*st.ACTIVE, *st.TERMINAL, st.STOPPING):
        SESSIONS_GAUGE.labels(status).set(rows.get(status, 0))


async def sweeper_loop(settings: Settings) -> None:
    while True:
        try:
            async with sessionmaker()() as db:
                counts = await sweep_once(db, settings)
                await refresh_gauges(db)
            if any(counts.values()):
                log.info("sweep", extra={"component": "lifecycle", **counts})
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("sweep failed", extra={"component": "lifecycle"})
        await asyncio.sleep(settings.sweeper_interval_seconds)
