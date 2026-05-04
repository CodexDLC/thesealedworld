from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ItemPlacementRefDTO(BaseModel):
    holder_type: Literal["character", "container", "corpse", "auction", "system", "scenario_reward"]
    holder_id: str
    storage_type: str = "backpack"
    slot: str | None = None
    position_index: int | None = None


class ItemOriginRefDTO(BaseModel):
    origin_type: Literal["scenario", "craft", "loot", "admin", "import", "system"] = "system"
    origin_ref: str | None = None
    seed: str | None = None
    request_hash: str | None = None


class ItemGenerationRequestDTO(BaseModel):
    base_id: str
    rarity_tier: int = 0
    material_id: str | None = None
    affix_bundle_ids: list[str] = Field(default_factory=list)
    source: str | None = None
    char_id: int | None = None
    request_ai_text: bool = False
    placement_ref: ItemPlacementRefDTO | None = None
    origin_ref: ItemOriginRefDTO | None = None
    delivery_mode: Literal["reply", "forward"] = "reply"
    return_item: bool = True


class ItemGenerationBatchRequestDTO(BaseModel):
    items: list[ItemGenerationRequestDTO] = Field(min_length=1)
    delivery_mode: Literal["reply", "forward"] = "reply"
    return_items: bool = True


class GeneratedItemDTO(BaseModel):
    instance_id: str | None = None
    template_id: str
    item_type: str
    rarity: str
    rarity_tier: int
    name: str
    description: str
    base_id: str
    material_id: str | None = None
    affix_bundle_ids: list[str] = Field(default_factory=list)
    power: float
    durability_max: float
    damage_spread: float = 0.1
    slot: str
    valid_slots: list[str] = Field(default_factory=list)
    implicit_bonuses: dict[str, float] = Field(default_factory=dict)
    bonuses: dict[str, float] = Field(default_factory=dict)
    triggers: list[str] = Field(default_factory=list)
    narrative_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
