from __future__ import annotations

from typing import Any

BASIC_FEINTS: tuple[str, ...] = (
    "measured_strike",
    "steady_strike",
    "flawless_strike",
    "glancing_step",
    "wind_dance",
    "blade_dance",
    "foresight_parry",
    "second_breath",
    "perfect_riposte",
)

BASIC_ARCHERY_FEINTS: tuple[str, ...] = (
    "measured_strike",
    "steady_strike",
    "flawless_strike",
    "glancing_step",
    "wind_dance",
    "blade_dance",
)

SWORD_WEAPON_FEINTS: tuple[str, ...] = (
    "sword_measured_line",
    "sword_blade_bind",
    "sword_low_angle",
    "sword_open_line",
    "sword_hard_bind",
    "sword_cut_angle",
    "sword_clean_path",
)

FENCING_WEAPON_FEINTS: tuple[str, ...] = (
    "fencing_precise_prick",
    "fencing_corner_entry",
    "fencing_hidden_entry",
    "fencing_gap_probe",
    "fencing_needle_gap",
    "fencing_slip_guard",
    "fencing_inside_line",
)

POLEARM_WEAPON_FEINTS: tuple[str, ...] = (
    "polearm_long_line",
    "polearm_hook_step",
    "polearm_leg_sweep",
    "polearm_guard_intercept",
    "polearm_stunning_intercept",
    "polearm_pinning_point",
    "polearm_locked_distance",
)

MACING_WEAPON_FEINTS: tuple[str, ...] = (
    "macing_heavy_line",
    "macing_armor_crush",
    "macing_skullbreaker",
    "macing_break_swing",
    "macing_break_stance",
    "macing_guard_cracker",
)

ARCHERY_WEAPON_FEINTS: tuple[str, ...] = (
    "snap_shot",
    "headshot",
    "piercing_arrow",
    "precise_weak_spot",
    "quiet_weak_spot",
)

RANGED_TACTICAL_FEINTS: tuple[str, ...] = (
    "reveal_intentions",
    "covering_position",
    "backstep_shot",
    "open_distance",
    "blinding_shot",
)

SHIELD_TACTICAL_FEINTS: tuple[str, ...] = (
    "active_defense",
    "full_defense",
    "absolute_defense",
    "aggressive_defense",
    "read_tactic",
    "concussion",
)

TWO_HANDED_TACTICAL_FEINTS: tuple[str, ...] = (
    "crushing_pressure",
    "steel_line",
    "blade_return",
    "hard_intercept",
    "answering_stance",
    "closed_distance",
    "hidden_agility",
    "push_stance",
    "ignore_guard",
    "open_wound",
    "heavy_swing",
    "hidden_strength",
    "lucky_break",
)

DUAL_WIELD_TACTICAL_FEINTS: tuple[str, ...] = (
    "broken_step",
    "shifting_line",
    "empty_line",
    "torn_rhythm",
    "bind_blade",
    "offhand_over",
    "open_vein",
    "silent_puncture",
    "answering_series",
    "blade_mill",
    "blade_loop",
)

SKILL_FEINT_UNLOCKS: dict[str, tuple[tuple[float, tuple[str, ...]], ...]] = {
    "skill_swords": ((0.0, SWORD_WEAPON_FEINTS),),
    "skill_fencing": ((0.0, FENCING_WEAPON_FEINTS),),
    "skill_polearms": ((0.0, POLEARM_WEAPON_FEINTS),),
    "skill_macing": ((0.0, MACING_WEAPON_FEINTS),),
    "skill_archery": ((0.0, ARCHERY_WEAPON_FEINTS),),
    "skill_ranged_combat": ((0.0, RANGED_TACTICAL_FEINTS),),
    "skill_shield_mastery": ((0.0, SHIELD_TACTICAL_FEINTS),),
    "skill_two_handed": ((0.0, TWO_HANDED_TACTICAL_FEINTS),),
    "skill_dual_wield": ((0.0, DUAL_WIELD_TACTICAL_FEINTS),),
}
WEAPON_TECHNIQUE_UNLOCKS: tuple[tuple[float, tuple[str, ...]], ...] = ()
WEAPON_SKILL_TAGS: dict[str, frozenset[str]] = {}
WEAPON_TECHNIQUE_TAG_REQUIREMENTS: dict[str, frozenset[str]] = {}
WEAPON_MASTERY_FEINTS: dict[str, tuple[str, ...]] = {
    "skill_swords": SWORD_WEAPON_FEINTS,
    "skill_fencing": FENCING_WEAPON_FEINTS,
    "skill_polearms": POLEARM_WEAPON_FEINTS,
    "skill_macing": MACING_WEAPON_FEINTS,
    "skill_archery": ARCHERY_WEAPON_FEINTS,
}
TACTICAL_STYLE_FEINTS: dict[str, tuple[str, ...]] = {
    "skill_ranged_combat": RANGED_TACTICAL_FEINTS,
    "skill_shield_mastery": SHIELD_TACTICAL_FEINTS,
    "skill_two_handed": TWO_HANDED_TACTICAL_FEINTS,
    "skill_dual_wield": DUAL_WIELD_TACTICAL_FEINTS,
}


def build_known_feints(loadout: dict[str, Any], skills: dict[str, float] | None = None) -> list[str]:
    layout = loadout.get("layout") or {}
    known: list[str] = list(BASIC_ARCHERY_FEINTS if _uses_archery(layout) else BASIC_FEINTS)
    heavy_armor = _uses_heavy_armor(layout)

    for hand in ("main_hand", "off_hand"):
        skill_key = layout.get(hand)
        if skill_key == "skill_archery" and heavy_armor:
            continue
        if isinstance(skill_key, str):
            known.extend(WEAPON_MASTERY_FEINTS.get(skill_key, ()))

    tactical_style = layout.get("tactical_style")
    if tactical_style == "skill_ranged_combat" and heavy_armor:
        return _dedupe(known)
    if isinstance(tactical_style, str):
        known.extend(TACTICAL_STYLE_FEINTS.get(tactical_style, ()))

    return _dedupe(known)


def skill_feints_for_value(skill_key: str, skill_value: float) -> list[str]:
    unlocked: list[str] = []
    for threshold, feint_ids in SKILL_FEINT_UNLOCKS.get(skill_key, ()):
        if skill_value >= threshold:
            unlocked.extend(feint_ids)
    return _dedupe(unlocked)


def weapon_techniques_for_skill(skill_key: str, skill_value: float) -> list[str]:
    return []


def _uses_heavy_armor(layout: dict[str, Any]) -> bool:
    return layout.get("body") == "skill_heavy_armor"


def _uses_archery(layout: dict[str, Any]) -> bool:
    return layout.get("main_hand") == "skill_archery" or layout.get("off_hand") == "skill_archery"


def _dedupe(feint_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for feint_id in feint_ids:
        if feint_id in seen:
            continue
        seen.add(feint_id)
        result.append(feint_id)
    return result
