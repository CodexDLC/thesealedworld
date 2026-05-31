"""Smoke + determinism tests for the offline policy trainer."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.training import TrainArgs, train
from src.backend.features.combat.runtime.ai.training.environment import ScoringEnvironment
from src.backend.features.combat.runtime.ai.training.evolution import _constrain_training_weights
from src.backend.features.combat.runtime.ai.training.scenarios import (
    ScenarioTarget,
    SyntheticScenario,
    default_scenario_set,
)


@pytest.mark.unit
def test_train_smoke_returns_database_ready_payload_without_artifacts(tmp_path: Path) -> None:
    args = TrainArgs(generations=2, population=4, seed=0)
    run = train(args)

    Policy.model_validate(run.best_policy.model_dump(mode="json"))
    assert run.leaderboard, "Leaderboard should have at least one entry"
    assert run.metrics, "Metrics should contain at least one generation"
    assert run.metrics[0].generation == 0
    assert run.best_policy.metadata.get("final_reward") is not None
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.unit
def test_train_is_deterministic_for_same_seed(tmp_path: Path) -> None:
    args_a = TrainArgs(generations=3, population=6, seed=42)
    args_b = TrainArgs(generations=3, population=6, seed=42)

    run_a = train(args_a)
    run_b = train(args_b)

    assert run_a.best_policy.weights == run_b.best_policy.weights
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.unit
def test_training_weight_constraints_keep_semantic_signs() -> None:
    constrained = _constrain_training_weights(
        {
            "anti_parry": -1.0,
            "anti_evasion": -1.0,
            "damage_tag": -1.0,
            "expected_damage": -1.0,
            "multi_target": -1.0,
            "heal": -1.0,
            "dispel_prep": -1.0,
            "team_dedup_control": -1.0,
            "observed_evasion_rate": -1.0,
            "counter_resource": -1.0,
            "token_cost": 1.0,
            "stamina_cost": 1.0,
            "energy_cost": 1.0,
            "finishable_resource_save": 1.0,
            "self_low_stamina_save": 1.0,
            "randomness": 1.0,
        }
    )

    for key in (
        "anti_parry",
        "anti_evasion",
        "damage_tag",
        "expected_damage",
        "multi_target",
        "heal",
        "dispel_prep",
        "team_dedup_control",
        "observed_evasion_rate",
        "counter_resource",
    ):
        assert constrained[key] == 0.0
    for key in (
        "token_cost",
        "stamina_cost",
        "energy_cost",
        "finishable_resource_save",
        "self_low_stamina_save",
    ):
        assert constrained[key] == 0.0
    assert constrained["randomness"] == 0.0


@pytest.mark.unit
def test_scenario_set_covers_policy_noise_and_archetype_behaviour() -> None:
    scenarios = {scenario.name: scenario for scenario in default_scenario_set(seed=0)}

    assert {
        "stamina_discipline",
        "sticky_target_focus",
        "gift_resource_neutral",
        "variety_after_repeat",
        "archetype_berserker_damage",
        "archetype_bulwark_survival",
        "archetype_tactician_dispel",
        "archetype_duelist_counter_defence",
        "basic_blood_heal",
        "basic_break_stance_instant",
        "basic_energy_discipline",
    } <= set(scenarios)
    assert scenarios["stamina_discipline"].expected[0].expected_feint_id == "sword_blade_bind"
    assert scenarios["sticky_target_focus"].expected[0].target_id == "sticky_previous"
    assert scenarios["gift_resource_neutral"].expected[0].expected_tags == frozenset()
    assert scenarios["variety_after_repeat"].expected[0].expected_feint_id == "macing_break_stance"
    assert scenarios["basic_blood_heal"].expected[0].expected_ability_id == "basic_wipe_blood"
    assert scenarios["basic_break_stance_instant"].expected[0].expected_ability_id == "basic_break_stance"
    assert scenarios["basic_energy_discipline"].expected[0].expected_ability_id == "basic_punish_mistake"


@pytest.mark.unit
def test_synthetic_policy_regularization_rejects_bad_sign_drift() -> None:
    scenarios = default_scenario_set(seed=0)
    env = ScoringEnvironment(scenarios)
    disciplined = Policy.with_defaults(
        {
            "stamina_cost": -0.05,
            "energy_cost": -0.05,
            "token_cost": -0.2,
            "finishable": 0.2,
            "target_low_hp": 0.2,
            "anti_parry": 0.2,
            "observed_evasion_rate": 0.2,
            "team_dedup_control": 0.2,
            "team_focus": 0.2,
            "team_focus_pile_on": 0.2,
            "heal_dedup_penalty": 0.2,
            "finishable_resource_save": -0.5,
            "control": 0.2,
            "heal": 0.2,
            "defense": 0.2,
            "debuff": 0.2,
            "preparation": 0.2,
            "gift_resource": 0.0,
            "blood_resource": 0.0,
            "randomness": 0.0,
        }
    )
    bad_drift = Policy.with_defaults(
        {
            "stamina_cost": 0.5,
            "energy_cost": 0.5,
            "token_cost": 0.3,
            "finishable": -0.5,
            "target_low_hp": -0.5,
            "anti_parry": -0.5,
            "observed_evasion_rate": -0.5,
            "team_dedup_control": -0.5,
            "team_focus": -0.5,
            "team_focus_pile_on": -0.5,
            "heal_dedup_penalty": -0.5,
            "finishable_resource_save": 0.5,
            "control": -0.5,
            "heal": -0.5,
            "defense": -0.5,
            "debuff": -0.5,
            "preparation": -0.5,
            "gift_resource": 0.7,
            "blood_resource": -0.7,
            "randomness": 0.5,
        }
    )

    assert env.evaluate(disciplined).total_reward > env.evaluate(bad_drift).total_reward + 2.0


@pytest.mark.unit
def test_finishable_guardrail_rewards_saving_feints_on_dying_targets() -> None:
    scenario = next(s for s in default_scenario_set(seed=0) if s.name == "finishable_cheap_kill")
    env = ScoringEnvironment([scenario])
    saves_resources = Policy.with_defaults(
        {
            "damage_tag": 0.2,
            "finishable_resource_save": -2.0,
            "token_cost": -0.2,
            "stamina_cost": -0.05,
        }
    )
    burns_resources = Policy.with_defaults(
        {
            "damage_tag": 1.0,
            "group_weapon": 1.0,
            "finishable_resource_save": 2.0,
            "token_cost": 0.3,
            "stamina_cost": 0.3,
        }
    )

    assert env.evaluate(saves_resources).per_scenario["finishable_cheap_kill"] > 0.0
    assert env.evaluate(burns_resources).per_scenario["finishable_cheap_kill"] > 0.0


@pytest.mark.unit
def test_duplicate_control_scenario_prefers_clean_action() -> None:
    scenario = next(s for s in default_scenario_set(seed=0) if s.name == "team_dedup_control")
    env = ScoringEnvironment([scenario])
    high_control_policy = Policy.with_defaults(
        {
            "damage_tag": 2.0,
            "control": 2.0,
            "team_dedup_control": 0.1,
        }
    )

    assert env.evaluate(high_control_policy).per_scenario["team_dedup_control"] > 0.0


@pytest.mark.unit
def test_required_heal_missing_is_a_hard_synthetic_failure() -> None:
    scenario = next(s for s in default_scenario_set(seed=0) if s.name == "wounded_bot_heal")
    env = ScoringEnvironment([scenario])
    skips_heal = Policy.with_defaults(
        {
            "damage_tag": 2.0,
            "heal": -1.0,
            "group_basic": 1.0,
        }
    )

    assert env.evaluate(skips_heal).per_scenario["wounded_bot_heal"] <= -8.0


@pytest.mark.unit
def test_required_prep_dispel_missing_is_a_hard_synthetic_failure() -> None:
    scenario = next(s for s in default_scenario_set(seed=0) if s.name == "prep_threat_dispel")
    env = ScoringEnvironment([scenario])
    attacks_through_prep = Policy.with_defaults(
        {
            "damage_tag": 2.0,
            "dispel_prep": -1.0,
            "group_basic": 1.0,
        }
    )

    assert env.evaluate(attacks_through_prep).per_scenario["prep_threat_dispel"] <= -8.0


@pytest.mark.unit
def test_required_exact_instant_ability_mismatch_is_a_synthetic_failure() -> None:
    source = next(s for s in default_scenario_set(seed=0) if s.name == "basic_energy_discipline")
    scenario = SyntheticScenario(
        name="expects_expensive_finish_instant",
        bot=source.bot,
        targets=source.targets,
        expected=[
            ScenarioTarget(
                source.targets[0].meta.id,
                frozenset({"damage_tag"}),
                expected_ability_id="basic_finish_moment",
                reward_weight=2.0,
            ),
        ],
    )
    env = ScoringEnvironment([scenario])
    prefers_cheaper_instant = Policy.with_defaults(
        {
            "damage_tag": 2.0,
            "energy_cost": -1.0,
        }
    )

    assert env.evaluate(prefers_cheaper_instant).per_scenario["expects_expensive_finish_instant"] < 0.0


@pytest.mark.unit
def test_required_exact_feint_mismatch_is_a_synthetic_failure() -> None:
    scenario = next(s for s in default_scenario_set(seed=0) if s.name == "variety_after_repeat")
    env = ScoringEnvironment([scenario])
    repeats_old_feint = Policy.with_defaults(
        {
            "anti_parry": 2.0,
            "observed_parry_rate": 0.0,
            "repeat_feint_penalty": 0.0,
            "token_cost": 0.0,
            "stamina_cost": 0.0,
        }
    )

    assert env.evaluate(repeats_old_feint).per_scenario["variety_after_repeat"] < 0.0


# ---------------------------------------------------------------------------
# PR6 scenarios: multi-target swarm cleanup + anti-defence axes + discipline.
# ---------------------------------------------------------------------------


_MULTI_TARGET_SCENARIOS: tuple[str, ...] = (
    "arrow_rain_swarm",
    "ranged_covering_volley_swarm",
    "polearm_line_swarm",
    "two_handed_whirl_swarm",
    "dual_blade_whirl_swarm",
    "overkill_waste_vs_aoe",
)


_ANTI_DEFENCE_SCENARIOS: tuple[str, ...] = (
    "high_dodge_anti_evasion_semantic",
    "armor_bypass_vs_heavy",
    "shield_block_pressure",
)


_DISCIPLINE_SCENARIOS: tuple[str, ...] = (
    "aoe_stamina_discipline",
)


_ALL_PR6_SCENARIOS: tuple[str, ...] = (
    *_MULTI_TARGET_SCENARIOS,
    *_ANTI_DEFENCE_SCENARIOS,
    *_DISCIPLINE_SCENARIOS,
)


@pytest.mark.unit
def test_scenario_set_includes_all_pr6_swarm_and_anti_defence_scenarios() -> None:
    scenarios = {scenario.name: scenario for scenario in default_scenario_set(seed=0)}
    missing = set(_ALL_PR6_SCENARIOS) - set(scenarios)
    assert not missing, f"PR6 scenarios missing from default_scenario_set: {sorted(missing)}"


@pytest.mark.unit
@pytest.mark.parametrize("scenario_name", _MULTI_TARGET_SCENARIOS)
def test_multi_target_scenarios_have_more_than_one_target(scenario_name: str) -> None:
    scenarios = {scenario.name: scenario for scenario in default_scenario_set(seed=0)}
    scenario = scenarios[scenario_name]

    assert len(scenario.targets) > 1, (
        f"{scenario_name} rewards multi_target but only has {len(scenario.targets)} target — "
        "rewarding multi_target with a single target would teach the policy a false positive."
    )


@pytest.mark.unit
@pytest.mark.parametrize("scenario_name", _MULTI_TARGET_SCENARIOS)
def test_multi_target_scenarios_use_multi_target_expected_tag(scenario_name: str) -> None:
    scenarios = {scenario.name: scenario for scenario in default_scenario_set(seed=0)}
    scenario = scenarios[scenario_name]

    multi_target_expectations = [
        expected for expected in scenario.expected if "multi_target" in expected.expected_tags
    ]
    assert len(multi_target_expectations) == 1, (
        f"{scenario_name} should reward one primary AoE exchange, not require "
        "the same AoE feint to be registered on every target."
    )


@pytest.mark.unit
@pytest.mark.parametrize("scenario_name", _ALL_PR6_SCENARIOS)
def test_pr6_scenario_expected_feint_ids_are_in_bot_hand(scenario_name: str) -> None:
    scenarios = {scenario.name: scenario for scenario in default_scenario_set(seed=0)}
    scenario = scenarios[scenario_name]
    hand = (scenario.bot.meta.feints.hand if scenario.bot.meta.feints else None) or {}

    for expected in scenario.expected:
        if expected.expected_feint_id is None:
            continue
        assert expected.expected_feint_id in hand, (
            f"{scenario_name} expects feint {expected.expected_feint_id!r} on target "
            f"{expected.target_id} but it is not in the bot's hand "
            f"({sorted(hand)})."
        )


@pytest.mark.unit
@pytest.mark.parametrize("scenario_name", _ALL_PR6_SCENARIOS)
def test_pr6_expected_feints_resolve_to_real_catalog_entries(scenario_name: str) -> None:
    from src.backend.features.combat.integrations import CombatCatalogIntegrator

    scenarios = {scenario.name: scenario for scenario in default_scenario_set(seed=0)}
    scenario = scenarios[scenario_name]

    for expected in scenario.expected:
        if expected.expected_feint_id is None:
            continue
        entry = CombatCatalogIntegrator.get_feint_catalog_entry(expected.expected_feint_id)
        assert entry is not None, (
            f"{scenario_name} expects feint {expected.expected_feint_id!r} "
            "but it does not resolve in the live combat catalog."
        )


@pytest.mark.unit
@pytest.mark.parametrize("scenario_name", _ALL_PR6_SCENARIOS)
def test_pr6_expected_tags_are_subset_of_derived_tags(scenario_name: str) -> None:
    """For every PR6 scenario with an expected_feint_id, the scenario's
    expected_tags must be a subset of the tags ``derive_feint_tags`` actually
    produces for that catalog entry. Otherwise we'd ask the trainer to reward
    a tag the chosen feint cannot earn."""
    from src.backend.features.combat.integrations import CombatCatalogIntegrator
    from src.backend.features.combat.runtime.ai.feint_tags import derive_feint_tags

    scenarios = {scenario.name: scenario for scenario in default_scenario_set(seed=0)}
    scenario = scenarios[scenario_name]

    for expected in scenario.expected:
        if expected.expected_feint_id is None or not expected.expected_tags:
            continue
        entry = CombatCatalogIntegrator.get_feint_catalog_entry(expected.expected_feint_id)
        assert entry is not None
        derived = derive_feint_tags(entry, expected.expected_feint_id)
        missing = expected.expected_tags - derived
        assert not missing, (
            f"{scenario_name} expects tags {sorted(expected.expected_tags)} from "
            f"{expected.expected_feint_id} but derive_feint_tags produced "
            f"{sorted(derived)}; missing: {sorted(missing)}."
        )


@pytest.mark.unit
def test_aoe_stamina_discipline_does_not_let_bot_afford_the_aoe() -> None:
    """The discipline guardrail breaks if the AoE feint becomes affordable —
    the trainer would learn to always pick the AoE despite low stamina."""
    from src.backend.features.combat.runtime.engine.feint_service import FeintService

    scenarios = {scenario.name: scenario for scenario in default_scenario_set(seed=0)}
    scenario = scenarios["aoe_stamina_discipline"]
    hand = (scenario.bot.meta.feints.hand if scenario.bot.meta.feints else None) or {}
    aoe_cost = hand.get("two_handed_whirl")
    assert aoe_cost is not None, "aoe_stamina_discipline lost its AoE feint reference"
    aoe_stamina = FeintService.activation_stamina_cost(
        {str(k): int(v) for k, v in aoe_cost.items()}
    )
    assert aoe_stamina > scenario.bot.meta.stamina, (
        f"aoe_stamina_discipline: AoE costs {aoe_stamina} stamina but bot has "
        f"{scenario.bot.meta.stamina}; the scenario would no longer enforce the "
        "stamina-discipline lesson."
    )


@pytest.mark.unit
def test_overkill_waste_scenario_offers_both_single_and_aoe_options() -> None:
    """Verify the overkill_waste_vs_aoe trade-off: bot must hold one
    expensive single-target option and one true AoE, otherwise the scenario
    degenerates."""
    from src.backend.features.combat.integrations import CombatCatalogIntegrator

    scenarios = {scenario.name: scenario for scenario in default_scenario_set(seed=0)}
    scenario = scenarios["overkill_waste_vs_aoe"]
    hand = (scenario.bot.meta.feints.hand if scenario.bot.meta.feints else None) or {}
    single = [
        fid
        for fid in hand
        if (entry := CombatCatalogIntegrator.get_feint_catalog_entry(fid)) is not None
        and int(getattr(entry.technical, "target_count", 1) or 1) == 1
    ]
    aoe = [
        fid
        for fid in hand
        if (entry := CombatCatalogIntegrator.get_feint_catalog_entry(fid)) is not None
        and int(getattr(entry.technical, "target_count", 1) or 1) > 1
    ]
    assert single, "overkill_waste_vs_aoe must keep at least one single-target option"
    assert aoe, "overkill_waste_vs_aoe must keep at least one AoE option"
