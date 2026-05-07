from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from src.backend.features.items.resources import get_base_by_id
from src.backend.features.monsters.resources import get_family_config
from src.shared.schemas.modifier_dto import CombatModifiersDTO

if TYPE_CHECKING:
    import uuid

    from src.backend.features.monsters.dto.resources import MonsterFamilyDTO


class MonsterCombatSource(Protocol):
    @property
    def id(self) -> uuid.UUID | str: ...
    @property
    def clan_id(self) -> uuid.UUID | str: ...
    @property
    def family_id(self) -> str | None: ...

    variant_key: str
    role: str
    name_ru: str
    scaled_base_stats: dict[str, Any]
    loadout_ids: dict[str, Any] | list[Any]
    skills_snapshot: dict[str, Any] | list[Any]
    combat_seed: dict[str, Any]
    current_state: dict[str, Any] | None


ARMOR_SLOT_TO_COMBAT_SLOT: dict[str, str] = {
    "chest_armor": "body",
}

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

COMBAT_MODIFIER_KEYS = frozenset(CombatModifiersDTO.model_fields)
MODIFIER_ALIASES = {
    "block_chance": "block",
    "damage_reduction_flat": "armor",
    "dodge_chance": "evasion",
    "evasion_penalty": "evasion",
    "magical_resistance": "magic_resist",
    "magic_resistance": "magic_resist",
    "parry_chance": "parry",
    "physical_accuracy": "accuracy",
    "physical_crit_chance": "crit_chance",
    "physical_crit_power_float": "crit_power",
    "shield_block_chance": "block",
}


def build_monster_combat_seed(monster: MonsterCombatSource) -> dict[str, Any]:
    family = _family_for(monster)
    raw_tags = _monster_tags(monster, family)
    equipment = _resolve_equipment(monster, family)
    skills = _resolve_skills(monster, family)
    abilities = _resolve_abilities(monster, family)
    loadout = _build_combat_loadout(equipment, skills, raw_tags, abilities)
    return {
        "version": 1,
        "tags": sorted(set(raw_tags)),
        "skills": skills,
        "loadout": loadout,
        "vitals": build_monster_vitals(monster),
    }


def build_monster_combat_context(monster: MonsterCombatSource) -> dict[str, Any]:
    seed = _combat_seed(monster)
    if seed:
        loadout = _dump_mapping(seed.get("loadout"))
        equipment = _equipment_from_layout(loadout.get("equipment_layout"))
        return {
            "math_model": {
                "attributes": _attributes(monster),
                "modifiers": _modifiers(equipment),
                "tags": _list_str(seed.get("tags")),
            },
            "loadout": loadout,
            "skills": _float_map(seed.get("skills")),
        }

    family = _family_for(monster)
    raw_tags = _monster_tags(monster, family)
    equipment = _resolve_equipment(monster, family)
    skills = _resolve_skills(monster, family)
    abilities = _resolve_abilities(monster, family)

    return {
        "math_model": {
            "attributes": _attributes(monster),
            "modifiers": _modifiers(equipment),
            "tags": sorted(set(raw_tags)),
        },
        "loadout": _build_combat_loadout(equipment, skills, raw_tags, abilities),
        "skills": skills,
    }


def build_monster_vitals(monster: MonsterCombatSource) -> dict[str, Any]:
    seed = _combat_seed(monster)
    seed_vitals = _dump_mapping(seed.get("vitals")) if seed else {}
    if seed_vitals:
        return seed_vitals

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


def _family_for(monster: MonsterCombatSource) -> MonsterFamilyDTO | None:
    family_id = getattr(monster, "family_id", None)
    if family_id:
        return get_family_config(str(family_id))
    clan = getattr(monster, "clan", None)
    family_id = getattr(clan, "family_id", None)
    return get_family_config(str(family_id)) if family_id else None


def _attributes(monster: MonsterCombatSource) -> dict[str, dict[str, Any]]:
    attributes: dict[str, dict[str, Any]] = {}
    for source_key, value in (monster.scaled_base_stats or {}).items():
        actor_key = MONSTER_TO_ACTOR_STATS.get(source_key, source_key)
        if value is not None:
            attributes[actor_key] = {"base": float(value), "source": {}, "temp": {}}
    return attributes


def _monster_tags(monster: MonsterCombatSource, family: MonsterFamilyDTO | None) -> list[str]:
    raw_tags = ["monster", monster.role]
    if family is not None:
        raw_tags.extend([family.id, family.archetype, *family.default_tags])
    return raw_tags


def _resolve_equipment(monster: MonsterCombatSource, family: MonsterFamilyDTO | None) -> list[dict[str, Any]]:
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


def _equipment_from_layout(equipment_layout: Any) -> list[dict[str, Any]]:
    layout = equipment_layout if isinstance(equipment_layout, dict) else {}
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item_id in layout.values():
        if not item_id:
            continue
        item_id = str(item_id)
        if item_id in seen:
            continue
        seen.add(item_id)
        item = get_base_by_id(item_id)
        if item:
            resolved.append(dict(item))
    return resolved


def _resolve_skills(monster: MonsterCombatSource, family: MonsterFamilyDTO | None) -> dict[str, float]:
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


def _build_combat_loadout(
    equipment: list[dict[str, Any]],
    skills: dict[str, float],
    raw_tags: list[str],
    abilities: dict[str, Any],
) -> dict[str, Any]:
    layout: dict[str, str] = {}
    equipment_layout: dict[str, str] = {}
    hand_usage: dict[str, str] = {}
    tags = list(raw_tags)

    for item in equipment:
        slot = str(item.get("slot") or "")
        item_id = str(item.get("id") or "")
        if not slot or not item_id:
            continue

        equipment_layout[slot] = item_id
        combat_slot = ARMOR_SLOT_TO_COMBAT_SLOT.get(slot, slot)
        skill_key = _skill_key_for_item(combat_slot, item)
        if skill_key:
            layout[combat_slot] = skill_key
            skills.setdefault(skill_key, 0.0)

        trigger_id = _first_trigger(item)
        if trigger_id and combat_slot in {"main_hand", "off_hand"}:
            layout[f"{combat_slot}_trigger"] = trigger_id

        if slot == "two_hand":
            hand_usage["main_hand"] = "two_hand"

        tags.extend(_list_str(item.get("narrative_tags")))

    return {
        "layout": layout,
        "equipment_layout": equipment_layout,
        "hand_usage": hand_usage,
        "two_handed": bool(hand_usage),
        "belt": [],
        "abilities": abilities["mechanics"],
        "known_abilities": abilities["mechanics"],
        "ability_presentations": abilities["presentations"],
        "skills": sorted(skills),
        "tags": sorted(set(tags)),
    }


def _skill_key_for_item(combat_slot: str, item: dict[str, Any]) -> str | None:
    for key in ("related_skill", "skill_key", "weapon_skill_key", "armor_skill_key"):
        value = item.get(key)
        if value:
            return str(value)

    return None


def _first_trigger(item: dict[str, Any]) -> str | None:
    raw = item.get("triggers") or []
    return str(raw[0]) if isinstance(raw, list) and raw else None


def _resolve_abilities(monster: MonsterCombatSource, family: MonsterFamilyDTO | None) -> dict[str, Any]:
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
        base_power = float(item.get("base_power") or 0.0)
        damage_spread = item.get("damage_spread")
        slot = str(item.get("slot") or "")
        item_type = str(item.get("type") or "")
        tags = _list_str(item.get("narrative_tags"))
        combat_slot = "main_hand" if slot == "two_hand" else slot
        if base_power:
            if combat_slot == "main_hand":
                _add_base_modifier(modifiers, "main_hand_damage_base", base_power)
            elif combat_slot == "off_hand":
                if _is_shield(item_type, tags):
                    _add_base_modifier(modifiers, "block", base_power)
                else:
                    _add_base_modifier(modifiers, "off_hand_damage_base", base_power)
            elif item_type in {"armor", "monster_natural_armor"} or slot.endswith("_armor"):
                _add_base_modifier(modifiers, "armor", base_power)

        if damage_spread is not None:
            if combat_slot == "main_hand":
                _replace_base_modifier(modifiers, "main_hand_damage_spread", float(damage_spread))
            elif combat_slot == "off_hand" and not _is_shield(item_type, tags):
                _replace_base_modifier(modifiers, "off_hand_damage_spread", float(damage_spread))

        for key, value in (item.get("implicit_bonuses") or {}).items():
            _add_base_modifier(
                modifiers,
                _item_base_key(str(key), slot=combat_slot, item_type=item_type, tags=tags),
                float(value),
            )

    return modifiers


def _add_base_modifier(modifiers: dict[str, dict[str, Any]], key: str, value: float) -> None:
    key = MODIFIER_ALIASES.get(key, key)
    if key not in COMBAT_MODIFIER_KEYS:
        return
    modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
    modifiers[key]["base"] = round(float(modifiers[key].get("base", 0.0) or 0.0) + value, 4)


def _replace_base_modifier(modifiers: dict[str, dict[str, Any]], key: str, value: float) -> None:
    key = MODIFIER_ALIASES.get(key, key)
    if key not in COMBAT_MODIFIER_KEYS:
        return
    modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
    modifiers[key]["base"] = round(value, 4)


def _item_base_key(key: str, *, slot: str, item_type: str, tags: list[str]) -> str:
    if key == "physical_accuracy":
        if slot == "main_hand":
            return "main_hand_accuracy"
        if slot == "off_hand" and not _is_shield(item_type, tags):
            return "off_hand_accuracy"
        return "accuracy"
    if key == "physical_crit_chance":
        if slot == "main_hand":
            return "main_hand_crit_chance"
        if slot == "off_hand" and not _is_shield(item_type, tags):
            return "off_hand_crit_chance"
        return "crit_chance"
    return MODIFIER_ALIASES.get(key, key)


def _is_shield(item_type: str, tags: list[str]) -> bool:
    return item_type == "shield" or "shield" in tags


def _dump_model(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)


def _dump_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value) if isinstance(value, dict) else {}


def _float_map(value: Any) -> dict[str, float]:
    raw = _dump_mapping(value)
    result: dict[str, float] = {}
    for key, val in raw.items():
        try:
            result[str(key)] = float(val or 0.0)
        except (TypeError, ValueError):
            result[str(key)] = 0.0
    return result


def _list_str(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _combat_seed(monster: MonsterCombatSource) -> dict[str, Any]:
    return _dump_mapping(getattr(monster, "combat_seed", {}))


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
