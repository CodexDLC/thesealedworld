from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.backend.features.monsters.dto.loot_culture import MonsterLootCultureDTO, default_loot_culture_payload


class MonsterVariantFlavorDTO(BaseModel):
    variant_key: str = Field(default="", max_length=80)
    name: str = Field(min_length=1, max_length=80)
    appearance: str = Field(min_length=1, max_length=500)
    encounter: str = Field(default="", max_length=500)
    detected: str = Field(default="", max_length=500)
    ambush: str = Field(default="", max_length=500)
    idle: str = Field(default="", max_length=500)
    behavior: str = Field(default="", max_length=300)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_nested_flavor(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        flavor = value.get("flavor")
        if isinstance(flavor, dict):
            merged = dict(flavor)
            if value.get("name"):
                merged["name"] = value["name"]
            if value.get("variant_key"):
                merged["variant_key"] = value["variant_key"]
            merged.update(
                {
                    key: raw
                    for key, raw in value.items()
                    if key in {"variant_key", "appearance", "encounter", "detected", "ambush", "idle", "behavior"}
                }
            )
            cls._fill_encounter_defaults(merged)
            return merged
        value = dict(value)
        cls._fill_encounter_defaults(value)
        return value

    @staticmethod
    def _fill_encounter_defaults(value: dict[str, Any]) -> None:
        encounter = value.get("encounter")
        detected = value.get("detected")
        ambush = value.get("ambush")
        idle = value.get("idle")
        behavior = value.get("behavior")
        if not detected and encounter:
            value["detected"] = encounter
        if not ambush and encounter:
            value["ambush"] = encounter
        if not idle and behavior:
            value["idle"] = behavior
        if not encounter and detected:
            value["encounter"] = detected


class MonsterClanFlavorDTO(BaseModel):
    name_ru: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=1200)
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

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_variant_mapping(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        variants = value.get("variants_flavor")
        if not isinstance(variants, dict):
            return value

        converted: list[dict[str, Any]] = []
        for variant_key, raw_flavor in variants.items():
            if not isinstance(raw_flavor, dict):
                continue
            item = dict(raw_flavor)
            item.setdefault("variant_key", str(variant_key))
            converted.append(item)

        payload = dict(value)
        payload["variants_flavor"] = converted
        return payload

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
