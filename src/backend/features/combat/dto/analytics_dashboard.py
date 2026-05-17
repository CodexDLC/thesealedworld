from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Pydantic resolves response annotations at runtime.
from typing import Any

from pydantic import BaseModel, Field


class CombatAnalyticsFilterValueDTO(BaseModel):
    value: Any
    source_count: int = 0


class CombatAnalyticsFiltersDTO(BaseModel):
    aggregate_version: int | None = None
    dimensions: dict[str, list[CombatAnalyticsFilterValueDTO]] = Field(default_factory=dict)
    metric_keys: list[str] = Field(default_factory=list)
    bucket_grains: list[str] = Field(default_factory=list)
    bucket_start_min: datetime | None = None
    bucket_start_max: datetime | None = None


class CombatAnalyticsRollupPointDTO(BaseModel):
    bucket_start: datetime
    bucket_grain: str
    metric_key: str
    dimensions_hash: str
    dimensions: dict[str, Any] = Field(default_factory=dict)
    counters: dict[str, Any] = Field(default_factory=dict)
    source_count: int = 0
    aggregate_version: int
    schema_version: int = 1


class CombatAnalyticsRollupResponseDTO(BaseModel):
    aggregate_version: int | None = None
    bucket_grain: str
    metric_key: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    rows: list[CombatAnalyticsRollupPointDTO] = Field(default_factory=list)


class CombatAnalyticsExchangeFactDTO(BaseModel):
    combat_id: str
    turn: int
    wave: int
    seq: int
    finished_at: datetime | None = None
    battle_type: str | None = None
    location_id: str | None = None
    source_actor_id: str | None = None
    target_actor_id: str | None = None
    action_id: str | None = None
    feint_id: str | None = None
    outcome: str | None = None
    source_type: str | None = None
    is_crit: bool = False
    is_counter: bool = False
    is_extra_strike: bool = False
    weapon_base_id: str | None = None
    weapon_tier: int | None = None
    weapon_power: float | None = None
    armor_class: str | None = None
    armor_tier: int | None = None
    raw_damage: float | None = None
    final_damage: float | None = None
    armor_raw: float | None = None
    armor_effective: float | None = None
    armor_ignored: float | None = None
    phys_res_raw: float | None = None
    phys_res_effective: float | None = None
    physical_suppression: float | None = None
    checks: list[Any] = Field(default_factory=list)
    damage_trace: dict[str, Any] = Field(default_factory=dict)
    trigger_attempts: list[Any] = Field(default_factory=list)
    mutations: list[Any] = Field(default_factory=list)
    equipment: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    schema_version: int = 2


class CombatAnalyticsDrilldownResponseDTO(BaseModel):
    aggregate_version: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int
    offset: int
    rows: list[CombatAnalyticsExchangeFactDTO] = Field(default_factory=list)


class CombatAnalyticsRawDebugDTO(BaseModel):
    combat_id: str
    analytics_schema_version: int | None = None
    combat_math_version: str | None = None
    analytics: dict[str, Any] = Field(default_factory=dict)
