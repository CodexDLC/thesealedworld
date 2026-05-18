from __future__ import annotations

from pydantic import BaseModel, Field


class GearScoreSummaryDTO(BaseModel):
    version: int | None = None
    count: int = 0
    min: int = 0
    avg: float = 0.0
    max: int = 0
    total: int = 0
    by_role: dict[str, dict[str, int | float]] = Field(default_factory=dict)


class GeneratedMonsterViewDTO(BaseModel):
    monster_id: str
    variant_key: str
    role: str
    member_tier: int
    name_ru: str
    threat_rating: int
    gear_score: int | None = None
    base_cost: int | None = None
    effective_cost: float | None = None


class GeneratedClanViewDTO(BaseModel):
    clan_id: str
    family_id: str
    tier: int
    zone_id: str | None = None
    name_ru: str
    description: str
    gear_score_summary: GearScoreSummaryDTO
    members: list[GeneratedMonsterViewDTO] = Field(default_factory=list)


class PaginationDTO(BaseModel):
    limit: int
    offset: int
    total: int
    has_more: bool


class GeneratedMonstersResponseDTO(BaseModel):
    items: list[GeneratedClanViewDTO]
    pagination: PaginationDTO


__all__ = [
    "GearScoreSummaryDTO",
    "GeneratedClanViewDTO",
    "GeneratedMonsterViewDTO",
    "GeneratedMonstersResponseDTO",
    "PaginationDTO",
]
