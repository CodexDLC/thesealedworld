from __future__ import annotations

import time
from typing import Any

from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder
from src.backend.features.game_catalog.combat.resources.feints.availability import build_known_feints
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.visuals import version_generated_asset_url
from src.backend.features.monsters.runtime.ai_archetype import resolve_monster_ai_archetype
from src.backend.features.monsters.runtime.combat_math_model import MonsterCombatMathModelBuilder
from src.backend.features.monsters.skill_contract import filter_monster_combat_skills


class MonsterCombatActorInputBuilder:
    """Builds combat-facing actor input from a generated monster row."""

    def __init__(self, math_model: MonsterCombatMathModelBuilder | None = None) -> None:
        self.math_model = math_model or MonsterCombatMathModelBuilder()

    def build_input(self, monster: Any) -> dict[str, Any]:
        items = self._items_for_player_mapper(monster.items)
        skills = self._scaled_skills(monster.scaled_skills)
        raw = self.math_model.build_raw(
            attributes=dict(monster.scaled_attributes or {}),
            items=items,
            skills=skills,
            monster_meta=self._math_meta(monster),
            balance=self._balance(monster),
        )
        generation_meta = dict(getattr(monster, "generation_meta", None) or {})
        family_modifiers = generation_meta.get("family_modifiers") or []
        if family_modifiers:
            meta = generation_meta.get("meta") or {}
            family_id = str(meta.get("family_id") or "unknown")
            self._apply_family_modifiers(raw["modifiers"], family_modifiers, family_id)
        raw["tags"] = self._meta_tags(monster)
        loadout = self._loadout(monster, items, skills)
        return {
            "meta": self._meta(monster),
            "source": self._source(monster),
            "status": self._status_from_vitals(dict(monster.vitals or {})),
            "raw": raw,
            "skills": skills,
            "loadout": loadout,
        }

    def build_snapshot(self, monster: Any) -> dict[str, Any]:
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
    def _apply_family_modifiers(
        modifiers: dict[str, Any],
        family_modifiers: list[dict[str, Any]],
        family_id: str,
    ) -> None:
        from src.backend.features.character.runtime.combat_math_model import COMBAT_MODIFIER_KEYS, MODIFIER_ALIASES

        source = f"family:{family_id}"
        for entry in family_modifiers:
            target = str(entry.get("target") or "")
            effective = entry.get("effective_value")
            if not target or effective is None:
                continue
            key = MODIFIER_ALIASES.get(target, target)
            if key not in COMBAT_MODIFIER_KEYS:
                continue
            modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
            modifiers[key]["source"][source] = round(float(effective), 4)

    @staticmethod
    def _scaled_skills(raw: dict[str, Any]) -> dict[str, float]:
        return filter_monster_combat_skills(raw)

    @staticmethod
    def _items_for_player_mapper(items: dict[str, Any]) -> dict[str, Any]:
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
            "bonuses": combat.get("bonuses") or {},
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
    def _loadout(monster: Any, items: dict[str, Any], skills: dict[str, float]) -> dict[str, Any]:
        loadout = CharacterCombatActorInputBuilder._loadout(items, skills)
        tags = sorted(set([*loadout.get("tags", []), *MonsterCombatActorInputBuilder._meta_tags(monster)]))
        loadout["tags"] = tags
        loadout["known_feints"] = build_known_feints(loadout, skills)
        return loadout

    @staticmethod
    def _meta(monster: Any) -> dict[str, Any]:
        visual = MonsterCombatActorInputBuilder._visual(monster)
        return {
            "actor_type": "monster",
            "actor_id": str(monster.id),
            "name": monster.name_ru,
            "role": monster.role,
            "avatar_url": MonsterCombatActorInputBuilder._avatar_url(visual),
            "tags": MonsterCombatActorInputBuilder._meta_tags(monster),
            "archetype": MonsterCombatActorInputBuilder._archetype(monster),
            "ai_archetype": MonsterCombatActorInputBuilder._ai_archetype(monster),
        }

    @staticmethod
    def _math_meta(monster: Any) -> dict[str, Any]:
        generation_meta = dict(getattr(monster, "generation_meta", None) or {})
        meta = generation_meta.get("meta")
        meta_data = dict(meta) if isinstance(meta, dict) else {}
        meta_data["role"] = str(getattr(monster, "role", "") or meta_data.get("role") or "")
        return meta_data

    @staticmethod
    def _balance(monster: Any) -> dict[str, Any]:
        generation_meta = dict(getattr(monster, "generation_meta", None) or {})
        balance = generation_meta.get("balance")
        return dict(balance) if isinstance(balance, dict) else {}

    @staticmethod
    def _source(monster: Any) -> dict[str, Any]:
        meta = dict(monster.generation_meta or {})
        source = meta.get("source")
        meta_source = source if isinstance(source, dict) else {}
        family_id = getattr(monster, "family_id", None)
        return {
            **meta_source,
            "monster_id": str(monster.id),
            "clan_id": str(monster.clan_id),
            "family_id": family_id,
            "owner_family": MonsterCombatActorInputBuilder._owner_family(monster, family_id),
            "template_id": monster.variant_key,
            "member_tier": int(getattr(monster, "member_tier", 0) or 0),
            "visual": MonsterCombatActorInputBuilder._visual(monster),
            "db_refs": {
                "generated_monsters": str(monster.id),
                "generated_clans": str(monster.clan_id),
            },
        }

    @staticmethod
    def _owner_family(monster: Any, family_id: str | None) -> dict[str, Any]:
        clan = getattr(monster, "clan", None)
        flavor_content = dict(getattr(clan, "flavor_content", None) or {}) if clan is not None else {}
        family = get_family_config(str(family_id)) if family_id else None
        return {
            "clan_id": str(getattr(monster, "clan_id", "")),
            "family_resource_id": str(family_id or ""),
            "clan_name_ru": str(getattr(clan, "name_ru", "") or ""),
            "clan_description": str(getattr(clan, "description", "") or ""),
            "archetype": family.archetype if family is not None else MonsterCombatActorInputBuilder._archetype(monster),
            "organization_type": family.organization_type if family is not None else "",
            "tags": list(family.default_tags) if family is not None else [],
            "loot_culture": dict(flavor_content.get("loot_culture") or {}),
        }

    @staticmethod
    def _visual(monster: Any) -> dict[str, Any]:
        generation_meta = dict(getattr(monster, "generation_meta", None) or {})
        visual = generation_meta.get("visual")
        return dict(visual) if isinstance(visual, dict) else {}

    @staticmethod
    def _avatar_url(visual: dict[str, Any]) -> str | None:
        for key in ("image_url", "generated_image_url"):
            url = visual.get(key)
            if not isinstance(url, str) or not url:
                continue
            if "/static/images/monsters/families/" in url:
                continue
            if key == "generated_image_url" and visual.get("status") != "generated":
                continue
            return version_generated_asset_url(url, visual)
        return None

    @staticmethod
    def _meta_tags(monster: Any) -> list[str]:
        generation_meta = dict(getattr(monster, "generation_meta", None) or {})
        meta = generation_meta.get("meta")
        meta_data = meta if isinstance(meta, dict) else {}
        tags_raw = meta_data.get("tags")
        tags = [str(tag) for tag in tags_raw or [] if tag] if isinstance(tags_raw, list) else []
        tags.extend(["monster", monster.role])
        return sorted(set(tags))

    @staticmethod
    def _archetype(monster: Any) -> str:
        generation_meta = dict(getattr(monster, "generation_meta", None) or {})
        meta = generation_meta.get("meta")
        meta_data = meta if isinstance(meta, dict) else {}
        return str(meta_data.get("archetype") or "unknown")

    @staticmethod
    def _ai_archetype(monster: Any) -> str:
        return resolve_monster_ai_archetype(
            str(getattr(monster, "variant_key", "") or ""),
            MonsterCombatActorInputBuilder._archetype(monster),
            str(getattr(monster, "role", "") or ""),
        )

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
