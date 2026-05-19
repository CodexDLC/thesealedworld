from __future__ import annotations

import uuid  # noqa: TC003
from datetime import date, datetime  # noqa: TC003

from sqlalchemy import Date, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.frontend.core.database import Base


class PlayerDailyActivity(Base):
    __tablename__ = "player_daily_activity"
    __table_args__ = (
        UniqueConstraint("player_id", "date", name="uq_player_daily_activity"),
        {"schema": "site"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
