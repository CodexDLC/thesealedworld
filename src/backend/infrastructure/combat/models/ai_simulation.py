from __future__ import annotations

import datetime as dt  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.
from typing import Any

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, SchemaVersionMixin


class CombatAiSimulationRun(Base, SchemaVersionMixin):
    __tablename__ = "combat_ai_simulation_runs"
    __table_args__ = (
        Index("ix_combat_ai_simulation_runs_created_at", "created_at"),
        Index("ix_combat_ai_simulation_runs_scenario_status", "scenario_key", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    scenario_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed", index=True)
    policy_ref: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    rounds_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    winner: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    telemetry: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    report_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
