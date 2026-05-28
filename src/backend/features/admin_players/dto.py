from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AdminPlayerCharacterSummaryDTO(BaseModel):
    character_id: int
    user_id: UUID
    name: str
    name_key: str
    gender: str
    avatar_url: str | None = None
    game_stage: str
    prev_game_stage: str | None = None
    location_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminPlayerCharacterListResponseDTO(BaseModel):
    user_id: UUID
    total: int = 0
    limit: int = 25
    offset: int = 0
    items: list[AdminPlayerCharacterSummaryDTO] = Field(default_factory=list)


class AdminPlayerInventoryItemDTO(BaseModel):
    item_id: str
    base_id: str
    name: str
    description: str = ""
    item_type: str
    rarity: str
    rarity_tier: int
    lifecycle_status: str
    text_status: str
    placement: str
    slot: str | None = None
    position_index: int | None = None
    valid_slots: list[str] = Field(default_factory=list)
    mechanics: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminPlayerEquipmentSlotDTO(BaseModel):
    slot_id: str
    label: str
    item: AdminPlayerInventoryItemDTO | None = None


class AdminPlayerCharacterDetailDTO(BaseModel):
    character: AdminPlayerCharacterSummaryDTO
    attributes: dict[str, int] = Field(default_factory=dict)
    skills: dict[str, float] = Field(default_factory=dict)
    free_xp: float = 0.0
    equipment_slots: list[AdminPlayerEquipmentSlotDTO] = Field(default_factory=list)
    belt_slots: list[AdminPlayerEquipmentSlotDTO] = Field(default_factory=list)
    carried_items: list[AdminPlayerInventoryItemDTO] = Field(default_factory=list)
    carried_total: int = 0
    inventory_limit: int = 50
    inventory_offset: int = 0


class AdminPlayerGenerateCharacterRequestDTO(BaseModel):
    slot_index: int = Field(default=1, ge=1, le=4)
    name: str = Field(default="", max_length=64)
    gender: Literal["male", "female", "other", "random"] = "random"
    skill_progress_percent: int = Field(default=75, ge=0, le=100)
    item_tier: int = Field(default=1, ge=0, le=7)
    source_clan_id: str = Field(min_length=1, max_length=64)
    request_ai_text: bool = False


class AdminPlayerGenerationClanOptionDTO(BaseModel):
    clan_id: str
    label: str
    family_id: str
    tier: int
    zone_id: str | None = None
    can_generate_player_equipment: bool = True
    reason: str = ""


class AdminPlayerGenerationOptionsResponseDTO(BaseModel):
    clans: list[AdminPlayerGenerationClanOptionDTO] = Field(default_factory=list)


class AdminPlayerGenerateCharacterResponseDTO(BaseModel):
    character: AdminPlayerCharacterSummaryDTO
    generated_item_ids: list[str] = Field(default_factory=list)
    family_id: str
    source_clan_id: str
    variant_id: str
    item_tier: int
    skill_progress_percent: int
