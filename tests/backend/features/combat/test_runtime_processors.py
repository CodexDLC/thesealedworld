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
    CombatEffectFactDTO,
    CombatEventDTO,
    CombatMoveDTO,
    ExchangePayload,
    InstantPayload,
    InteractionResultDTO,
    PipelineContextDTO,
)
from src.backend.features.combat.dto.actor import ActorStats
from src.backend.features.combat.dto.pipeline import CombatDamageTraceDTO
from src.backend.features.combat.integrations import CombatCatalogIntegrator, CombatSessionIntegration
from src.backend.features.combat.runtime.engine.ability_service import AbilityService
from src.backend.features.combat.runtime.engine.context_builder import ContextBuilder
from src.backend.features.combat.runtime.engine.effect_factory import EffectFactory
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.engine.mechanics_service import MechanicsService
from src.backend.features.combat.runtime.engine.pipeline import CombatPipeline
from src.backend.features.combat.runtime.engine.resolver import CombatResolver
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine
from src.backend.features.combat.runtime.engine.trigger_activation import activate_trigger
from src.backend.features.combat.runtime.processors import AiProcessor, CombatCollector, CombatExecutor
from src.backend.features.combat.runtime.processors.chaos_service import ANCHOR_FORCE_TEAM, ChaosService
from src.backend.features.combat.runtime.support import CombatResultSupportTask, CombatResultSupportTaskDTO
from src.backend.features.combat.workers.tasks.chat_announcements import (
    publish_combat_final_announcement,
    publish_combat_start_announcement,
)
from src.backend.features.combat.workers.tasks.executor_task import (
    _enqueue_result_support_tasks,
    _publish_combat_logs_to_chat,
)
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


class FakeDataService:
    def __init__(self, meta: BattleMeta | None, moves: dict[str, Any], targets: dict[str, list[int | str]]) -> None:
        self.meta = meta
        self.moves = moves
        self.targets = targets
        self.transferred: list[CombatActionDTO] = []
        self.calls: list[str] = []

    async def get_action_queue_size(self, session_id: str) -> int:
        self.calls.append("get_action_queue_size")
        return 0

    async def get_battle_meta(self, session_id: str) -> BattleMeta | None:
        self.calls.append("get_battle_meta")
        return self.meta

    async def get_intent_moves(self, session_id: str, actor_ids: list[int | str]) -> dict[str, Any]:
        self.calls.append("get_intent_moves")
        return self.moves

    async def get_targets(self, session_id: str) -> dict[str, list[int | str]]:
        self.calls.append("get_targets")
        return self.targets

    async def transfer_actions(self, session_id: str, actions: list[CombatActionDTO]) -> None:
        self.calls.append("transfer_actions")
        self.transferred.extend(actions)


class CapturingCombatManager:
    def __init__(self) -> None:
        self.commit_kwargs: dict[str, Any] | None = None

    async def commit_battle_results(self, *args: Any, **kwargs: Any) -> None:
        self.commit_kwargs = {"args": args, "kwargs": kwargs}


class CapturingSupportDataService:
    def __init__(self) -> None:
        self.analytics: list[tuple[str, dict[str, Any]]] = []

    async def append_analytics(self, session_id: str, entry: dict[str, Any] | str) -> None:
        assert isinstance(entry, dict)
        self.analytics.append((session_id, entry))


class CapturingArqQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict[str, Any]]] = []

    async def enqueue_job(self, name: str, payload: dict[str, Any]) -> None:
        self.jobs.append((name, payload))


class FailingChatRedis:
    async def xadd(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("chat stream down")


class CapturingChatRedis:
    def __init__(self) -> None:
        self.claims: dict[str, str] = {}
        self.xadds: list[tuple[Any, ...]] = []

    async def set(self, key: str, value: str, **kwargs: Any) -> bool:
        if kwargs.get("nx") and key in self.claims:
            return False
        self.claims[key] = value
        return True

    async def xadd(self, *args: Any, **kwargs: Any) -> None:
        self.xadds.append((args, kwargs))


class AnnouncementDataService:
    def __init__(self) -> None:
        import json

        self.meta = {
            "active": "1",
            "teams": json.dumps({"team_1": ["1"], "team_2": ["wolf_1"]}),
        }
        self.actors = {
            "1": {"meta": {"name": "Hero", "type": "player", "hp": 42, "max_hp": 100}},
            "wolf_1": {"meta": {"name": "Wolf", "type": "monster", "is_ai": True, "hp": 0, "max_hp": 60}},
        }

    async def get_meta(self, session_id: str) -> dict[str, Any]:
        return self.meta

    async def get_actors_batch(self, session_id: str, actor_ids: list[str]) -> dict[str, Any]:
        return {actor_id: self.actors[actor_id] for actor_id in actor_ids}

    @staticmethod
    def actor_ids_from_meta(meta: dict[str, Any]) -> list[str]:
        return ["1", "wolf_1"]


class FakeCombatSessionsForChaos:
    def __init__(self, *, battle_type: str = "arena", actors_info: dict[str, str] | None = None) -> None:
        import json

        self.meta = {
            "battle_type": battle_type,
            "actors_info": json.dumps(actors_info or {"1": "player", "2": "player"}),
        }
        self.hot_joined: dict[str, Any] | None = None
        self.logs: list[tuple[str, list[str] | None]] = []

    async def get_raw_meta(self, session_id: str) -> dict[str, Any] | None:
        return self.meta

    async def hot_join_actor(
        self,
        *,
        session_id: str,
        actor_id: int,
        team_name: str,
        actor_data: dict[str, Any],
        is_ai: bool,
    ) -> None:
        self.hot_joined = {
            "session_id": session_id,
            "actor_id": actor_id,
            "team_name": team_name,
            "actor_data": actor_data,
            "is_ai": is_ai,
        }

    async def add_log(self, session_id: str, text: str, tags: list[str] | None = None) -> None:
        self.logs.append((text, tags))


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


def actor(actor_id: int | str, team: str, hp: int = 100) -> ActorSnapshot:
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
async def test_chaos_service_spawns_anchor_projection_from_family_resource() -> None:
    sessions = FakeCombatSessionsForChaos(battle_type="arena")

    spawned = await ChaosService(sessions).spawn_cleaner("combat-1")  # type: ignore[arg-type]

    assert spawned is True
    assert sessions.hot_joined is not None
    assert sessions.hot_joined["actor_id"] == -703
    assert sessions.hot_joined["team_name"] == ANCHOR_FORCE_TEAM
    actor_data = sessions.hot_joined["actor_data"]
    assert actor_data["meta"]["name"] == "Проекция Западной Гравитации"
    assert actor_data["meta"]["hp"] > 1000
    assert actor_data["raw"]["modifiers"]["main_hand_damage_base"]["base"] >= 100
    assert actor_data["loadout"]["layout"]["main_hand"] == "skill_polearms"
    assert actor_data["skills"]["skill_polearms"] == 1.0
    assert sessions.logs[0][1] == ["anchor", "higher_force", "spawn", "west_gravity_sovereign"]


@pytest.mark.unit
async def test_chaos_service_does_not_spawn_second_anchor_projection() -> None:
    sessions = FakeCombatSessionsForChaos(actors_info={"1": "player", "-703": "ai"})

    spawned = await ChaosService(sessions).spawn_cleaner("combat-1")  # type: ignore[arg-type]

    assert spawned is False
    assert sessions.hot_joined is None


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
async def test_collector_orders_exchange_pairs_by_response_readiness() -> None:
    meta = BattleMeta(
        active=1,
        step_counter=0,
        active_actors_count=4,
        teams={"a": [1, 3], "b": [2, 4]},
        actors_info={"1": "player", "2": "ai", "3": "player", "4": "ai"},
        battle_type="arena",
        location_id="arena",
    )
    data = FakeDataService(
        meta,
        {
            "1": {"exchange": {"m1": move_payload("m1", 1, 2)}},
            "3": {"exchange": {"m3": move_payload("m3", 3, 4)}},
            "4": {"exchange": {"m4": move_payload("m4", 4, 3)}},
            "2": {"exchange": {"m2": move_payload("m2", 2, 1)}},
        },
        {"1": [2], "2": [1], "3": [4], "4": [3]},
    )

    batch_size, ai_tasks, winner = await CombatCollector(data).collect_actions("c1")

    assert batch_size > 0
    assert ai_tasks == []
    assert winner is None
    assert [(action.move.move_id, action.partner_move.move_id) for action in data.transferred] == [
        ("m3", "m4"),
        ("m1", "m2"),
    ]


@pytest.mark.unit
async def test_collector_inactive_session_returns_before_queue_reads() -> None:
    data = FakeDataService(None, {}, {})

    batch_size, ai_tasks, winner = await CombatCollector(data).collect_actions(
        "c1",
        CollectorSignalDTO(session_id="c1", char_id=1, signal_type="check_timeout", move_id="m1"),
    )

    assert batch_size == 0
    assert ai_tasks == []
    assert winner is None
    assert data.calls == ["get_battle_meta"]


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

    assert ai_tasks[0].bot_id == "2"
    assert ai_tasks[0].missing_targets == ["1"]


@pytest.mark.unit
async def test_collector_finds_string_id_ai_missing_targets() -> None:
    meta = BattleMeta(
        active=1,
        step_counter=0,
        active_actors_count=2,
        teams={"a": ["1"], "b": ["goblin_1"]},
        actors_info={"1": "player", "goblin_1": "ai"},
        battle_type="arena",
        location_id="arena",
    )
    data = FakeDataService(meta, {"goblin_1": {"exchange": {}}}, {"goblin_1": ["1"]})

    _, ai_tasks, _ = await CombatCollector(data).collect_actions("c1")

    assert ai_tasks[0].bot_id == "goblin_1"
    assert ai_tasks[0].missing_targets == ["1"]


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
    assert ctx.pending_target_returns == [{"source_id": "1", "target_id": "2"}]
    assert "2" in ctx.pending_dead_actors
    assert ctx.meta.step_counter == 1
    assert ctx.actors["1"].meta.exchange_counter == 1
    assert ctx.actors["2"].meta.exchange_counter == 1
    assert [entry["type"] for entry in ctx.pending_logs] == ["LOG"]
    assert ctx.pending_logs[0]["kind"] == "death"
    assert ctx.pending_logs[0]["result"]["effects"][0]["effect_id"] == "death"


@pytest.mark.unit
async def test_executor_handles_string_actor_id_target_returns() -> None:
    meta = BattleMeta(
        active=1,
        step_counter=0,
        active_actors_count=2,
        teams={"a": ["1"], "b": ["goblin_1"]},
        actors_info={"1": "player", "goblin_1": "ai"},
        battle_type="arena",
        location_id="arena",
    )
    ctx = BattleContext(
        session_id="c1",
        meta=meta,
        actors={"1": actor(1, "a"), "goblin_1": actor("goblin_1", "b", hp=1)},
    )
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id="goblin_1"),
        ),
        is_forced=True,
    )

    processed = await CombatExecutor().process_batch(ctx, [action])

    assert processed == ["m1"]
    assert ctx.pending_target_returns == [{"source_id": "1", "target_id": "goblin_1"}]
    assert "goblin_1" in ctx.pending_dead_actors
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

    assert [entry["type"] for entry in ctx.pending_logs] == ["LOG"]
    assert ctx.pending_logs[0]["source"]["name"] == "A1"
    assert ctx.pending_logs[0]["target"]["name"] == "A2"
    assert ctx.pending_logs[0]["outcome"] == "hit"
    assert ctx.pending_logs[0]["global_turn"] == 1
    assert ctx.pending_logs[0]["resources"] == [
        {"actor_id": "2", "resource": "hp", "before": 100, "after": 93, "max": 100, "delta": -7, "label": "HP 93/100"}
    ]
    assert ctx.pending_logs[0]["result"]["resources"] == ctx.pending_logs[0]["resources"]
    assert ctx.pending_logs[0]["text"] == "A1 атакует A2, нанося 7 урона."
    assert "damage_final" not in ctx.pending_logs[0]
    assert "chain_events" not in ctx.pending_logs[0]


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
        "и попадает, не давая A2 уйти движением, нанося 7 урона."
    )
    assert len(ctx.pending_logs) == 1
    assert ctx.pending_logs[0]["catalog"] == "combat_entries"
    assert ctx.pending_logs[0]["catalog_key"] == "combat.feint.true_strike"
    assert ctx.pending_logs[0]["catalog_event"] == "hit"
    assert ctx.pending_logs[0]["catalog_tooltip"] == "description"
    assert ctx.pending_logs[0]["result"]["resources"] == [
        {"actor_id": "2", "resource": "hp", "before": 100, "after": 93, "max": 100, "delta": -7, "label": "HP 93/100"}
    ]


@pytest.mark.unit
def test_executor_log_entries_use_actual_partner_move_template() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].meta.hp = 96
    source_move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="true_strike"),
    )
    partner_move = CombatMoveDTO(
        move_id="m2",
        char_id=2,
        strategy="exchange",
        payload=ExchangePayload(target_id=1, feint_id="sand_throw"),
    )
    action = CombatActionDTO(action_type="exchange", move=source_move, partner_move=partner_move)
    result_action = CombatExecutor()._action_for_move(
        action,
        partner_move,
        result=InteractionResultDTO(source_id=2, target_id=1),
    )
    result = InteractionResultDTO(source_id=2, target_id=1, damage_final=4, is_hit=True)
    result.events.append(CombatEventDTO(type="CAST", source_id=2, target_id=1, action_id="sand_throw"))
    result.events.append(CombatEventDTO(type="HIT", source_id=2, target_id=1, value=4, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=result_action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog_key"] == "combat.feint.sand_throw"
    assert "бросает песок" in entry["text"]
    assert "выжидает момент" not in entry["text"]


@pytest.mark.unit
def test_executor_log_entries_render_counter_as_counterattack() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].meta.hp = 96
    source_move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="true_strike"),
    )
    action = CombatActionDTO(action_type="exchange", move=source_move)
    result = InteractionResultDTO(source_id=2, target_id=1, damage_final=4, is_hit=True, is_counter=True)
    result.events.append(CombatEventDTO(type="HIT", source_id=2, target_id=1, value=4, resource="hp"))
    result_action = CombatExecutor()._action_for_move(action, source_move, result=result)

    CombatExecutor()._append_result_logs(ctx, result, action=result_action, wave=2)

    entry = ctx.pending_logs[0]
    assert entry["text"] == "A2 отвечает контрударом по A1, нанося 4 урона."
    assert entry["targets"] == [{"id": "1", "name": "A1", "team": "a", "actor_type": "player"}]
    assert entry["flags"]["counter"] is True
    assert "выжидает момент" not in entry["text"]


@pytest.mark.unit
def test_executor_tick_logs_ignore_current_move_feint_template() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].meta.hp = 96
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="true_strike"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=1)
    result.events.append(CombatEventDTO(type="TICK", source_id=1, target_id=1, action_id="dot_bleed", value=-1, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=0)

    entry = ctx.pending_logs[0]
    assert entry["kind"] == "effect_tick"
    assert entry["catalog_key"] == "dot_bleed"
    assert "Кровотечение действует на A1" in entry["text"]
    assert "выжидает момент" not in entry["text"]


@pytest.mark.unit
def test_executor_tick_log_uses_effect_text_even_without_action_id_priority() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].meta.hp = 96
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="sand_throw"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=1)
    result.events.append(CombatEventDTO(type="TICK", source_id=1, target_id=1, action_id="dot_bleed", value=-1, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=0)

    entry = ctx.pending_logs[0]
    assert entry["text"] == "Кровотечение действует на A1."
    assert "бросает песок" not in entry["text"]


@pytest.mark.unit
def test_executor_lethal_tick_log_stays_effect_tick_text() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a", hp=1), "2": actor(2, "b")})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="power_attack"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=1)
    result.events.append(
        CombatEventDTO(type="TICK", source_id=1, target_id=1, action_id="dot_bleed", value=-3, resource="hp")
    )
    result.events.append(CombatEventDTO(type="DEATH", source_id=1, target_id=1, value=0))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=0)

    entry = ctx.pending_logs[0]
    assert entry["kind"] == "effect_tick"
    assert entry["outcome"] == "tick"
    assert entry["text"] == "Кровотечение действует на A1."
    assert entry["flags"]["death"] is True
    assert entry["result"]["effects"][0]["effect_id"] == "death"
    assert "применяет Кровотечение" not in entry["text"]
    assert "тяжелый удар" not in entry["text"]


@pytest.mark.unit
async def test_executor_periodic_tick_before_feint_keeps_effect_text() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="dot_bleed", source_id=2, expire_at_exchange=3, impact={"hp": -2})
    )
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="sand_throw"),
        ),
        is_forced=True,
    )

    await CombatExecutor().process_batch(ctx, [action])

    tick_entry = next(entry for entry in ctx.pending_logs if entry["kind"] == "effect_tick")
    assert tick_entry["text"] == "Кровотечение действует на A1."
    assert tick_entry["catalog_key"] == "dot_bleed"
    assert "бросает песок" not in tick_entry["text"]


@pytest.mark.unit
def test_executor_log_entries_use_ability_catalog_templates() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["2"].meta.hp = 84
    action = CombatActionDTO(
        action_type="instant",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="instant",
            payload=InstantPayload(ability_id="fireball", target_id=2),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=16, is_hit=True)
    result.events.append(CombatEventDTO(type="CAST", source_id=1, target_id=2, action_id="fireball"))
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=16, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog_key"] == "combat.ability.fireball"
    assert entry["template"]["event"] == "hit"
    assert entry["variables"]["ability"] == "Огненный Шар"
    assert entry["text"] == "пламя ударяет в A2, нанося 16 урона."
    assert entry["result"]["resources"] == [
        {"actor_id": "2", "resource": "hp", "before": 100, "after": 84, "max": 100, "delta": -16, "label": "HP 84/100"}
    ]


@pytest.mark.unit
def test_executor_log_entries_use_ability_no_resource_template() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    action = CombatActionDTO(
        action_type="instant",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="instant",
            payload=InstantPayload(ability_id="fireball", target_id=2),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, skip_reason="NO_RESOURCE")

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog_key"] == "combat.ability.fireball"
    assert entry["template"]["event"] == "no_resource"
    assert entry["text"] == "A1 пытается собрать Огненный Шар, но жар гаснет раньше броска."
    assert entry["result"]["resources"] == []


@pytest.mark.unit
def test_executor_log_entries_use_item_template_when_item_delegates_to_ability() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["2"].meta.hp = 90
    action = CombatActionDTO(
        action_type="item",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="item",
            payload=InstantPayload(item_id="fire_grenade", target_id=2),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=10, is_hit=True)
    result.events.append(CombatEventDTO(type="CAST", source_id=1, target_id=2, action_id="fireball"))
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=10, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog_key"] == "combat.item.fire_grenade"
    assert entry["variables"]["item"] == "Огненная граната"
    assert entry["text"] == "огонь накрывает A2, нанося 10 урона."


@pytest.mark.unit
def test_executor_log_entries_use_area_contract_for_multi_target_actions() -> None:
    ctx = BattleContext(
        session_id="c1",
        meta=battle_meta(),
        actors={"1": actor(1, "a"), "2": actor(2, "b"), "3": actor(3, "b")},
    )
    ctx.actors["2"].meta.hp = 91
    action = CombatActionDTO(
        action_type="instant",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="instant",
            payload=InstantPayload(ability_id="fireball", target_id=[2, 3]),
            targets=[2, 3],
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=9, is_hit=True)
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=9, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["kind"] == "ability_area_result"
    assert entry["template"]["event"] == "area_result"
    assert entry["variables"]["targets_count"] == 2
    assert [target["id"] for target in entry["targets"]] == ["2", "3"]
    assert entry["text"] == "A1 бросает Огненный Шар, пламя расходится по 2 целям, нанося 9 урона."
    assert entry["result"]["resources"][0]["delta"] == -9


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

    assert len(ctx.pending_logs) == 1
    assert ctx.pending_logs[0]["text"] == "A1 накладывает Кровотечение на A2."
    assert ctx.pending_logs[0]["kind"] == "effect_apply"
    assert ctx.pending_logs[0]["catalog"] == "effects"
    assert ctx.pending_logs[0]["catalog_key"] == "dot_bleed"
    assert ctx.pending_logs[0]["catalog_tooltip"] == "description"
    assert ctx.pending_logs[0]["result"]["effects"][0]["effect_id"] == "dot_bleed"


@pytest.mark.unit
def test_executor_hit_with_effect_event_keeps_attack_template() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].loadout.layout["main_hand"] = "skill_swords"
    ctx.actors["2"].meta.hp = 97
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=3, is_hit=True)
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=3, resource="hp"))
    result.events.append(CombatEventDTO(type="APPLY_EFFECT", source_id=1, target_id=2, action_id="dot_bleed"))
    result.applied_effects.append({"id": "dot_bleed"})

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog_key"] == "combat.exchange.basic"
    assert "применяет Кровотечение" not in entry["text"]
    assert "swords" in entry["text"]


@pytest.mark.unit
def test_executor_deduplicates_merged_bleed_trigger_suffixes() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["2"].meta.hp = 96
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="true_strike"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=4, is_hit=True, is_crit=True)
    result.fired_triggers.extend(["weapon_serrated_bleed_crit", "weapon_serrated_bleed_hit"])
    result.applied_effects.append({"id": "dot_bleed"})
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=4, resource="hp"))
    result.events.append(CombatEventDTO(type="APPLY_EFFECT", source_id=1, target_id=2, action_id="dot_bleed"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["text"].count("открывает кровотечение") == 1
    assert entry["text"] == (
        "A1 выжидает момент и ведет удар по открытой линии A2, "
        "и точно пробивает защиту A2, нанося 4 урона, и открывает кровотечение."
    )


@pytest.mark.unit
def test_bleed_effect_uses_catalog_minimum_without_stacking_base_damage() -> None:
    entry = CombatCatalogIntegrator.get_effect_catalog_entry("dot_bleed")
    assert entry is not None
    assert entry.technical.resource_impact["hp"] == -3

    weak_effect = EffectFactory.create_effect(
        config=entry.technical,
        params={},
        source_id=1,
        current_exchange=0,
        damage_ref=2,
    )
    strong_effect = EffectFactory.create_effect(
        config=entry.technical,
        params={},
        source_id=1,
        current_exchange=0,
        damage_ref=20,
    )

    assert weak_effect.impact == {"hp": -3}
    assert strong_effect.impact == {"hp": -6}


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
    meta_update = manager.commit_kwargs["kwargs"]["meta_update"]
    assert meta_update["step_counter"] == 3
    assert isinstance(meta_update["last_activity_at"], int)


@pytest.mark.unit
def test_ai_processor_generates_exchange_payload() -> None:
    payload = AiProcessor().decide_exchange(actor(2, "b"), actor(1, "a"))

    assert payload["action"] == "attack"
    assert payload["target_id"] == "1"


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
def test_ability_service_applies_feint_modifier_applications_and_triggers() -> None:
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
    assert ctx.trigger_activations["true_strike"][0].source == "feint"
    assert ctx.trigger_activations["true_strike"][0].source_id == "true_strike"
    damage_mult = source.raw.modifiers["damage_mult"]
    source_id = next(iter(damage_mult["temp"]))
    assert damage_mult["base"] == 1.0
    assert damage_mult["temp"][source_id] == "*0.8"
    assert source_id.startswith(f"feint:{source.statuses.abilities[0].uid}:true_strike:damage_mult")
    assert source.statuses.abilities[0].modified_sources == {"damage_mult": [source_id]}
    assert source.statuses.abilities[0].ability_id == "true_strike"
    assert ctx.result.events[0].type == "CAST"


@pytest.mark.unit
def test_ability_service_applies_weapon_technique_ignore_miss_and_tier_bonus() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.weapon_tiers = {"main_hand": 2}
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="measured_strike"),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.flags.force.hit is True
    assert ctx.mods.weapon_technique_bonus_damage == 6
    bonus = source.raw.modifiers["physical_damage_bonus"]
    source_id = next(iter(bonus["temp"]))
    assert bonus["temp"][source_id] == "+6"
    assert source_id.startswith(f"feint:{source.statuses.abilities[0].uid}:measured_strike")


@pytest.mark.unit
def test_ability_service_applies_press_defense_without_forcing_accuracy() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="press_defense"),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.flags.force.hit is False
    assert ctx.flags.force.hit_evasion is True
    assert ctx.flags.restriction.ignore_parry is True
    assert ctx.flags.restriction.ignore_block is True


@pytest.mark.unit
def test_ability_service_applies_cheap_tactical_modifier_to_target_defense() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="weapon_bind"),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    parry = target.raw.modifiers["parry"]
    source_id = next(iter(parry["temp"]))
    assert parry["temp"][source_id] == "*0.75"
    assert source_id.startswith(f"feint:{source.statuses.abilities[0].uid}:weapon_bind")


@pytest.mark.unit
def test_loaded_crit_boosts_critical_damage_without_forcing_crit() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats()
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="loaded_crit"),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.override_damage = (20, 20)

    AbilityService().pre_process(ctx, move, source, target)
    assert ctx.flags.force.crit is False
    assert ctx.flags.formula.crit_damage_boost is True
    assert ctx.mods.weapon_effect_value == 2.0

    ctx.flags.force.crit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.result.is_crit is True
    assert ctx.result.damage_final == 40


@pytest.mark.unit
def test_ability_service_applies_preparation_effect_to_source() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="counter_parry"),
    )
    ctx = PipelineContextDTO()

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    service.post_process(ctx, source, target, move)

    assert [effect.effect_id for effect in source.statuses.effects] == ["prep_counter_on_parry"]
    assert ctx.result.applied_effects[0]["target_id"] == source.char_id


@pytest.mark.unit
def test_prepared_parry_counter_consumes_buff_and_forces_counter() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats({"counter_attack_chance": 0.0, "counter_attack_cap": 0.0})
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_counter_on_parry", source_id=2, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_parried is True
    assert ctx.result.chain_events.trigger_counter_attack is True
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_counter_on_parry"
    assert ctx.result.effect_facts[-1].tags == ["prepared_reaction", "parry"]


@pytest.mark.unit
def test_dodge_counter_preparation_does_not_trigger_on_parry() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats({"counter_attack_chance": 0.0, "counter_attack_cap": 0.0})
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_counter_on_dodge", source_id=2, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_parried is True
    assert ctx.result.chain_events.trigger_counter_attack is False
    assert [effect.effect_id for effect in target.statuses.effects] == ["prep_counter_on_dodge"]


@pytest.mark.unit
def test_glancing_step_reduces_next_incoming_hit_and_consumes_buff() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats()
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_glancing_dodge", source_id=2, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.override_damage = (20, 20)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_hit is True
    assert ctx.result.damage_final == 10
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_glancing_dodge"


@pytest.mark.unit
def test_brace_guard_reduces_next_incoming_hit_and_consumes_buff() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats()
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_brace_guard", source_id=2, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.override_damage = (20, 20)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_hit is True
    assert ctx.result.damage_final == 15
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_brace_guard"


@pytest.mark.unit
def test_parry_riposte_allows_boosted_counter_on_next_parry(monkeypatch: pytest.MonkeyPatch) -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats({"counter_attack_chance": 0.0, "counter_attack_cap": 0.0})
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_parry_riposte", source_id=2, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    checked_chances: list[float] = []

    def fake_check_chance(chance: float) -> bool:
        checked_chances.append(chance)
        return True

    monkeypatch.setattr(MathCore, "check_chance", fake_check_chance)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert checked_chances == [0.2]
    assert ctx.result.is_parried is True
    assert ctx.result.chain_events.trigger_counter_attack is True
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_parry_riposte"


@pytest.mark.unit
def test_counter_window_uses_counter_cap_on_next_dodge(monkeypatch: pytest.MonkeyPatch) -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats({"counter_attack_chance": 0.0, "counter_attack_cap": 0.5})
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_counter_cap_on_dodge", source_id=2, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    checked_chances: list[float] = []

    def fake_check_chance(chance: float) -> bool:
        checked_chances.append(chance)
        return True

    monkeypatch.setattr(MathCore, "check_chance", fake_check_chance)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    ctx.flags.force.dodge = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert checked_chances == [0.5]
    assert ctx.result.chain_events.trigger_counter_attack is True
    assert target.statuses.effects == []


@pytest.mark.unit
def test_armor_slip_ignores_armor_without_forcing_hit() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats({"armor": 12.0})
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="armor_slip"),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.override_damage = (20, 20)

    AbilityService().pre_process(ctx, move, source, target)
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.flags.force.hit is False
    assert ctx.flags.formula.ignore_armor is True
    assert ctx.result.is_hit is True
    assert ctx.result.damage_final == 20


@pytest.mark.unit
def test_spiked_guard_reflects_on_block_without_consuming_buff() -> None:
    source = actor(1, "a", hp=100)
    target = actor(2, "b", hp=100)
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats()
    target.statuses.effects.append(
        ActiveEffectDTO(
            uid="fx1",
            effect_id="spiked_guard",
            source_id=2,
            expire_at_exchange=999,
            params={"reflect_damage": 7},
        )
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.block = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)
    MechanicsService().apply_interaction_result(ctx, source, target, ctx.result)

    assert ctx.result.is_blocked is True
    assert ctx.result.reflected_damage == 7
    assert source.meta.hp == 93
    assert [effect.effect_id for effect in target.statuses.effects] == ["spiked_guard"]


@pytest.mark.unit
def test_executor_log_merges_prepared_reaction_into_defender_outcome() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, is_parried=True)
    result.effect_facts.append(
        CombatEffectFactDTO(
            actor_id=2,
            owner="target",
            effect_id="prep_counter_on_parry",
            action="expire",
            tags=["prepared_reaction", "parry"],
        )
    )

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    assert "переводит парирование в контратаку" in ctx.pending_logs[0]["text"]


@pytest.mark.unit
def test_executor_log_uses_weapon_technique_render_context_variables() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].loadout.layout["main_hand"] = "skill_swords"
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="measured_strike"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=12, is_hit=True)
    result.damage_trace = CombatDamageTraceDTO(
        raw=12,
        final=12,
        min=12,
        max=12,
        details={"weapon_technique_bonus_damage": 6},
    )
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=12, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["variables"]["bonus_damage"] == 6
    assert entry["variables"]["weapon_attack_form"]
    assert "добавляя 6 урона" in entry["text"]


@pytest.mark.unit
def test_ability_service_cleans_feint_modifier_application_sources() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="true_strike"),
    )
    ctx = PipelineContextDTO()

    service = AbilityService()
    service.pre_process(ctx, move, source, target)

    service.post_process(ctx, source, target, move)

    assert source.raw.modifiers["damage_mult"]["temp"] == {}
    assert source.statuses.abilities == []


@pytest.mark.unit
def test_ability_service_applies_effect_modifier_applications_with_duration_cleanup() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="instant", payload=InstantPayload(ability_id="stone_skin"))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.result.applied_effects.append({"id": "buff_armor", "target_id": target.char_id, "params": {"duration": 3}})

    AbilityService().post_process(ctx, source, target, move)

    effect = target.statuses.effects[0]
    source_id = effect.modified_sources["armor"][0]
    assert target.raw.modifiers["armor"]["temp"][source_id] == "+1"
    assert source_id.startswith(f"effect:{effect.uid}:buff_armor:armor_add")

    target.meta.exchange_counter = effect.expire_at_exchange + 1
    AbilityService._cleanup_expired_effects_pre_calc(target)

    assert target.raw.modifiers["armor"]["temp"] == {}
    assert target.statuses.effects == []


@pytest.mark.unit
def test_resolver_records_source_aware_trigger_facts() -> None:
    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)
    activate_trigger(ctx, "accuracy.true_strike", source="feint", source_id="true_strike")

    CombatResolver._resolve_triggers(ctx, result, "ON_ACCURACY_CHECK")

    assert result.fired_triggers == ["true_strike"]
    assert result.trigger_facts[0].trigger_id == "true_strike"
    assert result.trigger_facts[0].source == "feint"
    assert result.trigger_facts[0].source_id == "true_strike"
    assert result.trigger_facts[0].event == "ON_ACCURACY_CHECK"
    assert "anti_evasion" in result.trigger_facts[0].tags


@pytest.mark.unit
def test_resolver_skips_trigger_sources_not_allowed_by_catalog() -> None:
    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)
    activate_trigger(ctx, "accuracy.true_strike", source="style", source_id="skill_one_handed")

    CombatResolver._resolve_triggers(ctx, result, "ON_ACCURACY_CHECK")

    assert result.fired_triggers == []
    assert result.trigger_facts == []


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
def test_session_integration_recovers_feint_arsenal_from_loadout() -> None:
    snapshot = CombatSessionIntegration(None)._build_snapshot(
        "1",
        "team_1",
        {"hp": 10, "max_hp": 10, "en": 0, "max_en": 0, "tokens": {"hit": 2}, "feints": {}},
        {},
        {"known_feints": ["true_strike"]},
        {"name": "a", "type": "player"},
        {"abilities": [], "effects": []},
        {},
        {},
    )

    assert snapshot.meta.feints.arsenal == ["true_strike"]


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
async def test_result_support_task_payload_captures_actor_refs_and_analytics_slice() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats({"accuracy": 0.8, "crit_chance": 0.2, "armor_penetration": 0.1}, {"skill_parrying": 0.3})
    target.stats = stats({"evasion": 0.4, "parry": 0.5, "block": 0.6, "armor": 7.0}, {"skill_parrying": 0.2})
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    result = InteractionResultDTO(source_id=1, target_id=2, is_hit=True, damage_final=6)
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )

    payload = CombatResultSupportTaskDTO.from_context(
        ctx=ctx,
        result=result,
        action=action,
        wave=3,
        seq=5,
        timestamp=10.0,
    )
    data_service = CapturingSupportDataService()

    await CombatResultSupportTask().process(data_service=data_service, payload=payload)

    assert payload.session_id == "c1"
    assert payload.global_turn == 1
    assert payload.actors["1"].name == "A1"
    assert payload.actors["2"].taxonomy == "humanoid"
    assert payload.stat_slice["s"]["acc"] == 0.8
    assert payload.stat_slice["d"]["arm"] == 7.0
    assert data_service.analytics[0][0] == "c1"
    assert data_service.analytics[0][1]["seq"] == 5
    assert data_service.analytics[0][1]["t"] == 1
    assert data_service.analytics[0][1]["w"] == 3
    assert data_service.analytics[0][1]["st"] == payload.stat_slice


@pytest.mark.unit
async def test_result_support_payload_is_enqueued_as_second_task() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    result = InteractionResultDTO(source_id=1, target_id=2, is_hit=True, damage_final=6)
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )

    CombatExecutor()._append_result_support_payload(ctx, result, action=action, wave=2)
    queue = CapturingArqQueue()

    await _enqueue_result_support_tasks({"redis": queue}, ctx)

    assert queue.jobs == [("combat_result_support_task", ctx.pending_result_support_tasks[0])]
    assert queue.jobs[0][1]["session_id"] == "c1"
    assert queue.jobs[0][1]["seq"] == 0
    assert queue.jobs[0][1]["wave"] == 2


@pytest.mark.unit
async def test_chat_publish_failure_does_not_block_committed_combat_path() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.pending_logs.append(
        {
            "id": "1:1:0",
            "global_turn": 1,
            "wave": 1,
            "text": "A1 атакует A2.",
            "template": {"text": "A1 атакует A2."},
        }
    )

    await _publish_combat_logs_to_chat({"redis_client_internal": FailingChatRedis()}, ctx)


@pytest.mark.unit
async def test_start_announcement_publishes_once_from_collector_context() -> None:
    redis = CapturingChatRedis()
    data_service = AnnouncementDataService()

    await publish_combat_start_announcement({"redis_client_internal": redis}, data_service, "combat-1")
    await publish_combat_start_announcement({"redis_client_internal": redis}, data_service, "combat-1")

    assert len(redis.xadds) == 1
    encoded = str(redis.xadds[0])
    assert "chat.combat_log_message" in encoded
    assert "БОЙ НАЧАЛСЯ" in encoded
    assert "Бой начался: Команда 1: Hero[42/100] против Команда 2: Wolf[0/60]." in encoded


@pytest.mark.unit
async def test_final_announcement_uses_finalization_snapshot() -> None:
    redis = CapturingChatRedis()
    finalization = {
        "combat_id": "combat-1",
        "winner_team": "team_1",
        "participant_char_ids": [1],
        "teams": {"team_1": ["1"], "team_2": ["wolf_1"]},
        "actors": {
            "1": {"actor_id": "1", "name": "Hero", "vitals_final": {"hp": 42, "max_hp": 100}},
            "wolf_1": {"actor_id": "wolf_1", "name": "Wolf", "vitals_final": {"hp": 0, "max_hp": 60}},
        },
        "report": {"last_turn": 12},
    }

    await publish_combat_final_announcement({"redis_client_internal": redis}, finalization)

    assert len(redis.xadds) == 1
    encoded = str(redis.xadds[0])
    assert "БОЙ ЗАВЕРШЕН" in encoded
    assert "Бой завершен на ходу 12. Победила Команда 1: Hero[42/100]." in encoded
    assert "Участники: Команда 1: Hero[42/100]; Команда 2: Wolf[0/60]." in encoded


@pytest.mark.unit
def test_mechanics_applies_defender_tokens_from_resolver_result() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    result = InteractionResultDTO(source_id=1, target_id=2, tokens_awarded_defender={"tempo": 1, "parry": 1})

    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, result)

    assert source.meta.tokens == {}
    assert target.meta.tokens["tempo"] == 1
    assert target.meta.tokens["parry"] == 1
    assert [fact.model_dump() for fact in result.token_facts] == [
        {
            "actor_id": "2",
            "owner": "target",
            "token": "tempo",
            "amount": 1,
            "before": 0,
            "after": 1,
            "reason": "award",
            "source_action_id": None,
            "source_effect_id": None,
            "source_trigger_id": None,
            "tags": [],
        },
        {
            "actor_id": "2",
            "owner": "target",
            "token": "parry",
            "amount": 1,
            "before": 0,
            "after": 1,
            "reason": "award",
            "source_action_id": None,
            "source_effect_id": None,
            "source_trigger_id": None,
            "tags": [],
        },
    ]


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
    assert [fact.model_dump() for fact in ctx.result.effect_facts] == [
        {
            "actor_id": "1",
            "owner": "self",
            "effect_id": "dot_bleed",
            "action": "tick",
            "value": -2,
            "resource": "hp",
            "duration": None,
            "source_action_id": None,
            "source_effect_id": None,
            "source_trigger_id": None,
            "tags": [],
        }
    ]
    assert [fact.model_dump() for fact in ctx.result.resource_facts] == [
        {
            "actor_id": "1",
            "owner": "self",
            "resource": "hp",
            "reason": "effect_tick",
            "delta": -2,
            "before": 2,
            "after": 0,
            "max": 2,
            "source_action_id": None,
            "source_effect_id": "dot_bleed",
            "source_trigger_id": None,
            "tags": ["dot_bleed"],
        }
    ]
    assert [fact.model_dump() for fact in ctx.result.death_facts] == [
        {
            "actor_id": "1",
            "owner": "self",
            "reason": "effect_tick",
            "source_action_id": None,
            "source_effect_id": None,
            "source_trigger_id": None,
            "tags": [],
        }
    ]


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
    assert any(
        entry["kind"] == "effect_tick"
        and entry["template"]["key"] == "dot_bleed"
        and entry["result"]["resources"] == [
            {"actor_id": "1", "resource": "hp", "before": 100, "after": 98, "max": 100, "delta": -2, "label": "HP 98/100"}
        ]
        for entry in ctx.pending_logs
    )


@pytest.mark.unit
async def test_crit_bleed_trigger_is_cancelled_when_attack_is_parried(monkeypatch: pytest.MonkeyPatch) -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout.update({"main_hand": "skill_swords", "main_hand_trigger": "crit.weapon_serrated_bleed_crit"})
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
    assert ctx.trigger_activations["style_dual_extra"][0].source == "style"
    assert ctx.trigger_activations["style_dual_extra"][0].source_id == "skill_dual_wield"
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
def test_shield_reflect_absorbs_percent_plus_shield_power(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.state.partial_absorb_reflect = True
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = CombatResolver._step_calculate_damage(
        stats({"main_hand_damage_base": 20.0, "main_hand_damage_spread": 0.0}),
        stats(
            {
                "shield_guard_power": 6.0,
                "shield_absorb_ratio": 0.40,
                "shield_reflect_ratio": 0.50,
            },
            {"skill_shield_mastery": 0.5},
        ),
        ctx,
        result,
    )

    assert damage == pytest.approx(4.0)
    assert result.damage_final == 4
    assert result.reflected_damage == 8
    assert result.damage_trace is not None
    assert result.damage_trace.details["shield_absorb"] == pytest.approx(16.0)
    assert result.damage_trace.details["shield_absorb_ratio"] == pytest.approx(0.5)
    assert result.damage_trace.details["shield_guard_power"] == pytest.approx(6.0)


@pytest.mark.unit
def test_shield_reflect_absorb_is_capped_by_incoming_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.state.partial_absorb_reflect = True
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = CombatResolver._step_calculate_damage(
        stats({"main_hand_damage_base": 5.0, "main_hand_damage_spread": 0.0}),
        stats({"shield_guard_power": 100.0}),
        ctx,
        result,
    )

    assert damage == 0.0
    assert result.damage_final == 0
    assert result.reflected_damage == 5


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
