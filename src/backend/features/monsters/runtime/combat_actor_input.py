from __future__ import annotations

import time
from typing import Any

from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder
from src.backend.features.character.runtime.combat_math_model import CharacterCombatMathModelBuilder
from src.backend.features.game_catalog.combat.resources.feints.availability import build_known_feints
from src.backend.features.monsters.runtime.combat_profile import (
    MonsterCombatSource,
    build_monster_combat_context,
    build_monster_vitals,
)


class MonsterCombatActorInputBuilder:
    """Builds combat-facing actor input from a generated monster row."""

    def __init__(self, math_model: CharacterCombatMathModelBuilder | None = None) -> None:
        self.math_model = math_model or CharacterCombatMathModelBuilder()

    def build_input(self, monster: MonsterCombatSource) -> dict[str, Any]:
        template = self._generated_template(monster)
        if not template:
            combat = build_monster_combat_context(monster)
            return {
                "meta": self._legacy_meta(monster),
                "source": self._legacy_source(monster),
                "status": self._status_from_vitals(build_monster_vitals(monster)),
                "raw": combat["math_model"],
                "skills": combat["skills"],
                "loadout": combat["loadout"],
            }

        items = self._items_for_player_mapper(template)
        skills = self._scaled_skills(template)
        raw = self.math_model.build_raw(
            attributes=self._scaled_attributes(template),
            items=items,
            skills=skills,
        )
        raw["tags"] = self._meta_tags(template, monster)
        loadout = self._loadout(template, items, skills)
        return {
            "meta": self._meta(monster, template),
            "source": self._source(monster, template),
            "status": self._status_from_vitals(build_monster_vitals(monster)),
            "raw": raw,
            "skills": skills,
            "loadout": loadout,
        }

    def build_snapshot(self, monster: MonsterCombatSource) -> dict[str, Any]:
        actor_input = self.build_input(monster)
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
    def _generated_template(monster: MonsterCombatSource) -> dict[str, Any]:
        seed = monster.combat_seed if isinstance(monster.combat_seed, dict) else {}
        template = seed.get("generated_template")
        return template if isinstance(template, dict) else {}

    @staticmethod
    def _scaled_attributes(template: dict[str, Any]) -> dict[str, Any]:
        raw = template.get("scaled_attributes")
        return dict(raw) if isinstance(raw, dict) else {}

    @staticmethod
    def _scaled_skills(template: dict[str, Any]) -> dict[str, float]:
        raw = template.get("scaled_skills")
        skills = raw.get("skills") if isinstance(raw, dict) else raw
        if not isinstance(skills, dict):
            return {}
        result: dict[str, float] = {}
        for key, value in skills.items():
            try:
                result[str(key)] = round(float(value or 0.0), 4)
            except (TypeError, ValueError):
                result[str(key)] = 0.0
        return result

    @staticmethod
    def _items_for_player_mapper(template: dict[str, Any]) -> dict[str, Any]:
        raw_items = template.get("items")
        items = raw_items if isinstance(raw_items, dict) else {}

        raw_layout = items.get("layout")
        layout = raw_layout if isinstance(raw_layout, dict) else {}

        raw_by_id = items.get("by_id")
        by_id = raw_by_id if isinstance(raw_by_id, dict) else {}

        mapped_by_id = {
            str(item_id): MonsterCombatActorInputBuilder._runtime_item_to_mapper_item(str(item_id), item)
            for item_id, item in by_id.items()
            if isinstance(item, dict)
        }
        return {
            "layout": {
                "equipment": dict(layout.get("equipment") or {}),
                "belt": dict(layout.get("belt") or {}),
            },
            "by_id": mapped_by_id,
        }

    @staticmethod
    def _runtime_item_to_mapper_item(item_id: str, item: dict[str, Any]) -> dict[str, Any]:
        combat_raw = item.get("combat")
        combat = combat_raw if isinstance(combat_raw, dict) else {}

        gen_raw = item.get("generation")
        generation = gen_raw if isinstance(gen_raw, dict) else {}

        metadata = {
            "related_skill": combat.get("related_skill"),
            "item_grade": generation.get("item_grade"),
            "source_context": generation.get("source_context") or {},
        }
        raw_affixes = generation.get("affixes")
        affixes = raw_affixes if isinstance(raw_affixes, list) else []

        mechanics = {
            "base_id": item.get("base_id"),
            "item_type": item.get("item_type"),
            "slot": item.get("slot"),
            "power": combat.get("power"),
            "damage_spread": combat.get("damage_spread"),
            "implicit_bonuses": combat.get("implicit_bonuses") or {},
            "bonuses": {} if affixes else combat.get("bonuses") or {},
            "triggers": combat.get("triggers") or [],
            "tags": combat.get("tags") or [],
            "related_skill": combat.get("related_skill"),
            "affixes": affixes,
            "metadata": metadata,
        }
        return {
            "item_id": item_id,
            "base_id": item.get("base_id"),
            "item_type": item.get("item_type"),
            "slot": item.get("slot"),
            "mechanics": mechanics,
            "metadata": metadata,
            "tags": combat.get("tags") or [],
        }

    @staticmethod
    def _loadout(template: dict[str, Any], items: dict[str, Any], skills: dict[str, float]) -> dict[str, Any]:
        loadout = CharacterCombatActorInputBuilder._loadout(items, skills)
        granted = template.get("granted_abilities")
        granted_data = granted if isinstance(granted, dict) else {}
        known_abilities = [str(value) for value in granted_data.get("known_abilities") or [] if value]
        if known_abilities:
            loadout["abilities"] = known_abilities
            loadout["known_abilities"] = known_abilities
        presentations = granted_data.get("ability_presentations")
        if isinstance(presentations, dict):
            loadout["ability_presentations"] = dict(presentations)
        tags = sorted(set([*loadout.get("tags", []), *MonsterCombatActorInputBuilder._meta_tags(template, None)]))
        loadout["tags"] = tags
        loadout["known_feints"] = build_known_feints(loadout, skills)
        return loadout

    @staticmethod
    def _meta(monster: MonsterCombatSource, template: dict[str, Any]) -> dict[str, Any]:
        text_raw = template.get("text_content")
        text = text_raw if isinstance(text_raw, dict) else {}

        meta_raw = template.get("meta")
        meta = meta_raw if isinstance(meta_raw, dict) else {}

        return {
            "actor_type": "monster",
            "actor_id": str(monster.id),
            "name": text.get("name_ru") or monster.name_ru,
            "role": monster.role,
            "tags": MonsterCombatActorInputBuilder._meta_tags(template, monster),
            "archetype": meta.get("archetype") or "unknown",
        }

    @staticmethod
    def _source(monster: MonsterCombatSource, template: dict[str, Any]) -> dict[str, Any]:
        meta_raw = template.get("meta")
        meta = meta_raw if isinstance(meta_raw, dict) else {}

        source_raw = meta.get("source")
        meta_source = source_raw if isinstance(source_raw, dict) else {}

        family_id = meta.get("family_id") or getattr(monster, "family_id", None)
        return {
            **meta_source,
            "monster_id": str(monster.id),
            "clan_id": str(monster.clan_id),
            "family_id": family_id,
            "template_id": monster.variant_key,
            "db_refs": {
                "generated_monsters": str(monster.id),
                "generated_clans": str(monster.clan_id),
            },
        }

    @staticmethod
    def _legacy_meta(monster: MonsterCombatSource) -> dict[str, Any]:
        return {
            "actor_type": "monster",
            "actor_id": str(monster.id),
            "name": monster.name_ru,
            "role": monster.role,
            "tags": ["monster", monster.role],
            "archetype": "unknown",
        }

    @staticmethod
    def _legacy_source(monster: MonsterCombatSource) -> dict[str, Any]:
        return {
            "monster_id": str(monster.id),
            "clan_id": str(monster.clan_id),
            "family_id": getattr(monster, "family_id", None),
            "template_id": monster.variant_key,
            "db_refs": {
                "generated_monsters": str(monster.id),
                "generated_clans": str(monster.clan_id),
            },
        }

    @staticmethod
    def _meta_tags(template: dict[str, Any], monster: MonsterCombatSource | None) -> list[str]:
        meta_raw = template.get("meta")
        meta = meta_raw if isinstance(meta_raw, dict) else {}

        tags_raw = meta.get("tags")
        tags = [str(tag) for tag in tags_raw or [] if tag] if isinstance(tags_raw, list) else []

        if monster is not None:
            tags.extend(["monster", monster.role])
        return sorted(set(tags))

    @staticmethod
    def _status_from_vitals(vitals: dict[str, Any]) -> dict[str, Any]:
        raw_energy = vitals.get("energy")
        energy = dict(raw_energy) if isinstance(raw_energy, dict) else {}
        raw_hp = vitals.get("hp")
        hp = dict(raw_hp) if isinstance(raw_hp, dict) else {}
        raw_stamina = vitals.get("stamina")
        stamina = dict(raw_stamina) if isinstance(raw_stamina, dict) else energy
        return {
            "hp": hp,
            "energy": energy,
            "stamina": stamina,
            "last_update": time.time(),
        }


__all__ = ["MonsterCombatActorInputBuilder"]
