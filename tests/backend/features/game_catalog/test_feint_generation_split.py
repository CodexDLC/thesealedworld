from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.effects import get_effect_catalog_entry
from src.backend.features.game_catalog.combat.resources.feints import (
    FEINT_CATALOG_REGISTRY,
    get_feint_catalog_entry,
)
from src.backend.features.game_catalog.combat.resources.feints.availability import (
    BASIC_ARCHERY_FEINTS,
    BASIC_FEINTS,
    TACTICAL_STYLE_FEINTS,
    WEAPON_MASTERY_FEINTS,
    build_known_feints,
)
from src.backend.features.game_catalog.combat.resources.text_templates import build_combat_text_catalog

ACTIVE_BASIC_FEINT_IDS = {
    "blade_dance",
    "flawless_strike",
    "foresight_parry",
    "glancing_step",
    "measured_strike",
    "press_defense",
    "second_breath",
    "steady_strike",
    "wind_dance",
}

ACTIVE_SHIELD_TACTICAL_FEINT_IDS = {
    "absolute_defense",
    "aggressive_defense",
    "active_defense",
    "blood_wall_crash",
    "bloody_rebuke",
    "concussion",
    "full_defense",
    "read_tactic",
    "red_line_bash",
    "scarlet_riposte",
    "shield_line_bash",
}

ACTIVE_TWO_HANDED_TACTICAL_FEINT_IDS = {
    "answering_stance",
    "blade_return",
    "closed_distance",
    "crushing_pressure",
    "heavy_swing",
    "hidden_agility",
    "hidden_strength",
    "hard_intercept",
    "ignore_guard",
    "lucky_break",
    "open_wound",
    "push_stance",
    "steel_line",
    "two_handed_whirl",
}

ACTIVE_DUAL_WIELD_TACTICAL_FEINT_IDS = {
    "answering_series",
    "bind_blade",
    "blade_loop",
    "broken_step",
    "dual_blade_whirl",
    "empty_line",
    "offhand_over",
    "open_vein",
    "shifting_line",
    "silent_puncture",
    "torn_rhythm",
}

ACTIVE_ARCHERY_WEAPON_FEINT_IDS = {
    "arrow_rain",
    "headshot",
    "piercing_arrow",
    "precise_weak_spot",
    "quiet_weak_spot",
    "snap_shot",
}

ACTIVE_SWORD_WEAPON_FEINT_IDS = {
    "sword_blade_bind",
    "sword_clean_path",
    "sword_cut_angle",
    "sword_hard_bind",
    "sword_low_angle",
    "sword_measured_line",
    "sword_open_line",
}

ACTIVE_FENCING_WEAPON_FEINT_IDS = {
    "fencing_corner_entry",
    "fencing_gap_probe",
    "fencing_hidden_entry",
    "fencing_inside_line",
    "fencing_line_flurry",
    "fencing_needle_gap",
    "fencing_precise_prick",
    "fencing_slip_guard",
}

ACTIVE_POLEARM_WEAPON_FEINT_IDS = {
    "polearm_guard_intercept",
    "polearm_hook_step",
    "polearm_line_cleave",
    "polearm_leg_sweep",
    "polearm_locked_distance",
    "polearm_long_line",
    "polearm_pinning_point",
    "polearm_stunning_intercept",
}

ACTIVE_MACING_WEAPON_FEINT_IDS = {
    "macing_armor_crush",
    "macing_break_stance",
    "macing_break_swing",
    "macing_guard_cracker",
    "macing_heavy_line",
    "macing_skullbreaker",
    "macing_shock_sweep",
}

ACTIVE_RANGED_TACTICAL_FEINT_IDS = {
    "backstep_shot",
    "blinding_shot",
    "covering_position",
    "open_distance",
    "reveal_intentions",
    "ranged_covering_volley",
}

ACTIVE_MASS_TARGET_FEINTS = {
    "fencing_line_flurry": (TargetType.ALL_ENEMIES, 3, 0.55),
    "polearm_line_cleave": (TargetType.ALL_ENEMIES, 3, 0.75),
    "macing_shock_sweep": (TargetType.ALL_ENEMIES, 3, 0.65),
    "arrow_rain": (TargetType.ALL_ENEMIES, 99, 0.50),
    "red_line_bash": (TargetType.ALL_ENEMIES, 3, 0.50),
    "shield_line_bash": (TargetType.ALL_ENEMIES, 3, 0.45),
    "two_handed_whirl": (TargetType.ALL_ENEMIES, 3, 0.65),
    "dual_blade_whirl": (TargetType.ALL_ENEMIES, 99, 0.40),
}

ARCHIVED_FEINT_IDS = {
    "aimed_shot",
    "armor_slip",
    "brace_guard",
    "cleave",
    "close_grapple",
    "counter_parry",
    "counter_step",
    "counter_window",
    "critical_focus",
    "decisive_attack",
    "defensive_strike",
    "driven_line",
    "guard_breaker",
    "hamstring_cut",
    "line_catch",
    "loaded_crit",
    "low_blow",
    "low_line_step",
    "marked_opening",
    "parry_riposte",
    "piercing_thrust",
    "polearm_trip",
    "pommel_strike",
    "power_attack",
    "sand_throw",
    "seize_tempo",
    "shield_bash",
    "shield_drive",
    "shield_pressure",
    "side_cut",
    "spiked_guard",
    "steady_hand",
    "true_strike",
    "weapon_bind",
}


def test_archived_non_hit_feints_are_not_active_catalog_entries() -> None:
    assert ARCHIVED_FEINT_IDS.isdisjoint(FEINT_CATALOG_REGISTRY)
    for feint_id in ARCHIVED_FEINT_IDS:
        assert get_feint_catalog_entry(feint_id) is None


def test_feint_availability_matches_active_catalog() -> None:
    available_ids = set(BASIC_FEINTS) | set(BASIC_ARCHERY_FEINTS)
    for feint_ids in WEAPON_MASTERY_FEINTS.values():
        available_ids.update(feint_ids)
    for feint_ids in TACTICAL_STYLE_FEINTS.values():
        available_ids.update(feint_ids)

    assert available_ids == set(FEINT_CATALOG_REGISTRY)


def test_active_feint_preparation_effects_are_runtime_catalog_entries() -> None:
    for feint_id, entry in FEINT_CATALOG_REGISTRY.items():
        for effect_payload in entry.technical.preparation_effects or []:
            effect_id = effect_payload["id"]
            assert get_effect_catalog_entry(effect_id) is not None, (feint_id, effect_id)


def test_active_feint_catalog_contains_basic_and_shield_tactical_sets() -> None:
    removed_legacy_ids = {"blade_mill", "perfect_riposte", "sword_blade_whirl"}
    expected_active_ids = (
        ACTIVE_BASIC_FEINT_IDS
        | ACTIVE_SHIELD_TACTICAL_FEINT_IDS
        | ACTIVE_TWO_HANDED_TACTICAL_FEINT_IDS
        | ACTIVE_DUAL_WIELD_TACTICAL_FEINT_IDS
        | ACTIVE_ARCHERY_WEAPON_FEINT_IDS
        | ACTIVE_FENCING_WEAPON_FEINT_IDS
        | ACTIVE_MACING_WEAPON_FEINT_IDS
        | ACTIVE_POLEARM_WEAPON_FEINT_IDS
        | ACTIVE_SWORD_WEAPON_FEINT_IDS
        | ACTIVE_RANGED_TACTICAL_FEINT_IDS
    )
    assert expected_active_ids - removed_legacy_ids <= set(FEINT_CATALOG_REGISTRY)
    assert get_feint_catalog_entry("measured_strike").technical.cost.tactics == {"hit": 3}
    assert get_feint_catalog_entry("steady_strike").technical.cost.tactics == {"hit": 5}
    assert get_feint_catalog_entry("flawless_strike").technical.cost.tactics == {"hit": 7}
    assert get_feint_catalog_entry("glancing_step").technical.cost.tactics == {"dodge": 3}
    assert get_feint_catalog_entry("wind_dance").technical.cost.tactics == {"dodge": 5}
    assert get_feint_catalog_entry("blade_dance").technical.cost.tactics == {"dodge": 7}
    assert get_feint_catalog_entry("foresight_parry").technical.cost.tactics == {"parry": 3}
    assert get_feint_catalog_entry("second_breath").technical.cost.tactics == {"parry": 5}
    assert get_feint_catalog_entry("press_defense").technical.cost.tactics == {"pressure": 3}
    assert get_feint_catalog_entry("active_defense").technical.cost.tactics == {"block": 3}
    assert get_feint_catalog_entry("full_defense").technical.cost.tactics == {"block": 5}
    assert get_feint_catalog_entry("absolute_defense").technical.cost.tactics == {"block": 7}
    assert get_feint_catalog_entry("aggressive_defense").technical.cost.tactics == {"hit": 2, "block": 5}
    assert get_feint_catalog_entry("read_tactic").technical.cost.tactics == {"hit": 1, "block": 2}
    assert get_feint_catalog_entry("concussion").technical.cost.tactics == {"block": 3}
    assert get_feint_catalog_entry("shield_line_bash").technical.cost.tactics == {"hit": 3, "block": 3}
    assert get_feint_catalog_entry("bloody_rebuke").technical.cost.tactics == {"blood": 1, "hit": 2, "block": 2}
    assert get_feint_catalog_entry("blood_wall_crash").technical.cost.tactics == {"blood": 1, "hit": 3, "block": 3}
    assert get_feint_catalog_entry("scarlet_riposte").technical.cost.tactics == {"blood": 1, "block": 2, "parry": 2}
    assert get_feint_catalog_entry("red_line_bash").technical.cost.tactics == {"blood": 1, "hit": 4, "block": 2}
    assert get_feint_catalog_entry("crushing_pressure").technical.cost.tactics == {"hit": 3}
    assert get_feint_catalog_entry("steel_line").technical.cost.tactics == {"crit": 3}
    assert get_feint_catalog_entry("blade_return").technical.cost.tactics == {"hit": 2, "crit": 2}
    assert get_feint_catalog_entry("hard_intercept").technical.cost.tactics == {"hit": 1, "crit": 3}
    assert get_feint_catalog_entry("answering_stance").technical.cost.tactics == {"hit": 2, "crit": 3}
    assert get_feint_catalog_entry("closed_distance").technical.cost.tactics == {"hit": 3, "crit": 4}
    assert get_feint_catalog_entry("hidden_agility").technical.cost.tactics == {"hit": 1, "crit": 3, "parry": 2}
    assert get_feint_catalog_entry("push_stance").technical.cost.tactics == {"hit": 1, "parry": 2}
    assert get_feint_catalog_entry("ignore_guard").technical.cost.tactics == {"hit": 2, "parry": 2}
    assert get_feint_catalog_entry("open_wound").technical.cost.tactics == {"crit": 2, "parry": 2}
    assert get_feint_catalog_entry("heavy_swing").technical.cost.tactics == {"hit": 2, "parry": 3}
    assert get_feint_catalog_entry("hidden_strength").technical.cost.tactics == {"hit": 3, "parry": 3}
    assert get_feint_catalog_entry("lucky_break").technical.cost.tactics == {"crit": 5}
    assert get_feint_catalog_entry("two_handed_whirl").technical.cost.tactics == {"hit": 5, "parry": 2}
    assert get_feint_catalog_entry("broken_step").technical.cost.tactics == {"hit": 2, "dodge": 1}
    assert get_feint_catalog_entry("shifting_line").technical.cost.tactics == {"hit": 3, "dodge": 2}
    assert get_feint_catalog_entry("empty_line").technical.cost.tactics == {"hit": 4, "dodge": 2}
    assert get_feint_catalog_entry("torn_rhythm").technical.cost.tactics == {"hit": 5, "dodge": 3}
    assert get_feint_catalog_entry("bind_blade").technical.cost.tactics == {"hit": 2, "parry": 2}
    assert get_feint_catalog_entry("offhand_over").technical.cost.tactics == {"hit": 3, "parry": 2}
    assert get_feint_catalog_entry("open_vein").technical.cost.tactics == {"hit": 3, "parry": 3}
    assert get_feint_catalog_entry("silent_puncture").technical.cost.tactics == {"hit": 5, "parry": 3}
    assert get_feint_catalog_entry("answering_series").technical.cost.tactics == {"hit": 3, "pressure": 2}
    assert get_feint_catalog_entry("blade_loop").technical.cost.tactics == {"hit": 6, "parry": 3, "pressure": 3}
    assert get_feint_catalog_entry("dual_blade_whirl").technical.cost.tactics == {
        "hit": 5,
        "dodge": 3,
        "crit": 2,
    }
    assert get_feint_catalog_entry("arrow_rain").technical.cost.tactics == {"hit": 5, "crit": 2}
    assert get_feint_catalog_entry("snap_shot").technical.cost.tactics == {"hit": 3}
    assert get_feint_catalog_entry("headshot").technical.cost.tactics == {"hit": 3, "crit": 2}
    assert get_feint_catalog_entry("piercing_arrow").technical.cost.tactics == {"hit": 5, "crit": 2}
    assert get_feint_catalog_entry("precise_weak_spot").technical.cost.tactics == {"crit": 5}
    assert get_feint_catalog_entry("quiet_weak_spot").technical.cost.tactics == {"hit": 2, "crit": 3}
    assert get_feint_catalog_entry("sword_measured_line").technical.cost.tactics == {"hit": 3}
    assert get_feint_catalog_entry("sword_blade_bind").technical.cost.tactics == {"hit": 3, "parry": 2}
    assert get_feint_catalog_entry("sword_hard_bind").technical.cost.tactics == {"hit": 3, "parry": 5}
    assert get_feint_catalog_entry("sword_low_angle").technical.cost.tactics == {"hit": 3, "dodge": 2}
    assert get_feint_catalog_entry("sword_cut_angle").technical.cost.tactics == {"hit": 3, "dodge": 5}
    assert get_feint_catalog_entry("sword_open_line").technical.cost.tactics == {"hit": 3, "crit": 2}
    assert get_feint_catalog_entry("sword_clean_path").technical.cost.tactics == {"hit": 3, "crit": 5}
    assert get_feint_catalog_entry("fencing_precise_prick").technical.cost.tactics == {"hit": 3}
    assert get_feint_catalog_entry("fencing_corner_entry").technical.cost.tactics == {"hit": 3, "dodge": 2}
    assert get_feint_catalog_entry("fencing_hidden_entry").technical.cost.tactics == {"hit": 3, "dodge": 5}
    assert get_feint_catalog_entry("fencing_gap_probe").technical.cost.tactics == {"hit": 3, "crit": 2}
    assert get_feint_catalog_entry("fencing_needle_gap").technical.cost.tactics == {"hit": 3, "crit": 5}
    assert get_feint_catalog_entry("fencing_slip_guard").technical.cost.tactics == {"hit": 3, "parry": 2}
    assert get_feint_catalog_entry("fencing_inside_line").technical.cost.tactics == {"hit": 3, "parry": 5}
    assert get_feint_catalog_entry("fencing_line_flurry").technical.cost.tactics == {"hit": 4, "dodge": 2}
    assert get_feint_catalog_entry("polearm_long_line").technical.cost.tactics == {"hit": 3}
    assert get_feint_catalog_entry("polearm_hook_step").technical.cost.tactics == {"hit": 3, "dodge": 2}
    assert get_feint_catalog_entry("polearm_leg_sweep").technical.cost.tactics == {"hit": 3, "dodge": 5}
    assert get_feint_catalog_entry("polearm_guard_intercept").technical.cost.tactics == {"hit": 3, "parry": 2}
    assert get_feint_catalog_entry("polearm_stunning_intercept").technical.cost.tactics == {"hit": 3, "parry": 5}
    assert get_feint_catalog_entry("polearm_pinning_point").technical.cost.tactics == {"hit": 3, "crit": 2}
    assert get_feint_catalog_entry("polearm_locked_distance").technical.cost.tactics == {"hit": 3, "crit": 5}
    assert get_feint_catalog_entry("polearm_line_cleave").technical.cost.tactics == {"hit": 4, "parry": 1}
    assert get_feint_catalog_entry("macing_heavy_line").technical.cost.tactics == {"hit": 3}
    assert get_feint_catalog_entry("macing_armor_crush").technical.cost.tactics == {"hit": 3, "crit": 2}
    assert get_feint_catalog_entry("macing_skullbreaker").technical.cost.tactics == {"hit": 3, "crit": 5}
    assert get_feint_catalog_entry("macing_break_swing").technical.cost.tactics == {"hit": 3, "parry": 2}
    assert get_feint_catalog_entry("macing_break_stance").technical.cost.tactics == {"hit": 3, "parry": 5}
    assert get_feint_catalog_entry("macing_guard_cracker").technical.cost.tactics == {"hit": 5, "crit": 3}
    assert get_feint_catalog_entry("macing_shock_sweep").technical.cost.tactics == {"hit": 5, "parry": 2}
    assert get_feint_catalog_entry("reveal_intentions").technical.cost.tactics == {"hit": 2, "tempo": 1}
    assert get_feint_catalog_entry("covering_position").technical.cost.tactics == {"dodge": 3, "tempo": 2}
    assert get_feint_catalog_entry("backstep_shot").technical.cost.tactics == {"hit": 2, "dodge": 3}
    assert get_feint_catalog_entry("open_distance").technical.cost.tactics == {"dodge": 5, "tempo": 2}
    assert get_feint_catalog_entry("blinding_shot").technical.cost.tactics == {"hit": 3, "tempo": 2}
    assert get_feint_catalog_entry("ranged_covering_volley").technical.cost.tactics == {"hit": 4, "tempo": 2}
    assert all(
        "counter" not in get_feint_catalog_entry(feint_id).technical.cost.tactics
        for feint_id in ACTIVE_RANGED_TACTICAL_FEINT_IDS
    )
    assert get_feint_catalog_entry("ranged_covering_volley").technical.target == TargetType.SINGLE_ENEMY
    shield_weapon_feint_ids = {
        "blood_wall_crash",
        "bloody_rebuke",
        "concussion",
        "red_line_bash",
        "shield_line_bash",
    }
    two_handed_weapon_feint_ids = {
        "heavy_swing",
        "hidden_strength",
        "ignore_guard",
        "lucky_break",
        "open_wound",
        "push_stance",
        "two_handed_whirl",
    }
    dual_wield_weapon_feint_ids = {"dual_blade_whirl", "open_vein", "silent_puncture"}
    ranged_weapon_feint_ids = {"ranged_covering_volley"}
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "basic" for feint_id in ACTIVE_BASIC_FEINT_IDS
    )
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "tactical"
        for feint_id in ACTIVE_SHIELD_TACTICAL_FEINT_IDS - shield_weapon_feint_ids
    )
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "tactical"
        for feint_id in ACTIVE_TWO_HANDED_TACTICAL_FEINT_IDS - two_handed_weapon_feint_ids
    )
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "tactical"
        for feint_id in ACTIVE_DUAL_WIELD_TACTICAL_FEINT_IDS - dual_wield_weapon_feint_ids
    )
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "weapon"
        for feint_id in (
            ACTIVE_ARCHERY_WEAPON_FEINT_IDS
            | shield_weapon_feint_ids
            | two_handed_weapon_feint_ids
            | dual_wield_weapon_feint_ids
            | ranged_weapon_feint_ids
        )
    )
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "weapon"
        for feint_id in ACTIVE_SWORD_WEAPON_FEINT_IDS
    )
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "weapon"
        for feint_id in ACTIVE_FENCING_WEAPON_FEINT_IDS
    )
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "weapon"
        for feint_id in ACTIVE_POLEARM_WEAPON_FEINT_IDS
    )
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "weapon"
        for feint_id in ACTIVE_MACING_WEAPON_FEINT_IDS
    )
    assert all(
        "dodge" not in get_feint_catalog_entry(feint_id).technical.cost.tactics
        for feint_id in ACTIVE_MACING_WEAPON_FEINT_IDS
    )
    assert get_feint_catalog_entry("polearm_leg_sweep").technical.effects == [
        {"id": "knockdown", "target_actor": "target"},
        {"id": "force_ranged_close", "target_actor": "target"},
    ]
    assert get_feint_catalog_entry("polearm_stunning_intercept").technical.effects == [
        {"id": "stun", "target_actor": "target"},
        {"id": "force_ranged_close", "target_actor": "target"},
    ]
    assert get_feint_catalog_entry("macing_skullbreaker").technical.effects == [
        {"id": "stun", "target_actor": "target", "conditions": {"is_crit": True}},
        {"id": "force_ranged_close", "target_actor": "target", "conditions": {"is_crit": True}},
    ]
    assert [mutation.mutation_id for mutation in get_feint_catalog_entry("precise_weak_spot").technical.pipeline_mutations] == [
        "force.crit"
    ]
    assert [
        mutation.mutation_id for mutation in get_feint_catalog_entry("quiet_weak_spot").technical.pipeline_mutations
    ] == ["force.crit", "crit_damage_boost", "suppress_crit_triggers"]
    assert get_feint_catalog_entry("precise_weak_spot").technical.effects is None
    assert get_feint_catalog_entry("quiet_weak_spot").technical.effects is None
    assert all(
        get_feint_catalog_entry(feint_id).technical.purchase_group == "tactical"
        for feint_id in ACTIVE_RANGED_TACTICAL_FEINT_IDS - ranged_weapon_feint_ids
    )


def test_mass_target_feints_use_all_enemies_and_secondary_damage_caps() -> None:
    for feint_id, (target_type, target_count, secondary_damage_mult) in ACTIVE_MASS_TARGET_FEINTS.items():
        entry = get_feint_catalog_entry(feint_id)
        assert entry is not None, feint_id
        assert entry.technical.target == target_type
        assert entry.technical.target_count == target_count
        assert entry.technical.secondary_damage_mult == secondary_damage_mult
        assert "multi_target" in entry.technical.applicability_tags


def test_basic_hit_feints_have_combat_text_recipes_from_new_catalog_system() -> None:
    catalog = build_combat_text_catalog()
    for feint_id in (
        ACTIVE_BASIC_FEINT_IDS
        | ACTIVE_SHIELD_TACTICAL_FEINT_IDS
        | ACTIVE_TWO_HANDED_TACTICAL_FEINT_IDS
        | ACTIVE_DUAL_WIELD_TACTICAL_FEINT_IDS
        | ACTIVE_ARCHERY_WEAPON_FEINT_IDS
        | ACTIVE_FENCING_WEAPON_FEINT_IDS
        | ACTIVE_MACING_WEAPON_FEINT_IDS
        | ACTIVE_POLEARM_WEAPON_FEINT_IDS
        | ACTIVE_SWORD_WEAPON_FEINT_IDS
        | ACTIVE_RANGED_TACTICAL_FEINT_IDS
    ):
        assert f"combat.feint.{feint_id}.hit.humanoid_to_humanoid.weapon" in catalog["templates"]
        assert f"combat.feint.{feint_id}.crit.humanoid_to_humanoid.weapon" in catalog["templates"]

    assert "combat.feint.decisive_attack.hit.humanoid_to_humanoid.weapon" not in catalog["templates"]
    assert "combat.feint.true_strike.hit.humanoid_to_humanoid.weapon" not in catalog["templates"]


def test_ranged_feint_templates_use_archery_phrase_fragments() -> None:
    catalog = build_combat_text_catalog()
    hit_template = catalog["templates"]["combat.feint.snap_shot.hit.humanoid_to_humanoid.weapon"]
    crit_template = catalog["templates"]["combat.feint.quiet_weak_spot.crit.humanoid_to_humanoid.weapon"]

    assert hit_template["phrase_keys"]["weapon_form"] == "body.humanoid.weapon_form.skill_archery.moving_shot"
    assert hit_template["phrase_keys"]["impact"] == "body.humanoid.impact_vs_humanoid.ranged.hit.arrow"
    assert crit_template["phrase_keys"]["weapon_form"] == "body.humanoid.weapon_form.skill_archery.aimed_shot"
    assert crit_template["phrase_keys"]["impact"] == "body.humanoid.impact_vs_humanoid.ranged.crit.arrow"


def test_archery_basic_exchange_templates_use_archery_phrase_fragments() -> None:
    catalog = build_combat_text_catalog()
    hit_template = catalog["templates"]["combat.exchange.skill_archery.main_hand.hit.humanoid_to_humanoid.weapon"]
    dodge_template = catalog["templates"]["combat.exchange.skill_archery.main_hand.dodge.humanoid_to_humanoid.weapon"]

    assert hit_template["resource_id"] == "skill_archery.main_hand"
    assert hit_template["phrase_keys"]["weapon_form"] == "body.humanoid.weapon_form.skill_archery.moving_shot"
    assert hit_template["phrase_keys"]["impact"] == "body.humanoid.impact_vs_humanoid.ranged.hit.arrow"
    assert dodge_template["phrase_keys"]["weapon_form"] == "body.humanoid.weapon_form.skill_archery.quick_shot"
    assert all("skill_swords" not in value for value in hit_template["phrase_keys"].values())
    assert all("skill_swords" not in value for value in dodge_template["phrase_keys"].values())


def test_legacy_generic_humanoid_weapon_basic_exchange_templates_are_not_public() -> None:
    catalog = build_combat_text_catalog()

    assert "combat.exchange.basic.hit.humanoid_to_humanoid.weapon" not in catalog["templates"]
    assert "combat.exchange.basic.miss.humanoid_to_beast.weapon" not in catalog["templates"]
    assert "combat.exchange.basic.dodge.humanoid_to_humanoid.weapon" not in catalog["templates"]
    assert "combat.exchange.basic.hit.beast_to_humanoid.natural" not in catalog["templates"]
    assert "combat.exchange.natural_weapon.fangs.main_hand.hit.beast_to_humanoid.natural" in catalog["templates"]
    assert "combat.exchange.natural_weapon.claws.main_hand.hit.beast_to_humanoid.natural" in catalog["templates"]
    assert "combat.exchange.natural_weapon.default.main_hand.hit.beast_to_humanoid.natural" in catalog["templates"]


def test_known_feints_include_basic_archery_and_ranged_tactical_without_heavy_armor() -> None:
    known = build_known_feints(
        {
            "layout": {
                "main_hand": "skill_archery",
                "tactical_style": "skill_ranged_combat",
                "body": "skill_light_armor",
            }
        },
        {"skill_archery": 0.3, "skill_ranged_combat": 0.2},
    )

    assert set(known).issuperset(BASIC_ARCHERY_FEINTS)
    assert "foresight_parry" not in known
    assert "second_breath" not in known
    assert "perfect_riposte" not in known
    assert set(ACTIVE_ARCHERY_WEAPON_FEINT_IDS).issubset(known)
    assert set(ACTIVE_RANGED_TACTICAL_FEINT_IDS).issubset(known)


def test_heavy_armor_blocks_archery_and_ranged_tactical_feints_only() -> None:
    known = build_known_feints(
        {
            "layout": {
                "main_hand": "skill_archery",
                "tactical_style": "skill_ranged_combat",
                "body": "skill_heavy_armor",
            }
        },
        {"skill_archery": 0.3, "skill_ranged_combat": 0.2, "skill_heavy_armor": 0.4},
    )

    assert set(known) == set(BASIC_ARCHERY_FEINTS)

    shield_known = build_known_feints({"layout": {"tactical_style": "skill_shield_mastery", "body": "skill_heavy_armor"}})

    assert set(ACTIVE_SHIELD_TACTICAL_FEINT_IDS).issubset(shield_known)
