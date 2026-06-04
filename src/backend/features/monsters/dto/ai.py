from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.backend.features.monsters.dto.loot_culture import MonsterLootCultureDTO, default_loot_culture_payload


class MonsterVariantFlavorDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_key: str = Field(default="", max_length=80)
    name: str = Field(min_length=1, max_length=80)
    short_description: str = Field(min_length=1, max_length=300)
    visual_hint: str = Field(default="", max_length=300)

    @model_validator(mode="before")
    @classmethod
    def normalize_short_description(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if not payload.get("short_description") and payload.get("appearance"):
            payload["short_description"] = payload["appearance"]
        return payload


class MonsterEncounterTextsDTO(BaseModel):
    patrol: str = Field(min_length=1, max_length=500)
    ambush: str = Field(min_length=1, max_length=500)
    lair: str = Field(min_length=1, max_length=500)
    random_meeting: str = Field(min_length=1, max_length=500)


class MonsterClanFlavorDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_ru: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=1200)
    encounter_texts: MonsterEncounterTextsDTO
    loot_culture: MonsterLootCultureDTO = Field(
        default_factory=lambda: MonsterLootCultureDTO.model_validate(
            default_loot_culture_payload(
                family_id="unknown_family",
                archetype="unknown",
                organization_type="unknown",
            )
        )
    )
    variants_flavor: list[MonsterVariantFlavorDTO] = Field(default_factory=list)

    @property
    def variants_by_key(self) -> dict[str, MonsterVariantFlavorDTO]:
        return {variant.variant_key: variant for variant in self.variants_flavor if variant.variant_key}

    def model_dump_with_variant_mapping(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["variants_flavor"] = {
            variant.variant_key: variant.model_dump(mode="json", exclude={"variant_key"})
            for variant in self.variants_flavor
            if variant.variant_key
        }
        return payload
