from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.backend.features.monsters.dto.loot_culture import MonsterLootCultureDTO, default_loot_culture_payload


class LocalizedTextDTO(BaseModel):
    ru: str = Field(min_length=1, max_length=1200)
    en: str = Field(min_length=1, max_length=1200)

    @model_validator(mode="before")
    @classmethod
    def normalize_plain_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"ru": value, "en": value}
        if isinstance(value, dict):
            _reject_extra_keys(value, allowed={"ru", "en"})
        return value


class MonsterVariantFlavorDTO(BaseModel):
    variant_key: str = Field(default="", max_length=80)
    display_name: LocalizedTextDTO
    short_description: LocalizedTextDTO
    appearance: LocalizedTextDTO
    visual_hint: LocalizedTextDTO

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_variant_fields(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        _reject_extra_keys(
            payload,
            allowed={
                "variant_key",
                "display_name",
                "name",
                "short_description",
                "appearance",
                "visual_hint",
            },
        )
        if not payload.get("display_name") and payload.get("name"):
            payload["display_name"] = payload["name"]
        if not payload.get("short_description") and payload.get("appearance"):
            payload["short_description"] = payload["appearance"]
        if not payload.get("appearance") and payload.get("short_description"):
            payload["appearance"] = payload["short_description"]
        if not payload.get("visual_hint") and payload.get("appearance"):
            payload["visual_hint"] = payload["appearance"]
        return payload

    @property
    def name_ru(self) -> str:
        return self.display_name.ru

    @property
    def short_description_ru(self) -> str:
        return self.short_description.ru

    @property
    def visual_hint_ru(self) -> str:
        return self.visual_hint.ru


class MonsterEncounterTextsDTO(BaseModel):
    patrol: LocalizedTextDTO
    ambush: LocalizedTextDTO
    lair: LocalizedTextDTO
    random_meeting: LocalizedTextDTO

    def ru_dict(self) -> dict[str, str]:
        return {
            "patrol": self.patrol.ru,
            "ambush": self.ambush.ru,
            "lair": self.lair.ru,
            "random_meeting": self.random_meeting.ru,
        }


class MonsterClanFlavorDTO(BaseModel):
    display_name: LocalizedTextDTO
    description: LocalizedTextDTO
    encounter_texts: MonsterEncounterTextsDTO
    visual_hint: LocalizedTextDTO
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
    def reject_extra_fields(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        _reject_extra_keys(
            payload,
            allowed={
                "display_name",
                "name_ru",
                "description",
                "encounter_texts",
                "visual_hint",
                "loot_culture",
                "variants_flavor",
            },
        )
        if not payload.get("display_name") and payload.get("name_ru"):
            payload["display_name"] = payload["name_ru"]
        if not payload.get("visual_hint") and payload.get("description"):
            payload["visual_hint"] = payload["description"]
        return payload

    @property
    def name_ru(self) -> str:
        return self.display_name.ru

    @property
    def description_ru(self) -> str:
        return self.description.ru

    @property
    def variants_by_key(self) -> dict[str, MonsterVariantFlavorDTO]:
        return {variant.variant_key: variant for variant in self.variants_flavor if variant.variant_key}

    def model_dump_with_variant_mapping(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["variants_flavor"] = {
            variant.variant_key: {
                **variant.model_dump(mode="json", exclude={"variant_key"}),
                "name": variant.display_name.ru,
                "short_description_ru": variant.short_description.ru,
                "short_description_en": variant.short_description.en,
                "appearance_ru": variant.appearance.ru,
                "appearance_en": variant.appearance.en,
                "visual_hint_ru": variant.visual_hint.ru,
                "visual_hint_en": variant.visual_hint.en,
            }
            for variant in self.variants_flavor
            if variant.variant_key
        }
        payload["name_ru"] = self.display_name.ru
        payload["description_ru"] = self.description.ru
        payload["encounter_texts_ru"] = self.encounter_texts.ru_dict()
        return payload


def _reject_extra_keys(payload: dict[str, Any], *, allowed: set[str]) -> None:
    extra = sorted(set(payload) - allowed)
    if extra:
        raise ValueError(f"Extra inputs are not permitted: {', '.join(extra)}")
