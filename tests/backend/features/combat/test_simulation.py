from __future__ import annotations

import pytest

from src.backend.features.combat.dto import (
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    BattleContext,
    CombatMoveDTO,
    ExchangePayload,
    FeintHandDTO,
    InstantPayload,
)
from src.backend.features.combat.dto.actor import ActorStats
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.simulation import (
    BALANCE_TEST_SIMULATION_IMPRINTS,
    DEFAULT_STARTER_SIMULATION_IMPRINTS,
    AiSimulationIntentProvider,
    CombatTelemetry,
    InMemoryBattleFactory,
    InMemoryBattleLimits,
    InMemoryCombatSimulator,
    LiveInMemoryCombatSimulator,
    LiveSimulationTiming,
    SimulationActionCollector,
    SimulationMoveRegistrar,
    StartingImprintSimulationActorBuilder,
    random_starter_5v5_imprints,
    random_starter_roster_imprints,
    render_simulation_report,
)
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


class StaticBrain:
    def __init__(self, feint_id: str | None = None) -> None:
        self.feint_id = feint_id
        self.calls: list[tuple[str, list[str]]] = []

    def decide_turn(self, bot: ActorSnapshot, battle: BattleContext, candidate_targets: list[ActorSnapshot]):
        self.calls.append((str(bot.meta.id), [str(target.meta.id) for target in candidate_targets]))
        return [
            {
                "action": "attack",
                "target_id": str(candidate_targets[0].meta.id),
                **({"feint_id": self.feint_id} if self.feint_id else {}),
            }
        ]


def sim_actor(
    actor_id: str,
    team: str,
    *,
    hp: int = 40,
    damage: float = 18.0,
    is_ai: bool = True,
    feints: dict[str, dict[str, int]] | None = None,
    initiative: float = 0.0,
) -> ActorSnapshot:
    hand = dict(feints or {})
    return ActorSnapshot(
        meta=ActorMetaDTO(
            id=actor_id,
            name=actor_id,
            type="monster" if is_ai else "player",
            team=team,
            is_ai=is_ai,
            hp=hp,
            max_hp=hp,
            stamina=100,
            max_stamina=100,
            feints=FeintHandDTO(hand=hand, arsenal=list(hand)),
        ),
        raw=ActorRawDTO(
            modifiers={
                "main_hand_damage_base": damage,
                "main_hand_damage_spread": 0.0,
                "main_hand_accuracy": 1.0,
            }
        ),
        loadout=ActorLoadoutDTO(layout={"main_hand": "skill_swords"}),
        stats=ActorStats(
            mods=CombatModifiersDTO(
                main_hand_damage_base=damage,
                main_hand_damage_spread=0.0,
                main_hand_accuracy=1.0,
                initiative=initiative,
            ),
            skills=CombatSkillsDTO(skill_swords=1.0),
        ),
    )


@pytest.mark.unit
def test_starting_imprint_actor_builder_uses_real_character_presets() -> None:
    actor = StartingImprintSimulationActorBuilder().build_actor(
        "starter_guard_01",
        actor_id="starter_guard",
        team="blue",
    )

    snapshot = actor.actor

    assert snapshot.meta.name == "Ada Guard"
    assert snapshot.meta.ai_archetype == "bulwark"
    assert snapshot.meta.hp > 1
    assert snapshot.meta.stamina > 1
    assert snapshot.stats is not None
    assert snapshot.stats.mods.main_hand_damage_base > 0
    assert snapshot.stats.mods.block > 0
    assert snapshot.loadout.layout["main_hand"] == "skill_swords"
    assert snapshot.meta.feints.arsenal
    assert snapshot.meta.feints.hand
    assert actor.participant["imprint_key"] == "starter_guard_01"
    assert actor.participant["combat_stats"]["block"] > 0
    assert actor.participant["gear_score"]["total"] > 0
    assert actor.participant["gear_score"]["offense"] > 0
    assert actor.participant["gear_score"]["defense"] > 0


@pytest.mark.unit
def test_starting_imprint_actor_builder_builds_5v5_roster() -> None:
    actors, participants = StartingImprintSimulationActorBuilder().build_roster()

    assert len(actors) == 10
    assert len(participants) == 10
    assert {actor.meta.team for actor in actors} == {"blue", "red"}
    assert len({actor.meta.id for actor in actors}) == 10
    assert all(participant["item_base_ids"] for participant in participants)


@pytest.mark.unit
def test_starting_imprint_actor_builder_builds_seeded_random_5v5_roster() -> None:
    seed_zero = StartingImprintSimulationActorBuilder().build_roster(seed=0)
    seed_zero_again = StartingImprintSimulationActorBuilder().build_roster(seed=0)
    seed_one = StartingImprintSimulationActorBuilder().build_roster(seed=1)

    zero_teams = [(actor.meta.team, actor.meta.template_id) for actor in seed_zero[0]]
    zero_again_teams = [(actor.meta.team, actor.meta.template_id) for actor in seed_zero_again[0]]
    one_teams = [(actor.meta.team, actor.meta.template_id) for actor in seed_one[0]]

    assert zero_teams == zero_again_teams
    assert zero_teams != one_teams
    assert len({actor.meta.template_id for actor in seed_zero[0]}) == 10
    assert {actor.meta.team for actor in seed_zero[0]} == {"blue", "red"}
    assert len([actor for actor in seed_zero[0] if actor.meta.team == "blue"]) == 5
    assert len([actor for actor in seed_zero[0] if actor.meta.team == "red"]) == 5
    assert len(BALANCE_TEST_SIMULATION_IMPRINTS) > len(DEFAULT_STARTER_SIMULATION_IMPRINTS)
    assert {str(actor.meta.template_id) for actor in seed_zero[0]}.issubset(set(BALANCE_TEST_SIMULATION_IMPRINTS))
    assert random_starter_5v5_imprints(seed=0) == random_starter_5v5_imprints(seed=0)


@pytest.mark.unit
def test_starting_imprint_actor_builder_can_build_balance_only_variants() -> None:
    dual_heavy = StartingImprintSimulationActorBuilder().build_actor(
        "sim_dual_heavy_01",
        actor_id="sim_dual_heavy",
        team="blue",
    )
    polearm_medium = StartingImprintSimulationActorBuilder().build_actor(
        "sim_polearm_medium_01",
        actor_id="sim_polearm_medium",
        team="red",
    )

    assert dual_heavy.actor.stats is not None
    assert dual_heavy.participant["imprint_key"] == "sim_dual_heavy_01"
    assert dual_heavy.participant["combat_style"] == "dual_light"
    assert dual_heavy.participant["armor_pack"] == "heavy_full"
    assert dual_heavy.participant["skill_profile"] == "baseline"
    assert polearm_medium.actor.stats is not None
    assert polearm_medium.participant["combat_style"] == "polearm_reach"
    assert polearm_medium.participant["item_base_ids"][0] == "halberd"


@pytest.mark.unit
def test_starting_imprint_actor_builder_can_draft_partial_rosters() -> None:
    actors, participants = StartingImprintSimulationActorBuilder().build_roster(
        seed=3,
        min_team_size=2,
        max_team_size=2,
    )
    blue, red = random_starter_roster_imprints(seed=3, min_team_size=2, max_team_size=2)

    assert len(actors) == 4
    assert len(participants) == 4
    assert len(blue) == 2
    assert len(red) == 2
    assert {actor.meta.team for actor in actors} == {"blue", "red"}
    assert {actor.meta.template_id for actor in actors} == set(blue + red)


@pytest.mark.unit
def test_starting_imprint_actor_builder_can_build_mirror_10v10_roster() -> None:
    actors, participants = StartingImprintSimulationActorBuilder().build_roster(
        blue_imprints=DEFAULT_STARTER_SIMULATION_IMPRINTS,
        red_imprints=DEFAULT_STARTER_SIMULATION_IMPRINTS,
    )

    assert len(actors) == 20
    assert len(participants) == 20
    assert len([actor for actor in actors if actor.meta.team == "blue"]) == 10
    assert len([actor for actor in actors if actor.meta.team == "red"]) == 10
    assert {actor.meta.template_id for actor in actors if actor.meta.team == "blue"} == set(
        DEFAULT_STARTER_SIMULATION_IMPRINTS
    )
    assert {actor.meta.template_id for actor in actors if actor.meta.team == "red"} == set(
        DEFAULT_STARTER_SIMULATION_IMPRINTS
    )


@pytest.mark.unit
def test_in_memory_battle_factory_builds_valid_context() -> None:
    hero = sim_actor("hero", "blue", is_ai=False)
    wolf = sim_actor("wolf", "red")

    state = InMemoryBattleFactory.from_actors(
        [hero, wolf],
        session_id="sim-1",
        limits=InMemoryBattleLimits(max_rounds=3),
    )

    assert state.ctx.session_id == "sim-1"
    assert state.ctx.meta.battle_type == "simulation"
    assert state.ctx.meta.teams == {"blue": ["hero"], "red": ["wolf"]}
    assert state.ctx.meta.actors_info == {"hero": "player", "wolf": "ai"}
    assert state.limits.max_rounds == 3


@pytest.mark.unit
def test_intent_provider_returns_moves_without_redis() -> None:
    hero = sim_actor("hero", "blue", is_ai=False)
    wolf = sim_actor("wolf", "red")
    state = InMemoryBattleFactory.from_actors([hero, wolf], session_id="sim-2")
    brain = StaticBrain(feint_id="measured_strike")

    moves = AiSimulationIntentProvider(brain=brain).choose_moves(state, wolf)

    assert len(moves) == 1
    assert moves[0].char_id == "wolf"
    assert moves[0].strategy == "exchange"
    assert moves[0].payload == ExchangePayload(target_id="hero", feint_id="measured_strike")
    assert brain.calls == [("wolf", ["hero"])]


@pytest.mark.unit
def test_action_collector_pairs_and_forces_exchange_moves() -> None:
    state = InMemoryBattleFactory.from_actors(
        [sim_actor("a", "blue"), sim_actor("b", "red"), sim_actor("c", "red")],
        session_id="sim-3",
    )
    moves = [
        CombatMoveDTO(move_id="a-b", char_id="a", strategy="exchange", payload=ExchangePayload(target_id="b")),
        CombatMoveDTO(move_id="b-a", char_id="b", strategy="exchange", payload=ExchangePayload(target_id="a")),
        CombatMoveDTO(move_id="c-a", char_id="c", strategy="exchange", payload=ExchangePayload(target_id="a")),
    ]

    actions = SimulationActionCollector().collect_actions(state, moves)

    assert [(action.move.move_id, action.partner_move.move_id if action.partner_move else None, action.is_forced) for action in actions] == [
        ("a-b", "b-a", False),
        ("c-a", None, True),
    ]


@pytest.mark.unit
def test_action_collector_can_disable_forced_exchange_and_resolve_instant_targets() -> None:
    state = InMemoryBattleFactory.from_actors([sim_actor("a", "blue"), sim_actor("b", "red")], session_id="sim-3b")
    exchange = CombatMoveDTO(move_id="a-b", char_id="a", strategy="exchange", payload=ExchangePayload(target_id="b"))
    instant = CombatMoveDTO(
        move_id="cast",
        char_id="a",
        strategy="instant",
        payload=InstantPayload(ability_id="spark", target_id="b"),
    )

    actions = SimulationActionCollector(force_unanswered_exchange=False).collect_actions(state, [exchange, instant])

    assert len(actions) == 1
    assert actions[0].action_type == "instant"
    assert actions[0].move.targets == ["b"]


@pytest.mark.unit
def test_state_commit_updates_dead_actors_and_clears_pending_buffers() -> None:
    state = InMemoryBattleFactory.from_actors([sim_actor("a", "blue"), sim_actor("b", "red")], session_id="sim-4")
    state.ctx.pending_dead_actors = ["b"]
    state.ctx.pending_logs = [{"kind": "death"}]
    state.ctx.pending_result_support_tasks = [{"result": {"damage_final": 10}}]
    state.ctx.pending_target_returns = [{"source_id": "a", "target_id": "b"}]

    state.commit_executor_buffers()

    assert state.ctx.meta.dead_actors == ["b"]
    assert state.ctx.meta.active_actors_count == 1
    assert state.ctx.pending_dead_actors == []
    assert state.ctx.pending_logs == []
    assert state.ctx.pending_result_support_tasks == []
    assert state.ctx.pending_target_returns == []


@pytest.mark.unit
def test_state_commit_returns_live_targets_without_duplicates() -> None:
    state = InMemoryBattleFactory.from_actors([sim_actor("a", "blue"), sim_actor("b", "red")], session_id="sim-4b")
    state.ctx.targets["a"] = ["b"]
    state.ctx.pending_target_returns = [{"source_id": "a", "target_id": "b"}, {"source_id": "b", "target_id": "a"}]

    state.commit_executor_buffers()

    assert state.ctx.targets["a"] == ["b"]
    assert state.ctx.targets["b"] == ["a"]


@pytest.mark.unit
def test_telemetry_records_moves_and_executor_support_payloads() -> None:
    telemetry = CombatTelemetry()
    move = CombatMoveDTO(
        move_id="m1",
        char_id="a",
        strategy="exchange",
        payload=ExchangePayload(target_id="b", feint_id="measured_strike"),
    )
    state = InMemoryBattleFactory.from_actors([sim_actor("a", "blue"), sim_actor("b", "red")], session_id="sim-5")
    state.ctx.pending_result_support_tasks = [
        {
            "result": {
                "source_id": "a",
                "target_id": "b",
                "damage_final": 7,
                "damage_trace": {"details": {"after_resist": 12, "after_armor": 7, "arm": {"effective": 5}}},
                "healing_final": 0,
                "is_hit": True,
                "is_crit": True,
                "skip_reason": None,
                "resource_facts": [
                    {"actor_id": "a", "resource": "stamina", "delta": -5},
                    {
                        "actor_id": "b",
                        "owner": "target",
                        "resource": "hp",
                        "reason": "damage",
                        "delta": -4,
                        "before": 4,
                        "after": 0,
                        "max": 40,
                    },
                ],
                "effect_facts": [{"actor_id": "b", "effect_id": "stun", "action": "apply", "tags": ["control"]}],
                "death_facts": [{"actor_id": "b"}],
            }
        }
    ]

    telemetry.record_moves([move])
    telemetry.record_executor_context(state.ctx)

    assert telemetry.action_count == 1
    assert telemetry.action_count_by_actor == {"a": 1}
    assert telemetry.target_count_by_actor == {"a": {"b": 1}}
    assert telemetry.targeted_by_actor == {"b": 1}
    assert telemetry.feint_pick_count == {"measured_strike": 1}
    assert telemetry.damage_by_actor == {"a": 7}
    assert telemetry.damage_taken_by_actor == {"b": 7}
    assert telemetry.armor_absorbed_by_actor == {"b": 5}
    assert telemetry.armor_absorb_events_by_actor == {"b": 1}
    assert telemetry.damage_events_by_actor == {"a": 1}
    assert telemetry.incoming_events_by_actor == {"b": 1}
    assert telemetry.hit_by_actor == {"a": 1}
    assert telemetry.crit_by_actor == {"a": 1}
    assert telemetry.overkill_by_actor == {"a": 3}
    assert telemetry.overkill_taken_by_actor == {"b": 3}
    assert telemetry.resource_spent_by_actor == {"a": 5}
    assert telemetry.control_applied == 1
    assert telemetry.deaths == ["b"]
    assert telemetry.round_events[0]["source_id"] == "a"
    assert telemetry.round_events[0]["target_id"] == "b"
    assert telemetry.round_events[0]["damage"] == 7
    assert telemetry.round_events[0]["armor_absorbed"] == 5


@pytest.mark.unit
def test_telemetry_records_healing_buff_and_failed_actions() -> None:
    telemetry = CombatTelemetry()
    state = InMemoryBattleFactory.from_actors([sim_actor("a", "blue"), sim_actor("b", "red")], session_id="sim-5b")
    state.ctx.pending_result_support_tasks = [
        {
            "result": {
                "source_id": "a",
                "target_id": "a",
                "damage_final": 0,
                "healing_final": 5,
                "skip_reason": "NO_RESOURCE",
                "resource_facts": [{"actor_id": "a", "resource": "hp", "delta": -5}],
                "effect_facts": [{"actor_id": "a", "effect_id": "buff_guard", "action": "apply", "tags": ["buff"]}],
                "death_facts": [],
            }
        }
    ]

    telemetry.record_executor_context(state.ctx)

    assert telemetry.healing_by_actor == {"a": 5}
    assert telemetry.failed_action_count == 1
    assert telemetry.buff_applied == 1
    assert telemetry.resource_spent_by_actor == {}


@pytest.mark.unit
def test_telemetry_records_tactical_trigger_and_chain_parts() -> None:
    telemetry = CombatTelemetry()
    state = InMemoryBattleFactory.from_actors([sim_actor("a", "blue"), sim_actor("b", "red")], session_id="sim-5c")
    state.ctx.pending_result_support_tasks = [
        {
            "result": {
                "source_id": "a",
                "target_id": "b",
                "hand": "main",
                "damage_final": 9,
                "damage_trace": {
                    "raw": 30,
                    "details": {
                        "after_resist": 20,
                    },
                },
                "is_blocked": True,
                "shield_block_branch": "counter",
                "reflected_damage": 4,
                "trigger_attempts": [
                    {"trigger_id": "style_2h_ignore", "passed": True},
                    {"trigger_id": "style_ranged_perfect_backstep", "passed": True},
                ],
            }
        },
        {
            "result": {
                "source_id": "a",
                "target_id": "b",
                "hand": "main",
                "damage_final": 0,
                "is_blocked": True,
                "shield_block_branch": "defense",
                "damage_trace": {
                    "raw": 30,
                    "details": {
                        "after_resist": 20,
                        "shield_absorb": 3,
                    },
                },
            }
        },
        {
            "result": {
                "source_id": "a",
                "target_id": "b",
                "hand": "off_hand",
                "damage_final": 6,
            },
            "actors": {
                "a": {"loadout": {"layout": {"tactical_style": "skill_dual_wield", "off_hand": "skill_swords"}}}
            },
        },
        {
            "result": {
                "source_id": "a",
                "target_id": "b",
                "hand": "main",
                "damage_final": 7,
                "action_facts": {"id": "shield_line_bash", "role": "feint"},
            },
        },
        {
            "result": {
                "source_id": "b",
                "target_id": "a",
                "hand": "main",
                "damage_final": 5,
                "is_counter": True,
            }
        },
    ]

    telemetry.record_executor_context(state.ctx)

    assert telemetry.tactical_trigger_attempts_by_id == {
        "style_2h_ignore": 1,
        "style_ranged_perfect_backstep": 1,
    }
    assert telemetry.tactical_trigger_success_by_id == {"style_2h_ignore": 1, "style_ranged_perfect_backstep": 1}
    assert telemetry.tactical_trigger_attempts_by_actor == {
        "a": {"style_2h_ignore": 1},
        "b": {"style_ranged_perfect_backstep": 1},
    }
    assert telemetry.tactical_trigger_success_by_actor == {
        "a": {"style_2h_ignore": 1},
        "b": {"style_ranged_perfect_backstep": 1},
    }
    assert telemetry.tactical_damage_by_actor == {
        "a": {"style_2h_ignore": 9, "style_dual_extra": 6, "weapon_shield_bash_on_block": 7},
        "b": {"counter_attack": 5},
    }
    assert telemetry.tactical_reflected_by_actor == {"b": {"style_shield_reflect": 4}}
    assert telemetry.tactical_prevented_by_actor == {
        "b": {"style_ranged_perfect_backstep": 20, "style_shield_reflect": 3}
    }
    assert telemetry.tactical_shield_branch_by_actor == {"b": {"counter": 1, "defense": 1}}
    assert telemetry.tactical_shield_damage_by_actor == {"a": {"weapon_shield_bash_on_block": 7}}
    assert telemetry.tactical_shield_absorbed_by_actor == {"b": {"style_shield_reflect": 3}}
    assert telemetry.tactical_shield_reflected_by_actor == {"b": {"style_shield_reflect": 4}}
    assert telemetry.tactical_chain_hits_by_actor == {
        "a": {"style_dual_extra": 1},
        "b": {"counter_attack": 1},
    }


@pytest.mark.unit
def test_telemetry_estimates_prevented_damage_for_backstep_without_damage_trace() -> None:
    telemetry = CombatTelemetry()
    state = InMemoryBattleFactory.from_actors([sim_actor("a", "blue"), sim_actor("b", "red")], session_id="sim-5d")
    state.ctx.pending_result_support_tasks = [
        {
            "result": {
                "source_id": "a",
                "target_id": "b",
                "hand": "main",
                "is_dodged": True,
                "trigger_attempts": [
                    {"trigger_id": "style_ranged_perfect_backstep", "passed": True},
                ],
            },
            "actors": {
                "a": {
                    "stats": {
                        "mods": {
                            "main_hand_damage_base": 12,
                            "main_hand_damage_spread": 0.2,
                            "physical_damage_bonus": 0,
                            "damage_mult": 1.0,
                        }
                    }
                },
            },
        },
    ]

    telemetry.record_executor_context(state.ctx)

    assert telemetry.tactical_prevented_by_actor == {"b": {"style_ranged_perfect_backstep": 11}}


@pytest.mark.unit
def test_intent_provider_returns_no_moves_without_targets() -> None:
    state = InMemoryBattleFactory.from_actors([sim_actor("solo", "blue")], session_id="sim-solo")

    assert AiSimulationIntentProvider(brain=StaticBrain()).choose_moves(state, state.ctx.actors["solo"]) == []


@pytest.mark.unit
async def test_simulator_runs_1v1_through_real_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, _max_d: min_d))
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (0.0, chance >= 0.7)))
    state = InMemoryBattleFactory.from_actors(
        [sim_actor("hero", "blue", hp=20, damage=30.0), sim_actor("wolf", "red", hp=20, damage=1.0)],
        session_id="sim-real",
        limits=InMemoryBattleLimits(max_rounds=3),
    )

    result = await InMemoryCombatSimulator(intent_provider=AiSimulationIntentProvider(brain=StaticBrain())).run(state)

    assert result.winner in {"blue", "red", "draw"}
    assert result.rounds_completed >= 1
    assert state.telemetry.action_count >= 1
    assert state.telemetry.damage_by_actor


@pytest.mark.unit
def test_simulation_move_registrar_accepts_only_target_queue_entries() -> None:
    state = InMemoryBattleFactory.from_actors([sim_actor("a", "blue"), sim_actor("b", "red")], session_id="live-reg")
    registrar = SimulationMoveRegistrar()
    pending = {}
    move = CombatMoveDTO(move_id="a-b", char_id="a", strategy="exchange", payload=ExchangePayload(target_id="b"))

    assert registrar.register_exchange_move(state, move, pending) is True
    assert state.ctx.targets["a"] == []
    assert pending == {"a-b": move}

    duplicate = CombatMoveDTO(move_id="a-b-2", char_id="a", strategy="exchange", payload=ExchangePayload(target_id="b"))
    assert registrar.register_exchange_move(state, duplicate, pending) is False
    assert "a-b-2" not in pending


@pytest.mark.unit
async def test_live_simulator_resolves_one_exchange_per_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, _max_d: min_d))
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (0.0, chance >= 0.7)))
    state = InMemoryBattleFactory.from_actors(
        [sim_actor("a", "blue", hp=60, damage=5.0), sim_actor("b", "red", hp=60, damage=5.0)],
        session_id="live-one-exchange",
        limits=InMemoryBattleLimits(max_rounds=2, candidate_limit=1, force_unanswered_exchange=False),
    )
    simulator = LiveInMemoryCombatSimulator(timing=LiveSimulationTiming(tick_interval_seconds=0, timeout_ticks=None))

    first = await simulator.step(state, tick_index=10)
    second = await simulator.step(state, tick_index=20)

    assert first.action_count == 0
    assert first.registered_move_id
    assert second.action_count == 1
    assert state.ctx.meta.step_counter == 1
    assert second.exchange_index == 1
    assert state.telemetry.round_events[0]["round"] == 1


@pytest.mark.unit
async def test_live_simulator_uses_virtual_initiative_without_wall_clock_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_sleep(_seconds: float) -> None:
        raise AssertionError("wall-clock sleep must not be used for virtual simulation time")

    import asyncio

    monkeypatch.setattr(asyncio, "sleep", fail_sleep)
    state = InMemoryBattleFactory.from_actors(
        [
            sim_actor("slow", "blue", initiative=0.0),
            sim_actor("fast", "red", initiative=100.0),
        ],
        session_id="live-virtual-time",
        limits=InMemoryBattleLimits(max_rounds=1, candidate_limit=1, force_unanswered_exchange=False),
    )
    simulator = LiveInMemoryCombatSimulator(
        timing=LiveSimulationTiming(
            tick_interval_seconds=0.05,
            timeout_ticks=None,
            base_decision_ticks=10,
            min_decision_ticks=1,
        ),
        brain=StaticBrain(),
    )

    first = await simulator.step(state, tick_index=0)
    second = await simulator.step(state, tick_index=5)
    third = await simulator.step(state, tick_index=10)

    assert first.registered_move_id is None
    assert second.registered_move_id
    assert "fast" in second.registered_move_id
    assert third.action_count == 1


@pytest.mark.unit
async def test_simulator_stops_immediately_when_winner_already_known() -> None:
    state = InMemoryBattleFactory.from_actors([sim_actor("hero", "blue")], session_id="sim-winner")

    result = await InMemoryCombatSimulator(intent_provider=AiSimulationIntentProvider(brain=StaticBrain())).run(state)

    assert result.winner == "blue"
    assert result.rounds_completed == 0


@pytest.mark.unit
async def test_simulation_report_renders_core_metrics() -> None:
    state = InMemoryBattleFactory.from_actors([sim_actor("hero", "blue")], session_id="sim-report")

    result = await InMemoryCombatSimulator(intent_provider=AiSimulationIntentProvider(brain=StaticBrain())).run(state)

    report = render_simulation_report(result)
    assert "winner: blue" in report
    assert "actions:" in report
    assert "action_count_by_actor:" in report
    assert "checks_by_actor:" in report
