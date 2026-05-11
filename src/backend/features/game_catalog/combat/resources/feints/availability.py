from __future__ import annotations

from typing import Any

SKILL_FEINT_UNLOCKS: dict[str, tuple[tuple[float, tuple[str, ...]], ...]] = {
    "skill_tactics": (
        (0.0001, ("steady_hand",)),
        (0.10, ("driven_line", "seize_tempo")),
        (0.25, ("press_defense",)),
    ),
    "skill_light_armor": (
        (0.0001, ("low_line_step",)),
        (0.10, ("side_cut", "glancing_step")),
        (0.25, ("counter_window", "counter_step")),
    ),
    "skill_parrying": (
        (0.0001, ("weapon_bind",)),
        (0.10, ("line_catch", "parry_riposte")),
        (0.25, ("counter_parry",)),
    ),
    "skill_anatomy": (
        (0.0001, ("critical_focus",)),
        (0.10, ("marked_opening", "loaded_crit")),
        (0.25, ("armor_slip",)),
    ),
    "skill_one_handed": (
        (0.0001, ("steady_hand",)),
        (0.10, ("driven_line",)),
    ),
    "skill_two_handed": (
        (0.10, ("driven_line",)),
        (0.25, ("press_defense",)),
    ),
    "skill_shield_mastery": (
        (0.0001, ("shield_pressure",)),
        (0.10, ("shield_drive", "brace_guard")),
        (0.25, ("spiked_guard",)),
    ),
    "skill_dual_wield": (
        (0.0001, ("low_line_step",)),
        (0.10, ("side_cut",)),
        (0.25, ("counter_step",)),
    ),
    "skill_swords": (
        (0.0001, ("weapon_bind",)),
        (0.10, ("line_catch",)),
        (0.25, ("armor_slip",)),
    ),
    "skill_fencing": (
        (0.0001, ("low_line_step", "weapon_bind", "critical_focus")),
        (0.10, ("side_cut", "line_catch", "marked_opening", "loaded_crit")),
        (0.25, ("armor_slip",)),
    ),
    "skill_polearms": (
        (0.0001, ("steady_hand",)),
        (0.10, ("driven_line",)),
        (0.25, ("press_defense",)),
    ),
    "skill_macing": (
        (0.0001, ("shield_pressure",)),
        (0.10, ("shield_drive", "brace_guard")),
        (0.25, ("press_defense",)),
    ),
    "skill_archery": (
        (0.0001, ("steady_hand", "critical_focus")),
        (0.10, ("marked_opening", "loaded_crit", "glancing_step")),
    ),
    "skill_unarmed": (
        (0.0001, ("steady_hand", "low_line_step")),
        (0.10, ("side_cut", "seize_tempo")),
    ),
    "skill_weapon_craft": (),
    "skill_armor_craft": (),
    "skill_jewelry_craft": (),
    "skill_engineering": (),
    "skill_artifact_craft": (),
}

WEAPON_TECHNIQUE_UNLOCKS: tuple[tuple[float, tuple[str, ...]], ...] = (
    (0.10, ("measured_strike",)),
    (0.25, ("steady_strike",)),
    (0.50, ("flawless_strike",)),
    (0.75, ("decisive_attack",)),
)

WEAPON_SKILL_TAGS: dict[str, frozenset[str]] = {
    "skill_swords": frozenset({"weapon", "melee", "blade", "balanced"}),
    "skill_fencing": frozenset({"weapon", "melee", "blade", "precision"}),
    "skill_polearms": frozenset({"weapon", "melee", "reach"}),
    "skill_macing": frozenset({"weapon", "melee", "impact"}),
    "skill_archery": frozenset({"weapon", "ranged", "precision"}),
    "skill_unarmed": frozenset({"weapon", "melee", "unarmed"}),
}

WEAPON_TECHNIQUE_TAG_REQUIREMENTS: dict[str, frozenset[str]] = {
    "measured_strike": frozenset({"weapon"}),
    "steady_strike": frozenset({"weapon"}),
    "flawless_strike": frozenset({"weapon"}),
    "decisive_attack": frozenset({"weapon"}),
}

WEAPON_MASTERY_FEINTS: dict[str, tuple[str, ...]] = {
    "skill_swords": (),
    "skill_fencing": (),
    "skill_polearms": (),
    "skill_macing": (),
    "skill_archery": (),
    "skill_unarmed": (),
}

TACTICAL_STYLE_FEINTS: dict[str, tuple[str, ...]] = {
    "skill_shield_mastery": (),
    "skill_two_handed": (),
}

FEINT_EXCLUSIONS_BY_OFFHAND: dict[str, tuple[str, ...]] = {
    "buckler": ("shield_bash",),
}


def build_known_feints(loadout: dict[str, Any], skills: dict[str, float] | None = None) -> list[str]:
    """Build the full pre-combat feint pool for an actor snapshot."""
    layout = _dict(loadout.get("layout"))
    skill_values = _skill_values(skills)
    known: list[str] = []
    handled_skills: set[str] = set()

    for slot in ("main_hand", "off_hand"):
        skill_key = layout.get(slot)
        if isinstance(skill_key, str) and _has_skill(skill_values, skill_key):
            skill_value = skill_values[skill_key]
            known.extend(weapon_techniques_for_skill(skill_key, skill_value))
            known.extend(skill_feints_for_value(skill_key, skill_value))
            known.extend(WEAPON_MASTERY_FEINTS.get(skill_key, ()))
            handled_skills.add(skill_key)

    body_skill = layout.get("body")
    if isinstance(body_skill, str) and _has_skill(skill_values, body_skill):
        known.extend(skill_feints_for_value(body_skill, skill_values[body_skill]))
        handled_skills.add(body_skill)

    tactical_style = layout.get("tactical_style")
    if isinstance(tactical_style, str) and _has_skill(skill_values, tactical_style):
        known.extend(skill_feints_for_value(tactical_style, skill_values[tactical_style]))
        known.extend(TACTICAL_STYLE_FEINTS.get(tactical_style, ()))
        handled_skills.add(tactical_style)

    for skill_key, skill_value in skill_values.items():
        if skill_key in handled_skills or not _has_skill(skill_values, skill_key):
            continue
        known.extend(skill_feints_for_value(skill_key, skill_value))

    known.extend(_item_feints(loadout))
    known = _without_excluded_feints(loadout, known)
    return list(dict.fromkeys(feint for feint in known if feint))


def skill_feints_for_value(skill_key: str, skill_value: float) -> list[str]:
    return [
        feint_id
        for threshold, feint_ids in SKILL_FEINT_UNLOCKS.get(skill_key, ())
        if skill_value >= threshold
        for feint_id in feint_ids
    ]


def weapon_techniques_for_skill(skill_key: str, skill_value: float) -> list[str]:
    skill_tags = WEAPON_SKILL_TAGS.get(skill_key, frozenset())
    if not skill_tags:
        return []
    return [
        feint_id
        for threshold, feint_ids in WEAPON_TECHNIQUE_UNLOCKS
        if skill_value >= threshold
        for feint_id in feint_ids
        if WEAPON_TECHNIQUE_TAG_REQUIREMENTS[feint_id].issubset(skill_tags)
    ]


def _without_excluded_feints(loadout: dict[str, Any], feints: list[str]) -> list[str]:
    equipment = _dict(loadout.get("equipment_layout"))
    offhand_id = str(equipment.get("off_hand") or "").lower()
    excluded: set[str] = set()
    for marker, blocked in FEINT_EXCLUSIONS_BY_OFFHAND.items():
        if marker in offhand_id:
            excluded.update(blocked)
    if not excluded:
        return feints
    return [feint for feint in feints if feint not in excluded]


def _item_feints(loadout: dict[str, Any]) -> list[str]:
    feints: list[str] = []
    for item in _list(loadout.get("belt")):
        feints.extend(_feints_from_item(_dict(item)))
    return feints


def _feints_from_item(item: dict[str, Any]) -> list[str]:
    mechanics = _dict(item.get("mechanics") or item.get("data"))
    raw = (
        item.get("feints") or item.get("known_feints") or mechanics.get("feints") or mechanics.get("known_feints") or []
    )
    return [str(value) for value in raw] if isinstance(raw, list) else []


def _dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _skill_values(skills: dict[str, float] | None) -> dict[str, float]:
    values: dict[str, float] = {}
    for key, raw in (skills or {}).items():
        try:
            values[str(key)] = float(raw or 0.0)
        except (TypeError, ValueError):
            values[str(key)] = 0.0
    return values


def _has_skill(skill_values: dict[str, float], skill_key: str) -> bool:
    return skill_values.get(skill_key, 0.0) > 0.0
