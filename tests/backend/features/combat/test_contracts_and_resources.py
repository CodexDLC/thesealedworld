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
from src.backend.features.game_catalog.combat.resources.common import CombatEventTextSetDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import (
    PIPELINE_MUTATION_CONTRACTS,
    pipeline_mutation,
)
from src.backend.features.game_catalog.combat.resources.feints import get_feint_catalog_entry
from src.backend.features.game_catalog.combat.resources.gifts import get_gift_catalog_entry
from src.backend.features.game_catalog.combat.resources.items import get_combat_item_action_catalog_entry
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
    assert set(catalog["feints"]) == {
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
        "blade_mill",
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
        "perfect_riposte",
        "piercing_arrow",
        "polearm_guard_intercept",
        "polearm_hook_step",
        "polearm_leg_sweep",
        "polearm_line_cleave",
        "polearm_locked_distance",
        "polearm_long_line",
        "polearm_pinning_point",
        "polearm_stunning_intercept",
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
        "sword_blade_whirl",
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
    assert catalog["feints"]["measured_strike"]["cost"]["tactics"] == {"hit": 3}
    assert catalog["feints"]["glancing_step"]["cost"]["tactics"] == {"dodge": 3}
    assert catalog["feints"]["perfect_riposte"]["cost"]["tactics"] == {"parry": 7}
    assert catalog["feints"]["absolute_defense"]["cost"]["tactics"] == {"block": 7}
    assert catalog["feints"]["read_tactic"]["cost"]["tactics"] == {"hit": 1, "block": 2}
    assert catalog["feints"]["bloody_rebuke"]["cost"]["tactics"] == {"blood": 1, "hit": 2, "block": 2}
    assert catalog["feints"]["scarlet_riposte"]["cost"]["tactics"] == {"blood": 1, "block": 2, "parry": 2}
    assert catalog["feints"]["crushing_pressure"]["cost"]["tactics"] == {"hit": 3}
    assert catalog["feints"]["ignore_guard"]["cost"]["tactics"] == {"hit": 2, "parry": 2}
    assert catalog["feints"]["offhand_over"]["cost"]["tactics"] == {"hit": 3, "parry": 2}
    assert catalog["feints"]["blade_mill"]["cost"]["tactics"] == {"hit": 5, "counter": 4}
    assert catalog["feints"]["snap_shot"]["cost"]["tactics"] == {"hit": 3}
    assert catalog["feints"]["sword_blade_bind"]["cost"]["tactics"] == {"hit": 3, "parry": 2}
    assert catalog["feints"]["sword_clean_path"]["cost"]["tactics"] == {"hit": 3, "crit": 5}
    assert catalog["feints"]["fencing_gap_probe"]["cost"]["tactics"] == {"hit": 3, "crit": 2}
    assert catalog["feints"]["fencing_needle_gap"]["cost"]["tactics"] == {"hit": 3, "crit": 5}
    assert catalog["feints"]["polearm_hook_step"]["cost"]["tactics"] == {"hit": 3, "dodge": 2}
    assert catalog["feints"]["polearm_locked_distance"]["cost"]["tactics"] == {"hit": 3, "crit": 5}
    assert catalog["feints"]["macing_break_swing"]["cost"]["tactics"] == {"hit": 3, "parry": 2}
    assert catalog["feints"]["macing_guard_cracker"]["cost"]["tactics"] == {"hit": 5, "crit": 3}
    assert catalog["feints"]["reveal_intentions"]["cost"]["tactics"] == {"hit": 2, "dodge": 1}
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


def test_basic_gift_abilities_are_runtime_resources_with_combat_token_costs() -> None:
    expected_costs = {
        "basic_punish_mistake": {"tempo": 1, "hit": 1},
        "basic_finish_moment": {"tempo": 1, "crit": 1},
        "basic_break_stance": {"tempo": 1, "hit": 1},
        "basic_expose_weakness": {"tempo": 1, "crit": 1},
        "basic_wipe_blood": {"blood": 1},
        "basic_grit_teeth": {"blood": 1},
        "basic_bloody_answer": {"blood": 1, "hit": 1},
        "basic_last_push": {"blood": 1, "tempo": 1},
    }

    assert tuple(expected_costs) == BASIC_GIFT_ABILITY_IDS

    for ability_id, token_costs in expected_costs.items():
        entry = get_ability_catalog_entry(ability_id)
        assert entry is not None
        assert entry.key == f"combat.ability.{ability_id}"
        assert entry.technical.cost.energy > 0
        assert entry.technical.cost.gift_tokens == 0
        assert entry.technical.cost.tokens == token_costs
        assert entry.descriptive.variants["humanoid"].display_name

    wipe_blood = get_ability_catalog_entry("basic_wipe_blood")
    last_push = get_ability_catalog_entry("basic_last_push")

    assert wipe_blood is not None
    assert wipe_blood.technical.override_damage == (6.0, 10.0)
    assert last_push is not None
    assert last_push.technical.override_damage == (8.0, 12.0)
    assert [app.modifier_id for app in last_push.technical.modifier_applications] == ["physical_damage_bonus_add"]


def test_public_ability_catalog_exposes_tooltip_payload() -> None:
    catalog = CombatResourceCatalogService.load_default().all_public_text()

    punish = catalog["abilities"]["basic_punish_mistake"]
    break_stance = catalog["abilities"]["basic_break_stance"]
    bloody_answer = catalog["abilities"]["basic_bloody_answer"]

    assert punish["title"] == "Наказать ошибку"
    assert punish["description"] == "Тратит темп и попадание, чтобы нанести быстрый урон."
    assert punish["cost"] == {"energy": 10, "hp": 0, "gift_tokens": 0, "tokens": {"tempo": 1, "hit": 1}}
    assert punish["target_label"] == "Один враг"
    assert "Тип: атака" in punish["mechanics"]
    assert "Урон: 18-22" in punish["mechanics"]

    assert break_stance["target_label"] == "Один враг"
    assert "Тип: эффект" in break_stance["mechanics"]
    assert "Цель получает: уклонение -0.05 на 2 размена" in break_stance["mechanics"]

    assert "Урон: 20-26" in bloody_answer["mechanics"]
    assert "Эффект: кровотечение на 2 размена, сила 0.75" in bloody_answer["mechanics"]


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
    assert PIPELINE_MUTATION_CONTRACTS["force_shield_defense_branch"].path == (
        "flags.formula.force_shield_defense_branch"
    )
    assert PIPELINE_MUTATION_CONTRACTS["force_shield_counter_branch"].path == (
        "flags.formula.force_shield_counter_branch"
    )
    assert PIPELINE_MUTATION_CONTRACTS["shield_branch_invert"].path == "flags.formula.shield_branch_invert"
    assert PIPELINE_MUTATION_CONTRACTS["shield_guard_power_mult"].path == "mods.shield_guard_power_mult"
    assert PIPELINE_MUTATION_CONTRACTS["shield_counter_power_mult"].path == "mods.shield_counter_power_mult"

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
            pipeline_mutation("force_shield_counter_branch"),
            pipeline_mutation("shield_counter_from_absorbed"),
            pipeline_mutation("shield_guard_power_mult", 1.25),
            pipeline_mutation("shield_counter_power_mult", 1.5),
            pipeline_mutation("shield_block_chance_mult", 1.2),
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
    assert ctx.flags.formula.force_shield_counter_branch is True
    assert ctx.flags.formula.shield_counter_from_absorbed is True
    assert ctx.mods.shield_guard_power_mult == 1.25
    assert ctx.mods.shield_counter_power_mult == 1.5
    assert ctx.mods.shield_block_chance_mult == 1.2
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
