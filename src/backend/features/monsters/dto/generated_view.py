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


class GeneratedAssetVisualDTO(BaseModel):
    status: str = ""
    source: str = ""
    image_url: str = ""
    generated_image_url: str = ""
    fallback_image_url: str = ""
    storage_key: str = ""
    storage_backend: str = ""
    asset_hash: str = ""
    content_type: str = ""
    size_bytes: int | None = None
    pending_task_id: str | None = None


class GeneratedMonsterEquipmentSummaryDTO(BaseModel):
    equipment: list[str] = Field(default_factory=list)
    weapons: list[str] = Field(default_factory=list)
    armor: list[str] = Field(default_factory=list)
    affixes: list[str] = Field(default_factory=list)


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
    visual: GeneratedAssetVisualDTO = Field(default_factory=GeneratedAssetVisualDTO)
    equipment_summary: GeneratedMonsterEquipmentSummaryDTO = Field(default_factory=GeneratedMonsterEquipmentSummaryDTO)


class GeneratedClanViewDTO(BaseModel):
    clan_id: str
    family_id: str
    tier: int
    zone_id: str | None = None
    name_ru: str
    description: str
    visual: GeneratedAssetVisualDTO = Field(default_factory=GeneratedAssetVisualDTO)
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


class MonsterImageRegenerationResponseDTO(BaseModel):
    task_id: str
    entity_type: str
    entity_id: str
    status: str
    storage_key: str
    image_url: str


__all__ = [
    "GearScoreSummaryDTO",
    "GeneratedAssetVisualDTO",
    "GeneratedClanViewDTO",
    "GeneratedMonsterEquipmentSummaryDTO",
    "GeneratedMonsterViewDTO",
    "GeneratedMonstersResponseDTO",
    "MonsterImageRegenerationResponseDTO",
    "PaginationDTO",
]
