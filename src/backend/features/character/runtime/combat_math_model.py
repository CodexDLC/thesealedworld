from __future__ import annotations

from typing import Any

from src.backend.features.character.dto.modifiers import CombatModifiersDTO
from src.backend.features.character.schemas.session import CharacterSessionAttributesDTO

RawStatBlock = dict[str, dict[str, Any]]
RawCombatMathModel = dict[str, Any]

ATTRIBUTE_KEYS = tuple(CharacterSessionAttributesDTO.model_fields)
COMBAT_MODIFIER_KEYS = frozenset(CombatModifiersDTO.model_fields)
UNARMED_ACCURACY = 0.70
UNARMED_DAMAGE_SPREAD = 0.50
MODIFIER_ALIASES = {
    "block_chance": "block",
    "damage_reduction_flat": "armor",
    "dodge_chance": "evasion",
    "energy_max": "en",
    "evasion_penalty": "evasion",
    "hp_max": "hp",
    "magical_resistance": "magic_resist",
    "magic_resistance": "magic_resist",
    "parry_chance": "parry",
    "physical_accuracy": "accuracy",
    "physical_crit_chance": "crit_chance",
    "physical_crit_power_float": "crit_power",
    "shield_block_chance": "block",
}


class CharacterCombatMathModelBuilder:
    """Builds combat raw math input from active-character runtime data."""

    def build_raw(
        self,
        *,
        attributes: Any,
        items: dict[str, Any] | None = None,
        skills: dict[str, Any] | None = None,
    ) -> RawCombatMathModel:
        equipped = self._equipped_items(items or {})
        skill_values = self._skill_values(skills or {})
        attributes_data = self._dump(attributes)
        return {
            "attributes": self._build_attributes(attributes_data),
            "modifiers": self._build_modifiers(equipped, skill_values, attributes_data),
            "tags": ["player"],
        }

    def _build_attributes(self, attributes: Any) -> RawStatBlock:
        data = self._dump(attributes)
        return {
            key: {"base": float(data.get(key, 0) or 0), "source": {}, "temp": {}}
            for key in ATTRIBUTE_KEYS
            if data.get(key) is not None
        }

    def _build_modifiers(
        self, equipment: list[dict[str, Any]], skills: dict[str, float], attributes: dict[str, Any]
    ) -> RawStatBlock:
        modifiers = self._empty_modifiers()
        has_main_hand_weapon = False
        for item in equipment:
            item_id = str(item.get("item_id") or item.get("inventory_id") or item.get("id") or "")
            if not item_id:
                continue

            source = f"item:{item_id}"
            mechanics = self._mechanics(item)
            slot = str(item.get("slot") or mechanics.get("slot") or "")
            combat_slot = self._combat_slot(slot)
            item_type = str(item.get("item_type") or item.get("type") or mechanics.get("item_type") or "")
            tags = self._tags(item, mechanics)
            if combat_slot == "main_hand" and item_type == "weapon":
                has_main_hand_weapon = True

            power = self._float_value(mechanics.get("power", mechanics.get("base_power")))
            if power:
                self._add_power_modifier(modifiers, slot=combat_slot, item_type=item_type, tags=tags, value=power)

            damage_spread = self._float_value(mechanics.get("damage_spread"))
            if damage_spread is not None:
                if combat_slot == "main_hand":
                    self._replace_base_modifier(modifiers, "main_hand_damage_spread", damage_spread)
                elif combat_slot == "off_hand" and not self._is_shield(item_type, tags):
                    self._replace_base_modifier(modifiers, "off_hand_damage_spread", damage_spread)

            for bonus_key, value in (mechanics.get("implicit_bonuses") or {}).items():
                self._add_item_base_modifier(
                    modifiers,
                    str(bonus_key),
                    value,
                    slot=combat_slot,
                    item_type=item_type,
                    tags=tags,
                )
            for bonus_key, value in (mechanics.get("bonuses") or {}).items():
                self._add_modifier(modifiers, str(bonus_key), source, value)
            self._add_skill_sources(modifiers, item=item, mechanics=mechanics, tags=tags, source=source, skills=skills)

        if not has_main_hand_weapon:
            self._apply_unarmed_base(modifiers, attributes)

        return modifiers

    @staticmethod
    def _apply_unarmed_base(modifiers: RawStatBlock, attributes: dict[str, Any]) -> None:
        strength = CharacterCombatMathModelBuilder._float_value(attributes.get("strength")) or 0.0
        CharacterCombatMathModelBuilder._set_base_modifier(modifiers, "main_hand_damage_base", strength)
        CharacterCombatMathModelBuilder._replace_base_modifier(
            modifiers, "main_hand_damage_spread", UNARMED_DAMAGE_SPREAD
        )
        CharacterCombatMathModelBuilder._set_base_modifier(modifiers, "main_hand_accuracy", UNARMED_ACCURACY)

    def _add_skill_sources(
        self,
        modifiers: RawStatBlock,
        *,
        item: dict[str, Any],
        mechanics: dict[str, Any],
        tags: list[str],
        source: str,
        skills: dict[str, float],
    ) -> None:
        bonuses = {
            **(mechanics.get("implicit_bonuses") or {}),
            **(mechanics.get("bonuses") or {}),
        }

        parry_base = self._first_numeric(bonuses, ("parry", "parry_chance"))
        if parry_base:
            parrying = skills.get("skill_parrying", 0.0)
            self._add_modifier(
                modifiers, "parry", f"skill:skill_parrying:{source}", parry_base * 4.0 * parrying / 100.0
            )

        block_base = self._first_numeric(bonuses, ("block", "shield_block_chance"))
        if block_base and self._is_shield(str(item.get("item_type") or item.get("type") or ""), tags):
            shield = skills.get("skill_shield_mastery", 0.0)
            self._add_modifier(
                modifiers, "block", f"skill:skill_shield_mastery:{source}", block_base * 1.5 * shield / 100.0
            )

    def _add_power_modifier(
        self,
        modifiers: RawStatBlock,
        *,
        slot: str,
        item_type: str,
        tags: list[str],
        value: float,
    ) -> None:
        if slot == "main_hand":
            self._set_base_modifier(modifiers, "main_hand_damage_base", value)
            return
        if slot == "off_hand":
            key = "block" if self._is_shield(item_type, tags) else "off_hand_damage_base"
            self._set_base_modifier(modifiers, key, value)
            return
        if item_type == "armor" or slot.endswith("_armor"):
            self._set_base_modifier(modifiers, "armor", value)

    @staticmethod
    def _combat_slot(slot: str) -> str:
        return "main_hand" if slot == "two_hand" else slot

    @staticmethod
    def _equipped_items(items: dict[str, Any]) -> list[dict[str, Any]]:
        layout = items.get("layout") or {}
        equipment_layout = layout.get("equipment") or {}
        by_id = items.get("by_id") or {}

        equipped: list[dict[str, Any]] = []
        for slot, item_id in equipment_layout.items():
            if not item_id:
                continue
            item = by_id.get(str(item_id))
            if not isinstance(item, dict):
                continue
            item = dict(item)
            item.setdefault("slot", slot)
            equipped.append(item)
        return equipped

    @staticmethod
    def _mechanics(item: dict[str, Any]) -> dict[str, Any]:
        mechanics = item.get("mechanics")
        if isinstance(mechanics, dict):
            return mechanics
        data = item.get("data")
        return data if isinstance(data, dict) else item

    @staticmethod
    def _tags(item: dict[str, Any], mechanics: dict[str, Any]) -> list[str]:
        raw_tags = (
            item.get("tags")
            or item.get("narrative_tags")
            or mechanics.get("tags")
            or mechanics.get("narrative_tags")
            or []
        )
        return [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []

    @staticmethod
    def _is_shield(item_type: str, tags: list[str]) -> bool:
        return item_type == "shield" or "shield" in tags

    @staticmethod
    def _add_modifier(modifiers: RawStatBlock, key: str, source: str, value: Any) -> None:
        key = MODIFIER_ALIASES.get(key, key)
        if key not in COMBAT_MODIFIER_KEYS:
            return
        numeric = CharacterCombatMathModelBuilder._float_value(value)
        if numeric is None:
            return
        modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
        modifiers[key]["source"][source] = round(numeric, 4)

    @staticmethod
    def _add_item_base_modifier(
        modifiers: RawStatBlock,
        key: str,
        value: Any,
        *,
        slot: str,
        item_type: str,
        tags: list[str],
    ) -> None:
        mapped_key = CharacterCombatMathModelBuilder._item_base_key(key, slot=slot, item_type=item_type, tags=tags)
        CharacterCombatMathModelBuilder._set_base_modifier(modifiers, mapped_key, value)

    @staticmethod
    def _set_base_modifier(modifiers: RawStatBlock, key: str, value: Any) -> None:
        key = MODIFIER_ALIASES.get(key, key)
        if key not in COMBAT_MODIFIER_KEYS:
            return
        numeric = CharacterCombatMathModelBuilder._float_value(value)
        if numeric is None:
            return
        modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
        modifiers[key]["base"] = round(float(modifiers[key].get("base", 0.0) or 0.0) + numeric, 4)

    @staticmethod
    def _replace_base_modifier(modifiers: RawStatBlock, key: str, value: Any) -> None:
        key = MODIFIER_ALIASES.get(key, key)
        if key not in COMBAT_MODIFIER_KEYS:
            return
        numeric = CharacterCombatMathModelBuilder._float_value(value)
        if numeric is None:
            return
        modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
        modifiers[key]["base"] = round(numeric, 4)

    @staticmethod
    def _item_base_key(key: str, *, slot: str, item_type: str, tags: list[str]) -> str:
        if key == "physical_accuracy":
            if slot == "main_hand":
                return "main_hand_accuracy"
            if slot == "off_hand" and not CharacterCombatMathModelBuilder._is_shield(item_type, tags):
                return "off_hand_accuracy"
            return "accuracy"
        if key == "physical_crit_chance":
            if slot == "main_hand":
                return "main_hand_crit_chance"
            if slot == "off_hand" and not CharacterCombatMathModelBuilder._is_shield(item_type, tags):
                return "off_hand_crit_chance"
            return "crit_chance"
        return MODIFIER_ALIASES.get(key, key)

    @staticmethod
    def _empty_modifiers() -> RawStatBlock:
        defaults = CombatModifiersDTO().model_dump(mode="json")
        return {
            key: {"base": float(value or 0.0), "source": {}, "temp": {}}
            for key, value in defaults.items()
            if key in COMBAT_MODIFIER_KEYS
        }

    @staticmethod
    def _first_numeric(data: dict[str, Any], keys: tuple[str, ...]) -> float | None:
        for key in keys:
            value = CharacterCombatMathModelBuilder._float_value(data.get(key))
            if value is not None:
                return value
        return None

    @staticmethod
    def _skill_values(skills: dict[str, Any]) -> dict[str, float]:
        values: dict[str, float] = {}
        for key, raw in skills.items():
            if isinstance(raw, dict):
                value = raw.get("value", raw.get("level", raw.get("total_xp", raw.get("xp", 0.0))))
            else:
                value = raw
            numeric = CharacterCombatMathModelBuilder._float_value(value)
            values[str(key)] = numeric if numeric is not None else 0.0
        return values

    @staticmethod
    def _float_value(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _dump(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return dict(value) if isinstance(value, dict) else {}


__all__ = ["COMBAT_MODIFIER_KEYS", "CharacterCombatMathModelBuilder", "RawCombatMathModel", "RawStatBlock"]
