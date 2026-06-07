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
    "press_defense",
    "press_defense_advanced",
    "basic_seize_tempo",
    "measured_strike_advanced",
)

BASIC_ARCHERY_FEINTS: tuple[str, ...] = (
    "measured_strike",
    "steady_strike",
    "flawless_strike",
    "glancing_step",
    "wind_dance",
    "blade_dance",
    "press_defense",
)

SWORD_WEAPON_FEINTS: tuple[str, ...] = (
    "sword_measured_line",
    "sword_blade_bind",
    "sword_low_angle",
    "sword_open_line",
    "sword_hard_bind",
    "sword_cut_angle",
    "sword_clean_path",
    "sword_cross_arc",
    "sword_full_circle",
    "sword_low_angle_advanced",
    "sword_clean_path_advanced",
    "sword_full_circle_advanced",
)

FENCING_WEAPON_FEINTS: tuple[str, ...] = (
    "fencing_precise_prick",
    "fencing_corner_entry",
    "fencing_hidden_entry",
    "fencing_gap_probe",
    "fencing_needle_gap",
    "fencing_slip_guard",
    "fencing_inside_line",
    "fencing_line_flurry",
    "fencing_storm_lattice",
    "fencing_corner_entry_advanced",
    "fencing_hidden_entry_advanced",
    "fencing_storm_lattice_advanced",
)

POLEARM_WEAPON_FEINTS: tuple[str, ...] = (
    "polearm_long_line",
    "polearm_hook_step",
    "polearm_leg_sweep",
    "polearm_guard_intercept",
    "polearm_stunning_intercept",
    "polearm_pinning_point",
    "polearm_locked_distance",
    "polearm_line_cleave",
    "polearm_field_sweep",
    "polearm_topple_strike",
    "polearm_pinning_point_advanced",
    "polearm_locked_distance_advanced",
    "polearm_field_sweep_advanced",
)

MACING_WEAPON_FEINTS: tuple[str, ...] = (
    "macing_heavy_line",
    "macing_armor_crush",
    "macing_skullbreaker",
    "macing_break_swing",
    "macing_break_stance",
    "macing_guard_cracker",
    "macing_shock_sweep",
    "macing_earthshatter",
    "macing_skullbreaker_advanced",
    "macing_break_stance_advanced",
    "macing_earthshatter_advanced",
)

ARCHERY_WEAPON_FEINTS: tuple[str, ...] = (
    "arrow_rain",
    "arrow_fan",
    "snap_shot",
    "headshot",
    "piercing_arrow",
    "precise_weak_spot",
    "quiet_weak_spot",
    "snap_shot_advanced",
    "headshot_advanced",
    "piercing_arrow_advanced",
    "arrow_rain_advanced",
    "blood_aim_crit",
    "pain_backstep",
)

RANGED_TACTICAL_FEINTS: tuple[str, ...] = (
    "reveal_intentions",
    "covering_position",
    "backstep_shot",
    "open_distance",
    "blinding_shot",
    "ranged_covering_volley",
    "ranged_terrain_read",
)

SHIELD_TACTICAL_FEINTS: tuple[str, ...] = (
    "active_defense",
    "full_defense",
    "absolute_defense",
    "aggressive_defense",
    "read_tactic",
    "concussion",
    "shield_line_bash",
    "bloody_rebuke",
    "blood_wall_crash",
    "scarlet_riposte",
    "red_line_bash",
    "shield_anti_dispel_brace",
    "shield_focused_pressure",
    "shield_blood_ward",
    "read_tactic_advanced",
    "shield_blood_mend",
    "shield_aegis_break",
    "concussion_advanced",
    "shield_line_bash_advanced",
    "shield_aegis_break_advanced",
)

TWO_HANDED_TACTICAL_FEINTS: tuple[str, ...] = (
    "crushing_pressure",
    "steel_line",
    "blade_return",
    "hard_intercept",
    "answering_stance",
    "closed_distance",
    "hidden_agility",
    "2h_brace_to_blade",
    "2h_blade_to_break",
    "2h_break_to_step",
    "2h_press_to_parry",
    "2h_blood_to_crit",
    "2h_perfect_riposte",
    "push_stance",
    "ignore_guard",
    "open_wound",
    "heavy_swing",
    "hidden_strength",
    "lucky_break",
    "two_handed_whirl",
    "two_handed_devastation",
    "two_handed_momentum_strike",
    "heavy_swing_advanced",
    "ignore_guard_advanced",
    "lucky_break_advanced",
    "two_handed_whirl_advanced",
    "two_handed_devastation_advanced",
)

DUAL_WIELD_TACTICAL_FEINTS: tuple[str, ...] = (
    "broken_step",
    "shifting_line",
    "empty_line",
    "torn_rhythm",
    "bind_blade",
    "offhand_over",
    "dual_blade_mill_v2",
    "dual_split_targets",
    "dual_chain_follow",
    "dual_paired_open",
    "dual_cross_lock",
    "dual_blade_vise",
    "dual_crimson_lock",
    "open_vein",
    "silent_puncture",
    "answering_series",
    "blade_loop",
    "dual_cross_slash",
    "dual_blade_whirl",
    "open_vein_advanced",
    "silent_puncture_advanced",
    "dual_blade_whirl_advanced",
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
