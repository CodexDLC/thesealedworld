from __future__ import annotations

import datetime as dt  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, SchemaVersionMixin


class CombatExchangeFact(Base, SchemaVersionMixin):
    __tablename__ = "combat_exchange_facts"
    __table_args__ = (
        Index("ix_combat_exchange_facts_combat_turn_seq", "combat_id", "turn", "seq"),
        Index("ix_combat_exchange_facts_finished_at", "finished_at"),
        Index("ix_combat_exchange_facts_weapon", "weapon_base_id", "weapon_tier"),
        Index("ix_combat_exchange_facts_armor", "armor_class", "armor_tier"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    combat_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    turn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wave: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    battle_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    location_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    target_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_combatant_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    target_combatant_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    action_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    feint_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    is_crit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_counter: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_extra_strike: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weapon_base_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    weapon_tier: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weapon_power: Mapped[float | None] = mapped_column(Float, nullable=True)
    armor_class: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    armor_tier: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_damage: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_damage: Mapped[float | None] = mapped_column(Float, nullable=True)
    armor_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    armor_effective: Mapped[float | None] = mapped_column(Float, nullable=True)
    armor_ignored: Mapped[float | None] = mapped_column(Float, nullable=True)
    phys_res_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    phys_res_effective: Mapped[float | None] = mapped_column(Float, nullable=True)
    physical_suppression: Mapped[float | None] = mapped_column(Float, nullable=True)
    mongo_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trace_status: Mapped[str] = mapped_column(String(32), default="mongo", nullable=False, index=True)


class CombatBalanceRollup(Base, SchemaVersionMixin):
    __tablename__ = "combat_balance_rollups"
    __table_args__ = (
        UniqueConstraint(
            "bucket_start",
            "bucket_grain",
            "metric_key",
            "dimensions_hash",
            "aggregate_version",
            name="uq_combat_balance_rollup_bucket_metric_dims_version",
        ),
        Index("ix_combat_balance_rollups_bucket", "bucket_start", "bucket_grain"),
        Index("ix_combat_balance_rollups_metric", "metric_key"),
        Index("ix_combat_balance_rollups_aggregate_version", "aggregate_version"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bucket_start: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bucket_grain: Mapped[str] = mapped_column(String(16), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False)
    dimensions_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    counters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
