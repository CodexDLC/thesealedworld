from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

from src.backend.features.game_catalog.combat.resources.abilities import get_all_ability_catalog_entries
from src.backend.features.game_catalog.combat.resources.basic_exchanges import get_all_basic_exchange_entries
from src.backend.features.game_catalog.combat.resources.effects import (
    get_all_effect_catalog_entries,
    get_effect_catalog_entry,
)
from src.backend.features.game_catalog.combat.resources.feints import get_all_feint_catalog_entries
from src.backend.features.game_catalog.combat.resources.gifts import get_all_gift_catalog_entries
from src.backend.features.game_catalog.combat.resources.items import get_all_combat_item_action_catalog_entries
from src.backend.features.game_catalog.combat.resources.text_templates import build_combat_text_catalog
from src.backend.features.game_catalog.combat.resources.tokens import get_all_combat_tokens
from src.backend.features.game_catalog.combat.resources.triggers import get_all_triggers

if TYPE_CHECKING:
    from pydantic import BaseModel


@dataclass(slots=True)
class CombatResourceCatalogService:
    """Read-only projections of combat resources for runtime lookups and UI text."""

    @classmethod
    def load_default(cls) -> CombatResourceCatalogService:
        return cls()

    def all_public_text(self) -> dict[str, dict[str, dict[str, Any]]]:
        ability_entries = get_all_ability_catalog_entries()
        gift_entries = get_all_gift_catalog_entries()
        item_entries = get_all_combat_item_action_catalog_entries()
        feint_entries = get_all_feint_catalog_entries()
        effect_entries = get_all_effect_catalog_entries()
        trigger_entries = get_all_triggers()
        basic_exchange_entries = get_all_basic_exchange_entries()
        combat_entries = self._catalog_entries_by_key(
            [
                *ability_entries,
                *gift_entries,
                *item_entries,
                *feint_entries,
                *effect_entries,
                *trigger_entries,
                *basic_exchange_entries,
            ]
        )
        return {
            "abilities": self._catalog_entries_by_id(ability_entries, id_field="ability_id"),
            "feints": self._catalog_entries_by_id(feint_entries, id_field="feint_id"),
            "effects": self._catalog_entries_by_id(effect_entries, id_field="effect_id"),
            "triggers": self._catalog_entries_by_key(trigger_entries),
            "basic_exchanges": self._catalog_entries_by_key(basic_exchange_entries),
            "gifts": self._catalog_entries_by_id(gift_entries, id_field="gift_id"),
            "combat_item_actions": self._catalog_entries_by_id(item_entries, id_field="item_action_id"),
            "combat_tokens": self._public_mapping(get_all_combat_tokens()),
            "combat_entries": combat_entries,
            "combat_text": build_combat_text_catalog(),
        }

    @staticmethod
    def _public_mapping(entries: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {str(entry_id): dict(data) for entry_id, data in entries.items()}

    def _catalog_by_id(self, entries: Sequence[BaseModel], *, id_field: str) -> dict[str, dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}
        for entry in entries:
            data = entry.model_dump(mode="json")
            entry_id = str(data[id_field])
            catalog[entry_id] = self._public_entry(entry_id, data)
        return catalog

    def _catalog_entries_by_id(self, entries: Sequence[BaseModel], *, id_field: str) -> dict[str, dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}
        for entry in entries:
            data = entry.model_dump(mode="json")
            technical = data["technical"]
            descriptive = data["descriptive"]
            entry_id = str(technical[id_field])
            public = self._public_entry_from_description(entry_id, descriptive)
            for field in ("cost", "target", "target_count"):
                if field in technical and technical[field] not in (None, [], {}):
                    public[field] = technical[field]
            if id_field == "ability_id":
                public.update(self._ability_public_details(technical))
            public["catalog_key"] = data["key"]
            catalog[entry_id] = public
        return catalog

    def _catalog_entries_by_key(self, entries: Sequence[BaseModel]) -> dict[str, dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}
        for entry in entries:
            data = entry.model_dump(mode="json")
            key = str(data["key"])
            technical = data["technical"]
            descriptive = data["descriptive"]
            public = self._public_entry_from_description(key, descriptive)
            public["catalog_key"] = key
            public["resource_type"] = key.split(".")[1] if "." in key else ""
            public["resource_id"] = (
                technical.get("item_action_id")
                or technical.get("ability_id")
                or technical.get("gift_id")
                or technical.get("feint_id")
                or technical.get("effect_id")
                or technical.get("trigger_id")
                or technical.get("exchange_id")
                or key
            )
            if technical.get("cost") not in (None, [], {}):
                public["cost"] = technical["cost"]
            catalog[key] = public
        return catalog

    @staticmethod
    def _public_entry(entry_id: str, data: dict[str, Any]) -> dict[str, Any]:
        title = data.get("name_ru") or data.get("name_en") or entry_id
        description = (
            data.get("description_ru") or data.get("description") or f"DATA_MISSING: combat_description:{entry_id}"
        )
        public: dict[str, Any] = {
            "title": title,
            "description": description,
        }
        for field in (
            "source",
            "type",
            "target",
            "target_count",
            "event",
            "chance",
            "school",
            "role",
            "duration",
            "tags",
        ):
            if field in data and data[field] not in (None, [], {}):
                public[field] = data[field]
        return public

    @staticmethod
    def _public_entry_from_description(entry_id: str, descriptive: dict[str, Any]) -> dict[str, Any]:
        default_taxonomy = descriptive.get("default_taxonomy") or "humanoid"
        variants = descriptive.get("variants") or {}
        selected = variants.get(default_taxonomy) or variants.get("humanoid") or {}
        return {
            "title": selected.get("display_name") or entry_id,
            "label": selected.get("ui_label") or selected.get("display_name") or entry_id,
            "description": selected.get("short_description") or f"DATA_MISSING: combat_description:{entry_id}",
            "long_description": selected.get("long_description") or selected.get("short_description") or "",
            "icon": selected.get("icon") or "",
            "default_taxonomy": default_taxonomy,
            "taxonomy_variants": variants,
        }

    @classmethod
    def _ability_public_details(cls, technical: dict[str, Any]) -> dict[str, Any]:
        target = str(technical.get("target") or "")
        details: dict[str, Any] = {
            "target_label": cls._target_label(target),
        }
        mechanics = cls._ability_mechanics(technical)
        if mechanics:
            details["mechanics"] = mechanics
        return details

    @classmethod
    def _ability_mechanics(cls, technical: dict[str, Any]) -> list[str]:
        mechanics: list[str] = []
        preset = (technical.get("pipeline_mutations") or {}).get("preset")
        if preset:
            mechanics.append(f"Тип: {cls._preset_label(str(preset))}")

        damage = technical.get("override_damage")
        if damage:
            label = "Лечение" if preset == "HEALING" else "Урон"
            mechanics.append(f"{label}: {cls._range_text(damage)}")

        for mutation in (technical.get("pipeline_mutations") or {}).get("applications") or []:
            text = cls._pipeline_mutation_text(mutation)
            if text:
                mechanics.append(text)

        for application in technical.get("modifier_applications") or []:
            text = cls._modifier_text(application)
            if text:
                mechanics.append(text)

        for effect in technical.get("effects") or []:
            text = cls._effect_text(effect)
            if text:
                mechanics.append(text)

        triggers = technical.get("triggers") or []
        for trigger in triggers:
            if trigger:
                mechanics.append(f"Триггер: {trigger}")

        return mechanics

    @staticmethod
    def _target_label(target: str) -> str:
        labels = {
            "self": "На себя",
            "single_enemy": "Один враг",
            "all_enemies": "Все враги",
            "single_ally": "Один союзник",
            "all_allies": "Все союзники",
            "random_enemy": "Случайный враг",
            "lowest_hp_ally": "Союзник с минимальным HP",
            "lowest_hp_enemy": "Враг с минимальным HP",
            "cleave": "Несколько врагов",
        }
        return labels.get(target, target or "NO_TARGET")

    @staticmethod
    def _preset_label(preset: str) -> str:
        labels = {
            "MAGIC_ATTACK": "атака",
            "TACTICAL_INSTANT_STRIKE": "тактический удар",
            "HEALING": "лечение",
            "BUFF": "эффект",
        }
        return labels.get(preset, preset.lower())

    @classmethod
    def _pipeline_mutation_text(cls, mutation: dict[str, Any]) -> str:
        if str(mutation.get("mutation_id") or "") != "damage_mult":
            return ""
        value = mutation.get("value_override")
        if value is None:
            return ""
        return f"Урон оружия: x{cls._number_text(value)}"

    @classmethod
    def _modifier_text(cls, application: dict[str, Any]) -> str:
        modifier_id = str(application.get("modifier_id") or "")
        if not modifier_id:
            return ""
        target_actor = str(application.get("target_actor") or "self")
        value = application.get("value_override")
        if str(application.get("value_mode") or "") == "source_main_hand_damage_multiplier":
            value_text = f"{cls._number_text(float(application.get('value_multiplier') or 0.0) * 100.0)}% урона умения"
        else:
            value_text = (
                cls._number_text(value)
                if value is not None
                else f"x{cls._number_text(application.get('value_multiplier'))}"
            )
        duration = application.get("duration_exchanges")
        duration_text = f" на {duration} {cls._exchange_word(duration)}" if duration else ""
        target_text = "Цель получает" if target_actor == "target" else "Вы получаете"
        return f"{target_text}: {cls._modifier_label(modifier_id)} {value_text}{duration_text}"

    @staticmethod
    def _modifier_label(modifier_id: str) -> str:
        labels = {
            "armor_add": "броня",
            "damage_mult": "урон",
            "evasion_add": "уклонение",
            "physical_damage_bonus_add": "физический урон",
        }
        return labels.get(modifier_id, modifier_id)

    @classmethod
    def _effect_text(cls, effect: dict[str, Any]) -> str:
        effect_id = str(effect.get("id") or "")
        if not effect_id:
            return ""
        params = effect.get("params") or {}
        text = f"Эффект: {cls._effect_label(effect_id).lower()}"
        parts: list[str] = []
        duration = params.get("duration")
        if duration:
            text = f"{text} на {duration} {cls._exchange_word(duration)}"
        power = params.get("power")
        if power is not None:
            parts.append(f"сила {cls._number_text(power)}")
        value = params.get("value")
        if value is not None:
            parts.append(f"значение {cls._number_text(value)}")
        if parts:
            text = f"{text}, {', '.join(parts)}"
        return text

    @staticmethod
    def _effect_label(effect_id: str) -> str:
        entry = get_effect_catalog_entry(effect_id)
        if entry is None:
            return effect_id
        variant = entry.descriptive.variants.get(entry.descriptive.default_taxonomy)
        variant = variant or entry.descriptive.variants.get("humanoid")
        if variant is None:
            return effect_id
        return variant.display_name or effect_id

    @classmethod
    def _range_text(cls, value: Any) -> str:
        if isinstance(value, list | tuple) and len(value) == 2:
            return f"{cls._number_text(value[0])}-{cls._number_text(value[1])}"
        return cls._number_text(value)

    @staticmethod
    def _number_text(value: Any) -> str:
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    @staticmethod
    def _exchange_word(value: Any) -> str:
        try:
            number = abs(int(value))
        except (TypeError, ValueError):
            return "размена"
        if number % 10 == 1 and number % 100 != 11:
            return "размен"
        if 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
            return "размена"
        return "разменов"
