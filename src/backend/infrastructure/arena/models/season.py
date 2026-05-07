from __future__ import annotations

import datetime as dt  # noqa: TC003

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, TimestampMixin


class ArenaSeason(Base, TimestampMixin):
    __tablename__ = "arena_seasons"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    reward_pool_total: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
