from __future__ import annotations

from typing import Any

from src.backend.features.character.dto.modifiers import CombatModifiersDTO
from src.backend.features.character.runtime.item_sync import (
    apply_penalty_sync,
    item_combat_tier,
    symbiote_tier,
    sync_factors,
)
from src.backend.features.character.runtime.rules.attribute_modifiers import ATTRIBUTE_MODIFIER_RULES
from src.backend.features.character.runtime.vital_profile import resolve_player_vital_profile_key_from_equipped
from src.backend.features.character.schemas.session import CharacterSessionAttributesDTO
from src.shared.enums.stats_enums import StatKey

RawStatBlock = dict[str, dict[str, Any]]
RawCombatMathModel = dict[str, Any]

ATTRIBUTE_KEYS = tuple(CharacterSessionAttributesDTO.model_fields)
COMBAT_MODIFIER_KEYS = frozenset(CombatModifiersDTO.model_fields)
UNARMED_DAMAGE_SPREAD = 0.50
ARMOR_BEARING_SLOTS = frozenset({"head_armor", "chest_armor", "arms_armor", "legs_armor"})
JEWELRY_SLOTS = frozenset({"ring_1", "ring_2", "amulet", "earring"})
HEAVY_CHEST_DODGE_CAPS = {
    "plate_chest": 0.35,
}
HEAVY_ARMOR_NATURAL_RESISTANCE_BONUS_AT_FULL = 0.50
PHYSICAL_RESISTANCE_PER_ENDURANCE = ATTRIBUTE_MODIFIER_RULES[StatKey.PHYSICAL_RESISTANCE][StatKey.ENDURANCE]
MEDIUM_CHEST_DODGE_CAP_PENALTY = -0.20
LIGHT_ARMOR_SKILL_DODGE_CAP_BOOST = 0.20
DUAL_WIELD_DAMAGE_QUALITY_MIN = 0.50
DUAL_WIELD_DAMAGE_QUALITY_MAX = 0.80
DUAL_WIELD_RESTORE_QUALITY_MIN = 0.50
DUAL_WIELD_RESTORE_QUALITY_MAX = 1.00
DUAL_WIELD_PENALTY_MULT_MIN = 1.00
DUAL_WIELD_PENALTY_MULT_MAX = 2.00
DUAL_WIELD_DAMAGE_FIELDS = frozenset({"main_hand_damage_base", "off_hand_damage_base"})
DUAL_WIELD_RESTORE_FIELDS = frozenset({"main_hand_crit_chance", "off_hand_crit_chance", "parry"})
DUAL_WIELD_PENALTY_FIELDS = frozenset(
    {
        "main_hand_accuracy_penalty",
        "off_hand_accuracy_penalty",
        "main_hand_damage_spread",
        "off_hand_damage_spread",
    }
)
ITEM_SYNC_POSITIVE_PENALTY_KEYS = frozenset(
    {
        "main_hand_accuracy_penalty",
        "off_hand_accuracy_penalty",
        "weapon_accuracy_penalty",
        "item_accuracy_penalty",
    }
)
ITEM_SYNC_NEGATIVE_PENALTY_KEYS = frozenset(
    {
        "anti_dodge_chance",
        "evasion_penalty",
        "parry_penalty",
        "stamina_regen",
    }
)
MODIFIER_ALIASES = {
    "block_chance": "block",
    "damage_reduction_flat": "armor",
    "dodge_chance": "evasion",
    "energy_max": "en",
    "evasion_penalty": "evasion",
    "hp_max": "hp",
    "magical_resistance": "magic_resist",
    "magical_armor": "magic_armor",
    "magic_resistance": "magic_resist",
    "parry_penalty": "parry",
    "parry_chance": "parry",
    "physical_accuracy": "accuracy",
    "physical_crit_chance": "crit_chance",
    "physical_crit_power_float": "crit_power",
}


class CharacterCombatMathModelBuilder:
    """Builds combat raw math input from active-character runtime data."""

    def build_raw(
        self,
        *,
        attributes: Any,
        items: dict[str, Any] | None = None,
        skills: dict[str, Any] | None = None,
        symbiote: dict[str, Any] | None = None,
    ) -> RawCombatMathModel:
        equipped = self._equipped_items(items or {})
        attributes_data = self._dump(attributes)
        raw_attributes = self._build_attributes(attributes_data)
        return {
            "attributes": raw_attributes,
            "modifiers": self._build_modifiers(
                equipped,
                attributes_data,
                skills or {},
                raw_attributes,
                symbiote=symbiote,
            ),
            "rules": {"attribute_profile": resolve_player_vital_profile_key_from_equipped(equipped)},
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
        *,
        symbiote: dict[str, Any] | None = None,
    ) -> RawStatBlock:
        modifiers = self._empty_modifiers()
        symbiote_rank = symbiote_tier(symbiote)
        dual_quality = self._dual_wield_quality(equipment, skills)
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
            armor_class = self._armor_class(item, mechanics)
            dual_weapon_quality = (
                dual_quality
                if self._is_dual_wield_weapon(
                    slot=slot,
                    combat_slot=combat_slot,
                    item_type=item_type,
                    tags=tags,
                )
                else None
            )
            if combat_slot == "chest_armor" and item_type == "armor":
                chest_item = item
            if combat_slot == "main_hand" and item_type == "weapon":
                has_main_hand_weapon = True

            power = self._float_value(mechanics.get("power", mechanics.get("base_power")))
            if power:
                power = self._apply_dual_wield_quality_to_value(
                    f"{combat_slot}_damage_base",
                    power,
                    dual_weapon_quality,
                )
                self._add_power_modifier(modifiers, slot=combat_slot, item_type=item_type, tags=tags, value=power)

            damage_spread = self._float_value(mechanics.get("damage_spread"))
            if damage_spread is not None:
                damage_spread = self._apply_dual_wield_quality_to_value(
                    f"{combat_slot}_damage_spread",
                    damage_spread,
                    dual_weapon_quality,
                )
                if combat_slot == "main_hand":
                    self._replace_base_modifier(modifiers, "main_hand_damage_spread", damage_spread)
                elif combat_slot == "off_hand" and not self._is_shield(item_type, tags):
                    self._replace_base_modifier(modifiers, "off_hand_damage_spread", damage_spread)

            for bonus_key, value in (mechanics.get("implicit_bonuses") or {}).items():
                value, extra_bonuses = self._apply_item_sync_to_implicit_bonus(
                    item,
                    mechanics,
                    str(bonus_key),
                    value,
                    skills,
                    item_type=item_type,
                    armor_class=armor_class,
                    symbiote_rank=symbiote_rank,
                )
                self._add_item_base_modifier(
                    modifiers,
                    str(bonus_key),
                    value,
                    slot=combat_slot,
                    item_type=item_type,
                    tags=tags,
                    dual_quality=dual_weapon_quality,
                )
                for extra_key, extra_value in extra_bonuses.items():
                    self._add_item_base_modifier(
                        modifiers,
                        extra_key,
                        extra_value,
                        slot=combat_slot,
                        item_type=item_type,
                        tags=tags,
                    )
            for bonus_key, value in (mechanics.get("bonuses") or {}).items():
                mapped_key = MODIFIER_ALIASES.get(bonus_key, bonus_key)
                command = str(value)
                if mapped_key in ATTRIBUTE_KEYS:
                    self._set_attribute_source_command(raw_attributes, mapped_key, source, command)
                else:
                    self._add_item_source_modifier(
                        modifiers,
                        bonus_key,
                        source,
                        command,
                        slot=combat_slot,
                        item_type=item_type,
                        tags=tags,
                    )

        if not has_main_hand_weapon:
            self._apply_unarmed_base(modifiers, attributes)

        self._apply_armor_dodge_cap_rules(modifiers, chest_item, skills, attributes)

        return modifiers

    @staticmethod
    def _dual_wield_quality(equipment: list[dict[str, Any]], skills: dict[str, Any]) -> dict[str, float] | None:
        weapon_slots: set[str] = set()
        for item in equipment:
            mechanics = CharacterCombatMathModelBuilder._mechanics(item)
            slot = str(item.get("slot") or mechanics.get("slot") or "")
            combat_slot = CharacterCombatMathModelBuilder._combat_slot(slot)
            item_type = str(
                item.get("item_type") or item.get("type") or mechanics.get("item_type") or mechanics.get("type") or ""
            )
            tags = CharacterCombatMathModelBuilder._tags(item, mechanics)
            if CharacterCombatMathModelBuilder._is_dual_wield_weapon(
                slot=slot,
                combat_slot=combat_slot,
                item_type=item_type,
                tags=tags,
            ):
                weapon_slots.add(combat_slot)

        if not {"main_hand", "off_hand"}.issubset(weapon_slots):
            return None

        skill = CharacterCombatMathModelBuilder._skill_value(skills.get("skill_dual_wield"))
        return {
            "damage": DUAL_WIELD_DAMAGE_QUALITY_MIN
            + ((DUAL_WIELD_DAMAGE_QUALITY_MAX - DUAL_WIELD_DAMAGE_QUALITY_MIN) * skill),
            "restore": DUAL_WIELD_RESTORE_QUALITY_MIN
            + ((DUAL_WIELD_RESTORE_QUALITY_MAX - DUAL_WIELD_RESTORE_QUALITY_MIN) * skill),
            "penalty": DUAL_WIELD_PENALTY_MULT_MAX
            - ((DUAL_WIELD_PENALTY_MULT_MAX - DUAL_WIELD_PENALTY_MULT_MIN) * skill),
        }

    @staticmethod
    def _is_dual_wield_weapon(*, slot: str, combat_slot: str, item_type: str, tags: list[str]) -> bool:
        return (
            slot != "two_hand"
            and combat_slot in {"main_hand", "off_hand"}
            and item_type == "weapon"
            and not CharacterCombatMathModelBuilder._is_shield(item_type, tags)
        )

    @staticmethod
    def _apply_dual_wield_quality_to_value(
        key: str,
        value: Any,
        dual_quality: dict[str, float] | None,
    ) -> Any:
        if dual_quality is None:
            return value
        numeric = CharacterCombatMathModelBuilder._float_value(value)
        if numeric is None:
            return value
        if key in DUAL_WIELD_DAMAGE_FIELDS:
            return round(numeric * dual_quality["damage"], 4)
        if key in DUAL_WIELD_RESTORE_FIELDS:
            return round(numeric * dual_quality["restore"], 4)
        if key in DUAL_WIELD_PENALTY_FIELDS:
            return round(numeric * dual_quality["penalty"], 4)
        return value

    @staticmethod
    def _apply_armor_dodge_cap_rules(
        modifiers: RawStatBlock,
        chest_item: dict[str, Any] | None,
        skills: dict[str, Any],
        attributes: dict[str, Any],
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
            skill = CharacterCombatMathModelBuilder._skill_value(skills.get("skill_heavy_armor"))
            endurance = CharacterCombatMathModelBuilder._float_value(attributes.get("endurance")) or 0.0
            natural_resistance = endurance * PHYSICAL_RESISTANCE_PER_ENDURANCE
            skill_bonus = natural_resistance * HEAVY_ARMOR_NATURAL_RESISTANCE_BONUS_AT_FULL * skill
            if skill_bonus > 0:
                CharacterCombatMathModelBuilder._add_modifier(
                    modifiers,
                    "physical_resistance",
                    "skill:skill_heavy_armor:natural_resistance",
                    skill_bonus,
                )
            return

        if armor_class == "medium":
            tier_mult = CharacterCombatMathModelBuilder._tier_mult(chest_item, mechanics)
            penalty = round(MEDIUM_CHEST_DODGE_CAP_PENALTY * tier_mult, 4)
            CharacterCombatMathModelBuilder._add_modifier(
                modifiers, "dodge_cap", f"{source}:medium_cap_penalty", penalty
            )
            skill = CharacterCombatMathModelBuilder._skill_value(skills.get("skill_medium_armor"))
            if skill > 0:
                recovery = min(abs(penalty), skill * abs(penalty))
                CharacterCombatMathModelBuilder._add_modifier(
                    modifiers, "dodge_cap", "skill:skill_medium_armor", recovery
                )
            return

        if armor_class == "light":
            skill = CharacterCombatMathModelBuilder._skill_value(skills.get("skill_light_armor"))
            if skill > 0:
                skill_boost = min(LIGHT_ARMOR_SKILL_DODGE_CAP_BOOST, skill * LIGHT_ARMOR_SKILL_DODGE_CAP_BOOST)
                CharacterCombatMathModelBuilder._add_modifier(
                    modifiers, "dodge_cap", "skill:skill_light_armor", skill_boost
                )

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
        if item_type == "accessory" and slot in JEWELRY_SLOTS:
            self._set_base_modifier(modifiers, "magic_armor", value)
            return

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
    def _armor_class(item: dict[str, Any], mechanics: dict[str, Any]) -> str:
        metadata = CharacterCombatMathModelBuilder._dump(item.get("metadata") or mechanics.get("metadata"))
        return str(item.get("armor_class") or mechanics.get("armor_class") or metadata.get("armor_class") or "")

    @staticmethod
    def _tier_mult(item: dict[str, Any], mechanics: dict[str, Any]) -> float:
        material = CharacterCombatMathModelBuilder._dump(item.get("material") or mechanics.get("material"))
        raw = item.get("tier_mult") or mechanics.get("tier_mult") or material.get("tier_mult")
        value = CharacterCombatMathModelBuilder._float_value(raw)
        if value is None or value <= 0:
            return 1.0
        return value

    @staticmethod
    def _apply_item_sync_to_implicit_bonus(
        item: dict[str, Any],
        mechanics: dict[str, Any],
        bonus_key: str,
        scaled_value: Any,
        skills: dict[str, Any],
        *,
        item_type: str,
        armor_class: str,
        symbiote_rank: int,
    ) -> tuple[Any, dict[str, float]]:
        if not CharacterCombatMathModelBuilder._is_sync_penalty_key(bonus_key):
            return scaled_value, {}
        if item_type not in {"armor", "weapon", "shield"}:
            return scaled_value, {}

        scaled_numeric = CharacterCombatMathModelBuilder._float_value(scaled_value)
        if scaled_numeric is None:
            return scaled_value, {}

        base_value = CharacterCombatMathModelBuilder._base_implicit_value(mechanics, bonus_key, scaled_numeric)
        skill = CharacterCombatMathModelBuilder._item_sync_skill(
            item, mechanics, skills, item_type=item_type, armor_class=armor_class
        )
        factors = sync_factors(
            symbiote_rank=symbiote_rank,
            item_tier=item_combat_tier(item, mechanics),
        )
        effective, bonus = apply_penalty_sync(
            base_value=base_value,
            scaled_value=scaled_numeric,
            skill=skill,
            factors=factors,
        )
        extra_bonuses: dict[str, float] = {}
        if bonus > 0.0 and bonus_key in ITEM_SYNC_POSITIVE_PENALTY_KEYS:
            extra_bonuses["physical_accuracy"] = bonus
        return effective, extra_bonuses

    @staticmethod
    def _is_sync_penalty_key(key: str) -> bool:
        return key in ITEM_SYNC_POSITIVE_PENALTY_KEYS or key in ITEM_SYNC_NEGATIVE_PENALTY_KEYS

    @staticmethod
    def _base_implicit_value(mechanics: dict[str, Any], key: str, scaled_value: float) -> float:
        base_bonuses = CharacterCombatMathModelBuilder._dump(mechanics.get("implicit_bonuses_base"))
        base_value = CharacterCombatMathModelBuilder._float_value(base_bonuses.get(key))
        if base_value is not None:
            return base_value
        tier_mult = CharacterCombatMathModelBuilder._tier_mult({}, mechanics)
        return round(scaled_value / tier_mult, 4)

    @staticmethod
    def _item_sync_skill(
        item: dict[str, Any],
        mechanics: dict[str, Any],
        skills: dict[str, Any],
        *,
        item_type: str,
        armor_class: str,
    ) -> float:
        related_skill = str(
            item.get("related_skill")
            or mechanics.get("related_skill")
            or CharacterCombatMathModelBuilder._dump(item.get("metadata") or mechanics.get("metadata")).get(
                "related_skill"
            )
            or ""
        )
        if not related_skill and item_type == "armor" and armor_class in {"light", "medium", "heavy"}:
            related_skill = f"skill_{armor_class}_armor"
        return max(0.0, min(1.0, float(skills.get(related_skill, 0.0) or 0.0)))

    @staticmethod
    def _is_shield(item_type: str, tags: list[str]) -> bool:
        return item_type == "shield" or "shield" in tags

    @staticmethod
    def _is_guard_shield(item_type: str, tags: list[str]) -> bool:
        return CharacterCombatMathModelBuilder._is_shield(item_type, tags)

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
    def _add_item_source_modifier(
        modifiers: RawStatBlock,
        key: str,
        source: str,
        value: Any,
        *,
        slot: str,
        item_type: str,
        tags: list[str],
    ) -> None:
        mapped_key = MODIFIER_ALIASES.get(key, key)
        if mapped_key == "armor" and not CharacterCombatMathModelBuilder._allows_armor_modifier(
            slot=slot,
            item_type=item_type,
            tags=tags,
        ):
            return
        CharacterCombatMathModelBuilder._add_modifier(modifiers, key, source, value)

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
        dual_quality: dict[str, float] | None = None,
    ) -> None:
        mapped_key = CharacterCombatMathModelBuilder._item_base_key(key, slot=slot, item_type=item_type, tags=tags)
        if mapped_key == "armor" and not CharacterCombatMathModelBuilder._allows_armor_modifier(
            slot=slot,
            item_type=item_type,
            tags=tags,
        ):
            return
        value = CharacterCombatMathModelBuilder._apply_dual_wield_quality_to_value(mapped_key, value, dual_quality)
        CharacterCombatMathModelBuilder._set_base_modifier(modifiers, mapped_key, value)

    @staticmethod
    def _allows_armor_modifier(*, slot: str, item_type: str, tags: list[str]) -> bool:
        return (
            item_type == "armor"
            and slot in ARMOR_BEARING_SLOTS
            and not CharacterCombatMathModelBuilder._is_shield(
                item_type,
                tags,
            )
        )

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
        if (
            key
            in {
                "weapon_accuracy_penalty",
                "main_hand_accuracy_penalty",
                "off_hand_accuracy_penalty",
            }
            and item_type == "weapon"
        ):
            if slot == "off_hand" and not CharacterCombatMathModelBuilder._is_shield(item_type, tags):
                return "off_hand_accuracy_penalty"
            return "main_hand_accuracy_penalty"
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
