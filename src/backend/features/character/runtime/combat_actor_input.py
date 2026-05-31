from __future__ import annotations

from typing import Any

from src.backend.features.character.runtime.combat_math_model import CharacterCombatMathModelBuilder
from src.backend.features.character.runtime.item_sync import symbiote_tier, sync_factors
from src.backend.features.game_catalog.combat.resources.abilities.definitions.basic_gift import BASIC_GIFT_ABILITY_IDS
from src.backend.features.game_catalog.combat.resources.feints.availability import build_known_feints


class CharacterCombatActorInputBuilder:
    """Builds combat-facing actor input from a game:ac document."""

    def __init__(self, math_model: CharacterCombatMathModelBuilder | None = None) -> None:
        self.math_model = math_model or CharacterCombatMathModelBuilder()

    def build_input(self, active_character: dict[str, Any]) -> dict[str, Any]:
        items = self._dict(active_character.get("items"))
        symbiote = self._dict(active_character.get("symbiote"))
        flat_skills = self._flat_skills(self._dict(active_character.get("skills")))
        flat_skills = self._apply_pending_skills(flat_skills, active_character.get("pending_progress"))
        return {
            "meta": self._meta(active_character),
            "source": self._source(active_character),
            "status": self._dict(active_character.get("vitals")),
            "raw": self.math_model.build_raw(
                attributes=active_character.get("attributes") or {},
                items=items,
                skills=flat_skills,
                symbiote=symbiote,
            ),
            "skills": flat_skills,
            "loadout": self._loadout(items, flat_skills, symbiote),
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
            "archetype": "humanoid",
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
    def _loadout(
        items: dict[str, Any], flat_skills: dict[str, float], symbiote: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        layout = CharacterCombatActorInputBuilder._dict(items.get("layout"))
        equipment_layout = CharacterCombatActorInputBuilder._dict(layout.get("equipment"))
        belt_layout = CharacterCombatActorInputBuilder._dict(layout.get("belt"))
        by_id = CharacterCombatActorInputBuilder._dict(items.get("by_id"))

        combat_layout: dict[str, str] = {}
        hand_usage: dict[str, str] = {}
        weapon_slots: list[str] = []
        weapon_tiers: dict[str, int] = {}
        combat_surfaces: dict[str, dict[str, Any]] = {}
        equipment_refs: dict[str, dict[str, Any]] = {}
        quiver_payload: dict[str, Any] | None = None
        quiver_charges: int | None = None
        for slot, item_id in equipment_layout.items():
            if not item_id:
                continue
            item = CharacterCombatActorInputBuilder._dict(by_id.get(str(item_id)))
            if str(slot) == "quiver":
                quiver_payload = CharacterCombatActorInputBuilder._ammo_effect_payload(item)
                quiver_charges = CharacterCombatActorInputBuilder._ammo_charges(item, flat_skills)
            skill_key = CharacterCombatActorInputBuilder._skill_key_for_slot(str(slot), item)
            combat_slot = CharacterCombatActorInputBuilder._combat_slot(str(slot))
            item_type = CharacterCombatActorInputBuilder._item_type(item)
            equipment_refs[combat_slot] = CharacterCombatActorInputBuilder._equipment_ref(
                slot=str(slot),
                combat_slot=combat_slot,
                item_id=str(item_id),
                item=item,
                skill_key=skill_key,
                symbiote=symbiote,
            )
            if str(slot) == "two_hand":
                hand_usage[combat_slot] = "two_hand"
            if item_type == "weapon" and str(slot) != "two_hand":
                weapon_slots.append(combat_slot)
            if item_type == "weapon" and combat_slot in {"main_hand", "off_hand"}:
                weapon_tiers[combat_slot] = CharacterCombatActorInputBuilder._weapon_tier(item)
                combat_surfaces[combat_slot] = CharacterCombatActorInputBuilder._combat_surface(
                    slot=combat_slot,
                    item_id=str(item_id),
                    item=item,
                    skill_key=skill_key,
                )
            if skill_key:
                combat_layout[combat_slot] = skill_key
            trigger_id = CharacterCombatActorInputBuilder._first_trigger(item)
            if trigger_id and combat_slot in {"main_hand", "off_hand"}:
                combat_layout[f"{combat_slot}_trigger"] = trigger_id

        if "main_hand" not in combat_layout:
            combat_layout["main_hand"] = "skill_unarmed"
            combat_surfaces["main_hand"] = {
                "slot": "main_hand",
                "delivery": "unarmed",
                "surface": "hands",
                "tags": [],
                "item_id": "",
                "base_id": "",
                "skill_key": "skill_unarmed",
            }

        tactical_style = CharacterCombatActorInputBuilder._tactical_style(combat_layout, hand_usage, weapon_slots)
        if tactical_style:
            combat_layout["tactical_style"] = tactical_style[0]
            combat_layout["tactical_style_trigger"] = tactical_style[1]

        ammo_effects: dict[str, dict[str, Any]] = {}
        ammo_charges: dict[str, int] = {}
        ammo_charge_caps: dict[str, int] = {}
        if quiver_payload and combat_layout.get("main_hand") == "skill_archery":
            ammo_effects["main_hand"] = quiver_payload
        if quiver_charges is not None and combat_layout.get("main_hand") == "skill_archery":
            ammo_charges["main_hand"] = quiver_charges
            ammo_charge_caps["main_hand"] = quiver_charges

        belt = []
        for belt_slot, item_id in belt_layout.items():
            if not item_id:
                continue
            item = CharacterCombatActorInputBuilder._dict(by_id.get(str(item_id)))
            if item:
                belt.append({**item, "belt_slot": str(belt_slot)})

        known_abilities = CharacterCombatActorInputBuilder._known_abilities(by_id)
        default_known_abilities = list(dict.fromkeys([*BASIC_GIFT_ABILITY_IDS, *known_abilities]))

        loadout = {
            "layout": combat_layout,
            "equipment_layout": {str(slot): str(item_id) for slot, item_id in equipment_layout.items() if item_id},
            "hand_usage": hand_usage,
            "two_handed": bool(hand_usage),
            "weapon_slots": sorted(set(weapon_slots)),
            "weapon_tiers": weapon_tiers,
            "combat_surfaces": combat_surfaces,
            "equipment_refs": equipment_refs,
            "ammo_effects": ammo_effects,
            "ammo_charges": ammo_charges,
            "ammo_charge_caps": ammo_charge_caps,
            "belt": belt,
            "abilities": default_known_abilities,
            "known_abilities": default_known_abilities,
            "skills": sorted(flat_skills),
        }
        loadout["known_feints"] = build_known_feints(loadout, flat_skills)
        return loadout

    @staticmethod
    def _tactical_style(
        combat_layout: dict[str, str], hand_usage: dict[str, str], weapon_slots: list[str]
    ) -> tuple[str, str] | None:
        if combat_layout.get("main_hand") == "skill_archery":
            return "skill_ranged_combat", "dodge.style_ranged_perfect_backstep"

        if hand_usage.get("main_hand") == "two_hand":
            return "skill_two_handed", "accuracy.style_2h_ignore"

        if combat_layout.get("off_hand") == "skill_shield_mastery":
            return "skill_shield_mastery", "block.style_shield_reflect"

        weapon_slot_set = set(weapon_slots)
        if {"main_hand", "off_hand"}.issubset(weapon_slot_set):
            return "skill_dual_wield", "accuracy.style_dual_extra"

        return None

    @staticmethod
    def _skill_key_for_slot(slot: str, item: dict[str, Any]) -> str | None:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        metadata = CharacterCombatActorInputBuilder._dict(item.get("metadata") or mechanics.get("metadata"))
        tags = CharacterCombatActorInputBuilder._tags(item, mechanics)
        item_type = str(item.get("item_type") or item.get("type") or mechanics.get("item_type") or "")

        for key in ("skill_key", "weapon_skill_key", "armor_skill_key", "related_skill"):
            value = item.get(key) or mechanics.get(key) or metadata.get(key)
            if value:
                return str(value)

        if slot == "off_hand" and (item_type == "shield" or ("shield" in tags and "buckler" not in tags)):
            return "skill_shield_mastery"

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
    def _combat_surface(
        *,
        slot: str,
        item_id: str,
        item: dict[str, Any],
        skill_key: str | None,
    ) -> dict[str, Any]:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        tags = CharacterCombatActorInputBuilder._tags(item, mechanics)
        delivery = "natural" if "natural_weapon" in tags else "weapon"
        surface = CharacterCombatActorInputBuilder._surface_from_tags(tags, delivery=delivery)
        return {
            "slot": slot,
            "delivery": delivery,
            "surface": surface,
            "tags": tags,
            "item_id": str(item.get("item_id") or item_id),
            "base_id": str(item.get("base_id") or mechanics.get("base_id") or ""),
            "skill_key": str(skill_key or ""),
        }

    @staticmethod
    def _equipment_ref(
        *,
        slot: str,
        combat_slot: str,
        item_id: str,
        item: dict[str, Any],
        skill_key: str | None,
        symbiote: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        metadata = CharacterCombatActorInputBuilder._dict(item.get("metadata") or mechanics.get("metadata"))
        material = CharacterCombatActorInputBuilder._dict(item.get("material") or mechanics.get("material"))
        tags = CharacterCombatActorInputBuilder._tags(item, mechanics)
        triggers = CharacterCombatActorInputBuilder._triggers(item)
        tier = CharacterCombatActorInputBuilder._raw_tier(item)
        sync = CharacterCombatActorInputBuilder._sync_ref(symbiote=symbiote, item_tier=max(1, tier + 1))
        return {
            "slot": slot,
            "combat_slot": combat_slot,
            "item_id": str(item.get("item_id") or item_id),
            "base_id": str(item.get("base_id") or mechanics.get("base_id") or metadata.get("base_id") or ""),
            "item_type": CharacterCombatActorInputBuilder._item_type(item),
            "material_id": str(item.get("material_id") or material.get("id") or material.get("material_id") or ""),
            "tier": tier,
            "combat_tier": max(1, tier + 1),
            "tier_mult": CharacterCombatActorInputBuilder._float_value(material.get("tier_mult"), default=1.0),
            **sync,
            "power": CharacterCombatActorInputBuilder._float_value(
                item.get("power") if item.get("power") is not None else mechanics.get("power"),
                default=0.0,
            ),
            "armor_class": CharacterCombatActorInputBuilder._optional_str(
                item.get("armor_class") or mechanics.get("armor_class") or metadata.get("armor_class")
            ),
            "skill_key": str(skill_key or ""),
            "triggers": triggers,
            "tags": tags,
        }

    @staticmethod
    def _sync_ref(*, symbiote: dict[str, Any] | None, item_tier: int) -> dict[str, float | int]:
        factors = sync_factors(symbiote_rank=symbiote_tier(symbiote), item_tier=item_tier)
        return {
            "sync_delta": factors.delta,
            "durability_stress_mult": factors.durability_stress_mult,
            "overload_penalty_mult": factors.overload_penalty_mult,
            "overdrive_bonus_factor": factors.overdrive_bonus_factor,
        }

    @staticmethod
    def _surface_from_tags(tags: list[str], *, delivery: str) -> str:
        if delivery == "natural":
            for tag in ("fangs", "bite", "claws", "talons", "paws", "natural_weapon"):
                if tag in tags:
                    return tag
            return "natural_weapon"
        for tag in ("sword", "blade", "dagger", "spear", "polearm", "axe", "mace", "hammer", "bow", "weapon"):
            if tag in tags:
                return tag
        return "weapon"

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
    def _ammo_effect_payload(item: dict[str, Any]) -> dict[str, Any] | None:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        raw = item.get("ammo_effect_payload") or mechanics.get("ammo_effect_payload")
        if not isinstance(raw, dict):
            return None
        payload = dict(raw)
        item_power = CharacterCombatActorInputBuilder._float_value(
            item.get("power") if item.get("power") is not None else mechanics.get("power"),
            default=0.0,
        )
        raw_effects = payload.get("effects")
        if isinstance(raw_effects, list):
            effects = [
                CharacterCombatActorInputBuilder._scaled_ammo_effect(effect, item_power)
                for effect in raw_effects
                if isinstance(effect, dict)
            ]
            effects = [effect for effect in effects if effect is not None]
            return {"effects": effects} if effects else None
        return CharacterCombatActorInputBuilder._scaled_ammo_effect(payload, item_power)

    @staticmethod
    def _ammo_charges(item: dict[str, Any], flat_skills: dict[str, float]) -> int | None:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        raw_base = item.get("ammo_charge_base")
        if raw_base is None:
            raw_base = mechanics.get("ammo_charge_base")
        raw_bonus = item.get("ammo_charge_skill_bonus")
        if raw_bonus is None:
            raw_bonus = mechanics.get("ammo_charge_skill_bonus")
        if raw_base is None and raw_bonus is None:
            return None
        base = CharacterCombatActorInputBuilder._float_value(raw_base, default=0.0)
        bonus = CharacterCombatActorInputBuilder._float_value(raw_bonus, default=0.0)
        skill = max(
            0.0,
            min(
                1.0,
                CharacterCombatActorInputBuilder._float_value(flat_skills.get("skill_archery"), default=0.0),
            ),
        )
        return max(0, int(base + bonus * skill))

    @staticmethod
    def _scaled_ammo_effect(payload: dict[str, Any], item_power: float) -> dict[str, Any] | None:
        effect_id = payload.get("id") or payload.get("effect_id")
        if not isinstance(effect_id, str) or not effect_id:
            return None
        payload = dict(payload)
        if item_power > 0:
            params = dict(payload.get("params") or {})
            params["power"] = item_power
            payload["params"] = params
        return payload

    @staticmethod
    def _weapon_tier(item: dict[str, Any]) -> int:
        return max(1, CharacterCombatActorInputBuilder._raw_tier(item) + 1)

    @staticmethod
    def _raw_tier(item: dict[str, Any]) -> int:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        metadata = CharacterCombatActorInputBuilder._dict(item.get("metadata") or mechanics.get("metadata"))
        raw = (
            metadata.get("tier")
            if metadata.get("tier") is not None
            else mechanics.get("tier", item.get("rarity_tier", mechanics.get("rarity_tier", 0)))
        )
        try:
            return max(0, int(raw)) if isinstance(raw, (int, str)) else 0
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _triggers(item: dict[str, Any]) -> list[str]:
        mechanics = CharacterCombatActorInputBuilder._mechanics(item)
        raw = item.get("triggers") or mechanics.get("triggers") or []
        return [str(value) for value in raw if value] if isinstance(raw, list) else []

    @staticmethod
    def _float_value(value: Any, *, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

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
    def _apply_pending_skills(skills: dict[str, float], pending_progress: Any) -> dict[str, float]:
        pending = CharacterCombatActorInputBuilder._dict(pending_progress)
        pending_skills = CharacterCombatActorInputBuilder._dict(pending.get("skills"))
        if not pending_skills:
            return skills
        merged = dict(skills)
        for key, raw in pending_skills.items():
            try:
                merged[str(key)] = round(float(merged.get(str(key), 0.0) or 0.0) + float(raw or 0.0), 4)
            except (TypeError, ValueError):
                continue
        return merged

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
