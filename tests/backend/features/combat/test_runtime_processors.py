from __future__ import annotations

import inspect
import json
from types import SimpleNamespace
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
    CombatDeathFactDTO,
    CombatEffectFactDTO,
    CombatEventDTO,
    CombatMoveDTO,
    CombatPipelineMutationFactDTO,
    CombatResourceFactDTO,
    CombatStatusApplicationDTO,
    CombatTriggerAttemptDTO,
    CombatTriggerFactDTO,
    ExchangePayload,
    FeintHandDTO,
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
from src.backend.features.combat.runtime.engine.modifier_application_service import ModifierApplicationService
from src.backend.features.combat.runtime.engine.pipeline import CombatPipeline
from src.backend.features.combat.runtime.engine.ranged_position import RangedPositionService
from src.backend.features.combat.runtime.engine.resolver import CombatResolver
from src.backend.features.combat.runtime.engine.resolver.steps import (
    accuracy_step,
    block_step,
    counter_check_step,
    crit_step,
    evasion_step,
    parry_step,
    ranged_position_defense_step,
)
from src.backend.features.combat.runtime.engine.resolver.steps.damage import damage_step
from src.backend.features.combat.runtime.engine.resolver.support import (
    offensive_lookup,
    token_awarder,
    trigger_activator,
)
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine
from src.backend.features.combat.runtime.engine.target_resolver import TargetResolver
from src.backend.features.combat.runtime.engine.trigger_activation import activate_trigger
from src.backend.features.combat.runtime.processors import AiProcessor, CombatCollector, CombatExecutor
from src.backend.features.combat.runtime.processors.chaos_service import ANCHOR_FORCE_TEAM, ChaosService
from src.backend.features.combat.runtime.support import CombatResultSupportTask, CombatResultSupportTaskDTO
from src.backend.features.combat.workers.tasks import executor_task
from src.backend.features.combat.workers.tasks.chaos_task import chaos_check_task
from src.backend.features.combat.workers.tasks.chat_announcements import (
    publish_combat_final_announcement,
    publish_combat_start_announcement,
)
from src.backend.features.combat.workers.tasks.executor_task import _enqueue_result_support_tasks
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


class FakeDataService:
    def __init__(
        self,
        meta: BattleMeta | None,
        moves: dict[str, Any],
        targets: dict[str, list[int | str]],
        *,
        action_queue_size: int = 0,
    ) -> None:
        self.meta = meta
        self.moves = moves
        self.targets = targets
        self.action_queue_size = action_queue_size
        self.transferred: list[CombatActionDTO] = []
        self.calls: list[str] = []

    async def get_action_queue_size(self, session_id: str) -> int:
        self.calls.append("get_action_queue_size")
        return self.action_queue_size

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
        self.action_queue_size += len(actions)


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


class FakeChaosTaskDataService(FakeCombatSessionsForChaos):
    def __init__(
        self,
        *,
        battle_type: str = "arena",
        actors_info: dict[str, str] | None = None,
        started_at: int | None = 1,
    ) -> None:
        super().__init__(battle_type=battle_type, actors_info=actors_info)
        self.started_at = started_at

    async def get_battle_meta(self, session_id: str) -> BattleMeta:
        return battle_meta().model_copy(update={"last_activity_at": 1, "started_at": self.started_at})


class FakeAnchorSnapshotCache:
    async def get_snapshot(self, variant_id: str) -> dict[str, Any] | None:
        return {
            "meta": {"name": "Проекция Западной Гравитации", "actor_type": "monster", "archetype": "mythic"},
            "combat": {
                "skills": {"skill_polearms": 1.0},
                "loadout": {"layout": {"main_hand": "skill_polearms"}, "known_abilities": []},
                "math_model": {
                    "attributes": {},
                    "modifiers": {"main_hand_damage_base": {"base": 140, "source": {}, "temp": {}}},
                },
            },
            "status": {"hp": {"cur": 2500, "max": 2500}, "energy": {"cur": 1000, "max": 1000}},
            "source": {"monster_id": variant_id, "template_id": variant_id},
        }


class CapturingChaosQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, Any, dict[str, Any]]] = []

    async def enqueue_job(self, name: str, payload: Any, **kwargs: Any) -> None:
        self.jobs.append((name, payload, kwargs))


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
        meta=ActorMetaDTO(
            id=actor_id,
            name=f"A{actor_id}",
            type="player",
            team=team,
            hp=hp,
            max_hp=max(hp, 1),
            stamina=100,
            max_stamina=100,
        ),
        raw=ActorRawDTO(modifiers={"main_hand_damage_base": 200, "main_hand_accuracy": 1.0}),
        loadout=ActorLoadoutDTO(layout={"main_hand": "skill_swords"}),
    )


@pytest.mark.unit
def test_feint_service_refill_skips_feints_on_cooldown() -> None:
    meta = ActorMetaDTO(
        id=1,
        name="A1",
        type="player",
        team="a",
        tokens={"hit": 10},
        exchange_counter=1,
        feints=FeintHandDTO(
            arsenal=["measured_strike"],
            hand={},
            cooldowns={"measured_strike": 3},
        ),
    )

    FeintService.refill_hand(meta, hand_size=1)

    assert meta.feints.hand == {}
    assert meta.tokens["hit"] == 10

    meta.exchange_counter = 3
    FeintService.refill_hand(meta, hand_size=1)

    assert set(meta.feints.hand) == {"measured_strike"}


def beast_actor(actor_id: int | str, team: str, hp: int = 100) -> ActorSnapshot:
    snapshot = actor(actor_id, team, hp=hp)
    snapshot.meta.type = "monster"
    snapshot.meta.archetype = "beast"
    snapshot.loadout.layout["main_hand"] = "skill_fencing"
    snapshot.loadout.combat_surfaces = {
        "main_hand": {
            "slot": "main_hand",
            "delivery": "natural",
            "surface": "fangs",
            "tags": ["natural_weapon", "fangs", "claws", "rat"],
            "item_id": "rat_bite_claws",
            "base_id": "rat_bite_claws",
            "skill_key": "skill_fencing",
        }
    }
    return snapshot


def stats(mods: dict[str, float] | None = None, skills: dict[str, float] | None = None) -> ActorStats:
    return ActorStats(
        mods=CombatModifiersDTO(**(mods or {})),
        skills=CombatSkillsDTO(**(skills or {})),
    )


@pytest.mark.unit
def test_queued_effect_resistance_can_prevent_dot_application(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.99, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    source = actor(1, "a")
    target = actor(2, "b")
    target.stats = stats({"poison_resistance": 1.0})
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.result.is_hit = True
    ctx.result.damage_final = 10
    ctx.result.applied_effects.append(
        {"id": "dot_poison", "target_id": target.char_id, "source_trigger_id": "poison_arrow"}
    )

    AbilityService().post_process(
        ctx,
        source,
        target,
        CombatMoveDTO(
            move_id="m1",
            char_id=source.char_id,
            strategy="exchange",
            payload=ExchangePayload(target_id=target.char_id),
        ),
    )

    assert captured_chances == [pytest.approx(0.05)]
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "dot_poison"
    assert ctx.result.effect_facts[-1].action == "resist"
    assert ctx.result.effect_facts[-1].source_trigger_id == "poison_arrow"


@pytest.mark.unit
def test_queued_effect_resistance_uses_source_and_param_apply_bonus(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.25, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    source = actor(1, "a")
    source.stats = stats({"control_chance_bonus": 0.2})
    target = actor(2, "b")
    target.stats = stats({"poison_resistance": 0.7})
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.result.is_hit = True
    ctx.result.damage_final = 10
    ctx.result.applied_effects.append(
        {"id": "dot_poison", "target_id": target.char_id, "params": {"apply_bonus": 0.1}}
    )

    AbilityService().post_process(
        ctx,
        source,
        target,
        CombatMoveDTO(
            move_id="m1",
            char_id=source.char_id,
            strategy="exchange",
            payload=ExchangePayload(target_id=target.char_id),
        ),
    )

    assert captured_chances == [pytest.approx(0.6)]
    assert [effect.effect_id for effect in target.statuses.effects] == ["dot_poison"]
    assert ctx.result.effect_facts[-1].effect_id == "dot_poison"
    assert ctx.result.effect_facts[-1].action == "apply"


@pytest.mark.unit
async def test_chaos_service_spawns_anchor_projection_from_bootstrap_snapshot() -> None:
    sessions = FakeCombatSessionsForChaos(battle_type="arena")

    spawned = await ChaosService(
        sessions,
        anchor_snapshots=FakeAnchorSnapshotCache(),
    ).spawn_cleaner("combat-1")  # type: ignore[arg-type]

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
async def test_chaos_task_enqueues_collector_after_anchor_spawn(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.backend.features.combat.workers.tasks.chaos_task.time.time",
        lambda: 600 + 2,
    )
    data_service = FakeChaosTaskDataService(battle_type="arena")
    queue = CapturingChaosQueue()

    await chaos_check_task({"combat_data_service": data_service, "redis": queue}, "combat-1")

    assert data_service.hot_joined is not None
    assert queue.jobs[0][0] == "combat_collector_task"
    assert queue.jobs[0][1]["signal_type"] == "heartbeat"
    assert queue.jobs[0][1]["move_id"] == "chaos_spawn"
    assert queue.jobs[1][0] == "chaos_check_task"
    assert queue.jobs[1][2].get("_defer_until") is not None


@pytest.mark.unit
async def test_chaos_task_does_not_spawn_before_combat_started(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.backend.features.combat.workers.tasks.chaos_task.time.time",
        lambda: 600 + 2,
    )
    data_service = FakeChaosTaskDataService(battle_type="arena", started_at=None)
    queue = CapturingChaosQueue()

    await chaos_check_task({"combat_data_service": data_service, "redis": queue}, "combat-1")

    assert data_service.hot_joined is None
    assert [job[0] for job in queue.jobs] == ["chaos_check_task"]
    assert queue.jobs[0][2].get("_defer_until") is not None


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
async def test_collector_dispatches_existing_action_queue_backlog() -> None:
    data = FakeDataService(
        battle_meta(),
        {"1": {"exchange": {}}, "2": {"exchange": {}}},
        {"1": [], "2": []},
        action_queue_size=1,
    )

    batch_size, ai_tasks, winner = await CombatCollector(data).collect_actions("c1")

    assert batch_size > 0
    assert ai_tasks == []
    assert winner is None
    assert data.transferred == []


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
async def test_executor_does_not_return_dead_target_after_forced_exchange(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (None, chance > 0.0)))
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b", hp=1)})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        is_forced=True,
    )

    processed = await CombatExecutor().process_batch(ctx, [action])

    assert processed == ["m1"]
    assert ctx.pending_target_returns == []
    assert "2" in ctx.pending_dead_actors
    assert ctx.meta.step_counter == 1
    assert ctx.actors["1"].meta.exchange_counter == 1
    assert ctx.actors["2"].meta.exchange_counter == 1
    assert [entry["type"] for entry in ctx.pending_logs] == ["LOG"]
    assert ctx.pending_logs[0]["kind"] == "death"
    assert ctx.pending_logs[0]["result"]["effects"][0]["effect_id"] == "death"


@pytest.mark.unit
async def test_executor_handles_string_actor_id_target_returns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (None, chance > 0.0)))
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
    assert ctx.pending_target_returns == []
    assert "goblin_1" in ctx.pending_dead_actors
    assert all("runtime" in entry["tags"] for entry in ctx.pending_logs)


@pytest.mark.unit
async def test_executor_returns_only_living_targets_after_exchange() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b", hp=1000)})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        is_forced=True,
    )

    processed = await CombatExecutor().process_batch(ctx, [action])

    assert processed == ["m1"]
    assert ctx.pending_target_returns == [{"source_id": "1", "target_id": "2"}]
    assert ctx.pending_dead_actors == []


@pytest.mark.unit
async def test_executor_skips_queued_exchange_when_target_is_already_dead() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b", hp=0)})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        is_forced=True,
    )

    processed = await CombatExecutor().process_batch(ctx, [action])

    assert processed == ["m1"]
    assert ctx.meta.step_counter == 0
    assert ctx.actors["1"].meta.exchange_counter == 0
    assert ctx.actors["2"].meta.exchange_counter == 0
    assert ctx.pending_target_returns == []
    assert ctx.pending_logs[0]["kind"] == "stale_action"
    assert ctx.pending_logs[0]["reason"] == "target_dead"
    assert "цель уже мертва" in ctx.pending_logs[0]["text"]


@pytest.mark.unit
def test_target_resolver_rejects_dead_direct_target_id() -> None:
    meta = battle_meta().model_copy(update={"dead_actors": [2]})

    assert TargetResolver().resolve(1, 2, meta) == []


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
    assert ctx.pending_logs[0]["catalog"] == "combat_text"
    assert ctx.pending_logs[0]["template"]["key"] == "combat.exchange.skill_swords.main_hand.hit.humanoid_to_humanoid.weapon"
    assert ctx.pending_logs[0]["template"]["text"]
    assert ctx.pending_logs[0]["text"].endswith("нанося 7 урона.")
    assert "damage_final" not in ctx.pending_logs[0]
    assert "chain_events" not in ctx.pending_logs[0]


@pytest.mark.unit
def test_executor_log_entries_include_reflected_shield_damage() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].meta.hp = 88
    ctx.actors["2"].meta.hp = 93
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=7, reflected_damage=12, is_hit=True)
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

    entry = ctx.pending_logs[0]
    assert "Щит A2 возвращает A1 12 урона." in entry["text"]
    assert entry["resources"] == [
        {"actor_id": "2", "resource": "hp", "before": 100, "after": 93, "max": 100, "delta": -7, "label": "HP 93/100"},
        {"actor_id": "1", "resource": "hp", "before": 100, "after": 88, "max": 100, "delta": -12, "label": "HP 88/100"},
    ]
    assert entry["flags"]["reflect"] is True


@pytest.mark.unit
def test_executor_death_log_entries_include_killing_damage() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["2"].meta.hp = 0
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=7, is_hit=True)
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=7, resource="hp"))
    result.events.append(CombatEventDTO(type="DEATH", source_id=1, target_id=2))
    result.death_facts.append(CombatDeathFactDTO(actor_id=2, owner="target", reason="damage"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["kind"] == "death"
    assert entry["outcome"] == "death"
    assert "7 урона" in entry["text"]
    assert entry["variables"]["damage"] == 7
    assert entry["flags"]["death"] is True


@pytest.mark.unit
def test_executor_log_entries_use_dual_wield_proc_text_without_runtime_fallback() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=7, is_hit=True, is_crit=True)
    result.fired_triggers.append("style_dual_cross_cut")
    result.trigger_facts.append(
        CombatTriggerFactDTO(
            trigger_id="style_dual_cross_cut",
            event="ON_CRIT",
            source="style",
            source_id="skill_dual_wield",
            chance=0.25,
            display_policy="separate",
            tags=["style", "dual_wield", "crit", "cross_cut"],
        )
    )

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    assert len(ctx.pending_logs) == 2
    trigger_entry = ctx.pending_logs[1]
    assert trigger_entry["catalog_key"] == "combat.trigger.style.dual_cross_cut.proc.humanoid"
    assert trigger_entry["text"] == "A1 усиливает критический удар перекрестным срезом."
    assert "(F)" not in trigger_entry["text"]


@pytest.mark.unit
def test_executor_log_entries_use_combat_text_for_beast_natural_exchange() -> None:
    source = beast_actor(1, "a")
    target = actor(2, "b")
    target.meta.archetype = "humanoid"
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    ctx.actors["2"].meta.hp = 93
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=7, is_hit=True)
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=7, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["template"]["key"] == "combat.exchange.natural_weapon.fangs.main_hand.hit.beast_to_humanoid.natural"
    assert entry["template"]["text"]
    assert all(forbidden not in entry["text"].casefold() for forbidden in ("клинк", "остри", "доспех"))
    assert "(F)" not in entry["text"]


@pytest.mark.unit
def test_executor_log_entries_use_archery_basic_exchange_text_for_bow_attacks() -> None:
    source = actor(1, "a")
    source.meta.archetype = "humanoid"
    source.loadout.layout["main_hand"] = "skill_archery"
    source.loadout.combat_surfaces = {
        "main_hand": {
            "slot": "main_hand",
            "delivery": "weapon",
            "surface": "bow",
            "tags": ["weapon", "bow", "archery", "ranged", "skill_archery"],
            "item_id": "training_bow",
            "base_id": "training_bow",
            "skill_key": "skill_archery",
        }
    }
    target = actor(2, "b")
    target.meta.archetype = "humanoid"
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=9, is_hit=True)
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=9, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["catalog_key"] == "combat.exchange.skill_archery.main_hand.hit.humanoid_to_humanoid.weapon"
    assert "стрел" in entry["text"].casefold() or "выстрел" in entry["text"].casefold()
    assert "режущ" not in entry["text"].casefold()
    assert "рубящ" not in entry["text"].casefold()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("result", "expected_key"),
    [
        (
            InteractionResultDTO(source_id=1, target_id=2, is_miss=True),
            "combat.exchange.natural_weapon.fangs.main_hand.miss.beast_to_humanoid.natural",
        ),
        (
            InteractionResultDTO(source_id=1, target_id=2, is_dodged=True),
            "combat.exchange.natural_weapon.fangs.main_hand.dodge.beast_to_humanoid.natural",
        ),
        (
            InteractionResultDTO(source_id=1, target_id=2, is_parried=True),
            "combat.exchange.natural_weapon.fangs.main_hand.parry.beast_to_humanoid.natural",
        ),
    ],
)
def test_executor_log_entries_cover_beast_natural_exchange_avoidance(
    result: InteractionResultDTO,
    expected_key: str,
) -> None:
    source = beast_actor(1, "a")
    target = actor(2, "b")
    target.meta.archetype = "humanoid"
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["template"]["key"] == expected_key
    assert entry["catalog_key"] == expected_key
    assert "(F)" not in entry["text"]


@pytest.mark.unit
def test_executor_log_entries_treat_beast_monster_without_surface_as_natural() -> None:
    source = beast_actor(1, "a")
    source.meta.type = "monster"
    source.loadout.combat_surfaces = {}
    target = actor(2, "b")
    target.meta.archetype = "humanoid"
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, is_parried=True)

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["template"]["key"] == "combat.exchange.natural_weapon.default.main_hand.parry.beast_to_humanoid.natural"
    assert entry["catalog_key"] == "combat.exchange.natural_weapon.default.main_hand.parry.beast_to_humanoid.natural"
    assert entry["catalog_tooltip"] == ""
    assert "(F)" not in entry["text"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("result", "expected_key"),
    [
        (
            InteractionResultDTO(source_id=1, target_id=2, is_miss=True),
            "combat.exchange.skill_swords.main_hand.miss.humanoid_to_beast.weapon",
        ),
        (
            InteractionResultDTO(source_id=1, target_id=2, is_dodged=True),
            "combat.exchange.skill_swords.main_hand.dodge.humanoid_to_beast.weapon",
        ),
    ],
)
def test_executor_log_entries_cover_humanoid_weapon_exchange_against_beasts(
    result: InteractionResultDTO,
    expected_key: str,
) -> None:
    source = actor(1, "a")
    source.meta.archetype = "humanoid"
    source.loadout.layout["main_hand"] = "skill_swords"
    target = beast_actor(2, "b")
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["template"]["key"] == expected_key
    assert entry["catalog_key"] == expected_key
    assert "(F)" not in entry["text"]


@pytest.mark.unit
def test_executor_log_entries_use_natural_weapon_template_for_beast_surface_even_with_skill_mapping() -> None:
    source = actor(1, "a")
    source.meta.type = "monster"
    source.meta.archetype = "beast"
    source.loadout.layout["main_hand"] = "skill_fencing"
    source.loadout.combat_surfaces = {
        "main_hand": {
            "slot": "main_hand",
            "delivery": "natural",
            "surface": "fangs",
            "tags": ["natural_weapon", "fangs", "rat"],
            "item_id": "rat_bite_claws",
            "base_id": "rat_bite_claws",
            "skill_key": "skill_fencing",
        }
    }
    target = actor(2, "b")
    target.meta.archetype = "humanoid"
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    ctx.actors["2"].meta.hp = 93
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=7, is_hit=True, is_crit=True)
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=7, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["template"]["key"] == "combat.exchange.natural_weapon.fangs.main_hand.crit.beast_to_humanoid.natural"
    assert "(F)" not in entry["text"]
    assert entry["text"].endswith("7 урона.")


@pytest.mark.unit
def test_combat_log_missing_combat_text_template_uses_runtime_fallback(monkeypatch) -> None:
    monkeypatch.setattr(CombatCatalogIntegrator, "get_combat_text_template", staticmethod(lambda **_kwargs: None), raising=False)
    source = actor(1, "a")
    source.loadout.layout["main_hand"] = "skill_swords"
    target = actor(2, "b")
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=7, is_hit=True)

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["template"]["key"] == "combat_text.runtime_fallback.basic_exchange.hit"
    assert entry["text"].endswith("(F)")
    assert entry["variables"]["target_results"] == "A2 получает 7 урона"


@pytest.mark.unit
def test_combat_trigger_log_missing_combat_text_template_uses_runtime_fallback(monkeypatch) -> None:
    monkeypatch.setattr(CombatCatalogIntegrator, "get_combat_text_template", staticmethod(lambda **_kwargs: None), raising=False)
    source = actor(1, "a")
    source.loadout.layout["main_hand"] = "skill_swords"
    target = actor(2, "b")
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, is_parried=True)
    result.fired_triggers.append("weapon_riposte_on_parry")

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[1]
    assert entry["kind"] == "trigger_proc"
    assert entry["template"]["key"] == "combat_text.runtime_fallback.trigger.parry_proc"
    assert entry["text"].endswith("(F)")


@pytest.mark.unit
def test_combat_riposte_trigger_log_uses_beast_target_template() -> None:
    source = actor(1, "a")
    source.loadout.layout["main_hand"] = "skill_swords"
    target = actor(2, "b")
    target.meta.archetype = "beast"
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, is_parried=True)
    result.fired_triggers.append("weapon_riposte_on_parry")

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[1]
    assert entry["kind"] == "trigger_proc"
    assert entry["template"]["key"] == "combat.trigger.weapon.riposte_on_parry.parry_proc.beast"
    assert "(F)" not in entry["text"]


@pytest.mark.unit
def test_executor_log_entries_render_counter_as_counterattack() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    ctx.actors["1"].meta.hp = 96
    source_move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="future_feint_placeholder"),
    )
    action = CombatActionDTO(action_type="exchange", move=source_move)
    result = InteractionResultDTO(source_id=2, target_id=1, damage_final=4, is_hit=True, is_counter=True)
    result.events.append(CombatEventDTO(type="HIT", source_id=2, target_id=1, value=4, resource="hp"))
    result_action = CombatExecutor()._action_for_move(action, source_move, result=result)

    CombatExecutor()._append_result_logs(ctx, result, action=result_action, wave=2)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["template"]["key"] == "combat.exchange.skill_swords.main_hand.hit.humanoid_to_humanoid.weapon"
    assert entry["text"].endswith("нанося 4 урона.")
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
            payload=ExchangePayload(target_id=2, feint_id="future_feint_placeholder"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=1)
    result.events.append(CombatEventDTO(type="TICK", source_id=1, target_id=1, action_id="dot_bleed", value=-1, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=0)

    entry = ctx.pending_logs[0]
    assert entry["kind"] == "effect_tick"
    assert entry["catalog"] == "combat_text"
    assert entry["catalog_key"] == "combat.effect.dot_bleed.tick.humanoid.hp"
    assert entry["text"] == "Кровотечение терзает A1: -1 hp."
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
            payload=ExchangePayload(target_id=2, feint_id="future_feint_placeholder"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=1)
    result.events.append(CombatEventDTO(type="TICK", source_id=1, target_id=1, action_id="dot_bleed", value=-1, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=0)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["text"] == "Кровотечение терзает A1: -1 hp."
    assert "future_feint_placeholder" not in entry["text"]


@pytest.mark.unit
def test_executor_lethal_tick_log_stays_effect_tick_text() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a", hp=1), "2": actor(2, "b")})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="future_feint_placeholder"),
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
    assert entry["catalog"] == "combat_text"
    assert entry["template"]["key"] == "combat.effect.dot_bleed.tick.humanoid.hp"
    assert entry["text"] == "Кровотечение терзает A1: -3 hp."
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
            payload=ExchangePayload(target_id=2, feint_id="future_feint_placeholder"),
        ),
        is_forced=True,
    )

    await CombatExecutor().process_batch(ctx, [action])

    tick_entry = next(entry for entry in ctx.pending_logs if entry["kind"] == "effect_tick")
    assert tick_entry["text"] == "Кровотечение терзает A1: -2 hp."
    assert tick_entry["catalog_key"] == "combat.effect.dot_bleed.tick.humanoid.hp"
    assert "future_feint_placeholder" not in tick_entry["text"]


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
    assert entry["catalog"] == "combat_text"
    assert entry["catalog_key"] == "combat.ability.fireball.target.hit.humanoid"
    assert entry["template"]["event"] == "hit"
    assert entry["variables"]["ability"] == "Огненный Шар"
    assert entry["text"] == "пламя ударяет в A2"
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
    assert entry["catalog"] == "combat_text"
    assert entry["catalog_key"] == "combat.ability.fireball.no_resource"
    assert entry["template"]["event"] == "no_resource"
    assert entry["text"] == "A1 пытается собрать Огненный Шар, но жар гаснет раньше броска"
    assert entry["result"]["resources"] == []


@pytest.mark.unit
def test_executor_feint_hit_against_beast_uses_combat_text_template() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    target.meta.archetype = "beast"
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="fencing_precise_prick"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=8, is_hit=True)
    result.events.append(CombatEventDTO(type="HIT", source_id=1, target_id=2, value=8, resource="hp"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["template"]["key"] == "combat.feint.fencing_precise_prick.hit.humanoid_to_beast.weapon"
    assert "(F)" not in entry["text"]
    assert entry["text"].endswith("8 урона.")


@pytest.mark.unit
def test_executor_feint_no_resource_uses_feint_template_without_runtime_fallback() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    target.meta.archetype = "beast"
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="dual_cross_slash"),
        ),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, skip_reason="NO_RESOURCE")

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["template"]["key"] == "combat.feint.dual_cross_slash.no_resource.weapon"
    assert "(F)" not in entry["text"]
    assert entry["text"] == "A1 пытается провести Крестовой срез, но темп финта срывается."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("result_kwargs", "expected_outcome", "expected_key", "uses_runtime_fallback"),
    [
        (
            {"damage_final": 16, "is_hit": True, "is_crit": True},
            "crit",
            "combat.ability.fireball.target.crit.humanoid",
            False,
        ),
        ({"is_dodged": True}, "dodge", "combat.ability.fireball.target.dodge.humanoid", False),
        ({"is_parried": True}, "parry", "combat.ability.fireball.target.parry.humanoid", False),
        ({"is_blocked": True}, "block", "combat.ability.fireball.target.block.humanoid", False),
        ({"skip_reason": "CONTROLLED"}, "controlled", "combat_text.runtime_fallback.ability.controlled", True),
        ({}, "cast", "combat.ability.fireball.cast.single", False),
    ],
)
def test_executor_log_entries_use_ability_templates_for_instant_outcomes(
    result_kwargs: dict[str, Any],
    expected_outcome: str,
    expected_key: str,
    uses_runtime_fallback: bool,
) -> None:
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
    result = InteractionResultDTO(source_id=1, target_id=2, **result_kwargs)
    result.events.append(CombatEventDTO(type="CAST", source_id=1, target_id=2, action_id="fireball"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["template"]["key"] == expected_key
    assert entry["template"]["event"] == expected_outcome
    assert entry["outcome"] == expected_outcome
    assert entry["variables"]["ability"] == "Огненный Шар"
    assert entry["text"].endswith("(F)") is uses_runtime_fallback


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
    assert entry["catalog"] == "combat_text"
    assert entry["catalog_key"] == "combat.item.fire_grenade.target.hit.humanoid"
    assert entry["variables"]["item"] == "Огненная граната"
    assert entry["text"] == "A2 получает 10 урона от Огненная граната"


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
    assert entry["catalog"] == "combat_text"
    assert entry["catalog_key"] == "combat.ability.fireball.cast.area"
    assert entry["text"] == "пламя расходится по 2 целям"
    assert entry["result"]["resources"][0]["delta"] == -9


@pytest.mark.unit
async def test_executor_groups_multi_target_ability_logs_into_single_comma_message() -> None:
    ctx = BattleContext(
        session_id="c1",
        meta=battle_meta(),
        actors={"1": actor(1, "a"), "2": actor(2, "b"), "3": actor(3, "b"), "4": actor(4, "b")},
    )
    ctx.actors["2"].meta.hp = 19
    ctx.actors["2"].meta.max_hp = 46
    ctx.actors["3"].meta.hp = 13
    ctx.actors["3"].meta.max_hp = 46
    ctx.actors["4"].meta.hp = 21
    ctx.actors["4"].meta.max_hp = 46
    action = CombatActionDTO(
        action_type="instant",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="instant",
            payload=InstantPayload(ability_id="basic_splinter_strike", target_id=[2, 3, 4]),
            targets=[2, 3, 4],
        ),
    )
    executor = CombatExecutor()
    results = [
        InteractionResultDTO(source_id=1, target_id=2, damage_final=11, is_hit=True),
        InteractionResultDTO(source_id=1, target_id=3, damage_final=10, is_hit=True),
        InteractionResultDTO(source_id=1, target_id=4, damage_final=10, is_hit=True),
    ]
    for result in results:
        result.events.append(
            CombatEventDTO(type="HIT", source_id=1, target_id=result.target_id, value=result.damage_final, resource="hp")
        )

    async def fake_create_task(source, target, move, *, mods=None):  # noqa: ANN001
        return results[int(target.char_id) - 2]

    executor._create_task = fake_create_task  # type: ignore[method-assign]

    await executor._handle_unidirectional(ctx, action)

    area_logs = [entry for entry in ctx.pending_logs if entry["kind"] == "ability_area_result"]
    assert len(area_logs) == 1
    assert area_logs[0]["text"] == (
        "A1 применяет Осколочный удар: "
        "A2 получает 11 урона [HP 8/46], "
        "A3 получает 10 урона [HP 3/46], "
        "A4 получает 10 урона [HP 11/46]."
    )
    assert [resource["actor_id"] for resource in area_logs[0]["result"]["resources"]] == ["2", "3", "4"]


@pytest.mark.unit
def test_executor_log_entries_use_combat_text_for_humanoid_effect_apply() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2)
    result.events.append(CombatEventDTO(type="APPLY_EFFECT", source_id=1, target_id=2, action_id="dot_bleed"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    assert len(ctx.pending_logs) == 1
    assert ctx.pending_logs[0]["text"] == "A2 получает Кровотечение."
    assert ctx.pending_logs[0]["kind"] == "effect_apply"
    assert ctx.pending_logs[0]["catalog"] == "combat_text"
    assert ctx.pending_logs[0]["catalog_key"] == "combat.effect.dot_bleed.apply.humanoid"
    assert ctx.pending_logs[0]["catalog_tooltip"] == ""
    assert ctx.pending_logs[0]["result"]["effects"][0]["effect_id"] == "dot_bleed"


@pytest.mark.unit
def test_executor_effect_resist_log_does_not_use_runtime_fallback_text() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
    )
    result = InteractionResultDTO(source_id=1, target_id=2)
    result.applied_effects.append({"id": "stun", "target_id": 2})
    result.effect_facts.append(CombatEffectFactDTO(actor_id=2, owner="target", effect_id="stun", action="resist"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    assert len(ctx.pending_logs) == 1
    assert ctx.pending_logs[0]["kind"] == "effect_resist"
    assert "(F)" not in ctx.pending_logs[0]["text"]
    assert "не срабатывает" in ctx.pending_logs[0]["text"]


@pytest.mark.unit
def test_executor_basic_ability_hit_log_uses_ability_event_text() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_break_stance", target_id=2),
    )
    action = CombatActionDTO(action_type="instant", move=move)
    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=7, is_hit=True)
    result.events.append(CombatEventDTO(type="CAST", source_id=1, target_id=2, action_id="basic_break_stance"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog_key"] == "combat.ability.basic_break_stance.target.hit.humanoid"
    assert entry["text"] == "A1 ломает устойчивость A2"
    assert "(F)" not in entry["text"]


@pytest.mark.unit
def test_executor_basic_ability_no_resource_log_uses_ability_event_text() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_break_stance", target_id=2),
    )
    action = CombatActionDTO(action_type="instant", move=move)
    result = InteractionResultDTO(source_id=1, target_id=2, skip_reason="NO_RESOURCE")

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog_key"] == "combat.ability.basic_break_stance.no_resource"
    assert entry["text"] == "A1 не удерживает темп для сбития стойки"
    assert "(F)" not in entry["text"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_basic_debuff_strike_logs_hit_text_not_runtime_fallback() -> None:
    source = actor(1, "a")
    source.meta.stamina = 100
    source.meta.tokens.update({"tempo": 3, "hit": 2})
    target = actor(2, "b")
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_break_stance", target_id=2),
    )
    action = CombatActionDTO(action_type="instant", move=move)

    result = await CombatPipeline().calculate(source, target, move)
    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert result.action_facts["outcome"] == "apply"
    assert entry["catalog_key"] == "combat.ability.basic_break_stance.target.hit.humanoid"
    assert entry["text"] == "A1 ломает устойчивость A2"
    assert "(F)" not in entry["text"]


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
    result.effect_facts.append(CombatEffectFactDTO(actor_id=2, owner="target", effect_id="dot_bleed", action="apply"))

    CombatExecutor()._append_result_logs(ctx, result, action=action, wave=1)

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["catalog_key"] == "combat.exchange.skill_swords.main_hand.hit.humanoid_to_humanoid.weapon"
    assert "применяет Кровотечение" not in entry["text"]
    assert len(ctx.pending_logs) == 2
    assert ctx.pending_logs[1]["kind"] == "effect_apply"
    assert "A2" in ctx.pending_logs[1]["text"]
    assert "кровоточ" in ctx.pending_logs[1]["text"]
    assert entry["result"]["effects"][0]["effect_id"] == "dot_bleed"


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
async def test_executor_stun_blocks_dodge_and_expires_after_exchange() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats({"evasion": 1.0, "dodge_cap": 1.0})
    stun_entry = CombatCatalogIntegrator.get_effect_catalog_entry("stun")
    assert stun_entry is not None
    target.statuses.effects.append(
        EffectFactory.create_effect(
            config=stun_entry.technical,
            params={},
            source_id=1,
            current_exchange=0,
            damage_ref=0,
        )
    )
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        is_forced=True,
    )

    await CombatExecutor().process_batch(ctx, [action])

    assert all(entry["outcome"] != "dodge" for entry in ctx.pending_logs)
    assert [effect.effect_id for effect in target.statuses.effects] == []
    assert any(entry["kind"] == "effect_expire" and entry["text"] == "Оглушение A2 проходит." for entry in ctx.pending_logs)


@pytest.mark.unit
async def test_executor_controlled_skip_uses_effect_text_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (None, chance > 0.0)))
    source = actor(1, "a", hp=500)
    target = actor(2, "b", hp=500)
    stun_entry = CombatCatalogIntegrator.get_effect_catalog_entry("stun")
    assert stun_entry is not None
    target.statuses.effects.append(
        EffectFactory.create_effect(
            config=stun_entry.technical,
            params={},
            source_id=1,
            current_exchange=0,
            damage_ref=0,
        )
    )
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        partner_move=CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1)),
    )

    await CombatExecutor().process_batch(ctx, [action])

    controlled_entry = next(entry for entry in ctx.pending_logs if entry.get("outcome") == "controlled")
    assert "(F)" not in controlled_entry["text"]
    assert controlled_entry["text"].startswith("A2 оглушён")
    assert not controlled_entry["text"].startswith("A1 оглушён")
    assert controlled_entry["template"]["key"] == "combat.effect.stun.control_prevent_action.runtime"
    assert "fallback" not in controlled_entry["tags"]


@pytest.mark.unit
async def test_executor_log_ids_are_unique_in_same_wave(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (None, chance > 0.0)))
    ctx = BattleContext(
        session_id="c1",
        meta=battle_meta(),
        actors={"1": actor(1, "a", hp=500), "2": actor(2, "b", hp=500)},
    )
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        partner_move=CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1)),
    )

    await CombatExecutor().process_batch(ctx, [action])

    wave_entries = [entry for entry in ctx.pending_logs if entry.get("wave") == 1 and entry.get("kind") == "exchange"]
    ids = [entry["id"] for entry in wave_entries]
    assert len(ids) >= 2
    assert len(ids) == len(set(ids))


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
async def test_session_integration_round_trips_stamina_state() -> None:
    manager = CapturingCombatManager()
    integration = CombatSessionIntegration(manager)  # type: ignore[arg-type]
    snapshot = integration._build_snapshot(
        "1",
        "a",
        {
            "hp": 50,
            "max_hp": 100,
            "en": 20,
            "max_en": 30,
            "stamina": 37,
            "max_stamina": 80,
            "tokens": {},
            "token_progress": {"blood": 7},
            "ability_cooldowns": {"basic_break_stance": 5},
        },
        {},
        {},
        {"name": "Hero", "type": "player"},
        {},
        {},
        {},
    )

    assert snapshot.meta.stamina == 37
    assert snapshot.meta.max_stamina == 80
    assert snapshot.meta.token_progress == {"blood": 7}
    assert snapshot.meta.ability_cooldowns == {"basic_break_stance": 5}

    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": snapshot})
    snapshot.meta.stamina = 12
    snapshot.meta.token_progress["blood"] = 3
    snapshot.meta.ability_cooldowns["basic_break_stance"] = 4

    await integration.commit_session(ctx, ["m1"])

    updates = manager.commit_kwargs["args"][1]
    assert updates["1"]["state"]["stamina"] == 12
    assert updates["1"]["state"]["max_stamina"] == 80
    assert updates["1"]["state"]["token_progress"] == {"blood": 3}
    assert updates["1"]["state"]["ability_cooldowns"] == {"basic_break_stance": 4}


@pytest.mark.unit
async def test_commit_session_sends_dead_actor_prune_and_alive_counts() -> None:
    manager = CapturingCombatManager()
    integration = CombatSessionIntegration(manager)  # type: ignore[arg-type]
    meta = BattleMeta(
        active=1,
        step_counter=4,
        active_actors_count=3,
        teams={"a": ["1"], "b": ["2", "3"]},
        actors_info={"1": "player", "2": "ai", "3": "ai"},
        battle_type="arena",
        location_id="arena",
    )
    ctx = BattleContext(
        session_id="c1",
        meta=meta,
        actors={"1": actor("1", "a"), "2": actor("2", "b", hp=0), "3": actor("3", "b")},
    )
    ctx.pending_dead_actors = ["2"]

    await integration.commit_session(ctx, ["m1"])

    assert manager.commit_kwargs is not None
    kwargs = manager.commit_kwargs["kwargs"]
    assert kwargs["dead_actor_ids"] == {"2"}
    assert kwargs["dead_actors"] == '["2"]'
    assert kwargs["meta_update"]["alive_counts"] == '{"a": 1, "b": 1}'


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
def test_session_integration_snapshot_preserves_ai_archetype() -> None:
    integration = CombatSessionIntegration(CapturingCombatManager())  # type: ignore[arg-type]

    snapshot = integration._build_snapshot(
        "1",
        "a",
        {"hp": 100, "max_hp": 100},
        {"attributes": {}, "modifiers": {}},
        {},
        {"name": "A1", "type": "monster", "ai_archetype": "tactician"},
        {"abilities": [], "effects": []},
        {},
        {},
    )

    assert snapshot.meta.ai_archetype == "tactician"


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
def test_stats_engine_rounds_fractional_resource_maxima_for_dto_contract() -> None:
    snapshot = actor(1, "a")
    snapshot.raw = ActorRawDTO(
        attributes={
            "perception": {"base": 12.0, "source": {}, "temp": {}},
            "projection": {"base": 9.0, "source": {}, "temp": {}},
            "prediction": {"base": 13.0, "source": {}, "temp": {}},
        },
        modifiers={"stamina_regen": {"base": 1.0, "source": {}, "temp": {}}},
        rules={"attribute_profile": "player"},
    )

    StatsEngine.ensure_stats(snapshot)

    assert snapshot.stats is not None
    assert snapshot.stats.mods.stamina == 26
    assert snapshot.stats.mods.stamina_regen == pytest.approx(3.2091)


@pytest.mark.unit
def test_ability_service_applies_basic_hit_feint_weapon_technique_bonus() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
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
    assert ctx.mods.weapon_technique_bonus_damage == 4
    assert ctx.result.resource_changes["stamina"]["cost"] == "-9"
    bonus = source.raw.modifiers["physical_damage_bonus"]
    source_id = next(iter(bonus["temp"]))
    assert bonus["temp"][source_id] == "+4"
    assert source.statuses.abilities == []
    assert source_id.startswith("feint:")
    assert ":measured_strike:" in source_id


@pytest.mark.unit
@pytest.mark.parametrize(
    ("feint_id", "expected_cost", "expected_effect"),
    [
        ("glancing_step", "-9", "prep_glancing_dodge"),
        ("wind_dance", "-15", "prep_counter_cap_on_dodge"),
        ("blade_dance", "-21", "prep_counter_on_dodge"),
    ],
)
def test_ability_service_applies_basic_dodge_feint_preparation(
    feint_id: str, expected_cost: str, expected_effect: str
) -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id=feint_id),
    )
    ctx = PipelineContextDTO()

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    service.post_process(ctx, source, target, move)

    assert ctx.result.resource_changes["stamina"]["cost"] == expected_cost
    assert [effect.effect_id for effect in source.statuses.effects] == [expected_effect]


@pytest.mark.unit
def test_ability_service_does_not_mutate_feint_preparation_catalog_payload() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="glancing_step"),
    )
    ctx = PipelineContextDTO()

    entry = CombatCatalogIntegrator.get_feint_catalog_entry("glancing_step")
    assert entry is not None
    payload = entry.technical.preparation_effects[0]
    assert "target_id" not in payload

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    service.post_process(ctx, source, target, move)

    assert ctx.result.applied_effects[0]["target_id"] == source.char_id
    assert "target_id" not in payload


@pytest.mark.unit
@pytest.mark.parametrize(
    ("feint_id", "expected_cost", "expected_effect"),
    [
        ("foresight_parry", "-9", "prep_foresight_parry"),
        ("second_breath", "-15", "prep_second_breath"),
        ("2h_perfect_riposte", "-21", "prep_perfect_riposte"),
    ],
)
def test_ability_service_applies_basic_parry_feint_preparation(
    feint_id: str, expected_cost: str, expected_effect: str
) -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id=feint_id),
    )
    ctx = PipelineContextDTO()

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    service.post_process(ctx, source, target, move)

    assert ctx.result.resource_changes["stamina"]["cost"] == expected_cost
    assert [effect.effect_id for effect in source.statuses.effects] == [expected_effect]


@pytest.mark.unit
def test_ability_service_applies_basic_pressure_defense_preparation() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    source.meta.tokens["pressure"] = 3
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="press_defense"),
    )
    ctx = PipelineContextDTO()

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    service.post_process(ctx, source, target, move)

    assert ctx.result.resource_changes["stamina"]["cost"] == "-9"
    assert [effect.effect_id for effect in source.statuses.effects] == ["prep_brace_guard"]


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
    ctx.flags.force.hit = True
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_parried is True
    assert ctx.result.chain_events.trigger_counter_attack is True
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_counter_on_parry"
    assert ctx.result.effect_facts[-1].tags == ["prepared_reaction", "parry"]


@pytest.mark.unit
def test_foresight_parry_forces_next_incoming_parry_and_consumes_buff() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats({"parry": 0.0})
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_foresight_parry", source_id=2, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_parried is True
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_foresight_parry"


@pytest.mark.unit
def test_second_breath_heals_on_next_successful_parry_and_consumes_buff() -> None:
    source = actor(1, "a")
    target = actor(2, "b", hp=50)
    target.meta.max_hp = 100
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats()
    target.statuses.effects.append(
        ActiveEffectDTO(
            uid="fx1",
            effect_id="prep_second_breath",
            source_id=2,
            expire_at_exchange=999,
            params={"heal_max_hp_ratio": 0.18, "heal_min": 8},
        )
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)
    MechanicsService().apply_interaction_result(ctx, source, target, ctx.result)

    assert target.meta.hp == 68
    assert target.meta.tokens.get("parry", 0) == 0
    assert target.statuses.effects == []
    assert ctx.result.resource_facts[-1].reason == "prepared_heal"
    assert ctx.result.resource_facts[-1].delta == 18


@pytest.mark.unit
def test_perfect_riposte_heals_and_forces_counter_on_next_successful_parry() -> None:
    source = actor(1, "a")
    target = actor(2, "b", hp=50)
    target.meta.max_hp = 100
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats({"counter_attack_chance": 0.0, "counter_attack_cap": 0.0})
    target.statuses.effects.append(
        ActiveEffectDTO(
            uid="fx1",
            effect_id="prep_perfect_riposte",
            source_id=2,
            expire_at_exchange=999,
            params={"heal_max_hp_ratio": 0.12, "heal_min": 6},
        )
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)
    MechanicsService().apply_interaction_result(ctx, source, target, ctx.result)

    assert ctx.result.chain_events.trigger_counter_attack is True
    assert target.meta.hp == 62
    assert target.meta.tokens.get("parry", 0) == 0
    assert target.statuses.effects == []
    assert ctx.result.resource_facts[-1].reason == "prepared_heal"
    assert ctx.result.resource_facts[-1].delta == 12


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
    ctx.flags.force.hit = True
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
@pytest.mark.parametrize(
    ("feint_id", "expected_cost", "expected_effect"),
    [
        ("active_defense", "-9", "prep_active_defense"),
        ("full_defense", "-15", "prep_full_defense"),
        ("absolute_defense", "-21", "prep_absolute_defense"),
        ("aggressive_defense", "-21", "prep_aggressive_defense"),
    ],
)
def test_ability_service_applies_shield_tactical_feint_preparation(
    feint_id: str, expected_cost: str, expected_effect: str
) -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id=feint_id),
    )
    ctx = PipelineContextDTO()

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    service.post_process(ctx, source, target, move)

    assert ctx.result.resource_changes["stamina"]["cost"] == expected_cost
    assert [effect.effect_id for effect in source.statuses.effects] == [expected_effect]


@pytest.mark.unit
def test_active_defense_forces_defensive_shield_block_and_consumes_buff() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats({"shield_guard_power": 8.0})
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_active_defense", source_id=2, expire_at_exchange=999)
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
    assert ctx.result.is_blocked is True
    assert ctx.result.shield_block_branch == "defense"
    assert ctx.result.damage_final == 19
    assert ctx.result.damage_trace is not None
    assert ctx.result.damage_trace.details["shield_guard_power"] == pytest.approx(1.225)
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_active_defense"


@pytest.mark.unit
def test_full_defense_uses_amplified_shield_guard_power_and_consumes_buff() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats({"shield_guard_power": 8.0})
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_full_defense", source_id=2, expire_at_exchange=999)
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
    assert ctx.result.is_blocked is True
    assert ctx.result.shield_block_branch == "defense"
    assert ctx.result.damage_final == 18
    assert ctx.result.damage_trace is not None
    assert ctx.result.damage_trace.details["shield_guard_power"] == pytest.approx(2.45)
    assert ctx.result.damage_trace.details.get("incoming_damage_cap") is None
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_full_defense"


@pytest.mark.unit
def test_absolute_defense_caps_resolver_damage_without_consuming_until_duration_expires() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    target.meta.exchange_counter = 1
    source.stats = stats()
    target.stats = stats()
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_absolute_defense", source_id=2, expire_at_exchange=2)
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

    assert ctx.result.damage_final == 1
    assert [effect.effect_id for effect in target.statuses.effects] == ["prep_absolute_defense"]
    assert ctx.result.effect_facts[-1].action == "tick"

    target.meta.exchange_counter = 2
    service.pre_process(PipelineContextDTO(), move, target, source)

    assert target.statuses.effects == []


@pytest.mark.unit
def test_aggressive_defense_forces_block_and_scales_guard_without_reflect_branch() -> None:
    source = actor(1, "a", hp=100)
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats({"shield_guard_power": 20.0})
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_aggressive_defense", source_id=2, expire_at_exchange=999)
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
    MechanicsService().apply_interaction_result(ctx, source, target, ctx.result)

    assert ctx.result.is_blocked is True
    assert ctx.result.shield_block_branch == "defense"
    assert ctx.result.damage_final == 18
    assert ctx.result.reflected_damage == 0
    assert source.meta.hp == 100
    assert target.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_aggressive_defense"


@pytest.mark.unit
def test_read_tactic_removes_prepared_effects_on_successful_hit_only() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    source.stats = stats()
    target.stats = stats()
    target.statuses.effects.extend(
        [
            ActiveEffectDTO(uid="prep", effect_id="prep_parry_riposte", source_id=2, expire_at_exchange=999),
            ActiveEffectDTO(uid="dot", effect_id="dot_bleed", source_id=1, expire_at_exchange=999, impact={"hp": -2}),
        ]
    )
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="read_tactic"),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.override_damage = (5, 5)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert [effect.effect_id for effect in target.statuses.effects] == ["dot_bleed"]
    assert ctx.result.effect_facts[-1].effect_id == "dispel_preparations"
    assert ctx.result.effect_facts[-1].value == 1


@pytest.mark.unit
def test_concussion_uses_normal_attack_damage_and_blocks_next_feint_use() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    source.stats = stats({"main_hand_damage_base": 12.0, "main_hand_damage_spread": 0.0, "shield_guard_power": 20.0})
    target.stats = stats()
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="concussion"),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.damage_final == 12
    assert [effect.effect_id for effect in target.statuses.effects] == ["concussed_no_feints"]

    next_move = CombatMoveDTO(
        move_id="m2",
        char_id=2,
        strategy="exchange",
        payload=ExchangePayload(target_id=1, feint_id="measured_strike"),
    )
    next_ctx = PipelineContextDTO()
    service.pre_process(next_ctx, next_move, target, source)

    assert next_ctx.result.chain_events.preserve_feint is True


@pytest.mark.unit
def test_hit_condition_effects_do_not_apply_after_parry_but_hit_token_is_awarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: False)
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    source.stats = stats({"main_hand_damage_base": 12.0, "main_hand_damage_spread": 0.0})
    target.stats = stats()
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="concussion"),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_hit is True
    assert ctx.result.is_parried is True
    assert ctx.result.tokens_awarded_attacker == {"hit": 1}
    assert ctx.result.tokens_awarded_defender == {"parry": 1}
    assert target.statuses.effects == []


@pytest.mark.unit
def test_shield_blood_damage_converts_blood_feint_into_extra_hit_damage() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    ctx = PipelineContextDTO()
    ctx.result.source_id = "1"
    ctx.result.target_id = "2"
    ctx.result.is_hit = True
    ctx.result.damage_final = 4
    ctx.result.applied_effects.append(
        {
            "id": "shield_blood_damage",
            "target_actor": "target",
            "params": {"damage": 10},
        }
    )

    AbilityService._apply_queued_effects(ctx, source, target)

    assert ctx.result.damage_final == 14
    assert ctx.result.effect_facts[-1].effect_id == "shield_blood_damage"
    assert ctx.result.effect_facts[-1].value == 10


@pytest.mark.unit
def test_scarlet_riposte_reflects_blood_damage_on_block() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    target.statuses.effects.append(
        ActiveEffectDTO(
            uid="fx1",
            effect_id="prep_scarlet_riposte",
            source_id=2,
            expire_at_exchange=999,
            params={"reflect_damage": 10},
        )
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = "1"
    ctx.result.target_id = "2"
    ctx.result.is_blocked = True

    AbilityService._process_prepared_reactions_post_calc(ctx, source, target)

    assert ctx.result.reflected_damage == 10
    assert [effect.effect_id for effect in target.statuses.effects] == []
    assert ctx.result.effect_facts[-1].effect_id == "prep_scarlet_riposte"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("feint_id", "expected_cost", "expected_effect"),
    [
        ("steel_line", "-9", "prep_2h_steel_line"),
        ("blade_return", "-12", "prep_2h_blade_return"),
        ("hard_intercept", "-12", "prep_2h_hard_intercept"),
        ("answering_stance", "-15", "prep_2h_answering_stance"),
        ("closed_distance", "-21", "prep_2h_closed_distance"),
        ("hidden_agility", "-18", "prep_2h_hidden_agility"),
    ],
)
def test_ability_service_applies_two_handed_tactical_preparations(
    feint_id: str, expected_cost: str, expected_effect: str
) -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id=feint_id),
    )
    ctx = PipelineContextDTO()

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    service.post_process(ctx, source, target, move)

    assert ctx.result.resource_changes["stamina"]["cost"] == expected_cost
    assert [effect.effect_id for effect in source.statuses.effects] == [expected_effect]


@pytest.mark.unit
def test_crushing_pressure_halves_targets_next_outgoing_damage_after_hit() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    source.stats = stats()
    target.stats = stats()
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="crushing_pressure"),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.override_damage = (5, 5)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert [effect.effect_id for effect in target.statuses.effects] == ["debuff_2h_damage_halved"]

    target.meta.exchange_counter = 1
    next_move = CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1))
    next_ctx = PipelineContextDTO()
    next_ctx.result.source_id = target.char_id
    next_ctx.result.target_id = source.char_id
    next_ctx.override_damage = (20, 20)

    service.pre_process(next_ctx, next_move, target, source)
    next_ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(target.stats, source.stats, next_ctx)
    service.post_process(next_ctx, target, source, next_move)

    assert next_ctx.result.damage_final == 10
    assert target.statuses.effects == []


@pytest.mark.unit
def test_hard_intercept_applies_damage_halving_debuff_to_parried_attacker() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats()
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_2h_hard_intercept", source_id=2, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_parried is True
    assert [effect.effect_id for effect in source.statuses.effects] == ["debuff_2h_damage_halved"]
    assert target.statuses.effects == []


@pytest.mark.unit
def test_push_stance_adds_current_exchange_crit_chance() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="push_stance"),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.result.resource_changes["stamina"]["cost"] == "-9"
    crit_sources = source.raw.modifiers["crit_chance"]["temp"]
    assert next(iter(crit_sources.values())) == "+0.3"


@pytest.mark.unit
def test_open_wound_applies_bleed_on_successful_hit() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    source.stats = stats()
    target.stats = stats()
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="open_wound"),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.override_damage = (20, 20)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert [effect.effect_id for effect in target.statuses.effects] == ["dot_bleed"]
    assert target.statuses.effects[0].impact == {"hp": -3}


@pytest.mark.unit
def test_hidden_strength_forces_crit_damage_without_weapon_crit_trigger() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    source.loadout.layout.update({"main_hand": "skill_swords", "main_hand_trigger": "crit.weapon_serrated_bleed_crit"})
    source.stats = stats()
    target.stats = stats()
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="hidden_strength"),
    )
    ctx = ContextBuilder.build_context(source, target, move)
    ctx.override_damage = (10, 10)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_crit is True
    assert ctx.result.crit_mult == 2.0
    assert ctx.result.damage_final == 20
    assert ctx.result.fired_triggers == []
    assert ctx.result.applied_effects == []


@pytest.mark.unit
def test_lucky_break_keeps_weapon_crit_trigger_and_double_damage() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    source.loadout.layout.update({"main_hand": "skill_swords", "main_hand_trigger": "crit.weapon_serrated_bleed_crit"})
    source.stats = stats()
    target.stats = stats()
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="lucky_break"),
    )
    ctx = ContextBuilder.build_context(source, target, move)
    ctx.override_damage = (10, 10)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_crit is True
    assert ctx.result.crit_mult == 2.0
    assert ctx.result.damage_final == 20
    assert ctx.result.fired_triggers == ["weapon_serrated_bleed_crit"]
    assert ctx.result.applied_effects[0]["id"] == "dot_bleed"


@pytest.mark.unit
def test_ignore_guard_skips_dodge_parry_and_block_checks() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    source.stats = stats({"main_hand_accuracy": 1.0})
    target.stats = stats({"evasion": 1.0, "parry": 1.0, "block": 1.0})
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="ignore_guard"),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.override_damage = (7, 7)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.result.is_hit is True
    assert ctx.result.damage_final == 7
    assert ctx.result.is_dodged is False
    assert ctx.result.is_parried is False
    assert ctx.result.is_blocked is False


@pytest.mark.unit
def test_context_builder_disables_evasion_stage_for_shield_defender() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    target.loadout.layout.update({"off_hand": "skill_shield_mastery", "tactical_style": "skill_shield_mastery"})
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    ctx = ContextBuilder.build_context(source, target, move)

    assert ctx.stages.check_evasion is False
    assert ctx.stages.check_block is True


@pytest.mark.unit
def test_shield_block_chance_uses_shield_power_and_evasion_without_dodge_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    block_step.run(
        stats(),
        stats(
            {
                "block": 1.0,
                "dodge_cap": 0.0,
                "evasion": 0.5,
                "shield_guard_power": 20.0,
            },
            {"skill_shield_mastery": 1.0},
        ),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.45)]
    assert result.is_blocked is False


@pytest.mark.unit
def test_shield_block_success_opens_capped_half_weapon_counter_and_opening(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.0, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    block_step.run(
        stats({"armor": 4.0}),
        stats(
            {
                "counter_attack_chance": 0.9,
                "evasion": 0.2,
                "main_hand_damage_base": 40.0,
                "shield_guard_power": 20.0,
            },
            {"skill_shield_mastery": 1.0},
        ),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.36), pytest.approx(0.5)]
    assert result.is_blocked is True
    assert result.is_shield_counter is True
    assert result.shield_counter_damage == 17
    assert result.applied_effects == [
        {
            "id": "shield_opening",
            "target_id": result.source_id,
            "source_id": result.target_id,
            "params": {
                "evasion_mult": pytest.approx(0.74),
                "parry_mult": pytest.approx(0.74),
                "opening_strength": pytest.approx(0.26),
            },
        }
    ]


@pytest.mark.unit
def test_shield_block_denies_counter_against_ranged_combat_far_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.0, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.flags.meta.tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.source_ranged_position = "far"
    result = InteractionResultDTO(source_id=1, target_id=2)

    block_step.run(
        stats(),
        stats(
            {
                "counter_attack_chance": 1.0,
                "main_hand_damage_base": 40.0,
                "shield_guard_power": 20.0,
            },
            {"skill_shield_mastery": 1.0},
        ),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.3)]
    assert result.is_blocked is True
    assert result.is_shield_counter is False
    assert result.shield_counter_damage == 0
    assert result.applied_effects == []


@pytest.mark.unit
def test_shield_block_allows_counter_against_ranged_combat_close_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.0, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.flags.meta.tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.source_ranged_position = "close"
    result = InteractionResultDTO(source_id=1, target_id=2)

    block_step.run(
        stats(),
        stats(
            {
                "counter_attack_chance": 1.0,
                "main_hand_damage_base": 40.0,
                "shield_guard_power": 20.0,
            },
            {"skill_shield_mastery": 1.0},
        ),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.3), pytest.approx(0.5)]
    assert result.is_shield_counter is True
    assert result.shield_counter_damage == 20
    assert result.applied_effects[0]["id"] == "shield_opening"


@pytest.mark.unit
def test_shield_opening_applies_to_any_attacker_but_expires_after_tank_exchange() -> None:
    tank = actor(1, "a")
    ally = actor(3, "a")
    opened = actor(2, "b")
    opened.statuses.effects.append(
        ActiveEffectDTO(
            uid="opening-1",
            effect_id="shield_opening",
            source_id=tank.char_id,
            active_from_exchange=0,
            expire_at_exchange=999,
            params={"evasion_mult": 0.74, "parry_mult": 0.74},
        )
    )

    ally_ctx = PipelineContextDTO()
    ally_ctx.result.source_id = ally.char_id
    ally_ctx.result.target_id = opened.char_id
    AbilityService._apply_status_effects(ally_ctx, opened, mode="target")

    assert ally_ctx.mods.target_evasion_mult == pytest.approx(0.74)
    assert ally_ctx.mods.target_parry_mult == pytest.approx(0.74)

    result = InteractionResultDTO(source_id=tank.char_id, target_id=opened.char_id)
    MechanicsService().apply_interaction_result(PipelineContextDTO(), tank, opened, result)

    assert opened.statuses.effects == []


@pytest.mark.unit
@pytest.mark.parametrize(
    ("feint_id", "expected_cost", "expected_effect"),
    [
        ("broken_step", "-9", "prep_dual_broken_step"),
        ("shifting_line", "-15", "prep_dual_shifting_line"),
        ("empty_line", "-18", "prep_dual_empty_line"),
        ("torn_rhythm", "-24", "prep_dual_torn_rhythm"),
        ("bind_blade", "-12", "prep_dual_bind_blade"),
        ("offhand_over", "-15", "prep_dual_offhand_over"),
        ("answering_series", "-15", "prep_dual_answering_series_counter"),
        ("dual_blade_mill_v2", "-27", "prep_dual_blade_mill_counter"),
        ("blade_loop", "-36", "prep_dual_blade_loop_parry"),
    ],
)
def test_ability_service_applies_dual_wield_tactical_preparations(
    feint_id: str, expected_cost: str, expected_effect: str
) -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.meta.stamina = 100
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id=feint_id),
    )
    ctx = PipelineContextDTO()

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    service.post_process(ctx, source, target, move)

    assert ctx.result.resource_changes["stamina"]["cost"] == expected_cost
    assert [effect.effect_id for effect in source.statuses.effects] == [expected_effect]


@pytest.mark.unit
def test_dual_counter_only_preparation_does_not_modify_normal_attack() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats()
    source.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_dual_answering_series_counter", source_id=1, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)
    ctx.override_damage = (10, 10)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_counter is False
    assert ctx.result.damage_final == 10
    assert [effect.effect_id for effect in source.statuses.effects] == ["prep_dual_answering_series_counter"]


@pytest.mark.unit
def test_dual_answering_series_boosts_next_successful_counter() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats()
    source.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_dual_answering_series_counter", source_id=1, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move, {"is_counter_attack": True, "action_mode": "exchange"})
    ctx.override_damage = (10, 10)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_counter is True
    assert ctx.result.damage_final == 12
    assert source.statuses.effects == []


@pytest.mark.unit
def test_dual_blade_mill_boosts_successful_counter_and_forces_existing_offhand_chain() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats()
    source.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_dual_blade_mill_counter", source_id=1, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move, {"is_counter_attack": True, "action_mode": "exchange"})
    ctx.override_damage = (10, 10)

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.damage_final == 15
    assert ctx.result.chain_events.trigger_offhand_attack is True
    assert source.statuses.effects == []


@pytest.mark.unit
def test_dual_offhand_over_opens_counter_check_after_parry_without_medium_armor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: chance > 0))
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats({"counter_attack_chance": 0.0, "counter_attack_cap": 0.0})
    target.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_dual_offhand_over", source_id=2, expire_at_exchange=999)
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)

    assert ctx.result.is_parried is True
    assert ctx.result.chain_events.trigger_counter_attack is True
    assert target.statuses.effects == []


@pytest.mark.unit
def test_dual_blade_loop_turns_successful_parry_into_boosted_counter_debuff() -> None:
    attacker = actor(1, "a")
    defender = actor(2, "b")
    attacker.stats = stats()
    defender.stats = stats()
    defender.statuses.effects.append(
        ActiveEffectDTO(uid="fx1", effect_id="prep_dual_blade_loop_parry", source_id=2, expire_at_exchange=999)
    )
    incoming = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    incoming_ctx = PipelineContextDTO()
    incoming_ctx.result.source_id = attacker.char_id
    incoming_ctx.result.target_id = defender.char_id

    service = AbilityService()
    service.pre_process(incoming_ctx, incoming, attacker, defender)
    incoming_ctx.flags.force.hit = True
    incoming_ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(attacker.stats, defender.stats, incoming_ctx)
    service.post_process(incoming_ctx, attacker, defender, incoming)

    assert incoming_ctx.result.is_parried is True
    assert incoming_ctx.result.chain_events.trigger_counter_attack is True
    assert [effect.effect_id for effect in defender.statuses.effects] == ["prep_dual_blade_loop_counter"]

    counter_move = CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1))
    counter_ctx = ContextBuilder.build_context(
        defender,
        attacker,
        counter_move,
        {"is_counter_attack": True, "action_mode": "exchange"},
    )
    counter_ctx.override_damage = (10, 10)

    service.pre_process(counter_ctx, counter_move, defender, attacker)
    counter_ctx.flags.force.hit = True
    CombatResolver.resolve_exchange(defender.stats, attacker.stats, counter_ctx)
    service.post_process(counter_ctx, defender, attacker, counter_move)

    assert counter_ctx.result.damage_final == 15
    assert [effect.effect_id for effect in attacker.statuses.effects] == ["debuff_2h_damage_halved"]
    assert defender.statuses.effects == []


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
    ctx.flags.force.hit = True
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
def test_counter_check_denies_counter_against_ranged_combat_far_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.0, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.flags.state.check_counter = True
    ctx.flags.meta.tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.source_ranged_position = "far"
    result = InteractionResultDTO(source_id=1, target_id=2, is_parried=True)

    counter_check_step.run(
        stats(),
        stats({"counter_attack_chance": 1.0, "counter_attack_cap": 1.0}),
        ctx,
        result,
    )

    assert captured_chances == []
    assert result.is_counter is False
    assert result.chain_events.trigger_counter_attack is False


@pytest.mark.unit
def test_counter_check_allows_counter_against_ranged_combat_close_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: False)
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.0, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.flags.state.check_counter = True
    ctx.flags.meta.tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.source_ranged_position = "close"
    result = InteractionResultDTO(source_id=1, target_id=2, is_parried=True)

    counter_check_step.run(
        stats(),
        stats({"counter_attack_chance": 1.0, "counter_attack_cap": 1.0}),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(1.0)]
    assert result.is_counter is True
    assert result.chain_events.trigger_counter_attack is True
    assert result.tokens_awarded_defender == {}


@pytest.mark.unit
def test_plain_dodge_does_not_open_counter_window_without_light_armor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: True))
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats({"counter_attack_chance": 1.0, "counter_attack_cap": 1.0})
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    ctx.flags.force.hit = True
    ctx.flags.force.dodge = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.result.is_dodged is True
    assert ctx.result.chain_events.trigger_counter_attack is False


@pytest.mark.unit
def test_light_armor_dodge_opens_counter_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: True))
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats(
        {"counter_attack_chance": 1.0, "counter_attack_cap": 1.0},
        {"skill_light_armor": 1.0},
    )
    target.loadout.layout["body"] = "skill_light_armor"
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)

    ctx.flags.force.hit = True
    ctx.flags.force.dodge = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.result.is_dodged is True
    assert ctx.result.chain_events.trigger_counter_attack is True


@pytest.mark.unit
def test_medium_armor_dodge_does_not_open_counter_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: True))
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats(
        {"counter_attack_chance": 1.0, "counter_attack_cap": 1.0},
        {"skill_medium_armor": 1.0},
    )
    target.loadout.layout["body"] = "skill_medium_armor"
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)

    ctx.flags.force.hit = True
    ctx.flags.force.dodge = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.result.is_dodged is True
    assert ctx.result.chain_events.trigger_counter_attack is False


@pytest.mark.unit
def test_medium_armor_parry_opens_counter_window_through_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: chance > 0))
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats(
        {"counter_attack_chance": 1.0, "counter_attack_cap": 1.0},
        {"skill_medium_armor": 1.0},
    )
    target.loadout.layout["body"] = "skill_medium_armor"
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)

    ctx.flags.force.hit = True
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.result.is_parried is True
    assert ctx.result.chain_events.trigger_counter_attack is True


@pytest.mark.unit
def test_medium_armor_parry_without_skill_does_not_open_counter_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: chance > 0))
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats(
        {"counter_attack_chance": 1.0, "counter_attack_cap": 1.0},
        {"skill_medium_armor": 0.0},
    )
    target.loadout.layout["body"] = "skill_medium_armor"
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)

    ctx.flags.force.hit = True
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.result.is_parried is True
    assert ctx.result.chain_events.trigger_counter_attack is False


@pytest.mark.unit
def test_archery_light_armor_dodge_does_not_open_passive_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: True))
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: False)
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats(
        {"counter_attack_chance": 1.0, "counter_attack_cap": 1.0},
        {"skill_light_armor": 1.0},
    )
    target.loadout.layout.update({"main_hand": "skill_archery", "body": "skill_light_armor"})
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)

    ctx.flags.force.hit = True
    ctx.flags.force.dodge = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.result.is_hit is True
    assert ctx.result.is_dodged is True
    assert ctx.result.tokens_awarded_attacker == {"hit": 1}
    assert ctx.result.tokens_awarded_defender == {"dodge": 1}
    assert ctx.result.chain_events.trigger_counter_attack is False


@pytest.mark.unit
def test_archery_light_armor_dodge_feint_keeps_counter_and_light_bonus(monkeypatch: pytest.MonkeyPatch) -> None:
    checked_chances: list[float] = []

    def fake_check_chance(chance: float) -> bool:
        checked_chances.append(chance)
        return True

    monkeypatch.setattr(MathCore, "check_chance", fake_check_chance)
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats(
        {"counter_attack_chance": 0.1, "counter_attack_cap": 0.1},
        {"skill_light_armor": 1.0},
    )
    target.loadout.layout.update({"main_hand": "skill_archery", "body": "skill_light_armor"})
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)

    ctx.mods.counter_chance_bonus_on_dodge = 0.2
    ctx.flags.force.hit = True
    ctx.flags.force.dodge = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert checked_chances == pytest.approx([0.5, 0.4])
    assert ctx.result.is_dodged is True
    assert ctx.result.chain_events.trigger_counter_attack is True


@pytest.mark.unit
def test_archery_medium_armor_parry_does_not_open_passive_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: True))
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats()
    target.stats = stats(
        {"counter_attack_chance": 1.0, "counter_attack_cap": 1.0},
        {"skill_medium_armor": 1.0},
    )
    target.loadout.layout.update({"main_hand": "skill_archery", "body": "skill_medium_armor"})
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)

    ctx.flags.force.hit = True
    ctx.flags.force.parry = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.result.is_parried is True
    assert ctx.result.chain_events.trigger_counter_attack is False


@pytest.mark.unit
def test_spiked_guard_reflects_on_block_without_consuming_buff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: False)

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
            params={"reflect_damage": 12},
        )
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    service = AbilityService()
    service.pre_process(ctx, move, source, target)
    ctx.flags.force.hit = True
    ctx.flags.force.block = True
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)
    service.post_process(ctx, source, target, move)
    MechanicsService().apply_interaction_result(ctx, source, target, ctx.result)

    assert ctx.result.is_blocked is True
    assert ctx.result.reflected_damage == 12
    assert source.meta.hp == 88
    assert source.meta.token_progress["blood"] == 2
    assert ctx.result.tokens_awarded_attacker == {"blood": 1, "hit": 1}
    assert any(fact.owner == "source" and fact.token == "blood" for fact in ctx.result.token_facts)
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

    entry = ctx.pending_logs[0]
    assert entry["catalog"] == "combat_text"
    assert entry["template"]["key"] == "combat.exchange.skill_swords.main_hand.parry.humanoid_to_humanoid.weapon"
    assert entry["outcome"] == "parry"
    assert "переводит парирование в контратаку" not in entry["text"]


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

    trigger_activator.resolve_triggers(ctx, result, "ON_ACCURACY_CHECK")

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
    activate_trigger(ctx, "accuracy.true_strike", source="style", source_id="skill_tactics")

    trigger_activator.resolve_triggers(ctx, result, "ON_ACCURACY_CHECK")

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
def test_ability_service_applies_basic_gift_combat_token_costs() -> None:
    source = actor(1, "a")
    source.meta.tokens.update({"tempo": 3, "hit": 2})
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_break_stance", target_id=2),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.result.skip_reason is None
    assert ctx.result.resource_changes["tempo"]["cost"] == "-3"
    assert ctx.result.resource_changes["hit"]["cost"] == "-2"
    assert "stamina" not in ctx.result.resource_changes
    assert "en" not in ctx.result.resource_changes
    assert "gift" not in ctx.result.resource_changes
    assert ctx.flags.meta.source_type == "main_hand"
    assert ctx.stages.check_accuracy is False
    assert ctx.stages.check_evasion is False
    assert ctx.stages.check_parry is False
    assert ctx.stages.check_block is False
    assert ctx.stages.check_crit is False
    assert ctx.mods.damage_mult == pytest.approx(1.2)
    assert ctx.override_damage is None


@pytest.mark.unit
def test_basic_combat_token_instant_uses_main_hand_base_damage_without_magic_stats() -> None:
    source = actor(1, "a")
    source.meta.tokens.update({"tempo": 2, "crit": 2})
    source.stats = stats(
        {
            "main_hand_damage_base": 20.0,
            "main_hand_damage_spread": 0.0,
            "magical_damage": 200.0,
            "magical_accuracy": 1.0,
        }
    )
    target = actor(2, "b")
    target.stats = stats({"evasion": 1.0, "dodge_cap": 1.0, "armor": 0.0, "physical_resistance": 0.0})
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_expose_weakness", target_id=2),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id

    AbilityService().pre_process(ctx, move, source, target)
    CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert ctx.flags.meta.source_type == "main_hand"
    assert ctx.result.is_dodged is False
    assert ctx.result.damage_final == 24


@pytest.mark.unit
def test_basic_break_stance_applies_flat_damage_down_from_skill_damage_for_four_exchanges() -> None:
    source = actor(1, "a")
    source.meta.tokens.update({"tempo": 3, "hit": 2})
    source.stats = stats({"main_hand_damage_base": 20.0})
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_break_stance", target_id=2),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert source.statuses.abilities == []
    active = target.statuses.effects[-1]
    assert active.effect_id == "basic_break_stance"
    assert active.expire_at_exchange == source.meta.exchange_counter + 4
    assert active.modified_keys == ["physical_damage_bonus"]
    assert target.raw.modifiers["physical_damage_bonus"]["temp"][active.modified_sources["physical_damage_bonus"][0]] == (
        "-6"
    )


@pytest.mark.unit
def test_basic_expose_weakness_applies_evasion_down_before_cap_for_three_exchanges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.99, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))
    source = actor(1, "a")
    source.meta.tokens.update({"tempo": 2, "crit": 2})
    target = actor(2, "b")
    target.raw.modifiers["evasion"] = {"base": 1.0, "source": {}, "temp": {}}
    target.raw.modifiers["dodge_cap"] = {"base": 0.75, "source": {}, "temp": {}}
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_expose_weakness", target_id=2),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert source.statuses.abilities == []
    active = target.statuses.effects[-1]
    assert active.effect_id == "basic_expose_weakness"
    assert active.expire_at_exchange == source.meta.exchange_counter + 3
    assert active.modified_keys == ["evasion"]
    assert target.raw.modifiers["evasion"]["temp"][active.modified_sources["evasion"][0]] == "-0.5"
    StatsEngine.ensure_stats(target)
    assert target.stats is not None
    assert target.stats.mods.evasion == pytest.approx(0.5)

    evasion_ctx = PipelineContextDTO()
    evasion_result = InteractionResultDTO(source_id=1, target_id=2)
    evasion_step.run(stats(), target.stats, evasion_ctx, evasion_result)

    assert captured_chances == [pytest.approx(0.5)]


@pytest.mark.unit
def test_ability_service_rejects_basic_gift_when_combat_token_missing() -> None:
    source = actor(1, "a")
    source.meta.tokens.update({"tempo": 1})
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_break_stance", target_id=2),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.result.skip_reason == "NO_RESOURCE"
    assert ctx.result.resource_changes == {}


@pytest.mark.unit
def test_basic_wipe_blood_applies_symbiote_scaled_regen_and_parry_buff() -> None:
    source = actor(1, "a")
    source.meta.en = 20
    source.meta.tokens.update({"blood": 3, "block": 1, "gift": 1})
    source.raw.modifiers["hp_regen"] = {"base": 3.0, "source": {}, "temp": {}}
    source.raw.modifiers["parry"] = {"base": 0.10, "source": {}, "temp": {}}
    source.raw.modifiers["parry_cap"] = {"base": 0.50, "source": {}, "temp": {}}
    StatsEngine.ensure_stats(source)
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_wipe_blood", target_id=1),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.result.skip_reason is None
    assert ctx.result.resource_changes["en"]["cost"] == "-5"
    assert ctx.result.resource_changes["gift"]["cost"] == "-1"
    assert ctx.result.resource_changes["blood"]["cost"] == "-3"
    assert ctx.result.resource_changes["block"]["cost"] == "-1"
    assert "hp" not in ctx.result.resource_changes
    assert ctx.phases.run_calculator is False
    assert [ability.ability_id for ability in source.statuses.abilities] == ["basic_wipe_blood"]
    assert source.statuses.effects == []
    assert source.raw.modifiers["hp_regen"]["temp"] == {}

    AbilityService().post_process(ctx, source, target, move)

    assert source.statuses.abilities == []
    active = source.statuses.effects[-1]
    assert active.effect_id == "basic_wipe_blood"
    assert active.expire_at_exchange == source.meta.exchange_counter + 3
    assert active.modified_keys == ["hp_regen", "parry", "parry_cap"]
    assert source.raw.modifiers["hp_regen"]["temp"][active.modified_sources["hp_regen"][0]] == "+3"
    assert source.raw.modifiers["parry"]["temp"][active.modified_sources["parry"][0]] == "+0.05"
    assert source.raw.modifiers["parry_cap"]["temp"][active.modified_sources["parry_cap"][0]] == "+0.05"
    StatsEngine.ensure_stats(source)
    assert source.stats is not None
    assert source.stats.mods.hp_regen == pytest.approx(6.0)
    assert source.stats.mods.parry == pytest.approx(0.15)
    assert source.stats.mods.parry_cap == pytest.approx(0.55)


@pytest.mark.unit
def test_basic_last_push_applies_symbiote_scaled_regen_and_accuracy_cap_buff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.99, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))
    source = actor(1, "a")
    source.meta.en = 20
    source.meta.tokens.update({"blood": 3, "parry": 1, "gift": 1})
    source.raw.modifiers["hp_regen"] = {"base": 4.0, "source": {}, "temp": {}}
    source.raw.modifiers["accuracy"] = {"base": 0.30, "source": {}, "temp": {}}
    source.raw.modifiers["accuracy_cap"] = {"base": 0.0, "source": {}, "temp": {}}
    StatsEngine.ensure_stats(source)
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_last_push", target_id=1),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.result.skip_reason is None
    assert ctx.result.resource_changes["en"]["cost"] == "-5"
    assert ctx.result.resource_changes["gift"]["cost"] == "-1"
    assert ctx.result.resource_changes["blood"]["cost"] == "-3"
    assert ctx.result.resource_changes["parry"]["cost"] == "-1"
    assert "hp" not in ctx.result.resource_changes
    assert ctx.phases.run_calculator is False
    assert [ability.ability_id for ability in source.statuses.abilities] == ["basic_last_push"]
    assert source.statuses.effects == []
    assert source.raw.modifiers["hp_regen"]["temp"] == {}

    AbilityService().post_process(ctx, source, target, move)

    assert source.statuses.abilities == []
    active = source.statuses.effects[-1]
    assert active.effect_id == "basic_last_push"
    assert active.expire_at_exchange == source.meta.exchange_counter + 3
    assert active.modified_keys == ["accuracy", "accuracy_cap", "hp_regen"]
    assert source.raw.modifiers["hp_regen"]["temp"][active.modified_sources["hp_regen"][0]] == "+4"
    assert source.raw.modifiers["accuracy"]["temp"][active.modified_sources["accuracy"][0]] == "+0.03"
    assert source.raw.modifiers["accuracy_cap"]["temp"][active.modified_sources["accuracy_cap"][0]] == "+0.03"
    StatsEngine.ensure_stats(source)
    assert source.stats is not None
    assert source.stats.mods.hp_regen == pytest.approx(8.0)
    assert source.stats.mods.accuracy == pytest.approx(0.33)
    assert source.stats.mods.accuracy_cap == pytest.approx(0.03)

    accuracy_ctx = PipelineContextDTO()
    accuracy_result = InteractionResultDTO(source_id=1, target_id=2)
    accuracy_step.run(source.stats, stats(), accuracy_ctx, accuracy_result)

    assert captured_chances == [pytest.approx(0.93)]


@pytest.mark.unit
def test_basic_slip_pain_applies_symbiote_scaled_regen_and_absorb_from_evasion() -> None:
    source = actor(1, "a")
    source.meta.en = 20
    source.meta.tokens.update({"blood": 3, "dodge": 1, "gift": 1})
    source.raw.modifiers["hp_regen"] = {"base": 3.0, "source": {}, "temp": {}}
    source.raw.modifiers["evasion"] = {"base": 0.40, "source": {}, "temp": {}}
    source.raw.modifiers["incoming_damage_absorb_pct"] = {"base": 0.0, "source": {}, "temp": {}}
    StatsEngine.ensure_stats(source)
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_slip_pain", target_id=1),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.result.skip_reason is None
    assert ctx.result.resource_changes["en"]["cost"] == "-5"
    assert ctx.result.resource_changes["gift"]["cost"] == "-1"
    assert ctx.result.resource_changes["blood"]["cost"] == "-3"
    assert ctx.result.resource_changes["dodge"]["cost"] == "-1"
    assert ctx.phases.run_calculator is False
    assert [ability.ability_id for ability in source.statuses.abilities] == ["basic_slip_pain"]
    assert source.statuses.effects == []
    assert source.raw.modifiers["hp_regen"]["temp"] == {}

    AbilityService().post_process(ctx, source, target, move)

    assert source.statuses.abilities == []
    active = source.statuses.effects[-1]
    assert active.effect_id == "basic_slip_pain"
    assert active.expire_at_exchange == source.meta.exchange_counter + 3
    assert active.modified_keys == ["hp_regen", "incoming_damage_absorb_pct"]
    assert source.raw.modifiers["hp_regen"]["temp"][active.modified_sources["hp_regen"][0]] == "+3"
    assert source.raw.modifiers["incoming_damage_absorb_pct"]["temp"][
        active.modified_sources["incoming_damage_absorb_pct"][0]
    ] == "+0.05"
    StatsEngine.ensure_stats(source)
    assert source.stats is not None
    assert source.stats.mods.hp_regen == pytest.approx(6.0)
    assert source.stats.mods.incoming_damage_absorb_pct == pytest.approx(0.05)


@pytest.mark.unit
def test_basic_blood_hunger_applies_damage_and_vampiric_power_buff_without_regen() -> None:
    source = actor(1, "a")
    source.meta.en = 20
    source.meta.tokens.update({"tempo": 5, "pressure": 5, "gift": 1})
    source.raw.modifiers["hp_regen"] = {"base": 4.0, "source": {}, "temp": {}}
    source.raw.modifiers["physical_damage_bonus"] = {"base": 0.0, "source": {}, "temp": {}}
    source.raw.modifiers["vampiric_power"] = {"base": 0.0, "source": {}, "temp": {}}
    StatsEngine.ensure_stats(source)
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_blood_hunger", target_id=1),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.result.skip_reason is None
    assert "en" not in ctx.result.resource_changes
    assert ctx.result.resource_changes["gift"]["cost"] == "-1"
    assert "blood" not in ctx.result.resource_changes
    assert ctx.result.resource_changes["tempo"]["cost"] == "-5"
    assert ctx.result.resource_changes["pressure"]["cost"] == "-5"
    assert ctx.flags.damage.vampiric is True
    assert ctx.phases.run_calculator is False
    assert [ability.ability_id for ability in source.statuses.abilities] == ["basic_blood_hunger"]
    assert source.statuses.effects == []
    assert source.raw.modifiers["physical_damage_bonus"]["temp"] == {}
    assert source.raw.modifiers["vampiric_power"]["temp"] == {}

    AbilityService().post_process(ctx, source, target, move)

    assert source.statuses.abilities == []
    active = source.statuses.effects[-1]
    assert active.effect_id == "basic_blood_hunger"
    assert active.expire_at_exchange == source.meta.exchange_counter + 5
    assert active.modified_keys == ["physical_damage_bonus", "vampiric_power"]
    assert source.raw.modifiers["hp_regen"]["temp"] == {}
    assert source.raw.modifiers["physical_damage_bonus"]["temp"][active.modified_sources["physical_damage_bonus"][0]] == (
        "+2"
    )
    assert source.raw.modifiers["vampiric_power"]["temp"][active.modified_sources["vampiric_power"][0]] == "+0.15"
    StatsEngine.ensure_stats(source)
    assert source.stats is not None
    assert source.stats.mods.hp_regen == pytest.approx(4.0)
    assert source.stats.mods.physical_damage_bonus == pytest.approx(2.0)
    assert source.stats.mods.vampiric_power == pytest.approx(0.15)


@pytest.mark.unit
def test_basic_cleave_gift_applies_three_exchange_cleave_buff() -> None:
    source = actor(1, "a")
    source.meta.tokens.update({"hit": 3, "pressure": 3, "gift": 3})
    source.raw.modifiers["cleave_damage_mult"] = {"base": 0.0, "source": {}, "temp": {}}
    source.raw.modifiers["cleave_target_count"] = {"base": 0.0, "source": {}, "temp": {}}
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="instant",
        payload=InstantPayload(ability_id="basic_cleave_gift", target_id=1),
    )
    ctx = PipelineContextDTO()

    AbilityService().pre_process(ctx, move, source, target)

    assert ctx.result.skip_reason is None
    assert ctx.result.resource_changes["gift"]["cost"] == "-3"
    assert ctx.result.resource_changes["hit"]["cost"] == "-3"
    assert ctx.result.resource_changes["pressure"]["cost"] == "-3"
    assert "en" not in ctx.result.resource_changes
    assert ctx.phases.run_calculator is False
    assert [ability.ability_id for ability in source.statuses.abilities] == ["basic_cleave_gift"]
    assert source.statuses.effects == []
    assert source.raw.modifiers["cleave_damage_mult"]["temp"] == {}

    AbilityService().post_process(ctx, source, target, move)

    assert source.statuses.abilities == []
    active = source.statuses.effects[-1]
    assert active.effect_id == "basic_cleave_gift"
    assert active.expire_at_exchange == source.meta.exchange_counter + 3
    assert active.modified_keys == ["cleave_damage_mult", "cleave_target_count"]
    assert source.raw.modifiers["cleave_damage_mult"]["temp"][active.modified_sources["cleave_damage_mult"][0]] == (
        "+0.3"
    )
    assert source.raw.modifiers["cleave_target_count"]["temp"][active.modified_sources["cleave_target_count"][0]] == (
        "+2"
    )
    StatsEngine.ensure_stats(source)
    assert source.stats is not None
    assert source.stats.mods.cleave_damage_mult == pytest.approx(0.30)
    assert source.stats.mods.cleave_target_count == pytest.approx(2.0)


@pytest.mark.unit
def test_vampiric_post_process_heals_from_final_damage_with_fixed_base_chance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.50, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))
    source = actor(1, "a", hp=80)
    source.raw.modifiers["vampiric_power"] = {"base": 0.15, "source": {}, "temp": {}}
    source.raw.modifiers["vampiric_trigger_chance"] = {"base": 0.10, "source": {}, "temp": {}}
    source.raw.modifiers["vampiric_trigger_cap"] = {"base": 0.85, "source": {}, "temp": {}}
    target = actor(2, "b")
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    ctx.result.is_hit = True
    ctx.result.damage_final = 100
    ctx.flags.damage.vampiric = True

    AbilityService().post_process(ctx, source, target, move)

    assert captured_chances == [pytest.approx(0.85)]
    assert ctx.result.lifesteal_amount == 15
    assert ctx.result.healing_final == 15
    assert ctx.result.resource_applications[-1].resource == "hp"
    assert ctx.result.resource_applications[-1].reason == "vampiric"
    assert ctx.result.resource_applications[-1].value == "+15"
    assert ctx.result.checks[-1].stage == "vampiric"
    assert ctx.result.checks[-1].details["power"] == pytest.approx(0.15)


@pytest.mark.unit
def test_modifier_application_can_build_clamped_absorb_from_evasion() -> None:
    source = actor(1, "a")
    source.raw.modifiers["evasion"] = {"base": 0.40, "source": {}, "temp": {}}
    source.raw.modifiers["incoming_damage_absorb_pct"] = {"base": 0.0, "source": {}, "temp": {}}
    StatsEngine.ensure_stats(source)

    applied = ModifierApplicationService.apply(
        applications=[
            ModifierApplicationDTO(
                modifier_id="incoming_damage_absorb_pct_add",
                target_actor="self",
                value_mode="source_modifier_scaled_clamped",
                source_modifier_id="evasion",
                value_override=0.03,
                value_multiplier=0.05,
                value_cap=0.15,
                scope="duration",
                duration_exchanges=3,
                scale_value_with_symbiote=True,
            )
        ],
        owner="ability",
        owner_uid="absorb-test",
        owner_id="basic_dodge_absorb",
        source=source,
        target=None,
        symbiote_ability_mult=1.0,
    )

    assert applied.modified_keys == {"incoming_damage_absorb_pct"}
    source_id = applied.modified_sources["incoming_damage_absorb_pct"][0]
    assert source.raw.modifiers["incoming_damage_absorb_pct"]["temp"][source_id] == "+0.05"
    StatsEngine.ensure_stats(source)
    assert source.stats is not None
    assert source.stats.mods.incoming_damage_absorb_pct == pytest.approx(0.05)


@pytest.mark.unit
def test_incoming_damage_absorb_pct_reduces_final_damage() -> None:
    source = actor(1, "a")
    source.stats = stats({"main_hand_damage_base": 100.0, "main_hand_damage_spread": 0.0})
    target = actor(2, "b")
    target.stats = stats({"incoming_damage_absorb_pct": 0.10, "armor": 0.0, "physical_resistance": 0.0})
    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage_step.run(source.stats, target.stats, ctx, result)

    assert result.damage_final == 90
    assert result.damage_trace is not None
    assert result.damage_trace.details["incoming_damage_absorb_pct"] == pytest.approx(0.10)
    assert result.damage_trace.details["incoming_damage_absorbed"] == pytest.approx(10.0)
    assert result.damage_trace.details["after_incoming_absorb"] == pytest.approx(90.0)


@pytest.mark.unit
def test_mechanics_applies_stamina_resource_changes() -> None:
    source = actor(1, "a")
    source.meta.stamina = 11
    source.meta.max_stamina = 100
    target = actor(2, "b")
    result = InteractionResultDTO(source_id=1, target_id=2, resource_changes={"stamina": {"cost": "-10"}})

    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, result)

    assert source.meta.stamina == 1
    assert [fact.model_dump() for fact in result.resource_facts] == [
        {
            "actor_id": "1",
            "owner": "source",
            "resource": "stamina",
            "reason": "cost",
            "delta": -10,
            "before": 11,
            "after": 1,
            "max": 100,
            "source_action_id": None,
            "source_effect_id": None,
            "source_trigger_id": None,
            "tags": [],
        }
    ]


@pytest.mark.unit
def test_feint_service_refill_hand_ignores_unknown_archived_feints() -> None:
    source = actor(1, "a")
    source.meta.feints.arsenal = ["future_feint_placeholder"]
    source.meta.tokens["hit"] = 2

    FeintService.refill_hand(source.meta, hand_size=1)

    assert source.meta.feints.hand == {}
    assert source.meta.tokens["hit"] == 2


@pytest.mark.unit
def test_feint_service_refill_prioritizes_one_best_feint_per_purchase_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    source = actor(1, "a")
    source.meta.feints.arsenal = [
        "basic_cheap",
        "basic_expensive",
        "weapon_expensive",
        "weapon_cheap",
        "tactical_expensive",
        "tactical_cheap",
    ]
    source.meta.tokens = {"hit": 10, "crit": 10, "tempo": 10}
    fake_catalog = {
        "basic_cheap": ("basic", {"hit": 3}),
        "basic_expensive": ("basic", {"hit": 7}),
        "weapon_expensive": ("weapon", {"crit": 7}),
        "weapon_cheap": ("weapon", {"crit": 3}),
        "tactical_expensive": ("tactical", {"tempo": 7}),
        "tactical_cheap": ("tactical", {"tempo": 3}),
    }

    def fake_get_feint_catalog_entry(feint_id: str):
        group, cost = fake_catalog[feint_id]
        return SimpleNamespace(
            technical=SimpleNamespace(
                feint_id=feint_id,
                cost=SimpleNamespace(tactics=cost),
                purchase_group=group,
            )
        )

    monkeypatch.setattr(CombatCatalogIntegrator, "get_feint_catalog_entry", fake_get_feint_catalog_entry)

    FeintService.refill_hand(source.meta, hand_size=3)

    assert source.meta.feints.hand == {
        "weapon_expensive": {"crit": 7},
        "tactical_expensive": {"tempo": 7},
        "basic_expensive": {"hit": 7},
    }
    assert list(source.meta.feints.hand) == ["weapon_expensive", "tactical_expensive", "basic_expensive"]
    assert source.meta.tokens == {"hit": 3, "crit": 3, "tempo": 3}


@pytest.mark.unit
def test_feint_service_refill_never_spends_basic_before_affordable_non_basic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    source = actor(1, "a")
    source.meta.feints.arsenal = ["basic_expensive", "basic_cheap", "weapon_expensive"]
    source.meta.tokens = {"hit": 10}
    fake_catalog = {
        "basic_expensive": ("basic", {"hit": 7}),
        "basic_cheap": ("basic", {"hit": 3}),
        "weapon_expensive": ("weapon", {"hit": 7}),
    }

    def fake_get_feint_catalog_entry(feint_id: str):
        group, cost = fake_catalog[feint_id]
        return SimpleNamespace(
            technical=SimpleNamespace(
                feint_id=feint_id,
                cost=SimpleNamespace(tactics=cost),
                purchase_group=group,
            )
        )

    monkeypatch.setattr(CombatCatalogIntegrator, "get_feint_catalog_entry", fake_get_feint_catalog_entry)

    FeintService.refill_hand(source.meta, hand_size=3)

    assert source.meta.feints.hand == {
        "weapon_expensive": {"hit": 7},
        "basic_cheap": {"hit": 3},
    }
    assert "basic_expensive" not in source.meta.feints.hand
    assert source.meta.tokens == {"hit": 0}


@pytest.mark.unit
def test_feint_service_refill_fallback_prefers_non_basic_groups_before_basic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    source = actor(1, "a")
    source.meta.feints.arsenal = [
        "weapon_expensive",
        "weapon_cheap",
        "tactical_expensive",
        "basic_expensive",
        "basic_cheap",
    ]
    source.meta.tokens = {"hit": 20, "tempo": 10}
    fake_catalog = {
        "weapon_expensive": ("weapon", {"hit": 7}),
        "weapon_cheap": ("weapon", {"hit": 3}),
        "tactical_expensive": ("tactical", {"tempo": 7}),
        "basic_expensive": ("basic", {"hit": 7}),
        "basic_cheap": ("basic", {"hit": 3}),
    }

    def fake_get_feint_catalog_entry(feint_id: str):
        group, cost = fake_catalog[feint_id]
        return SimpleNamespace(
            technical=SimpleNamespace(
                feint_id=feint_id,
                cost=SimpleNamespace(tactics=cost),
                purchase_group=group,
            )
        )

    picked_from_free_pool: list[list[str]] = []

    def fake_choice(pool: list[str]) -> str:
        picked_from_free_pool.append(list(pool))
        return pool[0]

    monkeypatch.setattr(CombatCatalogIntegrator, "get_feint_catalog_entry", fake_get_feint_catalog_entry)
    monkeypatch.setattr("src.backend.features.combat.runtime.engine.feint_service.random.choice", fake_choice)

    FeintService.refill_hand(source.meta, hand_size=4)

    assert list(source.meta.feints.hand) == [
        "weapon_expensive",
        "tactical_expensive",
        "basic_expensive",
        "weapon_cheap",
    ]
    assert picked_from_free_pool == [["weapon_cheap"]]
    assert "basic_cheap" not in source.meta.feints.hand


@pytest.mark.unit
def test_feint_service_refill_uses_random_free_pool_when_purchase_group_slot_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    source = actor(1, "a")
    source.meta.feints.arsenal = ["basic_expensive", "basic_cheap", "weapon_expensive"]
    source.meta.tokens = {"hit": 10}
    fake_catalog = {
        "basic_expensive": ("basic", {"hit": 7}),
        "basic_cheap": ("basic", {"hit": 3}),
        "weapon_expensive": ("weapon", {"crit": 7}),
    }

    def fake_get_feint_catalog_entry(feint_id: str):
        group, cost = fake_catalog[feint_id]
        return SimpleNamespace(
            technical=SimpleNamespace(
                feint_id=feint_id,
                cost=SimpleNamespace(tactics=cost),
                purchase_group=group,
            )
        )

    picked_from_free_pool: list[list[str]] = []

    def fake_choice(pool: list[str]) -> str:
        picked_from_free_pool.append(list(pool))
        return "basic_cheap"

    monkeypatch.setattr(CombatCatalogIntegrator, "get_feint_catalog_entry", fake_get_feint_catalog_entry)
    monkeypatch.setattr("src.backend.features.combat.runtime.engine.feint_service.random.choice", fake_choice)

    FeintService.refill_hand(source.meta, hand_size=3)

    assert source.meta.feints.hand == {
        "basic_expensive": {"hit": 7},
        "basic_cheap": {"hit": 3},
    }
    assert picked_from_free_pool == [["basic_cheap"]]
    assert source.meta.tokens == {"hit": 0}


@pytest.mark.unit
def test_feint_service_refill_skips_feints_with_active_exclusive_prep_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    source = actor(1, "a")
    source.meta.feints.arsenal = ["cheap_parry_counter", "other_parry_tool"]
    source.meta.tokens = {"parry": 10}

    fake_feints = {
        "cheap_parry_counter": {
            "cost": {"parry": 3},
            "preparation_effects": [{"id": "prep_perfect_riposte", "target_actor": "source"}],
        },
        "other_parry_tool": {
            "cost": {"parry": 3},
            "preparation_effects": [{"id": "prep_second_breath", "target_actor": "source"}],
        },
    }
    fake_effect_channels = {
        "prep_counter_on_parry": "next_parry.counter",
        "prep_perfect_riposte": "next_parry.counter",
        "prep_second_breath": "next_parry.heal",
    }

    def fake_get_feint_catalog_entry(feint_id: str):
        data = fake_feints[feint_id]
        return SimpleNamespace(
            technical=SimpleNamespace(
                feint_id=feint_id,
                cost=SimpleNamespace(tactics=data["cost"]),
                purchase_group="basic",
                preparation_effects=data["preparation_effects"],
            )
        )

    def fake_get_effect_catalog_entry(effect_id: str):
        return SimpleNamespace(technical=SimpleNamespace(exclusive_channel=fake_effect_channels.get(effect_id)))

    monkeypatch.setattr(CombatCatalogIntegrator, "get_feint_catalog_entry", fake_get_feint_catalog_entry)
    monkeypatch.setattr(CombatCatalogIntegrator, "get_effect_catalog_entry", fake_get_effect_catalog_entry)

    FeintService.refill_hand(
        source.meta,
        hand_size=2,
        active_effect_ids={"prep_counter_on_parry"},
    )

    assert source.meta.feints.hand == {"other_parry_tool": {"parry": 3}}
    assert source.meta.tokens == {"parry": 7}


@pytest.mark.unit
def test_session_integration_recovers_feint_arsenal_from_loadout() -> None:
    snapshot = CombatSessionIntegration(None)._build_snapshot(
        "1",
        "team_1",
        {"hp": 10, "max_hp": 10, "en": 0, "max_en": 0, "tokens": {"hit": 2}, "feints": {}},
        {},
        {"known_feints": ["future_feint_placeholder"]},
        {"name": "a", "type": "player"},
        {"abilities": [], "effects": []},
        {},
        {},
    )

    assert snapshot.meta.feints.arsenal == ["future_feint_placeholder"]


@pytest.mark.unit
def test_feint_service_reroll_preserves_pinned_and_refunds_unpinned() -> None:
    source = actor(1, "a")
    source.meta.feints.arsenal = ["future_feint_placeholder", "another_future_feint"]
    source.meta.feints.hand = {
        "future_feint_placeholder": {"hit": 2},
        "another_future_feint": {"hit": 3},
    }
    source.meta.feints.pinned = "future_feint_placeholder"

    FeintService.reroll_hand(source.meta, hand_size=1)

    assert source.meta.feints.hand == {"future_feint_placeholder": {"hit": 2}}
    assert source.meta.feints.pinned == "future_feint_placeholder"
    assert source.meta.tokens["hit"] == 3


@pytest.mark.unit
def test_mechanics_service_ignores_status_application_with_active_exclusive_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    source = actor(1, "a")
    target = actor(2, "b")
    target.statuses.effects.append(
        ActiveEffectDTO(
            uid="existing_counter",
            effect_id="prep_counter_on_parry",
            source_id=2,
            expire_at_exchange=999,
        )
    )
    incoming = ActiveEffectDTO(
        uid="incoming_riposte",
        effect_id="prep_perfect_riposte",
        source_id=2,
        expire_at_exchange=999,
    )
    result = InteractionResultDTO(source_id=1, target_id=2)
    result.status_applications.append(
        CombatStatusApplicationDTO(
            actor_id=target.char_id,
            source_id=target.char_id,
            effect_id=incoming.effect_id,
            active_effect=incoming.model_dump(mode="json"),
        )
    )

    fake_effect_channels = {
        "prep_counter_on_parry": "next_parry.counter",
        "prep_perfect_riposte": "next_parry.counter",
    }

    def fake_get_effect_catalog_entry(effect_id: str):
        return SimpleNamespace(
            technical=SimpleNamespace(
                exclusive_channel=fake_effect_channels.get(effect_id),
                modifier_applications=[],
            )
        )

    monkeypatch.setattr(CombatCatalogIntegrator, "get_effect_catalog_entry", fake_get_effect_catalog_entry)

    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, result)

    assert [effect.effect_id for effect in target.statuses.effects] == ["prep_counter_on_parry"]


@pytest.mark.unit
def test_executor_flow_does_not_refund_unknown_feint_cost() -> None:
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a")})
    move = CombatMoveDTO(
        move_id="m1",
        char_id=1,
        strategy="exchange",
        payload=ExchangePayload(target_id=2, feint_id="future_feint_placeholder"),
    )
    result = InteractionResultDTO(source_id=1, target_id=2)
    result.chain_events.preserve_feint = True

    CombatExecutor._refund_feint_cost_if_needed(ctx, result, move)

    assert ctx.actors["1"].meta.tokens == {}


@pytest.mark.unit
async def test_result_support_task_payload_captures_actor_refs_and_analytics_slice() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.stats = stats({"accuracy": 0.8, "crit_chance": 0.2, "physical_suppression": 0.1}, {"skill_parrying": 0.3})
    target.stats = stats({"evasion": 0.4, "parry": 0.5, "block": 0.6, "armor": 7.0}, {"skill_parrying": 0.2})
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": source, "2": target})
    result = InteractionResultDTO(source_id=1, target_id=2, is_hit=True, damage_final=6)
    result.damage_trace = CombatDamageTraceDTO(
        raw=16.0,
        final=6.0,
        min=14.0,
        max=18.0,
        details={
            "dbp": {"attribute": 12.0, "weapon": 4.0, "bonus": 0.0},
            "resl": {"raw": 0.2, "effective": 0.1, "suppression": 0.5, "after": 14.4},
            "arm": {"raw": 8.0, "effective": 6.0, "ignored": 2.0, "chance": 0.25, "passed": True},
            "after_absorb": 6.0,
        },
    )
    result.fired_triggers.append("style_dual_cross_cut")
    result.trigger_attempts.append(
        CombatTriggerAttemptDTO(
            trigger_id="style_dual_cross_cut",
            event="ON_CRIT",
            source="style",
            source_id="skill_dual_wield",
            chance=0.25,
            roll=0.25,
            passed=True,
            display_policy="separate",
            tags=["style", "dual_wield", "crit", "cross_cut"],
        )
    )
    result.trigger_attempts.append(
        CombatTriggerAttemptDTO(
            trigger_id="crit.weapon_serrated_bleed_crit",
            event="ON_CRIT",
            source="weapon",
            source_id="short_sword",
            source_slot="main_hand",
            chance=0.35,
            roll=0.8,
            passed=False,
        )
    )
    result.mutation_facts.append(
        CombatPipelineMutationFactDTO(
            source="feint",
            source_id="armor_slip",
            mutation_id="m1",
            path="mods.flat_armor_penetration_bonus_pct",
            value=0.5,
        )
    )
    result.trigger_facts.append(
        CombatTriggerFactDTO(
            trigger_id="style_dual_cross_cut",
            event="ON_CRIT",
            source="style",
            source_id="skill_dual_wield",
            chance=0.25,
            display_policy="separate",
            tags=["style", "dual_wield", "crit", "cross_cut"],
        )
    )
    result.chain_events.trigger_offhand_attack = True
    result.reflected_damage = 2
    result.resource_facts.append(
        CombatResourceFactDTO(
            actor_id=1,
            owner="source",
            resource="hp",
            reason="reflect",
            delta=-2,
            before=50,
            after=48,
            max=100,
            tags=["REFLECT"],
        )
    )
    result.effect_facts.append(
        CombatEffectFactDTO(actor_id=2, owner="target", effect_id="dot_bleed", action="apply", duration=2)
    )
    result.death_facts.append(CombatDeathFactDTO(actor_id=2, owner="target", reason="damage"))
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
    assert data_service.analytics[0][1]["v"] == 2
    assert data_service.analytics[0][1]["analytics_schema_version"] == 2
    assert data_service.analytics[0][1]["combat_math_version"] == "combat-math:2026-06-01.1"
    assert data_service.analytics[0][1]["t"] == 1
    assert data_service.analytics[0][1]["w"] == 3
    assert data_service.analytics[0][1]["st"] == payload.stat_slice
    assert data_service.analytics[0][1]["trg"] == ["style_dual_cross_cut"]
    assert data_service.analytics[0][1]["tf"] == [
        [
            "style_dual_cross_cut",
            "crit",
            "st",
            "skill_dual_wield",
            None,
            0.25,
            "separate",
            ["style", "dual_wield", "crit", "cross_cut"],
        ]
    ]
    assert data_service.analytics[0][1]["trga"] == [
        [
            "style_dual_cross_cut",
            "crit",
            "st",
            "skill_dual_wield",
            None,
            0.25,
            0.25,
            1,
            "separate",
            ["style", "dual_wield", "crit", "cross_cut"],
        ],
        ["crit.weapon_serrated_bleed_crit", "crit", "w", "short_sword", "main_hand", 0.35, 0.8, 0, "merge", []],
    ]
    assert data_service.analytics[0][1]["mut"] == [
        ["f", "armor_slip", "m1", "mods.flat_armor_penetration_bonus_pct", 0.5, []]
    ]
    assert data_service.analytics[0][1]["dt"]["details"]["dbp"]["weapon"] == 4.0
    assert data_service.analytics[0][1]["dt"]["details"]["arm"]["ignored"] == 2.0
    assert data_service.analytics[0][1]["chn"] == ["oh"]
    assert data_service.analytics[0][1]["rf"] == [["1", "s", "hp", "reflect", -2, 50, 48, 100, ["REFLECT"]]]
    assert data_service.analytics[0][1]["ef"] == [["2", "d", "dot_bleed", "a", None, None, 2, []]]
    assert data_service.analytics[0][1]["df"] == [["2", "d", "damage", []]]
    assert data_service.analytics[0][1]["x"] == {"ref": 2}


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
async def test_executor_no_longer_publishes_exchange_logs_to_chat() -> None:
    assert not hasattr(executor_task, "_publish_combat_logs_to_chat")
    assert not hasattr(executor_task, "_combat_log_chat_payload")
    source = inspect.getsource(executor_task)
    assert "chat.combat_log_message" not in source
    assert "CombatChatPublished" not in source


@pytest.mark.unit
async def test_start_announcement_publishes_once_from_collector_context() -> None:
    redis = CapturingChatRedis()
    data_service = AnnouncementDataService()

    await publish_combat_start_announcement({"redis_client_internal": redis}, data_service, "combat-1")
    await publish_combat_start_announcement({"redis_client_internal": redis}, data_service, "combat-1")

    assert len(redis.xadds) == 1
    payload = redis.xadds[0][0][1]
    assert payload["type"] == "player.notice"
    assert payload["template_key"] == "combat.started"
    assert payload["presentation"] == "system_chat"
    assert json.loads(payload["character_ids"]) == [1]
    assert json.loads(payload["variables"])["participants"] == (
        "Команда 1: Hero[42/100] против Команда 2: Wolf[0/60]"
    )
    encoded = str(redis.xadds[0])
    assert "chat.combat_message" not in encoded
    assert "chat.combat_log_message" not in encoded


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
    payload = redis.xadds[0][0][1]
    variables = json.loads(payload["variables"])
    assert payload["type"] == "player.notice"
    assert payload["template_key"] == "combat.finished"
    assert payload["presentation"] == "system_chat"
    assert variables["outcome"] == "победила Команда 1: Hero[42/100] на ходу 12"
    assert variables["participants"] == "Команда 1: Hero[42/100]; Команда 2: Wolf[0/60]"
    encoded = str(redis.xadds[0])
    assert "chat.combat_message" not in encoded
    assert "chat.combat_log_message" not in encoded


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
def test_mechanics_grants_one_gift_token_to_source_for_exchange_action() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    ctx = PipelineContextDTO()
    ctx.flags.meta.action_mode = "exchange"
    ctx.flags.meta.grant_exchange_gift = True
    result = InteractionResultDTO(source_id=1, target_id=2)

    MechanicsService().apply_interaction_result(ctx, source, target, result)

    assert source.meta.tokens["gift"] == 1
    assert result.tokens_awarded_attacker["gift"] == 1
    assert result.token_facts[-1].model_dump() == {
        "actor_id": "1",
        "owner": "source",
        "token": "gift",
        "amount": 1,
        "before": 0,
        "after": 1,
        "reason": "exchange",
        "source_action_id": None,
        "source_effect_id": None,
        "source_trigger_id": None,
        "tags": ["exchange"],
    }


@pytest.mark.unit
def test_mechanics_does_not_grant_exchange_gift_for_unidirectional_action() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    ctx = PipelineContextDTO()
    ctx.flags.meta.action_mode = "unidirectional"
    result = InteractionResultDTO(source_id=1, target_id=2)

    MechanicsService().apply_interaction_result(ctx, source, target, result)

    assert "gift" not in source.meta.tokens
    assert "gift" not in result.tokens_awarded_attacker
    assert not result.token_facts


@pytest.mark.unit
def test_mechanics_applies_gift_token_cost_from_ability_resource_changes() -> None:
    source = actor(1, "a")
    source.meta.tokens["gift"] = 2
    target = actor(2, "b")
    ctx = PipelineContextDTO()
    ctx.flags.meta.action_mode = "unidirectional"
    result = InteractionResultDTO(source_id=1, target_id=2, resource_changes={"gift": {"cost": "-1"}})

    MechanicsService().apply_interaction_result(ctx, source, target, result)

    assert source.meta.tokens["gift"] == 1
    assert [fact.model_dump() for fact in result.token_facts] == [
        {
            "actor_id": "1",
            "owner": "source",
            "token": "gift",
            "amount": -1,
            "before": 2,
            "after": 1,
            "reason": "cost",
            "source_action_id": None,
            "source_effect_id": None,
            "source_trigger_id": None,
            "tags": ["cost"],
        }
    ]


@pytest.mark.unit
def test_mechanics_applies_generic_combat_token_cost_from_ability_resource_changes() -> None:
    source = actor(1, "a")
    source.meta.tokens["tempo"] = 2
    target = actor(2, "b")
    ctx = PipelineContextDTO()
    ctx.flags.meta.action_mode = "unidirectional"
    result = InteractionResultDTO(source_id=1, target_id=2, resource_changes={"tempo": {"cost": "-1"}})

    MechanicsService().apply_interaction_result(ctx, source, target, result)

    assert source.meta.tokens["tempo"] == 1
    assert [fact.model_dump() for fact in result.token_facts] == [
        {
            "actor_id": "1",
            "owner": "source",
            "token": "tempo",
            "amount": -1,
            "before": 2,
            "after": 1,
            "reason": "cost",
            "source_action_id": None,
            "source_effect_id": None,
            "source_trigger_id": None,
            "tags": ["cost"],
        }
    ]


@pytest.mark.unit
def test_mechanics_accumulates_blood_token_progress_from_survived_damage() -> None:
    source = actor(1, "a")
    target = actor(2, "b", hp=100)

    first = InteractionResultDTO(source_id=1, target_id=2, damage_final=5, is_hit=True)
    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, first)

    assert target.meta.hp == 95
    assert target.meta.token_progress["blood"] == 5
    assert "blood" not in target.meta.tokens
    assert not first.token_facts

    target.meta.hp = 100
    second = InteractionResultDTO(source_id=1, target_id=2, damage_final=5, is_hit=True)
    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, second)

    assert target.meta.hp == 95
    assert target.meta.token_progress["blood"] == 0
    assert target.meta.tokens["blood"] == 1
    assert second.tokens_awarded_defender["blood"] == 1
    assert second.token_facts[-1].token == "blood"
    assert second.token_facts[-1].reason == "damage_taken"


@pytest.mark.unit
def test_mechanics_accumulates_pressure_token_progress_from_dealt_damage() -> None:
    source = actor(1, "a")
    target = actor(2, "b", hp=100)

    first = InteractionResultDTO(source_id=1, target_id=2, damage_final=5, is_hit=True)
    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, first)

    assert target.meta.hp == 95
    assert source.meta.token_progress["pressure"] == 5
    assert "pressure" not in source.meta.tokens
    assert all(fact.token != "pressure" for fact in first.token_facts)

    target.meta.hp = 100
    second = InteractionResultDTO(source_id=1, target_id=2, damage_final=5, is_hit=True)
    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, second)

    assert target.meta.hp == 95
    assert source.meta.token_progress["pressure"] == 0
    assert source.meta.tokens["pressure"] == 1
    assert second.tokens_awarded_attacker["pressure"] == 1
    assert any(fact.token == "pressure" and fact.reason == "damage_dealt" for fact in second.token_facts)


@pytest.mark.unit
def test_mechanics_does_not_award_blood_token_progress_to_dead_actor() -> None:
    source = actor(1, "a")
    target = actor(2, "b", hp=8)
    target.meta.max_hp = 100
    target.meta.token_progress["blood"] = 9

    result = InteractionResultDTO(source_id=1, target_id=2, damage_final=20, is_hit=True)
    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, result)

    assert target.meta.hp == 0
    assert target.meta.is_dead is True
    assert target.meta.token_progress["blood"] == 9
    assert "blood" not in target.meta.tokens
    assert "blood" not in result.tokens_awarded_defender
    assert not result.token_facts


@pytest.mark.unit
def test_ability_post_process_registers_hp_and_stamina_combat_regen() -> None:
    source = actor(1, "a")
    source.meta.hp = 10
    source.meta.max_hp = 20
    source.meta.en = 4
    source.meta.max_en = 10
    source.meta.stamina = 5
    source.meta.max_stamina = 15
    source.stats = stats({"hp_regen": 0.96, "en_regen": 2.4, "stamina_regen": 3.0})
    ctx = PipelineContextDTO()
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    AbilityService().post_process(ctx, source, None, move)

    assert ctx.result.resource_changes == {
        "hp": {"combat_regen": "+1"},
        "stamina": {"combat_regen": "+3"},
    }

    MechanicsService().apply_interaction_result(ctx, source, None, ctx.result)
    assert source.meta.hp == 11
    assert source.meta.en == 4
    assert source.meta.stamina == 8
    assert [(fact.actor_id, fact.resource, fact.reason, fact.delta) for fact in ctx.result.resource_facts] == [
        ("1", "hp", "combat_regen", 1),
        ("1", "stamina", "combat_regen", 3),
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
        and entry["template"]["key"] == "combat.effect.dot_bleed.tick.humanoid.hp"
        and entry["result"]["resources"] == [
            {"actor_id": "1", "resource": "hp", "before": 100, "after": 98, "max": 100, "delta": -2, "label": "HP 98/100"}
        ]
        for entry in ctx.pending_logs
    )


@pytest.mark.unit
async def test_executor_applies_explicit_combat_regen_resource_changes_to_current_exchange_actors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fixed_result(self, source, target, move, exchange_count=0, external_mods=None):
        return InteractionResultDTO(
            source_id=source.char_id,
            target_id=target.char_id,
            resource_changes={
                "hp": {"combat_regen": "+1"},
                "stamina": {"combat_regen": "+3"},
            },
        )

    monkeypatch.setattr(CombatPipeline, "calculate", fixed_result)
    ctx = BattleContext(
        session_id="c1",
        meta=battle_meta(),
        actors={"1": actor(1, "a"), "2": actor(2, "b"), "3": actor(3, "b", hp=0)},
    )
    ctx.actors["1"].meta.hp = 10
    ctx.actors["1"].meta.en = 4
    ctx.actors["1"].meta.max_en = 10
    ctx.actors["1"].meta.stamina = 5
    ctx.actors["1"].stats = stats({"hp_regen": 1.0, "en_regen": 2.0, "stamina_regen": 3.0})
    ctx.actors["2"].meta.hp = 10
    ctx.actors["2"].meta.en = 4
    ctx.actors["2"].meta.max_en = 10
    ctx.actors["2"].meta.stamina = 5
    ctx.actors["2"].stats = stats({"hp_regen": 1.0, "en_regen": 2.0, "stamina_regen": 3.0})
    ctx.actors["3"].meta.hp = 10
    ctx.actors["3"].meta.en = 4
    ctx.actors["3"].meta.max_en = 10
    ctx.actors["3"].meta.stamina = 5
    ctx.actors["3"].stats = stats({"hp_regen": 10.0, "en_regen": 10.0, "stamina_regen": 10.0})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        partner_move=CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1)),
        is_forced=True,
    )

    await CombatExecutor().process_batch(ctx, [action])

    assert ctx.actors["1"].meta.hp == 11
    assert ctx.actors["1"].meta.en == 4
    assert ctx.actors["1"].meta.stamina == 8
    assert ctx.actors["2"].meta.hp == 11
    assert ctx.actors["2"].meta.en == 4
    assert ctx.actors["2"].meta.stamina == 8
    assert ctx.actors["3"].meta.hp == 10
    assert ctx.actors["3"].meta.en == 4
    assert ctx.actors["3"].meta.stamina == 5


@pytest.mark.unit
async def test_exchange_stun_applies_on_next_exchange_without_canceling_partner_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, bool]] = []
    stun_applied = False

    async def fixed_result(self, source, target, move, exchange_count=0, external_mods=None):
        nonlocal stun_applied
        source_stunned = any(effect.effect_id == "stun" for effect in source.statuses.effects)
        calls.append((str(source.char_id), str(target.char_id), source_stunned))
        result = InteractionResultDTO(source_id=source.char_id, target_id=target.char_id)
        if source_stunned:
            result.skip_reason = "CONTROLLED"
            return result
        result.is_hit = True
        result.damage_final = 1
        if str(source.char_id) == "1" and not stun_applied:
            stun_applied = True
            result.status_applications.append(
                CombatStatusApplicationDTO(
                    actor_id=target.char_id,
                    source_id=source.char_id,
                    effect_id="stun",
                    active_effect={
                        "uid": "stun",
                        "effect_id": "stun",
                        "source_id": source.char_id,
                        "active_from_exchange": target.meta.exchange_counter + 1,
                        "expire_at_exchange": target.meta.exchange_counter + 2,
                    },
                )
            )
        return result

    monkeypatch.setattr(CombatPipeline, "calculate", fixed_result)
    ctx = BattleContext(session_id="c1", meta=battle_meta(), actors={"1": actor(1, "a"), "2": actor(2, "b")})
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        partner_move=CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1)),
    )

    await CombatExecutor().process_batch(ctx, [action])

    assert calls == [("1", "2", False), ("2", "1", False)]
    assert ctx.actors["1"].meta.hp == 99
    assert ctx.actors["2"].meta.hp == 99
    assert [effect.effect_id for effect in ctx.actors["2"].statuses.effects] == ["stun"]

    await CombatExecutor().process_batch(ctx, [action])

    assert calls[-2:] == [("1", "2", False), ("2", "1", True)]
    assert ctx.actors["1"].meta.hp == 99
    assert ctx.actors["2"].meta.hp == 98
    assert ctx.actors["2"].statuses.effects == []


@pytest.mark.unit
async def test_exchange_commits_simultaneous_lethal_main_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fixed_result(self, source, target, move, exchange_count=0, external_mods=None):
        return InteractionResultDTO(source_id=source.char_id, target_id=target.char_id, is_hit=True, damage_final=10)

    monkeypatch.setattr(CombatPipeline, "calculate", fixed_result)
    ctx = BattleContext(
        session_id="c1",
        meta=battle_meta(),
        actors={"1": actor(1, "a", hp=5), "2": actor(2, "b", hp=5)},
    )
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        partner_move=CombatMoveDTO(move_id="m2", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1)),
    )

    await CombatExecutor().process_batch(ctx, [action])

    assert ctx.actors["1"].meta.hp == 0
    assert ctx.actors["2"].meta.hp == 0
    assert ctx.actors["1"].meta.is_dead is True
    assert ctx.actors["2"].meta.is_dead is True
    assert sorted(ctx.pending_dead_actors) == ["1", "2"]


@pytest.mark.unit
async def test_executor_resolves_aoe_feint_secondaries_as_unidirectional_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    async def fixed_result(self, source, target, move, exchange_count=0, external_mods=None):
        mods = dict(external_mods or {})
        calls.append((str(source.char_id), str(target.char_id), mods))
        return InteractionResultDTO(source_id=source.char_id, target_id=target.char_id, is_hit=True)

    def feint_entry(feint_id: str):
        if feint_id != "test_aoe_feint":
            return None
        return SimpleNamespace(
            technical=SimpleNamespace(
                target=TargetType.ALL_ENEMIES,
                target_count=3,
                secondary_damage_mult=0.75,
                cost=SimpleNamespace(tactics={"hit": 1}),
            )
        )

    monkeypatch.setattr(CombatPipeline, "calculate", fixed_result)
    monkeypatch.setattr(CombatCatalogIntegrator, "get_feint_catalog_entry", staticmethod(feint_entry))

    ctx = BattleContext(
        session_id="c1",
        meta=battle_meta().model_copy(
            update={
                "teams": {"a": [1], "b": [2, 3, 4]},
                "actors_info": {"1": "player", "2": "ai", "3": "ai", "4": "ai"},
            }
        ),
        actors={"1": actor(1, "a"), "2": actor(2, "b"), "3": actor(3, "b"), "4": actor(4, "b")},
    )
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="exchange",
            payload=ExchangePayload(target_id=2, feint_id="test_aoe_feint"),
        ),
        is_forced=True,
    )

    await CombatExecutor().process_batch(ctx, [action])

    assert calls == [
        ("1", "2", {"action_mode": "exchange"}),
        (
            "1",
            "3",
            {
                "action_mode": "unidirectional",
                "damage_mult": 0.75,
                "feint_role": "secondary",
                "pay_cost": False,
                "generate_feints": False,
            },
        ),
        (
            "1",
            "4",
            {
                "action_mode": "unidirectional",
                "damage_mult": 0.75,
                "feint_role": "secondary",
                "pay_cost": False,
                "generate_feints": False,
            },
        ),
    ]
    assert ctx.meta.step_counter == 1
    assert ctx.actors["1"].meta.exchange_counter == 1
    assert ctx.actors["2"].meta.exchange_counter == 1
    assert ctx.actors["3"].meta.exchange_counter == 0
    assert ctx.actors["4"].meta.exchange_counter == 0
    assert ctx.pending_target_returns == [{"source_id": "1", "target_id": "2"}]


@pytest.mark.unit
async def test_executor_resolves_multi_target_instant_ability_with_damage_penalty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    async def fixed_result(self, source, target, move, exchange_count=0, external_mods=None):
        mods = dict(external_mods or {})
        calls.append((str(source.char_id), str(target.char_id), mods))
        return InteractionResultDTO(source_id=source.char_id, target_id=target.char_id, is_hit=True, damage_final=10)

    monkeypatch.setattr(CombatPipeline, "calculate", fixed_result)

    ctx = BattleContext(
        session_id="c1",
        meta=battle_meta().model_copy(
            update={
                "teams": {"a": [1], "b": [2, 3, 4]},
                "actors_info": {"1": "player", "2": "ai", "3": "ai", "4": "ai"},
            }
        ),
        actors={"1": actor(1, "a"), "2": actor(2, "b"), "3": actor(3, "b"), "4": actor(4, "b")},
    )
    action = CombatActionDTO(
        action_type="instant",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="instant",
            payload=InstantPayload(ability_id="basic_splinter_strike", target_id=[2, 3, 4]),
            targets=[2, 3, 4],
        ),
    )

    await CombatExecutor().process_batch(ctx, [action])

    assert calls == [
        ("1", "2", {"action_mode": "unidirectional", "damage_mult": 0.5}),
        ("1", "3", {"action_mode": "unidirectional", "damage_mult": 0.5}),
        ("1", "4", {"action_mode": "unidirectional", "damage_mult": 0.5}),
    ]


@pytest.mark.unit
async def test_executor_resolves_self_instant_targets_when_collector_did_not_prefill_targets() -> None:
    source = actor(1, "a")
    source.meta.en = 20
    source.meta.tokens.update({"tempo": 5, "pressure": 5, "gift": 1})
    source.raw.modifiers["hp_regen"] = {"base": 4.0, "source": {}, "temp": {}}
    source.raw.modifiers["physical_damage_bonus"] = {"base": 0.0, "source": {}, "temp": {}}
    source.raw.modifiers["vampiric_power"] = {"base": 0.0, "source": {}, "temp": {}}
    ctx = BattleContext(
        session_id="c1",
        meta=battle_meta(),
        actors={"1": source, "2": actor(2, "b")},
    )
    action = CombatActionDTO(
        action_type="instant",
        move=CombatMoveDTO(
            move_id="m1",
            char_id=1,
            strategy="instant",
            payload=InstantPayload(ability_id="basic_blood_hunger", target_id=1),
        ),
    )

    await CombatExecutor().process_batch(ctx, [action])

    assert source.statuses.abilities == []
    assert [effect.effect_id for effect in source.statuses.effects] == ["basic_blood_hunger"]
    assert source.raw.modifiers["vampiric_power"]["temp"]
    assert source.meta.tokens.get("blood", 0) == 0
    assert source.meta.tokens["tempo"] == 0
    assert source.meta.tokens["pressure"] == 0
    assert source.meta.tokens["gift"] == 0
    assert source.meta.ability_cooldowns["basic_blood_hunger"] == 11


@pytest.mark.unit
async def test_executor_cleave_buff_splashes_final_damage_to_extra_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fixed_result(self, source, target, move, exchange_count=0, external_mods=None):
        return InteractionResultDTO(
            source_id=source.char_id,
            target_id=target.char_id,
            is_hit=True,
            damage_final=100,
        )

    monkeypatch.setattr(CombatPipeline, "calculate", fixed_result)
    source = actor(1, "a")
    source.raw.modifiers["cleave_damage_mult"] = {"base": 0.30, "source": {}, "temp": {}}
    source.raw.modifiers["cleave_target_count"] = {"base": 2.0, "source": {}, "temp": {}}
    ctx = BattleContext(
        session_id="c1",
        meta=battle_meta().model_copy(
            update={
                "teams": {"a": [1], "b": [2, 3, 4]},
                "actors_info": {"1": "player", "2": "ai", "3": "ai", "4": "ai"},
            }
        ),
        actors={"1": source, "2": actor(2, "b"), "3": actor(3, "b"), "4": actor(4, "b")},
    )
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        is_forced=True,
    )

    await CombatExecutor().process_batch(ctx, [action])

    assert ctx.actors["2"].meta.hp == 0
    assert ctx.actors["3"].meta.hp == 70
    assert ctx.actors["4"].meta.hp == 70


@pytest.mark.unit
def test_context_builder_can_mark_secondary_hits_as_costless_one_way() -> None:
    ctx = ContextBuilder.build_context(
        actor(1, "a"),
        actor(2, "b"),
        CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2)),
        external_mods={
            "action_mode": "unidirectional",
            "feint_role": "secondary",
            "pay_cost": False,
            "generate_feints": False,
        },
    )

    assert ctx.flags.meta.action_mode == "unidirectional"
    assert ctx.flags.meta.grant_exchange_gift is False
    assert ctx.flags.mechanics.pay_cost is False
    assert ctx.flags.mechanics.generate_feints is False


@pytest.mark.unit
async def test_crit_bleed_trigger_is_cancelled_when_attack_is_parried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: False)
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
    assert result.is_hit is True
    assert result.tokens_awarded_attacker == {"crit": 1}
    assert result.tokens_awarded_defender == {"parry": 1}
    assert target.statuses.effects == []
    assert "APPLY_EFFECT" not in [event.type for event in result.events]


@pytest.mark.unit
def test_dual_wield_style_activates_crit_trigger_and_guarantees_offhand_from_loadout() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout.update(
        {
            "main_hand": "skill_swords",
            "off_hand": "skill_fencing",
            "tactical_style": "skill_dual_wield",
            "tactical_style_trigger": "crit.style_dual_cross_cut",
        }
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    ctx = ContextBuilder.build_context(source, target, move)

    assert ctx.triggers.crit.style_dual_cross_cut is True
    assert ctx.trigger_activations["style_dual_cross_cut"][0].source == "style"
    assert ctx.trigger_activations["style_dual_cross_cut"][0].source_id == "skill_dual_wield"
    assert ctx.result.chain_events.trigger_offhand_attack is True


@pytest.mark.unit
def test_dual_wield_style_does_not_activate_for_offhand_chain() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout.update(
        {
            "main_hand": "skill_swords",
            "off_hand": "skill_fencing",
            "tactical_style": "skill_dual_wield",
            "tactical_style_trigger": "crit.style_dual_cross_cut",
        }
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    ctx = ContextBuilder.build_context(source, target, move, external_mods={"hand": "off"})

    assert ctx.flags.meta.source_type == "off_hand"
    assert ctx.triggers.crit.style_dual_cross_cut is True
    assert "style_dual_cross_cut" in ctx.trigger_activations
    assert ctx.result.chain_events.trigger_offhand_attack is False


@pytest.mark.unit
def test_dual_wield_cross_cut_fixed_chance_scales_crit_power_with_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda _chance: (0.0, True)))
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout.update(
        {
            "main_hand": "skill_swords",
            "off_hand": "skill_fencing",
            "tactical_style": "skill_dual_wield",
            "tactical_style_trigger": "crit.style_dual_cross_cut",
        }
    )
    source.stats = stats(
        {
            "main_hand_accuracy": 1.0,
            "main_hand_crit_chance": 1.0,
            "main_hand_crit_cap": 1.0,
            "main_hand_damage_base": 10.0,
            "main_hand_damage_spread": 0.0,
        },
        {"skill_dual_wield": 1.0, "skill_swords": 1.0},
    )
    target.stats = stats()
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)
    ctx.flags.force.hit = True
    ctx.flags.force.crit = True
    ctx.stages.check_evasion = False
    ctx.stages.check_parry = False
    ctx.stages.check_block = False
    ctx.flags.formula.crit_damage_boost = True
    ctx.mods.weapon_effect_value = 2.0

    result = CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    assert result.is_crit is True
    assert result.crit_mult == pytest.approx(6.0)
    assert result.damage_final == 60
    assert result.fired_triggers == ["style_dual_cross_cut"]
    assert result.trigger_facts[0].chance == pytest.approx(0.25)
    assert ctx.mods.crit_damage_mult == pytest.approx(3.0)


@pytest.mark.unit
def test_ranged_combat_style_activates_on_defender_from_loadout() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    target.loadout.layout.update(
        {
            "main_hand": "skill_archery",
            "tactical_style": "skill_ranged_combat",
            "tactical_style_trigger": "dodge.style_ranged_perfect_backstep",
        }
    )
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    ctx = ContextBuilder.build_context(source, target, move)

    assert ctx.triggers.dodge.style_ranged_perfect_backstep is True
    assert ctx.trigger_activations["style_ranged_perfect_backstep"][0].source == "style"
    assert ctx.trigger_activations["style_ranged_perfect_backstep"][0].source_id == "skill_ranged_combat"
    assert ctx.stages.check_evasion is False
    assert ctx.stages.check_parry is False
    assert ctx.stages.check_block is False
    assert ctx.stages.check_ranged_position_defense is True


@pytest.mark.unit
def test_archery_attack_keeps_parry_block_and_dodge_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_parry_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        seen_parry_chances.append(chance)
        return None, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout["main_hand"] = "skill_archery"
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    ctx = ContextBuilder.build_context(source, target, move)
    result = InteractionResultDTO(source_id=1, target_id=2)

    assert ctx.flags.restriction.ignore_parry is False
    assert ctx.stages.check_evasion is True
    assert ctx.stages.check_block is True
    assert parry_step.run(
        stats(),
        stats({"parry": 1.0, "parry_cap": 1.0}, {"skill_parrying": 1.0}),
        ctx,
        result,
    ) is True
    assert result.is_parried is True
    assert seen_parry_chances == [pytest.approx(1.0)]


@pytest.mark.unit
def test_context_builder_exposes_active_ammo_effect_only_for_archery() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout["main_hand"] = "skill_archery"
    source.loadout.ammo_charges["main_hand"] = 2
    source.loadout.ammo_effects["main_hand"] = {
        "effects": [
            {
                "id": "dot_burn",
                "params": {"power": 2.0, "apply_bonus": 0.1},
                "tags": ["arrow", "fire"],
            },
            {
                "id": "debuff_accuracy",
                "params": {"power": 2.0},
                "tags": ["arrow", "fire", "accuracy_debuff"],
            },
        ]
    }
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    ctx = ContextBuilder.build_context(source, target, move)

    assert source.loadout.ammo_charges["main_hand"] == 2
    assert ctx.trigger_effect_payloads["main_hand"] == [
        {
            "id": "dot_burn",
            "params": {"power": 2.0, "apply_bonus": 0.1},
            "tags": ["arrow", "fire"],
        },
        {
            "id": "debuff_accuracy",
            "params": {"power": 2.0},
            "tags": ["arrow", "fire", "accuracy_debuff"],
        }
    ]

    source.loadout.layout["main_hand"] = "skill_swords"
    sword_ctx = ContextBuilder.build_context(source, target, move)

    assert sword_ctx.trigger_effect_payloads == {}


@pytest.mark.unit
def test_archery_crit_queues_active_ammo_effect_payload_and_spends_charge() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout.update(
        {
            "main_hand": "skill_archery",
            "main_hand_trigger": "crit.weapon_precision_crit",
        }
    )
    source.loadout.ammo_charges["main_hand"] = 1
    source.loadout.ammo_effects["main_hand"] = {
        "effects": [
            {
                "id": "dot_burn",
                "params": {"power": 2.0, "apply_bonus": 0.1},
                "tags": ["arrow", "fire"],
            },
            {
                "id": "debuff_accuracy",
                "params": {"power": 2.0},
                "tags": ["arrow", "fire", "accuracy_debuff"],
            },
        ]
    }
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))
    ctx = ContextBuilder.build_context(source, target, move)
    ctx.flags.force.crit = True
    result = ctx.result

    crit_step.run(stats(), stats(), ctx, result)

    ammo_effects = [effect for effect in result.applied_effects if effect.get("id") == "dot_burn"]
    assert ammo_effects == [
        {
            "id": "dot_burn",
            "params": {"power": 2.0, "apply_bonus": 0.1},
            "tags": ["arrow", "fire", "ammo", "crit"],
            "source_trigger_id": "ammo_arrow_crit",
            "conditions": {"is_hit": True, "is_crit": True},
        }
    ]
    accuracy_debuffs = [effect for effect in result.applied_effects if effect.get("id") == "debuff_accuracy"]
    assert accuracy_debuffs == [
        {
            "id": "debuff_accuracy",
            "params": {"power": 2.0},
            "tags": ["arrow", "fire", "accuracy_debuff", "ammo", "crit"],
            "source_trigger_id": "ammo_arrow_crit",
            "conditions": {"is_hit": True, "is_crit": True},
        }
    ]
    assert result.ammo_spent == {"main_hand": 1}
    assert result.trigger_facts[0].trigger_id == "weapon_precision_crit"


@pytest.mark.unit
def test_archery_crit_without_ammo_keeps_base_shot_without_payload() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.layout["main_hand"] = "skill_archery"
    source.loadout.ammo_charges["main_hand"] = 0
    source.loadout.ammo_effects["main_hand"] = {"id": "dot_burn", "params": {"power": 2.0}}
    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=2))

    ctx = ContextBuilder.build_context(source, target, move)
    ctx.flags.force.crit = True
    crit_step.run(stats(), stats(), ctx, ctx.result)

    assert ctx.trigger_effect_payloads == {}
    assert ctx.result.applied_effects == []
    assert ctx.result.ammo_spent == {}


@pytest.mark.unit
def test_mechanics_service_commits_ammo_spend_to_source_loadout() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    source.loadout.ammo_charges["main_hand"] = 2
    source.loadout.ammo_charge_caps["main_hand"] = 2
    result = InteractionResultDTO(source_id=1, target_id=2, ammo_spent={"main_hand": 1})

    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, result)

    assert source.loadout.ammo_charges["main_hand"] == 1
    assert result.resource_facts[-1] == CombatResourceFactDTO(
        actor_id=1,
        owner="source",
        resource="ammo",
        reason="ammo_crit",
        delta=-1,
        before=2,
        after=1,
        max=2,
        tags=["ammo", "main_hand"],
    )


@pytest.mark.unit
def test_ranged_position_service_commits_next_position_effect_from_trigger_override() -> None:
    archer = actor(1, "a")
    enemy = actor(2, "b")
    archer.loadout.layout.update({"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"})
    archer.meta.exchange_counter = 3
    archer.statuses.effects.append(
        ActiveEffectDTO(
            uid="old-position",
            effect_id="ranged_position",
            source_id=archer.char_id,
            active_from_exchange=3,
            expire_at_exchange=4,
            params={"position": "close"},
        )
    )
    archer.stats = stats(skills={"skill_ranged_combat": 0.2})
    enemy.stats = stats()
    result = InteractionResultDTO(source_id=archer.char_id, target_id=enemy.char_id)
    result.action_facts["next_ranged_position_override"] = "far"

    RangedPositionService.update_after_exchange([(archer, enemy, result)])

    positions = [effect for effect in archer.statuses.effects if effect.effect_id == "ranged_position"]
    assert len(positions) == 1
    assert positions[0].params["position"] == "far"
    assert positions[0].active_from_exchange == 4
    assert positions[0].expire_at_exchange == 5
    assert result.effect_facts[-1].effect_id == "ranged_position"
    assert result.effect_facts[-1].action == "apply"


@pytest.mark.unit
def test_force_ranged_close_effect_commits_close_position_for_archer_target() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    target.loadout.layout.update({"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"})
    target.meta.exchange_counter = 4
    result = InteractionResultDTO(source_id=source.char_id, target_id=target.char_id)
    result.applied_effects.append(
        {
            "id": "force_ranged_close",
            "target_id": target.char_id,
            "source_trigger_id": "weapon_knockdown_hit",
        }
    )

    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=target.char_id))

    AbilityService().post_process(PipelineContextDTO(result=result), source, target, move)

    positions = [effect for effect in target.statuses.effects if effect.effect_id == "ranged_position"]
    assert len(positions) == 1
    assert positions[0].params["position"] == "close"
    assert positions[0].active_from_exchange == 5
    assert positions[0].expire_at_exchange == 6
    assert [fact.effect_id for fact in result.effect_facts[-2:]] == ["ranged_position", "force_ranged_close"]
    assert result.effect_facts[-1].source_trigger_id == "weapon_knockdown_hit"


@pytest.mark.unit
def test_force_ranged_close_effect_ignores_non_ranged_target() -> None:
    source = actor(1, "a")
    target = actor(2, "b")
    result = InteractionResultDTO(source_id=source.char_id, target_id=target.char_id)
    result.applied_effects.append({"id": "force_ranged_close", "target_id": target.char_id})

    move = CombatMoveDTO(move_id="m1", char_id=1, strategy="exchange", payload=ExchangePayload(target_id=target.char_id))

    AbilityService().post_process(PipelineContextDTO(result=result), source, target, move)

    assert target.statuses.effects == []
    assert result.effect_facts == []


@pytest.mark.unit
def test_ranged_position_service_counts_incoming_melee_contact_pressure(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, int] = {}

    def fake_roll_next_position(**kwargs: Any) -> str:
        captured["damage_taken"] = kwargs["damage_taken"]
        captured["melee_pressure"] = kwargs["melee_pressure"]
        return "mid"

    monkeypatch.setattr(RangedPositionService, "roll_next_position", staticmethod(fake_roll_next_position))
    archer = actor(1, "a")
    enemy = actor(2, "b")
    archer.loadout.layout.update({"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"})
    archer.stats = stats(skills={"skill_ranged_combat": 0.15})
    enemy.stats = stats()
    archer_result = InteractionResultDTO(source_id=archer.char_id, target_id=enemy.char_id)
    melee_result = InteractionResultDTO(source_id=enemy.char_id, target_id=archer.char_id, damage_final=0)
    melee_result.checks.append(
        {"stage": "ranged_position_defense", "chance": 0.1, "roll": 0.2, "passed": False, "details": {"position": "far"}}
    )

    RangedPositionService.update_after_exchange([(archer, enemy, archer_result), (enemy, archer, melee_result)])

    assert captured == {"damage_taken": 0, "melee_pressure": 1}


@pytest.mark.unit
def test_ranged_combat_style_perfect_backstep_improves_current_position_without_forcing_dodge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_chances: list[float] = []
    rolls = iter([(0.0, True), (0.99, False)])

    def fake_roll_chance(chance: float) -> tuple[float, bool]:
        seen_chances.append(chance)
        return next(rolls)

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(fake_roll_chance))
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: False)
    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "main_hand"
    ctx.flags.meta.weapon_class = "swords"
    ctx.flags.meta.target_tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.target_ranged_position = "mid"
    ctx.stages.check_ranged_position_defense = True
    result = InteractionResultDTO(source_id=1, target_id=2)
    ctx.result = result
    activate_trigger(ctx, "dodge.style_ranged_perfect_backstep", source="style", source_id="skill_ranged_combat")

    dodged = ranged_position_defense_step.run(
        stats(),
        stats({"evasion": 0.5, "parry": 0.0}, {"skill_ranged_combat": 1.0}),
        ctx,
        result,
    )

    assert seen_chances == [pytest.approx(0.25), pytest.approx(0.575)]
    assert dodged is False
    assert result.is_dodged is False
    assert result.tokens_awarded_defender == {}
    assert result.trigger_facts[0].trigger_id == "style_ranged_perfect_backstep"
    assert ctx.flags.meta.target_ranged_position == "far"
    assert result.checks[0].details["position"] == "far"
    assert result.action_facts["ranged_current_target_position_applied"] == "far"
    assert result.action_facts["next_ranged_position_override"] == "far"
    assert result.is_ranged_punish is False
    assert result.applied_effects == []


@pytest.mark.unit
def test_ranged_combat_style_perfect_backstep_far_position_becomes_critical_punish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rolls = iter([(0.0, True), (0.99, False)])
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: next(rolls)))
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: False)
    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "main_hand"
    ctx.flags.meta.weapon_class = "swords"
    ctx.flags.meta.target_tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.target_ranged_position = "far"
    ctx.stages.check_ranged_position_defense = True
    result = InteractionResultDTO(source_id=1, target_id=2)
    ctx.result = result
    activate_trigger(ctx, "dodge.style_ranged_perfect_backstep", source="style", source_id="skill_ranged_combat")

    stopped = ranged_position_defense_step.run(
        stats({"armor": 3.0, "physical_resistance": 0.10}),
        stats({"main_hand_damage_base": 10.0, "evasion": 0.0, "parry": 0.0}, {"skill_ranged_combat": 1.0}),
        ctx,
        result,
    )

    assert stopped is False
    assert result.trigger_facts[0].trigger_id == "style_ranged_perfect_backstep"
    assert result.is_ranged_punish is True
    assert result.ranged_punish_damage == 16
    assert result.ranged_punish_crit_mult == pytest.approx(2.0)
    assert result.chain_events.trigger_counter_attack is False
    assert result.events[-1].type == "HIT"
    assert result.events[-1].source_id == "2"
    assert result.events[-1].target_id == "1"
    assert result.events[-1].tags == ["RANGED_PUNISH", "CRIT"]


@pytest.mark.unit
def test_ranged_far_punish_damage_is_applied_to_exchange_source() -> None:
    source = actor(1, "a", hp=40)
    target = actor(2, "b", hp=40)
    target.meta.token_progress["pressure"] = 5
    result = InteractionResultDTO(source_id=source.char_id, target_id=target.char_id)
    result.is_ranged_punish = True
    result.ranged_punish_damage = 15

    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, result)

    assert source.meta.hp == 25
    assert target.meta.hp == 40
    assert result.resource_facts[-1].actor_id == "1"
    assert result.resource_facts[-1].owner == "source"
    assert result.resource_facts[-1].reason == "ranged_far_punish"
    assert result.resource_facts[-1].delta == -15
    assert result.resource_facts[-1].source_trigger_id == "style_ranged_perfect_backstep"
    assert result.resource_facts[-1].tags == ["RANGED_PUNISH", "CRIT"]
    assert target.meta.tokens["pressure"] == 2
    assert result.tokens_awarded_defender["pressure"] == 2
    assert result.token_facts[-1].token == "pressure"
    assert result.token_facts[-1].reason == "damage_dealt"


@pytest.mark.unit
def test_legacy_ranged_repositioning_no_longer_reduces_outgoing_exchange() -> None:
    source = actor(2, "b")
    target = actor(1, "a")
    source.stats = stats(
        mods={"main_hand_damage_base": 20.0, "main_hand_accuracy": 1.0},
        skills={"skill_ranged_combat": 0.5},
    )
    source.statuses.effects.append(
        ActiveEffectDTO(
            uid="repositioning-1",
            effect_id="debuff_ranged_repositioning",
            source_id=source.char_id,
            expire_at_exchange=source.meta.exchange_counter + 1,
        )
    )
    move = CombatMoveDTO(move_id="m1", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1))
    ctx = ContextBuilder.build_context(source, target, move)
    ctx.mods.damage_mult = 0.8
    service = AbilityService()

    service.pre_process(ctx, move, source, target)
    ctx.result.is_hit = True
    service.post_process(ctx, source, target, move)

    assert ctx.mods.damage_mult == pytest.approx(0.8)
    assert source.statuses.effects == []
    assert ctx.result.effect_facts[-1].effect_id == "debuff_ranged_repositioning"
    assert ctx.result.effect_facts[-1].action == "expire"


@pytest.mark.unit
def test_queued_effect_duration_uses_effect_target_exchange_counter() -> None:
    source = actor(2, "b")
    target = actor(1, "a")
    source.meta.exchange_counter = 0
    target.meta.exchange_counter = 7
    move = CombatMoveDTO(move_id="m1", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1))
    ctx = ContextBuilder.build_context(source, target, move)
    ctx.result.applied_effects.append(
        {"id": "debuff_ranged_repositioning", "source_trigger_id": "style_ranged_perfect_backstep"}
    )

    AbilityService._apply_queued_effects(ctx, source, target)

    effect = target.statuses.effects[-1]
    assert effect.effect_id == "debuff_ranged_repositioning"
    assert effect.source_id == source.char_id
    assert effect.active_from_exchange == target.meta.exchange_counter + 1
    assert effect.expire_at_exchange == target.meta.exchange_counter + 2


@pytest.mark.unit
def test_exchange_end_removes_expired_non_control_effects() -> None:
    source = actor(2, "b")
    target = actor(1, "a")
    target.meta.exchange_counter = 2
    target.statuses.effects.append(
        ActiveEffectDTO(
            uid="repositioning-1",
            effect_id="debuff_ranged_repositioning",
            source_id=source.char_id,
            active_from_exchange=1,
            expire_at_exchange=2,
        )
    )
    action = CombatActionDTO(
        action_type="exchange",
        move=CombatMoveDTO(move_id="m1", char_id=2, strategy="exchange", payload=ExchangePayload(target_id=1)),
    )
    ctx = BattleContext(
        session_id="s1",
        actors={source.char_id: source, target.char_id: target},
        meta=battle_meta(),
        pending_logs=[],
        pending_support_tasks=[],
    )

    CombatExecutor()._cleanup_finished_control_effects(ctx, [source, target], action=action, wave=0)

    assert target.statuses.effects == []


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
def test_two_handed_style_softens_parry_and_block_without_ignoring_evasion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda _chance: (0.0, True)))
    ctx = PipelineContextDTO()
    activate_trigger(ctx, "accuracy.style_2h_ignore", source="style", source_id="skill_two_handed")
    result = InteractionResultDTO(source_id=1, target_id=2)

    trigger_activator.resolve_triggers(ctx, result, "ON_ACCURACY_CHECK")

    assert ctx.flags.force.hit_evasion is False
    assert ctx.flags.restriction.ignore_parry is False
    assert ctx.flags.restriction.ignore_block is False
    assert ctx.mods.target_parry_mult == pytest.approx(0.65)
    assert ctx.mods.target_block_mult == pytest.approx(0.65)


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

    dodged = evasion_step.run(
        stats({"anti_dodge_chance": 0.6}),
        stats({"evasion": 0.5, "dodge_cap": 0.75, "anti_dodge_chance": 0.0}),
        ctx,
        result,
    )

    assert dodged is False
    assert result.is_dodged is False


@pytest.mark.unit
def test_evasion_cap_is_hard_ceiling_even_when_cap_ignore_flag_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.99, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.flags.formula.ignore_evasion_cap = True
    result = InteractionResultDTO(source_id=1, target_id=2)

    evasion_step.run(
        stats(),
        stats({"evasion": 0.90, "dodge_cap": 0.35}),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.35)]
    assert result.checks[0].chance == pytest.approx(0.35)


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

    crit_step.run(
        stats({"main_hand_crit_chance": 0.5}, {"skill_swords": 0.5}),
        stats(),
        ctx,
        result,
    )

    assert stats().mods.main_hand_crit_cap == 0.75
    assert captured_chances == [0.75]


@pytest.mark.unit
def test_accuracy_roll_starts_at_sixty_and_caps_below_guaranteed_hit_with_weapon_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.flags.meta.weapon_class = "swords"
    result = InteractionResultDTO(source_id=1, target_id=2)

    atk_stats = stats(skills={"skill_swords": 1.0})
    passed = accuracy_step.run(atk_stats, atk_stats, ctx, result)

    assert passed is True
    assert captured_chances == [0.90]
    assert result.checks[-1].details["base"] == pytest.approx(0.60)
    assert result.checks[-1].details["skill_bonus"] == pytest.approx(0.40)
    assert result.checks[-1].details["cap"] == pytest.approx(0.90)


@pytest.mark.unit
def test_accuracy_roll_applies_family_and_item_modifiers_after_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.flags.meta.weapon_class = "swords"
    result = InteractionResultDTO(source_id=1, target_id=2)

    atk_stats = stats({"main_hand_accuracy": 0.05, "accuracy": -0.10}, {"skill_swords": 0.5})
    accuracy_step.run(atk_stats, atk_stats, ctx, result)

    assert captured_chances == [pytest.approx(0.75)]
    assert result.checks[-1].details["modifier"] == pytest.approx(-0.05)
    assert result.checks[-1].details["skill_bonus"] == pytest.approx(0.20)


@pytest.mark.unit
def test_accuracy_roll_applies_weapon_penalty_reduced_by_weapon_and_style_skills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "main_hand"
    ctx.flags.meta.weapon_class = "macing"
    ctx.flags.meta.tactical_style_skill = "skill_two_handed"
    result = InteractionResultDTO(source_id=1, target_id=2)

    atk_stats = stats(
        {"main_hand_accuracy_penalty": 0.80},
        {"skill_macing": 0.5, "skill_two_handed": 0.5},
    )
    accuracy_step.run(
        atk_stats,
        atk_stats,
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.36)]
    assert result.checks[-1].details["raw_penalty"] == pytest.approx(0.80)
    assert result.checks[-1].details["effective_penalty"] == pytest.approx(0.44)
    assert result.checks[-1].details["style_skill"] == pytest.approx(0.5)


@pytest.mark.unit
def test_physical_damage_attribute_bonus_applies_to_weapon_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.meta.weapon_class = "swords"
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"main_hand_damage_base": 4.0, "main_hand_damage_spread": 0.0, "physical_damage": 6.0}),
        stats(),
        ctx,
        result,
    )

    assert damage == 4.0
    assert result.damage_final == 4


@pytest.mark.unit
def test_weapon_damage_spread_keeps_base_as_damage_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_ranges: list[tuple[float, float]] = []

    def capture_range(min_d: float, max_d: float) -> float:
        captured_ranges.append((min_d, max_d))
        return max_d

    monkeypatch.setattr(MathCore, "random_range", staticmethod(capture_range))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"main_hand_damage_base": 20.0, "main_hand_damage_spread": 0.25}),
        stats(),
        ctx,
        result,
    )

    assert captured_ranges == [(pytest.approx(15.0), pytest.approx(20.0))]
    assert damage == pytest.approx(20.0)
    assert result.damage_trace is not None
    assert result.damage_trace.max == pytest.approx(20.0)


@pytest.mark.unit
def test_physical_suppression_reduces_resistance_before_armor_power(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: False))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats(
            {
                "main_hand_damage_base": 100.0,
                "main_hand_damage_spread": 0.0,
                "physical_suppression": 0.20,
            }
        ),
        stats({"physical_resistance": 0.30}),
        ctx,
        result,
    )

    assert damage == pytest.approx(90.0)
    assert result.damage_trace is not None
    assert result.damage_trace.details["physical_suppression"] == pytest.approx(0.20)
    assert result.damage_trace.details["after_resist"] == pytest.approx(90.0)


@pytest.mark.unit
def test_armor_penetration_pct_and_flat_reduce_armor_power_before_percent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: False))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats(
            {
                "main_hand_damage_base": 100.0,
                "main_hand_damage_spread": 0.0,
                "main_hand_armor_penetration_pct": 0.50,
                "armor_penetration_flat": 10.0,
            }
        ),
        stats({"armor": 40.0}, {"skill_heavy_armor": 1.0}),
        ctx,
        result,
    )

    assert damage == pytest.approx(78.740157)
    assert result.damage_trace is not None
    assert result.damage_trace.details["arm"]["effective_power"] == pytest.approx(10.0)
    assert result.damage_trace.details["arm"]["pct"] == pytest.approx(0.212598425)


@pytest.mark.unit
def test_armor_power_uses_type_cap_instead_of_flat_full_absorb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: False))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"main_hand_damage_base": 5.0, "main_hand_damage_spread": 0.0}),
        stats({"armor": 10_000.0}, {"skill_heavy_armor": 1.0}),
        ctx,
        result,
    )

    assert damage == pytest.approx(1.0)
    assert result.damage_final == 1
    assert result.damage_trace is not None
    assert result.damage_trace.details["after_armor"] == pytest.approx(0.5)
    assert result.damage_trace.details["arm"]["pct"] == pytest.approx(0.90)
    assert result.damage_trace.details["arm"]["cap"] == pytest.approx(0.90)


@pytest.mark.unit
def test_magic_armor_reduces_elemental_damage_after_resistance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "magic"
    ctx.flags.damage.physical = False
    ctx.flags.damage.fire = True
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"magical_damage": 20.0, "magical_damage_spread": 0.0}),
        stats({"fire_resistance": 0.25, "magic_armor": 4.0}),
        ctx,
        result,
    )

    assert damage == pytest.approx(11.0)
    assert result.damage_final == 11
    assert result.damage_trace is not None
    assert result.damage_trace.details["parts"]["fire"] == pytest.approx(15.0)
    assert result.damage_trace.details["magic_armor"] == pytest.approx(4.0)
    assert result.damage_trace.details["after_magic_armor"] == pytest.approx(11.0)


@pytest.mark.unit
def test_armor_ignore_chance_can_skip_armor_power(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: True))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats(
            {
                "main_hand_damage_base": 100.0,
                "main_hand_damage_spread": 0.0,
                "main_hand_armor_ignore_chance": 1.0,
            }
        ),
        stats({"armor": 40.0}),
        ctx,
        result,
    )

    assert damage == pytest.approx(100.0)


@pytest.mark.unit
def test_flat_armor_ignore_trigger_bonus_can_skip_armor_power(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (0.0, chance == pytest.approx(0.5))))

    ctx = PipelineContextDTO()
    ctx.flags.formula.roll_flat_armor_ignore = True
    ctx.mods.flat_armor_ignore_chance_bonus = 0.5
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"main_hand_damage_base": 100.0, "main_hand_damage_spread": 0.0}),
        stats({"armor": 40.0}),
        ctx,
        result,
    )

    assert damage == pytest.approx(100.0)


@pytest.mark.unit
def test_flat_armor_penetration_trigger_bonus_reduces_armor_power_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: False))

    ctx = PipelineContextDTO()
    ctx.flags.mastery.medium_armor = True
    ctx.flags.formula.boost_flat_armor_penetration = True
    ctx.mods.flat_armor_penetration_bonus_pct = 0.5
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"main_hand_damage_base": 100.0, "main_hand_damage_spread": 0.0}),
        stats({"physical_resistance": 0.25, "armor": 40.0}, {"skill_medium_armor": 1.0}),
        ctx,
        result,
    )

    assert damage == pytest.approx(55.147059)
    assert result.damage_trace is not None
    assert result.damage_trace.details["after_resist"] == pytest.approx(75.0)
    assert result.damage_trace.details["arm"]["effective_power"] == pytest.approx(20.0)


@pytest.mark.unit
def test_far_position_boosts_archer_outgoing_bow_damage_after_mitigation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "main_hand"
    ctx.flags.meta.weapon_class = "archery"
    ctx.flags.meta.tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.source_ranged_position = "far"
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"main_hand_damage_base": 100.0, "main_hand_damage_spread": 0.0}),
        stats({"armor": 20.0}),
        ctx,
        result,
    )

    assert damage == pytest.approx(67.711598)
    assert result.damage_final == 67
    assert result.damage_trace is not None
    assert result.damage_trace.details["ranged_position_outgoing_mult"] == pytest.approx(1.08)


@pytest.mark.unit
def test_ranged_backstep_position_step_updates_current_archer_context() -> None:
    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "main_hand"
    ctx.flags.meta.weapon_class = "archery"
    ctx.flags.meta.tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.source_ranged_position = "close"
    ctx.mods.accuracy_mult = 0.85
    ctx.result.action_facts["ranged_current_position_step"] = 1
    ctx.result.action_facts["ranged_outgoing_accuracy_bonus_mult"] = 1.05

    RangedPositionService.apply_action_position_context(ctx)

    assert ctx.flags.meta.source_ranged_position == "mid"
    assert ctx.result.action_facts["ranged_current_position_applied"] == "mid"
    assert ctx.mods.accuracy_mult == pytest.approx(1.0 * 1.05)


@pytest.mark.unit
def test_ranged_covering_fire_expands_position_outgoing_damage_bonus(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "main_hand"
    ctx.flags.meta.weapon_class = "archery"
    ctx.flags.meta.tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.source_ranged_position = "close"
    ctx.result.action_facts["ranged_outgoing_damage_bonus_mult"] = 1.20
    result = InteractionResultDTO(source_id=1, target_id=2, action_facts=ctx.result.action_facts)

    damage = damage_step.run(
        stats({"main_hand_damage_base": 100.0, "main_hand_damage_spread": 0.0}),
        stats(),
        ctx,
        result,
    )

    assert damage == pytest.approx(84.0)
    assert result.damage_trace is not None
    assert result.damage_trace.details["ranged_position_outgoing_mult"] == pytest.approx(0.70)
    assert result.damage_trace.details["ranged_position_outgoing_bonus_mult"] == pytest.approx(1.20)


@pytest.mark.unit
def test_ranged_position_roll_uses_feint_weight_and_pressure_modifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rolls = iter(["tail", "head"])

    def controlled_roll(min_d: float, max_d: float) -> float:
        return max_d - 0.001 if next(rolls) == "tail" else min_d

    monkeypatch.setattr(MathCore, "random_range", staticmethod(controlled_roll))
    archer = actor("archer", team="blue", hp=100)
    enemy = actor("enemy", team="red", hp=100)
    archer.loadout.layout.update({"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"})
    archer.stats = stats(
        {"evasion": 0.05, "parry": 0.0, "initiative": 5.0},
        skills={"skill_ranged_combat": 0.2, "skill_archery": 0.2},
    )
    enemy.stats = stats({"initiative": 30.0, "anti_dodge_chance": 0.4})

    strong_result = InteractionResultDTO(source_id=archer.char_id, target_id=enemy.char_id)
    strong_result.action_facts.update(
        {
            "ranged_far_weight_bonus": 5.0,
            "ranged_close_weight_bonus": -5.0,
            "ranged_damage_pressure_mult": 0.0,
            "ranged_enemy_pressure_mult": 0.0,
            "next_ranged_position_min": "mid",
        }
    )

    assert RangedPositionService.roll_next_position(archer=archer, enemy=enemy, damage_taken=60) == "close"
    assert (
        RangedPositionService.roll_next_position(
            archer=archer,
            enemy=enemy,
            damage_taken=60,
            action_facts=strong_result.action_facts,
        )
        == "far"
    )


@pytest.mark.unit
def test_ranged_position_weights_treat_melee_contact_as_position_pressure() -> None:
    archer = actor(1, "a", hp=100)
    enemy = actor(2, "b")
    archer.loadout.layout.update({"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"})
    archer.statuses.effects.append(
        ActiveEffectDTO(
            uid="current-position",
            effect_id="ranged_position",
            source_id=archer.char_id,
            active_from_exchange=0,
            expire_at_exchange=1,
            params={"position": "far"},
        )
    )
    archer.stats = stats({"evasion": 0.50, "parry": 0.0, "initiative": 10.0}, {"skill_ranged_combat": 0.15})
    enemy.stats = stats({"initiative": 10.0, "anti_dodge_chance": 0.0})

    no_contact = RangedPositionService.position_weights(archer=archer, enemy=enemy, damage_taken=0)
    melee_contact = RangedPositionService.position_weights(
        archer=archer,
        enemy=enemy,
        damage_taken=0,
        melee_pressure=1,
    )

    assert melee_contact.far < no_contact.far
    assert melee_contact.close > no_contact.close


@pytest.mark.unit
def test_ranged_position_weights_amplify_far_damage_as_position_threat() -> None:
    archer = actor(1, "a", hp=100)
    enemy = actor(2, "b")
    archer.loadout.layout.update({"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"})
    archer.statuses.effects.append(
        ActiveEffectDTO(
            uid="current-position",
            effect_id="ranged_position",
            source_id=archer.char_id,
            active_from_exchange=0,
            expire_at_exchange=1,
            params={"position": "far"},
        )
    )
    archer.stats = stats({"evasion": 0.50, "parry": 0.0, "initiative": 10.0}, {"skill_ranged_combat": 0.15})
    enemy.stats = stats({"initiative": 10.0, "anti_dodge_chance": 0.0})

    no_damage = RangedPositionService.position_weights(archer=archer, enemy=enemy, damage_taken=0)
    far_hit = RangedPositionService.position_weights(archer=archer, enemy=enemy, damage_taken=10)

    assert far_hit.far < no_damage.far
    assert far_hit.mid > no_damage.mid
    assert far_hit.close > no_damage.close


@pytest.mark.unit
def test_ranged_position_low_skill_prefers_mid_then_close_before_far() -> None:
    archer = actor(1, "a", hp=100)
    enemy = actor(2, "b")
    archer.loadout.layout.update({"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"})
    archer.statuses.effects.append(
        ActiveEffectDTO(
            uid="current-position",
            effect_id="ranged_position",
            source_id=archer.char_id,
            active_from_exchange=0,
            expire_at_exchange=1,
            params={"position": "far"},
        )
    )
    archer.stats = stats({"evasion": 0.50, "parry": 0.0, "initiative": 10.0}, {"skill_ranged_combat": 0.15})
    enemy.stats = stats({"initiative": 10.0, "anti_dodge_chance": 0.0})

    weights = RangedPositionService.position_weights(archer=archer, enemy=enemy, damage_taken=0)

    assert weights.mid > weights.close > weights.far


@pytest.mark.unit
def test_ranged_position_weights_scale_melee_contact_recovery_with_ranged_skill() -> None:
    low = actor(1, "a", hp=100)
    full = actor(2, "a", hp=100)
    enemy = actor(3, "b")
    for archer, skill in ((low, 0.15), (full, 1.0)):
        archer.loadout.layout.update({"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"})
        archer.statuses.effects.append(
            ActiveEffectDTO(
                uid=f"current-position-{archer.char_id}",
                effect_id="ranged_position",
                source_id=archer.char_id,
                active_from_exchange=0,
                expire_at_exchange=1,
                params={"position": "far"},
            )
        )
        archer.stats = stats({"evasion": 0.50, "parry": 0.0, "initiative": 10.0}, {"skill_ranged_combat": skill})
    enemy.stats = stats({"initiative": 10.0, "anti_dodge_chance": 0.0})

    low_weights = RangedPositionService.position_weights(archer=low, enemy=enemy, damage_taken=0, melee_pressure=1)
    full_weights = RangedPositionService.position_weights(archer=full, enemy=enemy, damage_taken=0, melee_pressure=1)

    assert full_weights.far > low_weights.far
    assert full_weights.mid == pytest.approx(low_weights.mid, abs=0.10)
    assert full_weights.close > 0.10
    assert full_weights.close < low_weights.close


@pytest.mark.unit
def test_target_far_position_reduces_only_incoming_physical_melee_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    melee_ctx = PipelineContextDTO()
    melee_ctx.flags.meta.source_type = "main_hand"
    melee_ctx.flags.meta.weapon_class = "swords"
    melee_ctx.flags.meta.target_tactical_style_skill = "skill_ranged_combat"
    melee_ctx.flags.meta.target_ranged_position = "far"
    melee_result = InteractionResultDTO(source_id=1, target_id=2)

    melee_damage = damage_step.run(
        stats({"main_hand_damage_base": 100.0, "main_hand_damage_spread": 0.0}),
        stats(),
        melee_ctx,
        melee_result,
    )

    assert melee_damage == pytest.approx(70.0)
    assert melee_result.damage_final == 70
    assert melee_result.damage_trace is not None
    assert melee_result.damage_trace.details["ranged_position_incoming_mult"] == pytest.approx(0.7)

    arrow_ctx = PipelineContextDTO()
    arrow_ctx.flags.meta.source_type = "main_hand"
    arrow_ctx.flags.meta.weapon_class = "archery"
    arrow_ctx.flags.meta.tactical_style_skill = "skill_ranged_combat"
    arrow_ctx.flags.meta.source_ranged_position = "far"
    arrow_ctx.flags.meta.target_tactical_style_skill = "skill_ranged_combat"
    arrow_ctx.flags.meta.target_ranged_position = "far"
    arrow_result = InteractionResultDTO(source_id=1, target_id=2)

    arrow_damage = damage_step.run(
        stats({"main_hand_damage_base": 100.0, "main_hand_damage_spread": 0.0}),
        stats(),
        arrow_ctx,
        arrow_result,
    )

    assert arrow_damage == pytest.approx(108.0)
    assert arrow_result.damage_final == 108
    assert arrow_result.damage_trace is not None
    assert "ranged_position_incoming_mult" not in arrow_result.damage_trace.details
    assert arrow_result.damage_trace.details["ranged_position_outgoing_mult"] == pytest.approx(1.08)


@pytest.mark.unit
def test_target_far_position_ignores_magic_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "magic"
    ctx.flags.damage.physical = False
    ctx.flags.damage.fire = True
    ctx.flags.meta.target_tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.target_ranged_position = "far"
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"magical_damage": 100.0, "magical_damage_spread": 0.0}),
        stats(),
        ctx,
        result,
    )

    assert damage == pytest.approx(100.0)
    assert result.damage_trace is not None
    assert "ranged_position_incoming_mult" not in result.damage_trace.details


@pytest.mark.unit
def test_ranged_position_defense_keeps_meaningful_evasion_caps_by_distance() -> None:
    ctx = PipelineContextDTO()
    ctx.flags.meta.target_ranged_position = "close"

    close_low, close_low_details = RangedPositionService.ranged_avoid_chance(
        stats(),
        stats({"evasion": 1.0, "parry": 0.0}, {"skill_ranged_combat": 0.0}),
        ctx,
    )
    close_full, close_full_details = RangedPositionService.ranged_avoid_chance(
        stats(),
        stats({"evasion": 1.0, "parry": 0.0}, {"skill_ranged_combat": 1.0}),
        ctx,
    )

    ctx.flags.meta.target_ranged_position = "far"
    far_low, far_low_details = RangedPositionService.ranged_avoid_chance(
        stats(),
        stats({"evasion": 1.0, "parry": 0.0}, {"skill_ranged_combat": 0.0}),
        ctx,
    )
    far_full, far_full_details = RangedPositionService.ranged_avoid_chance(
        stats(),
        stats({"evasion": 1.0, "parry": 0.0}, {"skill_ranged_combat": 1.0}),
        ctx,
    )

    assert close_low == pytest.approx(0.35)
    assert close_full == pytest.approx(0.50)
    assert far_low == pytest.approx(0.65)
    assert far_full == pytest.approx(0.95)
    assert close_low_details["cap"] == pytest.approx(0.35)
    assert close_full_details["cap"] == pytest.approx(0.50)
    assert far_low_details["cap"] == pytest.approx(0.65)
    assert far_full_details["cap"] == pytest.approx(0.95)


@pytest.mark.unit
def test_successful_ranged_position_defense_awards_dodge_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(lambda chance: (0.0, True)))
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: False)

    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "main_hand"
    ctx.flags.meta.weapon_class = "macing"
    ctx.flags.meta.target_tactical_style_skill = "skill_ranged_combat"
    ctx.flags.meta.target_ranged_position = "far"
    ctx.stages.check_ranged_position_defense = True
    result = InteractionResultDTO(source_id=1, target_id=2)

    stopped = ranged_position_defense_step.run(
        stats(),
        stats({"evasion": 1.0, "parry": 0.0}, {"skill_ranged_combat": 1.0}),
        ctx,
        result,
    )

    assert stopped is True
    assert result.is_dodged is True
    assert result.tokens_awarded_defender == {"dodge": 1}
    assert result.checks[0].stage == "ranged_position_defense"


@pytest.mark.unit
def test_physical_resistance_suppression_trigger_bonus_reduces_only_natural_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: False))

    ctx = PipelineContextDTO()
    ctx.flags.formula.suppress_physical_resistance = True
    ctx.mods.physical_resistance_suppression_pct = 0.5
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"main_hand_damage_base": 100.0, "main_hand_damage_spread": 0.0}),
        stats({"physical_resistance": 0.40, "armor": 10.0}),
        ctx,
        result,
    )

    assert damage == pytest.approx(61.657033)


@pytest.mark.unit
def test_unblocked_shield_stats_do_not_absorb_or_reflect_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
        stats({"main_hand_damage_base": 20.0, "main_hand_damage_spread": 0.0}),
        stats(
            {
                "shield_guard_power": 100.0,
                "shield_absorb_ratio": 1.0,
                "shield_reflect_ratio": 1.0,
            },
            {"skill_shield_mastery": 1.0},
        ),
        ctx,
        result,
    )

    assert damage == pytest.approx(20.0)
    assert result.damage_final == 20
    assert result.reflected_damage == 0
    assert result.damage_trace is not None
    assert result.damage_trace.details["shield_absorb"] == pytest.approx(0.0)
    assert result.damage_trace.details["shield_reflect"] == pytest.approx(0.0)


@pytest.mark.unit
def test_defensive_shield_block_adds_guard_power_to_damage_reduction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2, is_hit=True, is_blocked=True, shield_block_branch="defense")

    damage = damage_step.run(
        stats({"main_hand_damage_base": 20.0, "main_hand_damage_spread": 0.0}),
        stats(
            {"armor": 10.0, "evasion": 0.2, "physical_endurance_power": 12.0, "shield_guard_power": 8.0},
            {"skill_heavy_armor": 1.0, "skill_shield_mastery": 0.5},
        ),
        ctx,
        result,
    )

    assert damage == pytest.approx(9.027394)
    assert result.damage_final == 9
    assert result.reflected_damage == 0
    assert result.damage_trace is not None
    assert result.damage_trace.details["shield_block_branch"] == "defense"
    assert result.damage_trace.details["shield_guard_power"] == pytest.approx(4.29975)
    assert result.damage_trace.details["arm"]["total_power"] == pytest.approx(14.29975)
    assert result.damage_trace.details["arm"]["shield_guard_power"] == pytest.approx(4.29975)
    assert result.damage_trace.details["shield_absorb"] == pytest.approx(3.299321)
    assert result.damage_trace.details["shield_guard_power"] == pytest.approx(4.29975)


@pytest.mark.unit
def test_counter_shield_block_no_longer_reflects_guard_power(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2, is_hit=True, is_blocked=True, shield_block_branch="counter")

    damage = damage_step.run(
        stats({"main_hand_damage_base": 20.0, "main_hand_damage_spread": 0.0}),
        stats({"armor": 3.0, "evasion": 0.2, "physical_endurance_power": 12.0, "shield_guard_power": 8.0}, {"skill_shield_mastery": 0.5}),
        ctx,
        result,
    )

    assert damage == pytest.approx(16.431591)
    assert result.damage_final == 16
    assert result.reflected_damage == 0
    assert result.damage_trace is not None
    assert result.damage_trace.details["shield_block_branch"] == "counter"
    assert result.damage_trace.details["shield_absorb"] == pytest.approx(2.101889)
    assert result.damage_trace.details["shield_reflect"] == pytest.approx(0.0)


@pytest.mark.unit
def test_unarmed_damage_uses_strength_and_unarmed_skill_efficiency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    ctx = PipelineContextDTO()
    ctx.flags.meta.weapon_class = "unarmed"
    result = InteractionResultDTO(source_id=1, target_id=2)

    damage = damage_step.run(
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

    damage = damage_step.run(
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

    parry_step.run(
        stats(),
        stats({"parry": 0.1, "parry_cap": 0.75}, {"skill_parrying": 0.5}),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.3)]


@pytest.mark.unit
def test_soft_target_reaction_multipliers_reduce_evasion_and_parry(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    evasion_ctx = PipelineContextDTO()
    evasion_ctx.mods.target_evasion_mult = 0.65
    evasion_result = InteractionResultDTO(source_id=1, target_id=2)
    evasion_step.run(
        stats(),
        stats({"evasion": 0.4, "dodge_cap": 1.0}),
        evasion_ctx,
        evasion_result,
    )

    parry_ctx = PipelineContextDTO()
    parry_ctx.mods.target_parry_mult = 0.65
    parry_result = InteractionResultDTO(source_id=1, target_id=2)
    parry_step.run(
        stats(),
        stats({"parry": 0.1, "parry_cap": 0.75}, {"skill_parrying": 0.5}),
        parry_ctx,
        parry_result,
    )

    assert captured_chances == [pytest.approx(0.26), pytest.approx(0.195)]
    assert evasion_result.checks[0].details["target_evasion_mult"] == 0.65
    assert parry_result.checks[0].details["target_parry_mult"] == 0.65


@pytest.mark.unit
def test_block_roll_uses_soft_target_block_multiplier(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    ctx.mods.target_block_mult = 0.75
    result = InteractionResultDTO(source_id=1, target_id=2)

    block_step.run(
        stats(),
        stats({"evasion": 0.7333333333, "shield_guard_power": 20.0}, {"skill_shield_mastery": 1.0}),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.39)]
    assert result.checks[0].details["target_block_mult"] == 0.75


@pytest.mark.unit
def test_block_roll_applies_shield_mastery_skill_bonus_in_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return None, False

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    block_step.run(
        stats(),
        stats({"shield_guard_power": 20.0}, {"skill_parrying": 1.0, "skill_shield_mastery": 0.0}),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.105)]

    captured_chances.clear()
    block_step.run(
        stats(),
        stats({"shield_guard_power": 20.0}, {"skill_parrying": 0.0, "skill_shield_mastery": 1.0}),
        ctx,
        result,
    )

    assert captured_chances == [pytest.approx(0.3)]


@pytest.mark.unit
def test_successful_shield_block_ignores_legacy_branch_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_chances: list[float] = []

    def capture_roll(chance: float) -> tuple[float | None, bool]:
        captured_chances.append(chance)
        return 0.0, True

    monkeypatch.setattr(MathCore, "roll_chance", staticmethod(capture_roll))
    monkeypatch.setattr(MathCore, "check_chance", staticmethod(lambda chance: False))
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: False)

    ctx = PipelineContextDTO()
    result = InteractionResultDTO(source_id=1, target_id=2)

    passed = block_step.run(
        stats(),
        stats(
            {
                "evasion": 0.4,
                "shield_guard_power": 10.0,
                "shield_block_defense_weight": 40.0,
                "shield_block_counter_weight": 60.0,
            },
            {"skill_shield_mastery": 0.0},
        ),
        ctx,
        result,
    )

    assert passed is True
    assert result.is_blocked is True
    assert result.tokens_awarded_defender == {"block": 1}
    assert result.shield_block_branch == "defense"
    assert captured_chances == [pytest.approx(0.0735)]


@pytest.mark.unit
def test_shield_block_pipeline_mods_scale_guard_power(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MathCore, "random_range", staticmethod(lambda min_d, max_d: min_d))

    defense_ctx = PipelineContextDTO()
    defense_ctx.mods.shield_guard_power_mult = 2.0
    defense_result = InteractionResultDTO(
        source_id=1,
        target_id=2,
        is_hit=True,
        is_blocked=True,
        shield_block_branch="defense",
    )

    damage = damage_step.run(
        stats({"main_hand_damage_base": 20.0, "main_hand_damage_spread": 0.0}),
        stats({"shield_guard_power": 8.0}, {"skill_shield_mastery": 0.0}),
        defense_ctx,
        defense_result,
    )

    assert damage == pytest.approx(18.898054)
    assert defense_result.damage_trace is not None
    assert defense_result.damage_trace.details["shield_guard_power"] == pytest.approx(1.96)


@pytest.mark.unit
def test_item_source_type_reads_item_offensive_modifiers() -> None:
    ctx = PipelineContextDTO()
    ctx.flags.meta.source_type = "item"
    actor_stats = stats(
        {
            "main_hand_damage_base": 999.0,
            "main_hand_accuracy": 0.99,
            "main_hand_crit_chance": 0.99,
            "main_hand_armor_penetration_pct": 0.99,
            "item_damage_base": 12.0,
            "item_damage_spread": 0.25,
            "item_accuracy": 0.8,
            "item_crit_chance": 0.2,
            "item_armor_penetration_pct": 0.1,
        }
    )

    assert offensive_lookup.get_offensive_val(actor_stats, ctx, "damage_base") == 12.0
    assert offensive_lookup.get_offensive_val(actor_stats, ctx, "damage_spread") == 0.25
    assert offensive_lookup.get_offensive_val(actor_stats, ctx, "accuracy") == 0.8
    assert offensive_lookup.get_offensive_val(actor_stats, ctx, "crit_chance") == 0.2
    assert offensive_lookup.get_offensive_val(actor_stats, ctx, "crit_cap") == 0.75
    assert offensive_lookup.get_offensive_val(actor_stats, ctx, "armor_penetration_pct") == 0.1


@pytest.mark.unit
def test_token_award_can_double_non_excluded_combat_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: True)
    bucket = {"hit": 1}

    token_awarder.award_token(bucket, "hit")

    assert bucket["hit"] == 3


@pytest.mark.unit
def test_token_award_does_not_double_tempo_or_gift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: True)
    bucket: dict[str, int] = {}

    token_awarder.award_token(bucket, "tempo")
    token_awarder.award_token(bucket, "gift")

    assert bucket == {"tempo": 1, "gift": 1}


@pytest.mark.unit
def test_trigger_token_grants_use_bonus_award_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_awarder, "bonus_token_roll", lambda: True)
    result = InteractionResultDTO(source_id=1, target_id=2)

    trigger_activator.apply_trigger_token_grants(
        result,
        {"token_grants_attacker": ["hit"], "token_grants_defender": ["block", "tempo"]},
    )

    assert result.tokens_awarded_attacker == {"hit": 2}
    assert result.tokens_awarded_defender == {"block": 2, "tempo": 1}
