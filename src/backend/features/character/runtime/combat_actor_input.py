from __future__ import annotations

from typing import Any

from src.backend.features.character.runtime.combat_math_model import CharacterCombatMathModelBuilder
from src.backend.features.game_catalog.combat.resources.feints.availability import build_known_feints


class CharacterCombatActorInputBuilder:
    """Builds combat-facing actor input from a game:ac document."""

    def __init__(self, math_model: CharacterCombatMathModelBuilder | None = None) -> None:
        self.math_model = math_model or CharacterCombatMathModelBuilder()

    def build_input(self, active_character: dict[str, Any]) -> dict[str, Any]:
        items = self._dict(active_character.get("items"))
        flat_skills = self._flat_skills(self._dict(active_character.get("skills")))
        return {
            "meta": self._meta(active_character),
            "source": self._source(active_character),
            "status": self._dict(active_character.get("vitals")),
            "raw": self.math_model.build_raw(
                attributes=active_character.get("attributes") or {},
                items=items,
                skills=flat_skills,
            ),
            "skills": flat_skills,
            "loadout": self._loadout(items, flat_skills),
        }

    def build_snapshot(self, active_character: dict[str, Any]) -> dict[str, Any]:
        actor_input = self.build_input(active_character)
        return {
            "meta": actor_input["meta"],
            "source": actor_input["source"],
            "status": actor_input["status"],
            "combat": {
                "math_model": actor_input["raw"],
                "skills": actor_input["skills"],
                "loadout": actor_input["loadout"],
            },
        }

    @staticmethod
    def _meta(active_character: dict[str, Any]) -> dict[str, Any]:
        bio = CharacterCombatActorInputBuilder._dict(active_character.get("bio"))
        char_id = active_character.get("char_id")
        return {
            "actor_type": "player",
            "actor_id": char_id,
            "name": bio.get("name") or f"Character {char_id}",
            "gender": bio.get("gender"),
            "avatar_url": bio.get("avatar"),
            "role": "player",
            "tags": ["player"],
        }

    @staticmethod
    def _source(active_character: dict[str, Any]) -> dict[str, Any]:
        location = CharacterCombatActorInputBuilder._dict(active_character.get("location"))
        source = {
            "character_id": active_character.get("char_id"),
            "user_id": str(active_character.get("user_id") or ""),
            "location_id": location.get("current"),
            "db_refs": {"characters": active_character.get("char_id")},
        }
        symbiote = CharacterCombatActorInputBuilder._dict(active_character.get("symbiote"))
        if symbiote:
            source["symbiote"] = symbiote
        return source

    @staticmethod
    def _loadout(items: dict[str, Any], flat_skills: dict[str, float]) -> dict[str, Any]:
        layout = CharacterCombatActorInputBuilder._dict(items.get("layout"))
        equipment_layout = CharacterCombatActorInputBuilder._dict(layout.get("equipment"))
        belt_layout = CharacterCombatActorInputBuilder._dict(layout.get("belt"))
        by_id = CharacterCombatActorInputBuilder._dict(items.get("by_id"))

        combat_layout: dict[str, str] = {}
        hand_usage: dict[str, str] = {}
        weapon_slots: list[str] = []
        for slot, item_id in equipment_layout.items():
            if not item_id:
                continue
            item = CharacterCombatActorInputBuilder._dict(by_id.get(str(item_id)))
            skill_key = CharacterCombatActorInputBuilder._skill_key_for_slot(str(slot), item)
            combat_slot = CharacterCombatActorInputBuilder._combat_slot(str(slot))
            item_type = CharacterCombatActorInputBuilder._item_type(item)
            if str(slot) == "two_hand":
                hand_usage[combat_slot] = "two_hand"
            if item_type == "weapon" and str(slot) != "two_hand":
                weapon_slots.append(combat_slot)
            if skill_key:
                combat_layout[combat_slot] = skill_key
            trigger_id = CharacterCombatActorInputBuilder._first_trigger(item)
            if trigger_id and combat_slot in {"main_hand", "off_hand"}:
                combat_layout[f"{combat_slot}_trigger"] = trigger_id

        if "main_hand" not in combat_layout:
            combat_layout["main_hand"] = "skill_unarmed"

        tactical_style = CharacterCombatActorInputBuilder._tactical_style(combat_layout, hand_usage, weapon_slots)
        if tactical_style:
            combat_layout["tactical_style"] = tactical_style[0]
            combat_layout["tactical_style_trigger"] = tactical_style[1]

        belt = []
        for belt_slot, item_id in belt_layout.items():
            if not item_id:
                continue
            item = CharacterCombatActorInputBuilder._dict(by_id.get(str(item_id)))
            if item:
                belt.append({**item, "belt_slot": str(belt_slot)})

        loadout = {
            "layout": combat_layout,
            "equipment_layout": {str(slot): str(item_id) for slot, item_id in equipment_layout.items() if item_id},
            "hand_usage": hand_usage,
            "two_handed": bool(hand_usage),
            "weapon_slots": sorted(set(weapon_slots)),
            "belt": belt,
            "abilities": CharacterCombatActorInputBuilder._known_abilities(by_id),
            "known_abilities": CharacterCombatActorInputBuilder._known_abilities(by_id),
            "skills": sorted(flat_skills),
        }
        loadout["known_feints"] = build_known_feints(loadout, flat_skills)
        return loadout

    @staticmethod
    def _tactical_style(
        combat_layout: dict[str, str], hand_usage: dict[str, str], weapon_slots: list[str]
    ) -> tuple[str, str] | None:
        if hand_usage.get("main_hand") == "two_hand":
            return "skill_two_handed", "accuracy.style_2h_ignore"

        if combat_layout.get("off_hand") == "skill_shield_mastery":
            return "skill_shield_mastery", "block.style_shield_reflect"

        weapon_slot_set = set(weapon_slots)
        if {"main_hand", "off_hand"}.issubset(weapon_slot_set):
            return "skill_dual_wield", "accuracy.style_dual_extra"

        if "main_hand" in weapon_slot_set and "off_hand" not in combat_layout:
            return "skill_one_handed", "accuracy.style_1h_flow"

        return None

    @staticmethod
    def _skill_key_for_slot(slot: str, item: dict[str, Any]) -> str | None:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        metadata = CharacterCombatActorInputBuilder._dict(item.get("metadata") or mechanics.get("metadata"))
        tags = CharacterCombatActorInputBuilder._tags(item, mechanics)
        item_type = str(item.get("item_type") or item.get("type") or mechanics.get("item_type") or "")

        if slot == "off_hand" and (item_type == "shield" or "shield" in tags or "buckler" in tags):
            return "skill_shield_mastery"

        for key in ("skill_key", "weapon_skill_key", "armor_skill_key", "related_skill"):
            value = item.get(key) or mechanics.get(key) or metadata.get(key)
            if value:
                return str(value)

        return None

    @staticmethod
    def _item_type(item: dict[str, Any]) -> str:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        return str(
            item.get("item_type") or item.get("type") or mechanics.get("item_type") or mechanics.get("type") or ""
        )

    @staticmethod
    def _combat_slot(slot: str) -> str:
        if slot == "two_hand":
            return "main_hand"
        if slot == "chest_armor":
            return "body"
        return slot

    @staticmethod
    def _first_trigger(item: dict[str, Any]) -> str | None:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        raw = item.get("triggers") or mechanics.get("triggers") or []
        return str(raw[0]) if isinstance(raw, list) and raw else None

    @staticmethod
    def _known_abilities(by_id: dict[str, Any]) -> list[str]:
        abilities: list[str] = []
        for raw_item in by_id.values():
            item = CharacterCombatActorInputBuilder._dict(raw_item)
            mechanics = CharacterCombatActorInputBuilder._mechanics(item)
            raw = item.get("abilities") or item.get("known_abilities") or mechanics.get("abilities") or []
            if isinstance(raw, list):
                abilities.extend(str(value) for value in raw if value)
        return list(dict.fromkeys(abilities))

    @staticmethod
    def _flat_skills(skills: dict[str, Any]) -> dict[str, float]:
        flat: dict[str, float] = {}
        for key, raw in skills.items():
            if isinstance(raw, dict):
                value = raw.get("value", raw.get("level", raw.get("total_xp", raw.get("xp", 0.0))))
            else:
                value = raw
            try:
                flat[str(key)] = round(float(value or 0.0), 4)
            except (TypeError, ValueError):
                flat[str(key)] = 0.0
        return flat

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
    def _dict(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return value if isinstance(value, dict) else {}


__all__ = ["CharacterCombatActorInputBuilder"]
