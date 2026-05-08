from __future__ import annotations

from typing import Any

import pytest

from src.backend.features.combat.dto import (
    ActiveEffectDTO,
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    BattleContext,
    BattleMeta,
    CollectorSignalDTO,
    CombatActionDTO,
    CombatEventDTO,
    CombatMoveDTO,
    ExchangePayload,
    InstantPayload,
    InteractionResultDTO,
    PipelineContextDTO,
)
from src.backend.features.combat.dto.actor import ActorStats
from src.backend.features.combat.integrations import CombatSessionIntegration
from src.backend.features.combat.runtime.engine.ability_service import AbilityService
from src.backend.features.combat.runtime.engine.context_builder import ContextBuilder
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.engine.mechanics_service import MechanicsService
from src.backend.features.combat.runtime.engine.pipeline import CombatPipeline
from src.backend.features.combat.runtime.engine.resolver import CombatResolver
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine
from src.backend.features.combat.runtime.processors import AiProcessor, CombatCollector, CombatExecutor
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


class FakeDataService:
    def __init__(self, meta: BattleMeta, moves: dict[str, Any], targets: dict[str, list[int]]) -> None:
        self.meta = meta
        self.moves = moves
        self.targets = targets
        self.transferred: list[CombatActionDTO] = []

    async def get_action_queue_size(self, session_id: str) -> int:
        return 0

    async def get_battle_meta(self, session_id: str) -> BattleMeta:
        return self.meta

    async def get_intent_moves(self, session_id: str, actor_ids: list[int | str]) -> dict[str, Any]:
        return self.moves

    async def get_targets(self, session_id: str) -> dict[str, list[int]]:
        return self.targets

    async def transfer_actions(self, session_id: str, actions: list[CombatActionDTO]) -> None:
        self.transferred.extend(actions)


class CapturingCombatManager:
    def __init__(self) -> None:
        self.commit_kwargs: dict[str, Any] | None = None

    async def commit_battle_results(self, *args: Any, **kwargs: Any) -> None:
        self.commit_kwargs = {"args": args, "kwargs": kwargs}


def battle_meta() -> BattleMeta:
    return BattleMeta(
        active=1,
        step_counter=0,
        active_actors_count=2,
        teams={"a": [1], "b": [2]},
        actors_info={"1": "player", "2": "ai"},
        battle_type="arena",
        location_id="arena",
    )


def move_payload(move_id: str, actor_id: int, target_id: int) -> dict[str, Any]:
    return CombatMoveDTO(
        move_id=move_id,
        char_id=actor_id,
        strategy="exchange",
        payload=ExchangePayload(target_id=target_id),
    ).model_dump(mode="json")


def actor(actor_id: int, team: str, hp: int = 100) -> ActorSnapshot:
    return ActorSnapshot(
        meta=ActorMetaDTO(id=actor_id, name=f"A{actor_id}", type="player", team=team, hp=hp, max_hp=max(hp, 1)),
        raw=ActorRawDTO(modifiers={"main_hand_damage_base": 200, "main_hand_accuracy": 1.0}),
        loadout=ActorLoadoutDTO(),
    )


def stats(mods: dict[str, float] | None = None, skills: dict[str, float] | None = None) -> ActorStats:
    return ActorStats(
        mods=CombatModifiersDTO(**(mods or {})),
        skills=CombatSkillsDTO(**(skills or {})),
    )


@pytest.mark.unit
async def test_collector_pairs_exchange_moves() -> None:
    data = FakeDataService(
        battle_meta(),
        {"1": {"exchange": {"m1": move_payload("m1", 1, 2)}}, "2": {"exchange": {"m2": move_payload("m2", 2, 1)}}},
        {"1": [2], "2": [1]},
    )

    batch_size, ai_tasks, winner = await CombatCollector(data).collect_actions("c1")

    assert batch_size > 0
    assert ai_tasks == []
    assert winner is None
    assert data.transferred[0].partner_move is not None


@pytest.mark.unit
async def test_collector_forces_timeout_move() -> None:
    data = FakeDataService(battle_meta(), {"1": {"exchange": {"m1": move_payload("m1", 1, 2)}}}, {"1": [2], "2": [1]})

    await CombatCollector(data).collect_actions(
        "c1",
        CollectorSignalDTO(session_id="c1", char_id=1, signal_type="check_timeout", move_id="m1"),
    )

    assert data.transferred[0].is_forced is True


@pytest.mark.unit
async def test_collector_ignores_unsafe_batch_timeout() -> None:
    data = FakeDataService(battle_meta(), {"2": {"exchange": {"m2": move_payload("m2", 2, 1)}}}, {"1": [2], "2": []})

    batch_size, ai_tasks, winner = await CombatCollector(data).collect_actions(
        "c1",
        CollectorSignalDTO(session_id="c1", char_id=2, signal_type="check_timeout", move_id="batch"),
    )

    assert batch_size == 0
    assert ai_tasks == []
    assert winner is None
    assert data.transferred == []


@pytest.mark.unit
async def test_collector_finds_ai_missing_targets() -> None:
    data = FakeDataService(battle_meta(), {"2": {"exchange": {}}}, {"1": [2], "2": [1]})

    _, ai_tasks, _ = await CombatCollector(data).collect_actions("c1")

    assert ai_tasks[0].bot_id == 2
    assert ai_tasks[0].missing_targets == [1]


@pytest.mark.unit
async def test_executor_returns_target_after_forced_exchange() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b", hp=1)})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        is_forced=True,
    )

    processed = await CombatExecutor().process_batch(ctx, [action])

    assert processed == ["m1"]
    assert ctx.pending_target_returns == [{"source_id": "1", "target_id": 2}]
    assert "2" in ctx.pending_dead_actors
    assert ctx.meta.step_counter == 1
    assert ctx.actors["1"].meta.exchange_counter == 1
    assert ctx.actors["2"].meta.exchange_counter == 1
    assert {entry["type"] for entry in ctx.pending_logs} >= {"HIT", "DEATH"}
    assert all("runtime" in entry["tags"] for entry in ctx.pending_logs)


@pytest.mark.unit
def test_executor_log_entries_use_actor_names_and_result_summary() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["2"].meta.hp = 93
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=7, is_hit=True)
    result.events.append(
        CombatEventDTO(
            type="HIT",
            source_id=1,
            target_id=2,
            value=7,
            resource="hp",
        )
    )

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    assert [entry["type"] for entry in ctx.pending_logs] == ["RESULT", "HIT"]
    assert ctx.pending_logs[0]["source_name"] == "A1"
    assert ctx.pending_logs[0]["target_name"] == "A2"
    assert ctx.pending_logs[0]["outcome"] == "hit"
    assert ctx.pending_logs[0]["global_turn"] == 1
    assert ctx.pending_logs[0]["target_hp_before"] == 100
    assert ctx.pending_logs[0]["target_hp_after"] == 93
    assert ctx.pending_logs[0]["target_hp_max"] == 100
    assert ctx.pending_logs[0]["resources"] == [
        {"actor_id": "2", "resource": "hp", "before": 100, "after": 93, "max": 100, "delta": -7, "direction": "loss"}
    ]
    assert ctx.pending_logs[0]["text"] == "A1 разменялся с A2: удар, -7 hp (HP 93/100)."
    assert ctx.pending_logs[1]["resource_max"] == 100
    assert ctx.pending_logs[1]["resources"] == [
        {"actor_id": "2", "resource": "hp", "before": 100, "after": 93, "max": 100, "delta": -7, "direction": "loss"}
    ]
    assert ctx.pending_logs[1]["text"] == "A1 наносит A2 7 hp (HP 93/100)."


@pytest.mark.unit
def test_executor_log_entries_use_humanoid_feint_text_templates() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["2"].meta.hp = 93
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="true_strike"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=7, is_hit=True)
    result.events.append(CombatEventDTO(type="CAST", source_id=1, target_id=2, action_id="true_strike"))
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=7, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    assert (
        ctx.pending_logs[0]["text"]
        == "A1 выжидает момент и ведет удар по открытой линии A2, "
        "и попадает, не давая A2 уйти движением (HP 93/100)."
    )
    assert ctx.pending_logs[0]["catalog"] == "combat_entries"
    assert ctx.pending_logs[0]["catalog_key"] == "combat.feint.true_strike"
    assert ctx.pending_logs[0]["catalog_event"] == "hit"
    assert ctx.pending_logs[0]["catalog_tooltip"] == "description"
    assert ctx.pending_logs[1]["text"] == "A1 выжидает момент и ведет удар по открытой линии A2."
    assert ctx.pending_logs[2]["text"] == "и попадает, не давая A2 уйти движением 7 hp (HP 93/100)."


@pytest.mark.unit
async def test_executor_expands_all_enemy_feint_to_secondary_targets() -> None:
    ctx = BattleContext(
        session_id="c1",
        meta=BattleMeta(
            active=1,
            step_counter=0,
            active_actors_count=4,
            teams={"a": [1], "b": [2, 3, 4]},
            actors_info={"1": "player", "2": "ai", "3": "ai", "4": "ai"},
            battle_type="arena",
            location_id="arena",
        ),
        actors={"1": actor(1, "a"), "2": actor(2, "b"), "3": actor(3, "b"), "4": actor(4, "b")},
    )
    for combat_actor in ctx.actors.values():
        combat_actor.raw.modifiers = {"main_hand_damage_base": {"base": 20}, "main_hand_accuracy": {"base": 1.0}}

    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="cleave"),
        ),
        partner_move=CombatMoveDTO(
            move_id="m2",
            char_id=2,
            strategy="exchange",
            payload=ExchangePayload(target_id=1),
        ),
    )

    await CombatExecutor()._handle_exchange(ctx, action)

    assert ctx.actors["2"].meta.hp < 100
    assert ctx.actors["3"].meta.hp < 100
    assert ctx.actors["4"].meta.hp < 100
    assert ctx.actors["3"].meta.hp > ctx.actors["2"].meta.hp
    assert ctx.actors["4"].meta.hp > ctx.actors["2"].meta.hp
    assert ctx.actors["1"].meta.hp < 100


@pytest.mark.unit
def test_executor_log_entries_use_humanoid_effect_fallback_text() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2)
    result.events.append(CombatEventDTO(type="APPLY_EFFECT", source_id=1, target_id=2, action_id="dot_bleed"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    assert ctx.pending_logs[1]["text"] == "A1 накладывает Кровотечение на A2."
    assert ctx.pending_logs[1]["catalog"] == "effects"
    assert ctx.pending_logs[1]["catalog_key"] == "dot_bleed"
    assert ctx.pending_logs[1]["catalog_tooltip"] == "description"


@pytest.mark.unit
async def test_commit_session_persists_step_and_actor_exchange_counters() -> None:
    manager = CapturingCombatManager()
    integration = CombatSessionIntegration(manager)  # type: ignore[arg-type]
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a")})
    ctx.meta.step_counter = 3
    ctx.actors["1"].meta.exchange_counter = 2

    await integration.commit_session(ctx, ["m1"])

    assert manager.commit_kwargs is not None
    updates = manager.commit_kwargs["args"][1]
    assert updates["1"]["state"]["exchange_counter"] == 2
    assert manager.commit_kwargs["kwargs"]["meta_update"] == {"step_counter": 3}


@pytest.mark.unit
def test_ai_processor_generates_exchange_payload() -> None:
    payload = AiProcessor().decide_exchange(actor(2, "b"), actor(1, "a"))

    assert payload["action"] == "attack"
    assert payload["target_id"] == 1


@pytest.mark.unit
def test_session_integration_snapshot_preserves_exchange_counter() -> None:
    integration = CombatSessionIntegration(CapturingCombatManager())  # type: ignore[arg-type]

    snapshot = integration._build_snapshot(
        "1",
        "a",
        {"hp": 100, "max_hp": 100, "exchange_counter": 17},
        {"attributes": {}, "modifiers": {}},
        {},
        {"name": "A1", "type": "player"},
        {"abilities": [], "effects": []},
        {},
        {},
    )

    assert snapshot.meta.exchange_counter == 17


@pytest.mark.unit
def test_session_integration_snapshot_uses_combat_layout_not_equipment_ids() -> None:
    integration = CombatSessionIntegration(CapturingCombatManager())  # type: ignore[arg-type]

    snapshot = integration._build_snapshot(
        "1",
        "a",
        {"hp": 100, "max_hp": 100},
        {"attributes": {}, "modifiers": {}},
        {
            "layout": {"main_hand": "skill_macing", "off_hand": "skill_shield_mastery"},
            "equipment_layout": {"main_hand": "mace-id", "off_hand": "shield-id"},
            "weapon_slots": ["main_hand"],
        },
        {"name": "A1", "type": "player"},
        {"abilities": [], "effects": []},
        {},
        {},
    )

    assert snapshot.loadout.layout["off_hand"] == "skill_shield_mastery"
    assert snapshot.loadout.equipment_layout["off_hand"] == "shield-id"
    assert snapshot.loadout.weapon_slots == ["main_hand"]


@pytest.mark.unit
def test_session_integration_snapshot_reuses_persisted_stats() -> None:
    integration = CombatSessionIntegration(CapturingCombatManager())  # type: ignore[arg-type]

    snapshot = integration._build_snapshot(
        "1",
        "a",
        {"hp": 100, "max_hp": 100},
        {"attributes": {}, "modifiers": {"accuracy": {"base": 0.1}}},
        {},
        {"name": "A1", "type": "player"},
        {"abilities": [], "effects": []},
        {},
        {},
        {"mods": {"accuracy": 0.77, "main_hand_damage_base": 9.0}, "skills": {"skill_unarmed": 3.0}},
        {"accuracy": "cached"},
    )

    assert snapshot.stats is not None
    assert snapshot.stats.mods.accuracy == 0.77
    assert snapshot.explanation == {"accuracy": "cached"}

    StatsEngine.ensure_stats(snapshot)

    assert snapshot.stats.mods.accuracy == 0.77


@pytest.mark.unit
def test_ability_service_applies_feint_mutations_and_triggers() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="true_strike"),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.triggers.accuracy.true_strike is True
    assert source.raw.modifiers["physical_damage_mult"]["temp"]
    assert source.statuses.abilities[0].ability_id == "true_strike"
    assert ctx.result.events[0].type == "CAST"


@pytest.mark.unit
def test_ability_service_applies_ability_cost_and_pipeline_flags() -> None:
    source = actor(1, "a")
    source.meta.en = 100
    source.meta.tokens["gift"] = 1
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="fireball", target_id=2),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.flags.meta.source_type == "magic"
    assert ctx.flags.damage.fire is True
    assert ctx.flags.damage.physical is False
    assert ctx.result.resource_changes["en"]["cost"] == "-25"
    assert ctx.result.resource_changes["gift"]["cost"] == "-1"
    assert ctx.override_damage == (40.0, 60.0)


@pytest.mark.unit
def test_feint_service_refill_hand_uses_token_costs() -> None:
    source = actor(1, "a")
    source.meta.feints.arsenal = ["true_strike"]
    source.meta.tokens["hit"] = 2

    FeintService.refill_hand(source.meta, hand_size=1)

    assert source.meta.feints.hand == {"true_strike": {"hit": 2}}
    assert source.meta.tokens["hit"] == 0


@pytest.mark.unit
def test_feint_service_reroll_preserves_pinned_and_refunds_unpinned() -> None:
    source = actor(1, "a")
    source.meta.feints.arsenal = ["true_strike", "piercing_thrust"]
    source.meta.feints.hand = {
        "true_strike": {"hit": 2},
        "piercing_thrust": {"hit": 3},
    }
    source.meta.feints.pinned = "true_strike"

    FeintService.reroll_hand(source.meta, hand_size=1)

    assert source.meta.feints.hand == {"true_strike": {"hit": 2}}
    assert source.meta.feints.pinned == "true_strike"
    assert source.meta.tokens["hit"] == 3


@pytest.mark.unit
def test_executor_flow_refunds_used_feint_cost() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a")})
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="true_strike"),
    )
    result = InteractionResultDTO(source_id=1, target_id=2)
    result.chain_events.preserve_feint = True

    CombatExecutor._refund_feint_cost_if_needed(ctx, result, move)

    assert ctx.actors["1"].meta.tokens["hit"] == 2


@pytest.mark.unit
def test_mechanics_applies_defender_tokens_from_resolver_result() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    result = InteractionResultDTO(source_id=1, target_id=2, tokens_awarded_defender={"tempo": 1, "parry": 1})

    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, result)

    assert source.meta.tokens == {}
    assert target.meta.tokens["tempo"] == 1
    assert target.meta.tokens["parry"] == 1


@pytest.mark.unit
def test_mechanics_applies_periodic_effect_ticks_and_death() -> None:
    source = actor(1, "a", hp=2)
    source.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="dot_bleed", source_id=2, expire_at_exchange=3, impact={"hp": -2})
    )
    ctx = PipelineContextDTO()
    ctx.flags.mechanics.apply_periodic = True

    MechanicsService().process_turn_start(ctx, source)

    assert source.meta.hp == 0
    assert source.meta.is_dead is True
    assert [event.type for event in ctx.result.events] == ["TICK", "DEATH"]


@pytest.mark.unit
async def test_executor_ticks_periodic_effects_before_exchange() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="dot_bleed", source_id=2, expire_at_exchange=3, impact={"hp": -2})
    )
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        is_forced=True,
    )

    await CombatExecutor().process_batch(ctx, [action])

    assert ctx.actors["1"].meta.hp == 98
    assert any(entry["type"] == "TICK" and entry["action_id"] == "dot_bleed" for entry in ctx.pending_logs)


@pytest.mark.unit
async def test_crit_bleed_trigger_is_cancelled_when_attack_is_parried(monkeypatch: pytest.MonkeyPatch) -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout.update({"main_hand": "skill_swords", "main_hand_trigger": "crit.bleed_on_crit"})
    source.stats = stats(
        {
            "main_hand_accuracy": 1.0,
            "main_hand_crit_chance": 1.0,
            "main_hand_crit_cap": 1.0,
            "main_hand_damage_base": 10.0,
            "main_hand_damage_spread": 0.0,
        },
        {"skill_swords": 0.0},
    )
    target.stats = stats({"evasion": 0.0, "parry": 1.0, "parry_cap": 1.0, "block": 0.0})
    rolls = iter([(0.0, True), (0.0, True), (1.0, False), (0.0, True)])
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda _chance: next(rolls)))

    result = await CombatPipeline().calculate(
        source,
        target,
        CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )

    assert result.is_crit is True
    assert result.is_parried is True
    assert result.is_hit is False
    assert target.statuses.effects == []
    assert "APPLY_EFFECT" not in [event.type for event in result.events]


@pytest.mark.unit
def test_dual_wield_style_activates_catalog_trigger_from_loadout() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout.update(
        {
            "main_hand": "skill_swords",
            "off_hand": "skill_fencing",
            "tactical_style": "skill_dual_wield",
            "tactical_style_trigger": "accuracy.style_dual_extra",
        }
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    ctx = ContextBuilder.build_context(source, target, move)

    assert ctx.triggers.accuracy.style_dual_extra is True
    assert ctx.result.chain_events.trigger_offhand_attack is False


@pytest.mark.unit
def test_two_handed_style_activates_catalog_trigger_from_loadout() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout.update(
        {
            "main_hand": "skill_macing",
            "tactical_style": "skill_two_handed",
            "tactical_style_trigger": "accuracy.style_2h_ignore",
        }
    )
    source.loadout.two_handed = True
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    ctx = ContextBuilder.build_context(source, target, move)

    assert ctx.triggers.accuracy.style_2h_ignore is True


@pytest.mark.unit
def test_shield_style_activates_on_defender_not_attacker() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout.update(
        {
            "main_hand": "skill_swords",
            "off_hand": "skill_shield_mastery",
            "tactical_style": "skill_shield_mastery",
            "tactical_style_trigger": "block.style_shield_reflect",
        }
    )
    target.loadout.layout.update(source.loadout.layout)
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    source_only_ctx = ContextBuilder.build_context(source, actor(3, "c"), move)
    defender_ctx = ContextBuilder.build_context(actor(3, "c"), target, move)

    assert source_only_ctx.triggers.block.style_shield_reflect is False
    assert defender_ctx.triggers.block.style_shield_reflect is True


@pytest.mark.unit
def test_evasion_uses_attacker_anti_dodge(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_roll(_chance: float) -> tuple[float | None, bool]:
        raise AssertionError("evasion roll should not run when attacker anti-dodge reduces chance below zero")

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(fail_roll))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    dodged = CombatResolver._step_evasion_roll(
        stats({"anti_dodge_chance": 0.6}),
        stats({"evasion": 0.5, "dodge_cap": 0.75, "anti_dodge_chance": 0.0}),
        ctx,
        result,
    )

    assert dodged is False
    assert result.is_dodged is False


@pytest.mark.unit
def test_crit_roll_uses_normalized_weapon_skill_and_default_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.flags.meta.weapon_class = "swords"
    result = InteractionResultDTO(source_id=1, target_id=2)

    CombatResolver._step_crit_roll(
        stats({"main_hand_crit_chance": 0.5}, {"skill_swords": 0.5}),
        stats(),
        ctx,
        result,
    )

    assert stats().mods.main_hand_crit_cap == 0.75
    assert captured_chances == [0.75]


@pytest.mark.unit
def test_physical_damage_attribute_bonus_applies_to_weapon_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.meta.weapon_class = "swords"
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = CombatResolver._step_calculate_damage(
        stats({"main_hand_damage_base": 4.0, "main_hand_damage_spread": 0.0, "physical_damage": 6.0}),
        stats(),
        ctx,
        result,
    )

    assert damage == 10.0
    assert result.damage_final == 10


@pytest.mark.unit
def test_unarmed_damage_uses_strength_and_unarmed_skill_efficiency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.meta.weapon_class = "unarmed"
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = CombatResolver._step_calculate_damage(
        stats(
            {"main_hand_damage_base": 6.0, "main_hand_damage_spread": 0.5, "physical_damage": 6.0},
            {"skill_unarmed": 1.0},
        ),
        stats(),
        ctx,
        result,
    )

    assert damage == 16.2
    assert result.damage_final == 16


@pytest.mark.unit
def test_unarmed_damage_uses_novice_efficiency_without_double_counting_strength(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.meta.weapon_class = "unarmed"
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = CombatResolver._step_calculate_damage(
        stats({"main_hand_damage_base": 6.0, "main_hand_damage_spread": 0.5, "physical_damage": 6.0}),
        stats(),
        ctx,
        result,
    )

    assert damage == 1.5
    assert result.damage_final == 1


@pytest.mark.unit
def test_parry_roll_applies_parrying_skill_multiplier_in_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    CombatResolver._step_parry_roll(
        stats(),
        stats({"parry": 0.1, "parry_cap": 0.75}, {"skill_parrying": 0.5}),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.3)]


@pytest.mark.unit
def test_block_roll_applies_parrying_skill_multiplier_in_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    CombatResolver._step_block_roll(
        stats(),
        stats({"block": 0.2, "shield_block_cap": 0.75}, {"skill_parrying": 1.0}),
        ctx,
        result,
    )

    assert captured_chances == [0.5]


@pytest.mark.unit
def test_item_source_type_reads_item_offensive_modifiers() -> None:
    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "item"
    actor_stats = stats(
        {
            "main_hand_damage_base": 999.0,
            "main_hand_accuracy": 0.99,
            "main_hand_crit_chance": 0.99,
            "main_hand_penetration": 0.99,
            "item_damage_base": 12.0,
            "item_damage_spread": 0.25,
            "item_accuracy": 0.8,
            "item_crit_chance": 0.2,
            "item_penetration": 0.1,
        }
    )

    assert CombatResolver._get_offensive_val(actor_stats, ctx, "damage_base") == 12.0
    assert CombatResolver._get_offensive_val(actor_stats, ctx, "damage_spread") == 0.25
    assert CombatResolver._get_offensive_val(actor_stats, ctx, "accuracy") == 0.8
    assert CombatResolver._get_offensive_val(actor_stats, ctx, "crit_chance") == 0.2
    assert CombatResolver._get_offensive_val(actor_stats, ctx, "crit_cap") == 0.75
    assert CombatResolver._get_offensive_val(actor_stats, ctx, "penetration") == 0.1
