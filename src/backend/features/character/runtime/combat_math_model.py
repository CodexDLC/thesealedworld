from __future__ import annotations

from typing import Any

from src.backend.features.character.dto.modifiers import CombatModifiersDTO
from src.backend.features.character.schemas.session import CharacterSessionAttributesDTO
from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG
from src.backend.features.items.resources.modifier_contracts import MODIFIER_CONTRACTS, compile_modifier_command

RawStatBlock = dict[str, dict[str, Any]]
RawCombatMathModel = dict[str, Any]

ATTRIBUTE_KEYS = tuple(CharacterSessionAttributesDTO.model_fields)
COMBAT_MODIFIER_KEYS = frozenset(CombatModifiersDTO.model_fields)
UNARMED_DAMAGE_SPREAD = 0.50
HEAVY_CHEST_DODGE_CAPS = {
    "plate_chest": 0.35,
}
MEDIUM_CHEST_DODGE_CAP_PENALTY = -0.10
MEDIUM_ARMOR_DODGE_CAP_RECOVERY = 0.10
LIGHT_ARMOR_DODGE_CAP_BOOST = 0.20
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
        attributes_data = self._dump(attributes)
        raw_attributes = self._build_attributes(attributes_data)
        return {
            "attributes": raw_attributes,
            "modifiers": self._build_modifiers(equipped, attributes_data, skills or {}, raw_attributes),
            "rules": {"attribute_profile": "player"},
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
        self,
        equipment: list[dict[str, Any]],
        attributes: dict[str, Any],
        skills: dict[str, Any],
        raw_attributes: RawStatBlock,
    ) -> RawStatBlock:
        modifiers = self._empty_modifiers()
        has_main_hand_weapon = False
        chest_item: dict[str, Any] | None = None
        for item in equipment:
            item_id = str(item.get("item_id") or item.get("inventory_id") or item.get("id") or "")
            if not item_id:
                continue

            source = f"item:{item_id}"
            mechanics = self._mechanics(item)
            slot = str(item.get("slot") or mechanics.get("slot") or "")
            combat_slot = self._combat_slot(slot)
            item_type = str(
                item.get("item_type") or item.get("type") or mechanics.get("item_type") or mechanics.get("type") or ""
            )
            tags = self._tags(item, mechanics)
            if combat_slot == "chest_armor" and item_type == "armor":
                chest_item = item
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
            self._apply_affix_sources(raw_attributes, modifiers, mechanics, source)

        if not has_main_hand_weapon:
            self._apply_unarmed_base(modifiers, attributes)

        self._apply_armor_dodge_cap_rules(modifiers, chest_item, skills)

        return modifiers

    @staticmethod
    def _apply_affix_sources(
        raw_attributes: RawStatBlock,
        modifiers: RawStatBlock,
        mechanics: dict[str, Any],
        item_source: str,
    ) -> None:
        affixes = mechanics.get("affixes") or []
        if not isinstance(affixes, list):
            return
        for raw_affix in affixes:
            if not isinstance(raw_affix, dict):
                continue
            affix_id = str(raw_affix.get("affix_id") or "")
            if not affix_id:
                continue
            entry = AFFIX_CATALOG.get(affix_id)
            if entry is None:
                continue
            contract = MODIFIER_CONTRACTS.get(entry.technical.modifier_id)
            if contract is None:
                continue
            value = CharacterCombatMathModelBuilder._float_value(raw_affix.get("value"))
            if value is None:
                continue
            command = compile_modifier_command(contract, value)
            source_id = f"{item_source}:affix:{affix_id}"
            target = MODIFIER_ALIASES.get(contract.target_field, contract.target_field)

            if contract.default_layer == "attributes" or target in ATTRIBUTE_KEYS:
                if target not in ATTRIBUTE_KEYS:
                    continue
                CharacterCombatMathModelBuilder._set_attribute_source_command(
                    raw_attributes, target, source_id, command
                )
                continue

            if contract.default_layer == "world" and target not in COMBAT_MODIFIER_KEYS:
                continue

            CharacterCombatMathModelBuilder._set_source_command(modifiers, target, source_id, command)

    @staticmethod
    def _apply_armor_dodge_cap_rules(
        modifiers: RawStatBlock, chest_item: dict[str, Any] | None, skills: dict[str, Any]
    ) -> None:
        if not chest_item:
            return

        mechanics = CharacterCombatMathModelBuilder._mechanics(chest_item)
        armor_class = str(chest_item.get("armor_class") or mechanics.get("armor_class") or "")
        if not armor_class:
            return

        item_id = str(chest_item.get("item_id") or chest_item.get("inventory_id") or chest_item.get("id") or "")
        source = f"item:{item_id}" if item_id else "item:chest_armor"
        base_id = str(chest_item.get("base_id") or mechanics.get("base_id") or mechanics.get("id") or item_id)

        if armor_class == "heavy":
            cap = HEAVY_CHEST_DODGE_CAPS.get(base_id, 0.35)
            CharacterCombatMathModelBuilder._set_source_command(modifiers, "dodge_cap", source, f"={cap:.2f}")
            return

        if armor_class == "medium":
            CharacterCombatMathModelBuilder._add_modifier(
                modifiers, "dodge_cap", f"{source}:medium_cap_penalty", MEDIUM_CHEST_DODGE_CAP_PENALTY
            )
            skill = CharacterCombatMathModelBuilder._skill_value(skills.get("skill_medium_armor"))
            if skill > 0:
                recovery = min(MEDIUM_ARMOR_DODGE_CAP_RECOVERY, skill * MEDIUM_ARMOR_DODGE_CAP_RECOVERY)
                CharacterCombatMathModelBuilder._add_modifier(
                    modifiers, "dodge_cap", "skill:skill_medium_armor", recovery
                )
            return

        if armor_class == "light":
            skill = CharacterCombatMathModelBuilder._skill_value(skills.get("skill_light_armor"))
            if skill > 0:
                boost = min(LIGHT_ARMOR_DODGE_CAP_BOOST, skill * LIGHT_ARMOR_DODGE_CAP_BOOST)
                CharacterCombatMathModelBuilder._add_modifier(modifiers, "dodge_cap", "skill:skill_light_armor", boost)

    @staticmethod
    def _apply_unarmed_base(modifiers: RawStatBlock, attributes: dict[str, Any]) -> None:
        strength = CharacterCombatMathModelBuilder._float_value(attributes.get("strength")) or 0.0
        CharacterCombatMathModelBuilder._set_base_modifier(modifiers, "main_hand_damage_base", strength)
        CharacterCombatMathModelBuilder._replace_base_modifier(
            modifiers, "main_hand_damage_spread", UNARMED_DAMAGE_SPREAD
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
            if not self._is_shield(item_type, tags):
                self._set_base_modifier(modifiers, "off_hand_damage_base", value)
            elif self._is_guard_shield(item_type, tags):
                self._set_base_modifier(modifiers, "shield_guard_power", value)
            return
        if slot.endswith("_armor"):
            self._set_base_modifier(modifiers, "armor", value)
            return
        if item_type == "garment" and (slot.endswith("_garment") or slot == "feetwear"):
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
    def _is_guard_shield(item_type: str, tags: list[str]) -> bool:
        return CharacterCombatMathModelBuilder._is_shield(item_type, tags) and "buckler" not in tags

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
    def _set_source_command(modifiers: RawStatBlock, key: str, source: str, command: str) -> None:
        key = MODIFIER_ALIASES.get(key, key)
        if key not in COMBAT_MODIFIER_KEYS:
            return
        modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
        modifiers[key]["source"][source] = command

    @staticmethod
    def _set_attribute_source_command(attributes: RawStatBlock, key: str, source: str, command: str) -> None:
        if key not in ATTRIBUTE_KEYS:
            return
        attributes.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
        attributes[key]["source"][source] = command

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
        if (
            key
            in {
                "weapon_armor_penetration_pct",
                "main_hand_armor_penetration_pct",
                "off_hand_armor_penetration_pct",
            }
            and item_type == "weapon"
        ):
            if slot == "main_hand":
                return "main_hand_armor_penetration_pct"
            if slot == "off_hand" and not CharacterCombatMathModelBuilder._is_shield(item_type, tags):
                return "off_hand_armor_penetration_pct"
        if (
            key
            in {
                "weapon_armor_ignore_chance",
                "main_hand_armor_ignore_chance",
                "off_hand_armor_ignore_chance",
            }
            and item_type == "weapon"
        ):
            if slot == "main_hand":
                return "main_hand_armor_ignore_chance"
            if slot == "off_hand" and not CharacterCombatMathModelBuilder._is_shield(item_type, tags):
                return "off_hand_armor_ignore_chance"
        return MODIFIER_ALIASES.get(key, key)

    @staticmethod
    def _empty_modifiers() -> RawStatBlock:
        from src.backend.features.character.runtime.rules.attribute_modifiers import DEFAULT_MODIFIER_VALUES

        defaults = {
            **CombatModifiersDTO().model_dump(mode="json"),
            **DEFAULT_MODIFIER_VALUES,
        }
        return {
            key: {"base": float(value or 0.0), "source": {}, "temp": {}}
            for key, value in defaults.items()
            if key in COMBAT_MODIFIER_KEYS
        }

    @staticmethod
    def _float_value(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _skill_value(value: Any) -> float:
        if isinstance(value, dict):
            value = value.get("xp", value.get("value", value.get("level", 0.0)))
        return CharacterCombatMathModelBuilder._float_value(value) or 0.0

    @staticmethod
    def _dump(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return dict(value) if isinstance(value, dict) else {}


__all__ = [
    "COMBAT_MODIFIER_KEYS",
    "CharacterCombatMathModelBuilder",
    "RawCombatMathModel",
    "RawStatBlock",
]
