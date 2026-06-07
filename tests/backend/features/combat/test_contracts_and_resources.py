from src.backend.features.combat.dto import (
    BattleContext,
    BattleMeta,
    CombatActionDTO,
    CombatMoveDTO,
    ExchangePayload,
)
from src.backend.features.combat.dto.pipeline import PipelineContextDTO
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.engine.pipeline_mutation_service import PipelineMutationService
from src.backend.features.game_catalog.combat.resources import CombatResourceCatalogService
from src.backend.features.game_catalog.combat.resources.abilities import get_ability_catalog_entry
from src.backend.features.game_catalog.combat.resources.abilities.definitions.basic_gift import (
    BASIC_GIFT_ABILITY_IDS,
)
from src.backend.features.game_catalog.combat.resources.abilities.enums import AbilitySource
from src.backend.features.game_catalog.combat.resources.common import CombatEventTextSetDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import (
    PIPELINE_MUTATION_CONTRACTS,
    pipeline_mutation,
)
from src.backend.features.game_catalog.combat.resources.feints import get_feint_catalog_entry
from src.backend.features.game_catalog.combat.resources.gifts import get_gift_catalog_entry
from src.backend.features.game_catalog.combat.resources.items import get_combat_item_action_catalog_entry
from src.backend.features.game_catalog.combat.resources.tokens import get_all_combat_tokens
from src.shared.schemas.messages import GameMessageDTO, GameMessageTabDTO, GameMessageTemplateDTO


def test_combat_action_contract_preserves_exchange_pair() -> None:
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="future_feint_placeholder"),
    )
    partner = CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1))

    action = CombatActionDTO(action_type="exchange", move=move, partner_move=partner)

    assert action.move.payload.target_id == "2"
    assert action.partner_move is not None
    assert action.partner_move.payload.target_id == "1"
    assert action.is_forced is False


def test_battle_context_contract_has_target_return_queue() -> None:
    meta = BattleMeta(
        active=1,
        step_counter=0,
        active_actors_count=0,
        teams={"a": [], "b": []},
        battle_type="standard",
        location_id="test",
    )
    context = BattleContext(session_id="combat-1", meta=meta, actors={})

    context.pending_target_returns.append({"source_id": "1", "target_id": "2"})

    assert context.pending_target_returns == [{"source_id": "1", "target_id": "2"}]


def test_combat_resources_load_runtime_and_public_catalog() -> None:
    catalog = CombatResourceCatalogService.load_default().all_public_text()

    assert get_ability_catalog_entry("fireball") is not None
    assert get_feint_catalog_entry("measured_strike") is not None
    assert catalog["abilities"]["fireball"]["target"] == "single_enemy"
    assert catalog["combat_entries"]["combat.ability.fireball"]["resource_id"] == "fireball"
    assert catalog["combat_entries"]["combat.gift.gift_true_fire"]["resource_id"] == "gift_true_fire"
    assert catalog["combat_entries"]["combat.item.fire_grenade"]["resource_id"] == "fire_grenade"
    expected_feints = {
        "blade_dance",
        "absolute_defense",
        "aggressive_defense",
        "active_defense",
        "answering_stance",
        "answering_series",
        "arrow_rain",
        "backstep_shot",
        "blade_return",
        "blade_loop",
        "dual_blade_mill_v2",
        "bind_blade",
        "blinding_shot",
        "blood_wall_crash",
        "bloody_rebuke",
        "broken_step",
        "closed_distance",
        "concussion",
        "covering_position",
        "crushing_pressure",
        "dual_blade_whirl",
        "empty_line",
        "fencing_corner_entry",
        "fencing_gap_probe",
        "fencing_hidden_entry",
        "fencing_inside_line",
        "fencing_line_flurry",
        "fencing_needle_gap",
        "fencing_precise_prick",
        "fencing_slip_guard",
        "flawless_strike",
        "foresight_parry",
        "full_defense",
        "glancing_step",
        "hard_intercept",
        "heavy_swing",
        "headshot",
        "hidden_agility",
        "hidden_strength",
        "ignore_guard",
        "lucky_break",
        "macing_armor_crush",
        "macing_break_stance",
        "macing_break_swing",
        "macing_guard_cracker",
        "macing_heavy_line",
        "macing_shock_sweep",
        "macing_skullbreaker",
        "measured_strike",
        "offhand_over",
        "open_distance",
        "open_wound",
        "open_vein",
        "2h_perfect_riposte",
        "piercing_arrow",
        "polearm_guard_intercept",
        "polearm_hook_step",
        "polearm_leg_sweep",
        "polearm_line_cleave",
        "polearm_locked_distance",
        "polearm_long_line",
        "polearm_pinning_point",
        "polearm_stunning_intercept",
        "press_defense",
        "precise_weak_spot",
        "push_stance",
        "quiet_weak_spot",
        "ranged_covering_volley",
        "read_tactic",
        "red_line_bash",
        "reveal_intentions",
        "scarlet_riposte",
        "second_breath",
        "shield_line_bash",
        "shifting_line",
        "silent_puncture",
        "snap_shot",
        "steel_line",
        "steady_strike",
        "sword_blade_bind",
        "sword_clean_path",
        "sword_cut_angle",
        "sword_hard_bind",
        "sword_low_angle",
        "sword_measured_line",
        "sword_open_line",
        "torn_rhythm",
        "two_handed_whirl",
        "wind_dance",
    }
    assert expected_feints.issubset(set(catalog["feints"]))
    assert catalog["feints"]["measured_strike"]["cost"]["tactics"] == {"hit": 3}
    assert catalog["feints"]["glancing_step"]["cost"]["tactics"] == {"dodge": 3}
    assert catalog["feints"]["2h_perfect_riposte"]["cost"]["tactics"] == {"parry": 7}
    assert catalog["feints"]["absolute_defense"]["cost"]["tactics"] == {"block": 7}
    assert catalog["feints"]["read_tactic"]["cost"]["tactics"] == {"hit": 1, "block": 2}
    assert catalog["feints"]["bloody_rebuke"]["cost"]["tactics"] == {"blood": 1, "hit": 2, "block": 2}
    assert catalog["feints"]["scarlet_riposte"]["cost"]["tactics"] == {"blood": 1, "block": 2, "parry": 2}
    assert catalog["feints"]["crushing_pressure"]["cost"]["tactics"] == {"hit": 3}
    assert catalog["feints"]["ignore_guard"]["cost"]["tactics"] == {"hit": 2, "parry": 2}
    assert catalog["feints"]["offhand_over"]["cost"]["tactics"] == {"hit": 3, "parry": 2}
    assert catalog["feints"]["dual_blade_mill_v2"]["cost"]["tactics"] == {"hit": 5, "pressure": 4}
    assert catalog["feints"]["snap_shot"]["cost"]["tactics"] == {"hit": 3}
    assert catalog["feints"]["sword_blade_bind"]["cost"]["tactics"] == {"hit": 3, "parry": 2}
    assert catalog["feints"]["sword_clean_path"]["cost"]["tactics"] == {"hit": 3, "crit": 5}
    assert catalog["feints"]["fencing_gap_probe"]["cost"]["tactics"] == {"hit": 3, "crit": 2}
    assert catalog["feints"]["fencing_needle_gap"]["cost"]["tactics"] == {"hit": 3, "crit": 5}
    assert catalog["feints"]["polearm_hook_step"]["cost"]["tactics"] == {"hit": 3, "dodge": 2}
    assert catalog["feints"]["polearm_locked_distance"]["cost"]["tactics"] == {"hit": 3, "crit": 5}
    assert catalog["feints"]["macing_break_swing"]["cost"]["tactics"] == {"hit": 3, "parry": 2}
    assert catalog["feints"]["macing_guard_cracker"]["cost"]["tactics"] == {"hit": 5, "crit": 3}
    assert catalog["feints"]["reveal_intentions"]["cost"]["tactics"] == {"hit": 2, "tempo": 1}
    assert catalog["combat_entries"]["combat.feint.measured_strike"]["resource_id"] == "measured_strike"
    assert catalog["combat_entries"]["combat.feint.absolute_defense"]["resource_id"] == "absolute_defense"
    assert catalog["combat_entries"]["combat.feint.hidden_strength"]["resource_id"] == "hidden_strength"
    assert catalog["combat_entries"]["combat.feint.blade_loop"]["resource_id"] == "blade_loop"
    assert not any(key.startswith("combat.trigger.crit.") for key in catalog["triggers"])
    assert not any(key.startswith("combat.trigger.crit.") for key in catalog["combat_entries"])
    assert catalog["triggers"]["combat.trigger.weapon.heavy_crit"]["resource_id"] == "weapon_heavy_crit"
    assert catalog["combat_entries"]["combat.trigger.weapon.heavy_crit"]["resource_id"] == "weapon_heavy_crit"
    assert catalog["combat_entries"]["combat.basic_exchange.skill_swords.main_hand"]["resource_id"] == (
        "skill_swords.main_hand"
    )


def test_combat_text_catalog_covers_feints_against_beasts_and_riposte_proc() -> None:
    feint_hit = CombatCatalogIntegrator.get_combat_text_template(
        resource_type="feint",
        resource_id="fencing_precise_prick",
        outcome="hit",
        source_body="humanoid",
        target_body="beast",
        delivery="weapon",
    )
    feint_miss = CombatCatalogIntegrator.get_combat_text_template(
        resource_type="feint",
        resource_id="dual_cross_slash",
        outcome="miss",
        source_body="humanoid",
        target_body="beast",
        delivery="weapon",
    )
    no_resource = CombatCatalogIntegrator.get_combat_text_template(
        resource_type="feint",
        resource_id="dual_cross_slash",
        outcome="no_resource",
        source_body="beast",
        target_body="humanoid",
        delivery="weapon",
    )
    riposte = CombatCatalogIntegrator.get_combat_text_template(
        resource_type="trigger",
        resource_id="weapon_riposte_on_parry",
        outcome="parry_proc",
        source_body="humanoid",
        target_body="beast",
        delivery="default",
    )

    assert feint_hit["key"] == "combat.feint.fencing_precise_prick.hit.humanoid_to_beast.weapon"
    assert feint_miss["key"] == "combat.feint.dual_cross_slash.miss.humanoid_to_beast.weapon"
    assert no_resource["key"] == "combat.feint.dual_cross_slash.no_resource.weapon"
    assert riposte["key"] == "combat.trigger.weapon.riposte_on_parry.parry_proc.beast"


def test_combat_token_catalog_replaces_counter_currency_with_pressure() -> None:
    tokens = get_all_combat_tokens()

    assert "pressure" in tokens
    assert tokens["pressure"]["title"] == "Нажим"
    assert "counter" not in tokens


def test_feint_costs_do_not_require_counter_token() -> None:
    catalog = CombatResourceCatalogService.load_default().all_public_text()

    for feint_id, payload in catalog["feints"].items():
        tactics = payload.get("cost", {}).get("tactics", {})
        assert "counter" not in tactics, feint_id


def test_basic_gift_abilities_are_runtime_resources_with_combat_token_costs() -> None:
    expected_costs = {
        "basic_break_stance": {"stamina": 0, "energy": 0, "gift_tokens": 0, "tokens": {"tempo": 3, "hit": 2}},
        "basic_expose_weakness": {"stamina": 0, "energy": 0, "gift_tokens": 0, "tokens": {"tempo": 2, "crit": 2}},
        "basic_wipe_blood": {"stamina": 0, "energy": 5, "gift_tokens": 1, "tokens": {"blood": 3, "block": 1}},
        "basic_last_push": {"stamina": 0, "energy": 5, "gift_tokens": 1, "tokens": {"blood": 3, "parry": 1}},
        "basic_slip_pain": {"stamina": 0, "energy": 5, "gift_tokens": 1, "tokens": {"blood": 3, "dodge": 1}},
        "basic_blood_hunger": {
            "stamina": 0,
            "energy": 0,
            "gift_tokens": 1,
            "tokens": {"tempo": 5, "pressure": 5},
        },
        "basic_splinter_strike": {"stamina": 0, "energy": 5, "gift_tokens": 1, "tokens": {"hit": 3}},
        "basic_cleave_gift": {
            "stamina": 0,
            "energy": 0,
            "gift_tokens": 3,
            "tokens": {"hit": 3, "pressure": 3},
        },
    }

    assert tuple(expected_costs) == BASIC_GIFT_ABILITY_IDS

    for ability_id, costs in expected_costs.items():
        entry = get_ability_catalog_entry(ability_id)
        assert entry is not None
        assert entry.key == f"combat.ability.{ability_id}"
        assert entry.technical.source == AbilitySource.COMBAT
        assert entry.technical.cost.energy == costs["energy"]
        assert entry.technical.cost.stamina == costs["stamina"]
        assert entry.technical.cost.gift_tokens == costs.get("gift_tokens", 0)
        assert entry.technical.cost.tokens == costs["tokens"]
        assert entry.descriptive.variants["humanoid"].display_name

    for removed_ability_id in (
        "basic_punish_mistake",
        "basic_finish_moment",
        "basic_grit_teeth",
        "basic_bloody_answer",
    ):
        assert get_ability_catalog_entry(removed_ability_id) is None

    for ability_id in ("basic_break_stance", "basic_expose_weakness"):
        entry = get_ability_catalog_entry(ability_id)
        assert entry is not None
        assert entry.technical.override_damage is None
        assert entry.technical.pipeline_mutations is not None
        assert entry.technical.pipeline_mutations.preset == "TACTICAL_INSTANT_STRIKE"
        applications = {app.mutation_id: app.value_override for app in entry.technical.pipeline_mutations.applications}
        assert applications["damage_mult"] == 1.2

    wipe_blood = get_ability_catalog_entry("basic_wipe_blood")
    last_push = get_ability_catalog_entry("basic_last_push")
    slip_pain = get_ability_catalog_entry("basic_slip_pain")
    blood_hunger = get_ability_catalog_entry("basic_blood_hunger")
    splinter_strike = get_ability_catalog_entry("basic_splinter_strike")
    cleave_gift = get_ability_catalog_entry("basic_cleave_gift")

    assert wipe_blood is not None
    assert wipe_blood.technical.symbiote_ability_mult == 1.0
    assert wipe_blood.technical.override_damage is None
    assert [app.modifier_id for app in wipe_blood.technical.modifier_applications] == [
        "hp_regen_add",
        "parry_add",
        "parry_cap_add",
    ]
    assert [app.duration_exchanges for app in wipe_blood.technical.modifier_applications] == [3, 3, 3]
    assert all(app.scale_value_with_symbiote for app in wipe_blood.technical.modifier_applications)
    assert all(app.scale_duration_with_symbiote for app in wipe_blood.technical.modifier_applications)
    assert last_push is not None
    assert last_push.technical.symbiote_ability_mult == 1.0
    assert last_push.technical.override_damage is None
    assert [app.modifier_id for app in last_push.technical.modifier_applications] == [
        "hp_regen_add",
        "accuracy_add",
        "accuracy_cap_add",
    ]
    assert [app.duration_exchanges for app in last_push.technical.modifier_applications] == [3, 3, 3]
    assert all(app.scale_value_with_symbiote for app in last_push.technical.modifier_applications)
    assert all(app.scale_duration_with_symbiote for app in last_push.technical.modifier_applications)
    assert slip_pain is not None
    assert slip_pain.technical.symbiote_ability_mult == 1.0
    assert slip_pain.technical.override_damage is None
    assert [app.modifier_id for app in slip_pain.technical.modifier_applications] == [
        "hp_regen_add",
        "incoming_damage_absorb_pct_add",
    ]
    assert [app.duration_exchanges for app in slip_pain.technical.modifier_applications] == [3, 3]
    assert all(app.scale_value_with_symbiote for app in slip_pain.technical.modifier_applications)
    assert all(app.scale_duration_with_symbiote for app in slip_pain.technical.modifier_applications)
    assert blood_hunger is not None
    assert blood_hunger.technical.symbiote_ability_mult == 1.0
    assert blood_hunger.technical.override_damage is None
    assert blood_hunger.technical.pipeline_mutations is not None
    assert blood_hunger.technical.pipeline_mutations.preset == "BUFF"
    assert [app.mutation_id for app in blood_hunger.technical.pipeline_mutations.applications] == ["damage.vampiric"]
    assert [app.modifier_id for app in blood_hunger.technical.modifier_applications] == [
        "physical_damage_bonus_add",
        "vampiric_power_add",
    ]
    assert [app.duration_exchanges for app in blood_hunger.technical.modifier_applications] == [5, 5]
    assert all(app.scale_value_with_symbiote for app in blood_hunger.technical.modifier_applications)
    assert all(app.scale_duration_with_symbiote for app in blood_hunger.technical.modifier_applications)
    assert splinter_strike is not None
    assert splinter_strike.technical.target.value == "random_enemy"
    assert splinter_strike.technical.target_count == 3
    assert splinter_strike.technical.secondary_damage_mult == 0.5
    assert cleave_gift is not None
    assert [app.modifier_id for app in cleave_gift.technical.modifier_applications] == [
        "cleave_damage_mult_add",
        "cleave_target_count_add",
    ]
    assert [app.duration_exchanges for app in cleave_gift.technical.modifier_applications] == [3, 3]


def test_public_ability_catalog_exposes_tooltip_payload() -> None:
    catalog = CombatResourceCatalogService.load_default().all_public_text()

    break_stance = catalog["abilities"]["basic_break_stance"]
    expose_weakness = catalog["abilities"]["basic_expose_weakness"]

    for removed_ability_id in (
        "basic_punish_mistake",
        "basic_finish_moment",
        "basic_grit_teeth",
        "basic_bloody_answer",
    ):
        assert removed_ability_id not in catalog["abilities"]

    assert break_stance["target_label"] == "Один враг"
    assert break_stance["cost"] == {
        "energy": 0,
        "stamina": 0,
        "hp": 0,
        "gift_tokens": 0,
        "tokens": {"tempo": 3, "hit": 2},
    }
    assert "Тип: тактический удар" in break_stance["mechanics"]
    assert "Урон оружия: x1.2" in break_stance["mechanics"]
    assert "Цель получает: физический урон -25% урона умения на 4 размена" in break_stance["mechanics"]

    assert expose_weakness["description"] == "Тратит темп и критический момент, чтобы подавить уклонение цели."
    assert expose_weakness["cost"] == {
        "energy": 0,
        "stamina": 0,
        "hp": 0,
        "gift_tokens": 0,
        "tokens": {"tempo": 2, "crit": 2},
    }
    assert "Тип: тактический удар" in expose_weakness["mechanics"]
    assert "Урон оружия: x1.2" in expose_weakness["mechanics"]
    assert "Цель получает: уклонение -0.5 на 3 размена" in expose_weakness["mechanics"]


def test_ability_gift_and_item_catalog_entries_split_technical_and_descriptive() -> None:
    ability = get_ability_catalog_entry("fireball")
    gift = get_gift_catalog_entry("gift_true_fire")
    item = get_combat_item_action_catalog_entry("fire_grenade")

    assert ability is not None
    assert ability.key == "combat.ability.fireball"
    assert ability.technical.ability_id == "fireball"
    assert not hasattr(ability.technical, "name_ru")
    assert ability.descriptive.variants["humanoid"].event_texts.area_result
    assert ability.descriptive.variants["humanoid"].event_texts.no_resource

    assert gift is not None
    assert gift.key == "combat.gift.gift_true_fire"
    assert gift.technical.gift_id == "gift_true_fire"
    assert gift.technical.abilities == ["fireball", "flame_thrower"]
    assert not hasattr(gift.technical, "description")
    assert gift.descriptive.variants["humanoid"].display_name == "Истинное Пламя"

    assert item is not None
    assert item.key == "combat.item.fire_grenade"
    assert item.technical.ability_id == "fireball"
    assert item.descriptive.variants["humanoid"].event_texts.area_result


def test_non_basic_hit_archived_feint_catalog_entries_are_not_runtime_resources() -> None:
    assert get_feint_catalog_entry("armor_slip") is None
    assert CombatCatalogIntegrator.get_catalog_entry_by_key("combat.feint.armor_slip") is None
    assert CombatCatalogIntegrator.get_catalog_entry_by_key("combat.feint.measured_strike") is not None


def test_combat_runtime_can_resolve_non_feint_catalog_entry_by_stable_key() -> None:
    ability_entry = CombatCatalogIntegrator.get_catalog_entry_by_key("combat.ability.fireball")
    assert ability_entry is not None
    assert ability_entry.technical.ability_id == "fireball"

    assert CombatCatalogIntegrator.get_catalog_entry_by_key("combat.trigger.style.1h_flow") is None
    ranged_trigger = CombatCatalogIntegrator.get_catalog_entry_by_key("combat.trigger.style.ranged_perfect_backstep")
    assert ranged_trigger is not None
    assert ranged_trigger.technical.trigger_id == "style_ranged_perfect_backstep"


def test_combat_description_resolves_event_and_exchange_templates_without_formatting() -> None:
    trigger = CombatCatalogIntegrator.get_trigger_catalog_entry("weapon_serrated_bleed_crit")
    assert trigger is not None
    proc = trigger.descriptive.resolve_event_template("crit_proc", taxonomy_chain=["humanoid"])

    assert proc is not None
    assert proc.event == "crit_proc"
    assert proc.taxonomy == "humanoid"
    assert "{source}" in proc.text


def test_combat_event_text_set_prefers_semantic_exchange_parts() -> None:
    texts = CombatEventTextSetDTO(
        attack_use=["{source} attacks {target}"],
        hit_result=["dealing {damage} damage"],
        use=["legacy use"],
        hit=["legacy hit"],
    )

    assert texts.event_template("hit") == "legacy hit"
    assert texts.exchange_template("hit") == "{source} attacks {target}, dealing {damage} damage."


def test_pipeline_mutation_contracts_are_technical_and_apply_to_context() -> None:
    assert "chain.trigger_cleave" not in PIPELINE_MUTATION_CONTRACTS
    assert "partial_absorb_reflect" not in PIPELINE_MUTATION_CONTRACTS
    assert PIPELINE_MUTATION_CONTRACTS["ignore_miss"].path == "flags.force.hit"
    assert PIPELINE_MUTATION_CONTRACTS["ignore_evasion"].path == "flags.force.hit_evasion"
    assert PIPELINE_MUTATION_CONTRACTS["target_evasion_mult"].path == "mods.target_evasion_mult"
    assert PIPELINE_MUTATION_CONTRACTS["target_parry_mult"].path == "mods.target_parry_mult"
    assert PIPELINE_MUTATION_CONTRACTS["target_block_mult"].path == "mods.target_block_mult"
    assert PIPELINE_MUTATION_CONTRACTS["stage.check_ranged_position_defense"].path == (
        "stages.check_ranged_position_defense"
    )
    assert PIPELINE_MUTATION_CONTRACTS["ranged.next_position_override"].path == (
        "result.action_facts.next_ranged_position_override"
    )
    assert PIPELINE_MUTATION_CONTRACTS["ranged.current_position_step"].path == (
        "result.action_facts.ranged_current_position_step"
    )
    assert PIPELINE_MUTATION_CONTRACTS["ranged.outgoing_damage_bonus_mult"].path == (
        "result.action_facts.ranged_outgoing_damage_bonus_mult"
    )
    assert PIPELINE_MUTATION_CONTRACTS["ranged.far_weight_bonus"].path == (
        "result.action_facts.ranged_far_weight_bonus"
    )
    assert "force_shield_defense_branch" not in PIPELINE_MUTATION_CONTRACTS
    assert "force_shield_counter_branch" not in PIPELINE_MUTATION_CONTRACTS
    assert "shield_branch_invert" not in PIPELINE_MUTATION_CONTRACTS
    assert "shield_counter_from_absorbed" not in PIPELINE_MUTATION_CONTRACTS
    assert PIPELINE_MUTATION_CONTRACTS["shield_guard_power_mult"].path == "mods.shield_guard_power_mult"
    assert "shield_counter_power_mult" not in PIPELINE_MUTATION_CONTRACTS

    ctx = PipelineContextDTO()

    PipelineMutationService.apply(
        applications=[
            pipeline_mutation("ignore_evasion"),
            pipeline_mutation("roll_flat_armor_ignore"),
            pipeline_mutation("flat_armor_ignore_chance_bonus", 0.5),
            pipeline_mutation("boost_flat_armor_penetration"),
            pipeline_mutation("flat_armor_penetration_bonus_pct", 0.5),
            pipeline_mutation("stage.check_parry", False),
            pipeline_mutation("weapon_effect_value", 2.0),
            pipeline_mutation("target_evasion_mult", 0.65),
            pipeline_mutation("target_parry_mult", 0.65),
            pipeline_mutation("target_block_mult", 0.75),
            pipeline_mutation("shield_guard_power_mult", 1.25),
            pipeline_mutation("shield_block_chance_mult", 1.2),
            pipeline_mutation("stage.check_ranged_position_defense"),
            pipeline_mutation("ranged.current_position_step", 1),
            pipeline_mutation("ranged.next_position_override", "far"),
            pipeline_mutation("ranged.outgoing_damage_bonus_mult", 1.1),
            pipeline_mutation("ranged.far_weight_bonus", 0.25),
            pipeline_mutation("chain.preserve_feint"),
        ],
        ctx=ctx,
        source="feint",
    )

    assert ctx.flags.force.hit_evasion is True
    assert ctx.flags.formula.roll_flat_armor_ignore is True
    assert ctx.mods.flat_armor_ignore_chance_bonus == 0.5
    assert ctx.flags.formula.boost_flat_armor_penetration is True
    assert ctx.mods.flat_armor_penetration_bonus_pct == 0.5
    assert ctx.stages.check_parry is False
    assert ctx.mods.weapon_effect_value == 2.0
    assert ctx.mods.target_evasion_mult == 0.65
    assert ctx.mods.target_parry_mult == 0.65
    assert ctx.mods.target_block_mult == 0.75
    assert ctx.mods.shield_guard_power_mult == 1.25
    assert ctx.mods.shield_block_chance_mult == 1.2
    assert ctx.stages.check_ranged_position_defense is True
    assert ctx.result.action_facts["ranged_current_position_step"] == 1
    assert ctx.result.action_facts["next_ranged_position_override"] == "far"
    assert ctx.result.action_facts["ranged_outgoing_damage_bonus_mult"] == 1.1
    assert ctx.result.action_facts["ranged_far_weight_bonus"] == 0.25
    assert ctx.result.chain_events.preserve_feint is True


def test_basic_hit_weapon_technique_feint_has_render_context() -> None:
    entry = get_feint_catalog_entry("measured_strike")

    assert entry is not None

    context = CombatCatalogIntegrator.get_feint_render_context(
        "measured_strike",
        skill_key="skill_swords",
        outcome="hit",
        seed="stable",
        bonus_damage=6,
    )

    assert context is not None
    assert context.variables["bonus_damage"] == 6
    assert "{bonus_damage}" in context.template


def test_trigger_rules_use_pipeline_mutation_applications_not_raw_paths() -> None:
    rule = CombatCatalogIntegrator.get_trigger_rule("weapon_heavy_crit")

    assert rule is not None
    assert "mutations" not in rule
    assert [application.mutation_id for application in rule["pipeline_mutations"]] == [
        "crit_damage_boost",
        "weapon_effect_value",
    ]
    assert all("armor" not in application.mutation_id for application in rule["pipeline_mutations"])


def test_weapon_armor_triggers_target_flat_armor_layers() -> None:
    gap = CombatCatalogIntegrator.get_trigger_rule("weapon_flat_armor_gap_crit")
    bypass = CombatCatalogIntegrator.get_trigger_rule("weapon_flat_armor_bypass_crit")
    crush = CombatCatalogIntegrator.get_trigger_rule("weapon_flat_armor_crush_crit")

    assert gap is not None
    assert [application.mutation_id for application in gap["pipeline_mutations"]] == [
        "roll_flat_armor_ignore",
        "flat_armor_ignore_chance_bonus",
    ]
    assert gap["pipeline_mutations"][1].value_override == 0.5

    assert bypass is not None
    assert [application.mutation_id for application in bypass["pipeline_mutations"]] == ["ignore_flat_armor"]

    assert crush is not None
    assert [application.mutation_id for application in crush["pipeline_mutations"]] == [
        "boost_flat_armor_penetration",
        "flat_armor_penetration_bonus_pct",
    ]
    assert crush["pipeline_mutations"][1].value_override == 0.5


def test_game_message_contract_wraps_template_variables_and_result() -> None:
    message = GameMessageDTO(
        channel="combat",
        tab=GameMessageTabDTO(
            kind="combat",
            key="combat_combat-1",
            title="БОЙ",
            open_policy="force_open",
            closeable=True,
            accent="combat",
        ),
        scope="combat_session",
        scope_id="combat-1",
        recipients=["1", "2"],
        template=GameMessageTemplateDTO(
            key="combat.basic_exchange.skill_swords.main_hand",
            event="hit",
            taxonomy="humanoid",
            text="{source} strikes {target}.",
        ),
        variables={"source": {"id": "1", "label": "A"}, "target": {"id": "2", "label": "B"}},
        result={"resources": [{"actor_id": "2", "resource": "hp", "delta": -4}]},
        presentation={"render": "combat_inline_result", "severity": "normal"},
    )

    assert message.channel == "combat"
    assert message.tab is not None
    assert message.tab.open_policy == "force_open"
    assert message.template.text == "{source} strikes {target}."
    assert message.variables["source"]["label"] == "A"
    assert message.result["resources"][0]["delta"] == -4
    assert message.presentation.render == "combat_inline_result"
