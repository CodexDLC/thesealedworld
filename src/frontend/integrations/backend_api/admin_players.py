from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.frontend.core.api import BaseApiClient


class AdminPlayerCharacterSummary(BaseModel):
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


class AdminPlayerCharacterListResponse(BaseModel):
    user_id: UUID
    total: int = 0
    limit: int = 25
    offset: int = 0
    items: list[AdminPlayerCharacterSummary] = Field(default_factory=list)


class AdminPlayerInventoryItem(BaseModel):
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


class AdminPlayerEquipmentSlot(BaseModel):
    slot_id: str
    label: str
    item: AdminPlayerInventoryItem | None = None


class AdminPlayerCharacterDetail(BaseModel):
    character: AdminPlayerCharacterSummary
    attributes: dict[str, int] = Field(default_factory=dict)
    skills: dict[str, float] = Field(default_factory=dict)
    free_xp: float = 0.0
    equipment_slots: list[AdminPlayerEquipmentSlot] = Field(default_factory=list)
    belt_slots: list[AdminPlayerEquipmentSlot] = Field(default_factory=list)
    carried_items: list[AdminPlayerInventoryItem] = Field(default_factory=list)
    carried_total: int = 0
    inventory_limit: int = 50
    inventory_offset: int = 0


class AdminPlayerGenerateCharacterRequest(BaseModel):
    slot_index: int = 1
    name: str = ""
    gender: str = "random"
    skill_progress_percent: int = 75
    item_tier: int = 1
    source_clan_id: str
    request_ai_text: bool = False


class AdminPlayerGenerationClanOption(BaseModel):
    clan_id: str
    label: str
    family_id: str
    tier: int
    zone_id: str | None = None
    can_generate_player_equipment: bool = True
    reason: str = ""


class AdminPlayerGenerationOptionsResponse(BaseModel):
    clans: list[AdminPlayerGenerationClanOption] = Field(default_factory=list)


class AdminPlayerGenerateCharacterResponse(BaseModel):
    character: AdminPlayerCharacterSummary
    generated_item_ids: list[str] = Field(default_factory=list)
    family_id: str
    source_clan_id: str
    variant_id: str
    item_tier: int
    skill_progress_percent: int


class AdminPlayersApi(BaseApiClient):
    async def list_user_characters(
        self,
        user_id: UUID,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> AdminPlayerCharacterListResponse:
        return await self._request(
            "GET",
            f"/api/admin/players/users/{user_id}/characters",
            response_model=AdminPlayerCharacterListResponse,
            params={"limit": limit, "offset": offset},
        )

    async def get_character_detail(
        self,
        character_id: int,
        *,
        inventory_limit: int = 50,
        inventory_offset: int = 0,
    ) -> AdminPlayerCharacterDetail:
        return await self._request(
            "GET",
            f"/api/admin/players/characters/{character_id}",
            response_model=AdminPlayerCharacterDetail,
            params={"inventory_limit": inventory_limit, "inventory_offset": inventory_offset},
        )

    async def generate_test_character(
        self,
        user_id: UUID,
        request: AdminPlayerGenerateCharacterRequest,
    ) -> AdminPlayerGenerateCharacterResponse:
        return await self._request(
            "POST",
            f"/api/admin/players/users/{user_id}/characters/generate",
            response_model=AdminPlayerGenerateCharacterResponse,
            json=request.model_dump(mode="json"),
        )

    async def list_character_generation_options(self, *, limit: int = 100) -> AdminPlayerGenerationOptionsResponse:
        return await self._request(
            "GET",
            "/api/admin/players/character-generation-options",
            response_model=AdminPlayerGenerationOptionsResponse,
            params={"limit": limit},
        )
