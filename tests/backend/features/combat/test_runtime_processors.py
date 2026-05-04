from __future__ import annotations

from typing import Any

import pytest

from src.backend.features.combat.dto import (
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    BattleContext,
    BattleMeta,
    CollectorSignalDTO,
    CombatActionDTO,
    CombatMoveDTO,
    ExchangePayload,
    InstantPayload,
    PipelineContextDTO,
)
from src.backend.features.combat.runtime.engine.ability_service import AbilityService
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.processors import AiProcessor, CombatCollector, CombatExecutor


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
    assert {entry["type"] for entry in ctx.pending_logs} >= {"HIT", "DEATH"}
    assert all("runtime" in entry["tags"] for entry in ctx.pending_logs)


@pytest.mark.unit
def test_ai_processor_generates_exchange_payload() -> None:
    payload = AiProcessor().decide_exchange(actor(2, "b"), actor(1, "a"))

    assert payload["action"] == "attack"
    assert payload["target_id"] == 1


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
