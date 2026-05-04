from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.items.resources import get_base_by_id
from src.backend.features.monsters.resources import get_family_config

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.resources import MonsterFamilyDTO
    from src.backend.infrastructure.actor_state.models import Monster


MONSTER_TO_ACTOR_STATS: dict[str, str] = {
    "strength": "strength",
    "agility": "agility",
    "endurance": "endurance",
    "intelligence": "intellect",
    "wisdom": "memory",
    "men": "mental",
    "perception": "perception",
    "charisma": "projection",
    "luck": "prediction",
}


def build_monster_combat_context(monster: Monster) -> dict[str, Any]:
    family = _family_for(monster)
    raw_tags = ["monster", monster.role]
    if family is not None:
        raw_tags.extend([family.id, family.archetype, *family.default_tags])

    equipment = _resolve_equipment(monster, family)
    skills = _resolve_skills(monster, family)
    abilities = _resolve_abilities(monster, family)

    return {
        "math_model": {
            "attributes": _attributes(monster),
            "modifiers": _modifiers(equipment),
            "tags": sorted(set(raw_tags)),
        },
        "loadout": {
            "layout": {item["slot"]: item["id"] for item in equipment if item.get("slot")},
            "equipment_layout": {item["slot"]: item["id"] for item in equipment if item.get("slot")},
            "belt": [],
            "abilities": abilities["mechanics"],
            "known_abilities": abilities["mechanics"],
            "ability_presentations": abilities["presentations"],
            "skills": sorted(skills),
            "tags": sorted(set(raw_tags + [tag for item in equipment for tag in item.get("narrative_tags", [])])),
        },
        "skills": skills,
    }


def build_monster_vitals(monster: Monster) -> dict[str, Any]:
    stats = monster.scaled_base_stats or {}
    endurance = int(stats.get("endurance") or 0)
    agility = int(stats.get("agility") or 0)
    mental = int(stats.get("men") or stats.get("intelligence") or 0)
    hp = max(1, 50 + endurance * 10)
    energy = max(1, 30 + agility * 4 + mental * 2)
    current_state = monster.current_state or {}
    hp = int(current_state.get("hp_current") or current_state.get("hp") or hp)
    energy = int(current_state.get("energy_current") or current_state.get("energy") or energy)
    return {
        "hp_current": hp,
        "energy_current": energy,
        "hp": {"cur": hp, "max": hp},
        "energy": {"cur": energy, "max": energy},
    }


def _family_for(monster: Monster) -> MonsterFamilyDTO | None:
    clan = getattr(monster, "clan", None)
    family_id = getattr(clan, "family_id", None)
    return get_family_config(str(family_id)) if family_id else None


def _attributes(monster: Monster) -> dict[str, dict[str, Any]]:
    attributes: dict[str, dict[str, Any]] = {}
    for source_key, value in (monster.scaled_base_stats or {}).items():
        actor_key = MONSTER_TO_ACTOR_STATS.get(source_key, source_key)
        if value is not None:
            attributes[actor_key] = {"base": float(value), "source": {}, "temp": {}}
    return attributes


def _resolve_equipment(monster: Monster, family: MonsterFamilyDTO | None) -> list[dict[str, Any]]:
    ids: list[str] = []
    profile = _dump_model(family.combat_profile) if family and family.combat_profile else {}
    if profile.get("natural_weapon_set"):
        ids.append(str(profile["natural_weapon_set"]))
    if profile.get("armor_class"):
        ids.append(str(profile["armor_class"]))

    loadout_ids = monster.loadout_ids or {}
    if isinstance(loadout_ids, dict):
        ids.extend(str(item_id) for item_id in loadout_ids.values() if item_id)
    elif isinstance(loadout_ids, list):
        ids.extend(str(item_id) for item_id in loadout_ids if item_id)

    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item_id in ids:
        if item_id in seen:
            continue
        seen.add(item_id)
        item = get_base_by_id(item_id)
        if item:
            resolved.append(dict(item))
    return resolved


def _resolve_skills(monster: Monster, family: MonsterFamilyDTO | None) -> dict[str, float]:
    skills: dict[str, float] = {}
    if family is not None:
        skill_kit = _dump_model(family.skill_kit) if family.skill_kit else {}
        for key, value in (skill_kit.get("base") or {}).items():
            skills[str(key)] = float(value)
        role_bonus = (skill_kit.get("role_bonus") or {}).get(monster.role) or {}
        for key, value in role_bonus.items():
            skills[str(key)] = skills.get(str(key), 0.0) + float(value)

    variant = family.variants.get(monster.variant_key) if family is not None else None
    if variant is not None:
        for key, value in variant.skill_overrides.items():
            if value is None:
                skills.pop(key, None)
            else:
                skills[key] = float(value)

    return skills


def _resolve_abilities(monster: Monster, family: MonsterFamilyDTO | None) -> dict[str, Any]:
    raw_ids = _ability_ids(monster.skills_snapshot)
    ability_map = family.ability_map if family else {}
    mechanics: list[str] = []
    presentations: dict[str, str] = {}
    for ability_id in raw_ids:
        mapped = _dump_model(ability_map.get(ability_id)) if ability_map.get(ability_id) else {}
        mechanic = str(mapped.get("mechanic") or ability_id)
        mechanics.append(mechanic)
        presentations[mechanic] = str(mapped.get("presentation") or ability_id)
    return {"mechanics": list(dict.fromkeys(mechanics)), "presentations": presentations}


def _modifiers(equipment: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    modifiers: dict[str, dict[str, Any]] = {}
    for item in equipment:
        item_id = str(item.get("id"))
        source_key = f"monster_equipment:{item_id}"
        base_power = float(item.get("base_power") or 0.0)
        slot = str(item.get("slot") or "")
        item_type = str(item.get("type") or "")
        if base_power:
            if slot == "main_hand":
                _add_modifier(modifiers, "main_hand_damage_base", source_key, base_power)
            elif slot == "off_hand":
                if "shield" in item.get("narrative_tags", []) or item_type == "shield":
                    _add_modifier(modifiers, "block", source_key, base_power)
                else:
                    _add_modifier(modifiers, "off_hand_damage_base", source_key, base_power)
            elif item_type in {"armor", "monster_natural_armor"} or slot.endswith("_armor"):
                _add_modifier(modifiers, "armor", source_key, base_power)

        for key, value in (item.get("implicit_bonuses") or {}).items():
            _add_modifier(modifiers, str(key), source_key, float(value))

    return modifiers


def _add_modifier(modifiers: dict[str, dict[str, Any]], key: str, source: str, value: float) -> None:
    modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
    modifiers[key]["source"][source] = value


def _dump_model(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)


def _ability_ids(snapshot: dict[str, Any] | list[Any]) -> list[str]:
    if isinstance(snapshot, dict):
        return [str(key) for key in snapshot]
    ability_ids: list[str] = []
    for item in snapshot:
        if isinstance(item, dict) and "id" in item:
            ability_ids.append(str(item["id"]))
        else:
            ability_ids.append(str(item))
    return ability_ids
