from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GearScoreSummaryDTO(BaseModel):
    version: int | None = None
    count: int = 0
    min: int = 0
    avg: float = 0.0
    max: int = 0
    total: int = 0
    by_role: dict[str, dict[str, int | float]] = Field(default_factory=dict)
    raw_count: int = 0
    raw_min: int = 0
    raw_avg: float = 0.0
    raw_max: int = 0
    raw_total: int = 0
    raw_by_role: dict[str, dict[str, int | float]] = Field(default_factory=dict)


class GeneratedAssetVisualDTO(BaseModel):
    status: str = ""
    source: str = ""
    image_url: str = ""
    generated_image_url: str = ""
    placeholder_image_url: str = ""
    storage_key: str = ""
    storage_backend: str = ""
    asset_hash: str = ""
    content_type: str = ""
    size_bytes: int | None = None
    pending_task_id: str | None = None
    task_id: str | None = None
    task_status: str = ""
    task_attempts: int = 0
    task_max_attempts: int = 0
    task_error_type: str = ""
    task_error_message: str = ""


class GeneratedMonsterEquipmentSummaryDTO(BaseModel):
    equipment: list[str] = Field(default_factory=list)
    weapons: list[str] = Field(default_factory=list)
    armor: list[str] = Field(default_factory=list)
    affixes: list[str] = Field(default_factory=list)


class GeneratedMonsterViewDTO(BaseModel):
    member_id: str
    monster_id: str
    clan_id: str
    variant_id: str
    variant_key: str
    member_hash: str
    role: str
    title: str
    name_ru: str
    localized: dict[str, Any] = Field(default_factory=dict)
    short_description: str = ""
    description: str = ""
    min_tier: int
    max_tier: int
    member_tier: int = 0
    mongo_actor_key: str
    text_content: dict[str, Any] = Field(default_factory=dict)
    scaled_attributes: dict[str, Any] = Field(default_factory=dict)
    scaled_skills: dict[str, Any] = Field(default_factory=dict)
    items: dict[str, Any] = Field(default_factory=dict)
    vitals: dict[str, Any] = Field(default_factory=dict)
    ai_profile: dict[str, Any] = Field(default_factory=dict)
    generation_meta: dict[str, Any] = Field(default_factory=dict)
    combat_actor_snapshot: dict[str, Any] = Field(default_factory=dict)
    metadata_: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    source_context: dict[str, Any] = Field(default_factory=dict)
    lifecycle_status: str = "active"
    archived_at: datetime | None = None
    expires_at: datetime | None = None
    schema_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    threat_rating: int = 0
    gear_score: int | None = None
    visual: GeneratedAssetVisualDTO = Field(default_factory=GeneratedAssetVisualDTO)
    equipment_summary: GeneratedMonsterEquipmentSummaryDTO = Field(default_factory=GeneratedMonsterEquipmentSummaryDTO)


class GeneratedClanViewDTO(BaseModel):
    clan_id: str
    family_id: str
    tier: int = 0
    zone_id: str | None = None
    context_hash: str = ""
    identity_hash: str = ""
    unique_hash: str = ""
    context_identity: dict[str, Any] = Field(default_factory=dict)
    selected_traits: list[dict[str, Any]] = Field(default_factory=list)
    title: str
    name_ru: str
    localized: dict[str, Any] = Field(default_factory=dict)
    description: str
    encounter_texts: dict[str, Any] = Field(default_factory=dict)
    raw_tags: dict[str, Any] = Field(default_factory=dict)
    flavor_content: dict[str, Any] = Field(default_factory=dict)
    generation_version: int = 1
    resource_version: str = ""
    metadata_: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    source_context: dict[str, Any] = Field(default_factory=dict)
    lifecycle_status: str = "active"
    archived_at: datetime | None = None
    expires_at: datetime | None = None
    schema_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    visual: GeneratedAssetVisualDTO = Field(default_factory=GeneratedAssetVisualDTO)
    gear_score_summary: GearScoreSummaryDTO = Field(default_factory=GearScoreSummaryDTO)
    members: list[GeneratedMonsterViewDTO] = Field(default_factory=list)


class PaginationDTO(BaseModel):
    limit: int
    offset: int
    total: int
    has_more: bool


class GeneratedMonstersResponseDTO(BaseModel):
    items: list[GeneratedClanViewDTO]
    pagination: PaginationDTO


class GeneratedMonstersSummaryDTO(BaseModel):
    clans: int = 0
    members: int = 0
    missing_images: int = 0


class MonsterImageRegenerationResponseDTO(BaseModel):
    task_id: str
    entity_type: str
    entity_id: str
    status: str
    storage_key: str
    image_url: str


class MonsterAIRegenerationResponseDTO(BaseModel):
    task_id: str
    entity_type: str
    entity_id: str
    status: str


class MonsterImageRegenerationBatchRequestDTO(BaseModel):
    clan_ids: list[str] = Field(min_length=1, max_length=100)


class MonsterImageRegenerationBatchResponseDTO(BaseModel):
    task_ids: list[str]
    entity_type: str
    entity_id: str | None = None
    status: str
    requested: int
    storage_keys: list[str]


class MonsterDataRebuildRequestDTO(BaseModel):
    family_id: str | None = None
    clan_id: str | None = None
    limit: int = Field(default=100, ge=1, le=500)
    force: bool = False
    remove_obsolete_members: bool = True


class MonsterDataRebuildItemDTO(BaseModel):
    clan_id: str
    family_id: str
    status: str
    reason: str = ""
    members_expected: int = 0
    members_changed: int = 0
    members_created: int = 0
    members_removed: int = 0


class MonsterDataRebuildResponseDTO(BaseModel):
    dry_run: bool
    status: str
    scanned: int
    stale: int
    rebuilt: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
    items: list[MonsterDataRebuildItemDTO] = Field(default_factory=list)


__all__ = [
    "GearScoreSummaryDTO",
    "GeneratedAssetVisualDTO",
    "GeneratedClanViewDTO",
    "GeneratedMonsterEquipmentSummaryDTO",
    "GeneratedMonsterViewDTO",
    "GeneratedMonstersSummaryDTO",
    "MonsterAIRegenerationResponseDTO",
    "MonsterDataRebuildItemDTO",
    "MonsterDataRebuildRequestDTO",
    "MonsterDataRebuildResponseDTO",
    "MonsterImageRegenerationBatchRequestDTO",
    "MonsterImageRegenerationBatchResponseDTO",
    "GeneratedMonstersResponseDTO",
    "MonsterImageRegenerationResponseDTO",
    "PaginationDTO",
]
