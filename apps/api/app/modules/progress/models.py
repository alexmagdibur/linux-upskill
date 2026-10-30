from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, PrimaryKeyConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ts_col, uuid_pk


class UserProgress(Base):
    __tablename__ = "user_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lab_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    best_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default="0", default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)

    __table_args__ = (PrimaryKeyConstraint("user_id", "lab_id", name="pk_user_progress"),)


class XpTransaction(Base):
    __tablename__ = "xp_transactions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = ts_col()

    __table_args__ = (
        UniqueConstraint("user_id", "session_id", "reason"),
        # XP за конкретное достижение (например, первое прохождение лаборатории) выдаётся один раз на пользователя
        UniqueConstraint("user_id", "reason", name="ux_xp_user_reason"),
        Index("ix_xp_transactions_user_id", "user_id"),
    )
