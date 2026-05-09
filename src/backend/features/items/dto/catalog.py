from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RawResourceTemplateDTO(BaseModel):
    id: str
    name_ru: str
    base_price: int
    narrative_description: str


class MaterialTemplateDTO(BaseModel):
    id: str
    name_ru: str
    name_prefix_ru: str | None = None
    tier_mult: float
    slots: int
    tier: int = 0
    category: str = ""
    allowed_item_types: list[str] = Field(default_factory=list)
    allowed_armor_classes: list[str] = Field(default_factory=list)
    color_key: str = "grey"
    narrative_tags: list[str] = Field(default_factory=list)
    narrative_description: str | None = None


class BaseItemTemplateDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name_ru: str
    narrative_description: str | None = None
    slot: str
    type: str | None = None
    base_power: int
    base_durability: int
    damage_spread: float = 0.1
    damage_type: str | None = None
    defense_type: str | None = None
    related_skill: str | None = None
    armor_class: str | None = None
    allowed_materials: list[str] = Field(default_factory=list)
    extra_slots: list[str] = Field(default_factory=list)
    implicit_bonuses: dict[str, float] = Field(default_factory=dict)
    triggers: list[str] = Field(default_factory=list)
    narrative_tags: list[str] = Field(default_factory=list)


class RarityConfigDTO(BaseModel):
    enum_key: str
    name_ru: str
    color_hex: str
    default_mult: float
    slots_capacity: int


class CatalogEntryDTO(BaseModel):
    id: str
    meta_type: str
    category: str
    data: dict[str, Any]
