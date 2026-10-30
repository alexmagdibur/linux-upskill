from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ts_col, uuid_pk


class ValidationAttempt(Base):
    __tablename__ = "validation_attempts"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # PENDING | FINISHED | ERROR
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    passed: Mapped[bool | None] = mapped_column(Boolean)
    checks_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(Text)
    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    created_at: Mapped[datetime] = ts_col()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_validation_attempts_session_id", "session_id"),
        # не более одной незавершённой проверки на сессию
        Index("ux_validation_attempts_one_pending", "session_id", unique=True, postgresql_where=text("status = 'PENDING'")),
    )
