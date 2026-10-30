from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ts_col, uuid_pk


class LabSession(Base):
    __tablename__ = "lab_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lab_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lab_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    runtime_ref: Mapped[str | None] = mapped_column(Text)  # внутренний идентификатор, клиенту не отдаётся
    created_at: Mapped[datetime] = ts_col()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(Text)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)

    __table_args__ = (
        Index("ix_lab_sessions_status_expires_at", "status", "expires_at"),
        Index("ix_lab_sessions_user_id_created_at", "user_id", "created_at"),
        Index("ix_lab_sessions_lab_version_id", "lab_version_id"),
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = ts_col()

    __table_args__ = (UniqueConstraint("user_id", "key"),)
