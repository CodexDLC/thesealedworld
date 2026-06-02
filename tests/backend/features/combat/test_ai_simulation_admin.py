from __future__ import annotations

import asyncio
import fnmatch
from types import SimpleNamespace

import pytest

from src.backend.core.arq import COMBAT_AI_SIMULATION_ARQ_QUEUE, COMBAT_ARQ_QUEUE
from src.backend.features.combat.api import ai_simulation_router as ai_simulation_router_module
from src.backend.features.combat.api.ai_simulation_router import (
    COMBAT_AI_BATTLE_TRAINING_TASK,
    COMBAT_AI_LIVE_SIMULATION_TASK,
    COMBAT_AI_SYNTHETIC_TRAINING_TASK,
    COMBAT_FAMILY_PRESSURE_TASK,
    _clear_combat_ai_simulation_runtime_state,
    _enqueue_battle_training_job,
    _enqueue_family_pressure_job,
    _enqueue_live_demo_job,
    _enqueue_synthetic_training_job,
    _live_skill_profile_from_scenario,
    _view,
    get_simulation_run,
    list_simulation_runs,
    run_family_pressure_batch_simulation,
    run_family_pressure_simulation,
    run_live_demo_simulation_batch,
)
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.simulation import (
    DEFAULT_STARTER_SIMULATION_IMPRINTS,
    STARTER_SKILL_PROFILE_BASELINE,
    STARTER_SKILL_PROFILE_MAXED_EXISTING,
    FamilyPressureComposition,
    FamilyPressureCompositionReport,
    FamilyPressureReport,
    FamilyPressureSimulator,
    LiveInMemoryCombatSimulator,
    build_family_pressure_compositions,
)
from src.backend.features.combat.services import ai_simulation_service as ai_simulation_service_module
from src.backend.features.combat.services.ai_simulation_service import (
    LIVE_DEFAULT_MAX_EXCHANGES,
    LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
    CombatAiSimulationRunService,
    _battle_training_scenarios,
    _simulation_reward,
    execute_battle_training,
)
from src.backend.features.combat.workers.ai_simulation_arq import (
    AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS,
    AI_LIVE_SIMULATION_JOB_TIMEOUT_SECONDS,
    AI_SYNTHETIC_TRAINING_JOB_TIMEOUT_SECONDS,
    COMBAT_AI_SIMULATION_TASKS,
    COMBAT_AI_SIMULATION_WORKER_MAX_JOBS,
    CombatAiSimulationArqSettings,
)
from src.backend.features.combat.workers.arq import (
    COMBAT_RUNTIME_MAX_JOBS,
    COMBAT_TASKS,
    PVE_FAMILY_PRESSURE_JOB_TIMEOUT_SECONDS,
    CombatArqSettings,
)
from src.backend.features.combat.workers.tasks import ai_simulation_task as ai_simulation_task_module
from src.backend.features.combat.workers.tasks.ai_simulation_task import (
    FAMILY_PRESSURE_WORKER_CONCURRENCY,
    LIVE_SIMULATION_WORKER_CONCURRENCY,
    _policy_payload_from_training_run,
    combat_ai_battle_training_task,
    combat_ai_live_simulation_task,
    combat_ai_synthetic_training_task,
    combat_family_pressure_task,
)


class FakeSimulationRunRepository:
    def __init__(self) -> None:
        self.created: dict | None = None
        self.recent: list[SimpleNamespace] = []

    async def create(self, **kwargs):
        self.created = kwargs
        return SimpleNamespace(id="run-1", created_at=None, schema_version=1, metadata_=kwargs.pop("metadata"), **kwargs)

    async def get(self, run_id: str):
        for row in self.recent:
            if getattr(row, "id", None) == run_id:
                return row
        return None

    async def list_recent(self, *, limit: int = 50, run_kind: str | None = None):
        if run_kind is None:
            return self.recent[:limit]
        return [row for row in self.recent if row.run_kind == run_kind][:limit]

    async def latest_completed_training_with_policy(self):
        for row in self.recent:
            if row.run_kind == "training" and row.status == "completed" and row.metadata_.get("best_policy"):
                return row
        return None

    async def clear_all(self):
        count = len(self.recent)
        self.recent = []
        return count

    async def clear_run_kinds(self, run_kinds: list[str]):
        before = len(self.recent)
        allowed = set(run_kinds)
        self.recent = [row for row in self.recent if getattr(row, "run_kind", "") not in allowed]
        return before - len(self.recent)

    async def mark_running_stale(self, *, before):
        count = 0
        for row in self.recent:
            if getattr(row, "status", None) == "running" and getattr(row, "created_at", before) < before:
                row.status = "failed"
                row.metadata_ = {
                    **dict(getattr(row, "metadata_", {}) or {}),
                    "completion_reason": "stale_running_cleanup",
                }
                count += 1
        return count

    async def mark_completed(
        self,
        run_id: str,
        *,
        rounds_completed: int,
        reward: float | None,
        telemetry: dict,
        report_text: str,
        metadata: dict,
        winner: str | None = None,
    ):
        row = await self.get(run_id)
        if row is None:
            return None
        row.status = "completed"
        row.rounds_completed = rounds_completed
        row.reward = reward
        row.telemetry = telemetry
        row.report_text = report_text
        row.metadata_ = metadata
        row.winner = winner
        return row


class FakeArqQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, dict]] = []

    async def enqueue_job(self, name: str, payload: dict) -> None:
        self.enqueued.append((name, payload))


class FakeRedisClient:
    def __init__(self) -> None:
        self.zsets: dict[str, list[str]] = {}
        self.keys: set[str] = set()
        self.docs: dict[str, dict] = {}
        self.ttls: dict[str, int] = {}

    async def zrange(self, key: str, start: int, end: int):
        values = list(self.zsets.get(key, []))
        return values[start:] if end == -1 else values[start : end + 1]

    async def scan(self, *, cursor: int, match: str, count: int):
        del cursor, count
        return 0, [key for key in sorted(self.keys) if fnmatch.fnmatch(key, match)]

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.zsets:
                del self.zsets[key]
                deleted += 1
            if key in self.keys:
                self.keys.remove(key)
                deleted += 1
            if key in self.docs:
                del self.docs[key]
        return deleted


class FakeJsonModule:
    def __init__(self, redis_client: FakeRedisClient) -> None:
        self.redis_client = redis_client

    async def set(self, key: str, _path: str, payload: dict) -> None:
        self.redis_client.keys.add(key)
        self.redis_client.docs[key] = payload

    async def get(self, key: str, _path: str):
        if key not in self.redis_client.docs:
            return []
        return [self.redis_client.docs[key]]


class FakeStringModule:
    def __init__(self, redis_client: FakeRedisClient) -> None:
        self.redis_client = redis_client

    async def expire(self, key: str, ttl: int) -> None:
        self.redis_client.ttls[key] = ttl

    async def delete(self, key: str) -> int:
        return await self.redis_client.delete(key)


class FakeRedisService:
    def __init__(self, redis_client: FakeRedisClient) -> None:
        self.redis_client = redis_client
        self.json_module = FakeJsonModule(redis_client)
        self.string = FakeStringModule(redis_client)


@pytest.mark.asyncio
async def test_live_demo_enqueue_uses_combat_ai_simulation_queue() -> None:
    arq = FakeArqQueue()
    payload = {
        "run_id": "run-1",
        "seed": 0,
        "max_rounds": 10,
        "tick_interval_seconds": 0.05,
        "timeout_ticks": 8,
        "min_team_size": 5,
        "max_team_size": 5,
        "mirror_full_roster": False,
    }

    await _enqueue_live_demo_job(arq, payload)

    assert arq.enqueued == [(COMBAT_AI_LIVE_SIMULATION_TASK, payload)]


@pytest.mark.asyncio
async def test_live_demo_enqueue_requires_arq() -> None:
    with pytest.raises(RuntimeError, match="Combat AI simulation ARQ service is not available"):
        await _enqueue_live_demo_job(None, {"run_id": "run-1"})


@pytest.mark.asyncio
async def test_clear_combat_ai_runtime_state_removes_queue_and_all_hot_progress() -> None:
    redis_client = FakeRedisClient()
    redis_client.zsets[COMBAT_AI_SIMULATION_ARQ_QUEUE] = ["job-1", "job-2"]
    redis_client.zsets[COMBAT_ARQ_QUEUE] = ["pve-job-1"]
    redis_client.keys = {
        "arq:job:job-1",
        "arq:retry:job-1",
        "arq:in-progress:job-2",
        "arq:job:pve-job-1",
        "combat_ai:simulation:run:run-1:progress",
        "combat_ai:simulation:run:run-2:progress",
        "arq:job:foreign-job",
    }
    redis_client.docs["combat_ai:simulation:run:run-1:progress"] = {
        "metadata": {"family_pressure": True},
        "telemetry": {"run_kind": "family_pressure"},
    }
    redis_client.docs["combat_ai:simulation:run:run-2:progress"] = {
        "metadata": {},
        "telemetry": {"run_kind": "simulation_live"},
    }
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(redis_client=redis_client, redis=FakeRedisService(redis_client)),
        )
    )

    result = await _clear_combat_ai_simulation_runtime_state(request)

    assert result == {"queued_deleted": 4, "ai_queue_deleted": 4, "progress_deleted": 2}
    assert COMBAT_AI_SIMULATION_ARQ_QUEUE not in redis_client.zsets
    assert redis_client.zsets[COMBAT_ARQ_QUEUE] == ["pve-job-1"]
    assert redis_client.keys == {"arq:job:pve-job-1", "arq:job:foreign-job"}


@pytest.mark.asyncio
async def test_live_demo_batch_creates_rows_once_and_enqueues_all(monkeypatch: pytest.MonkeyPatch) -> None:
    rows: list[SimpleNamespace] = []
    scheduled_calls: list[dict] = []

    class FakeDbSession:
        def __init__(self) -> None:
            self.commit_calls = 0

        async def commit(self) -> None:
            self.commit_calls += 1

    class FakeService:
        async def schedule_live_starter_presets_demo(
            self,
            *,
            seed: int,
            max_rounds: int,
            tick_interval_seconds: float,
            timeout_ticks: int,
            min_team_size: int,
            max_team_size: int,
            scenario_key: str,
            mirror_full_roster: bool,
            skill_profile: str,
            policy_ref: str = "runtime_default",
            policy_metadata: dict | None = None,
            policy_source_run_id: str | None = None,
        ):
            scheduled_calls.append(
                {
                    "seed": seed,
                    "max_rounds": max_rounds,
                    "min_team_size": min_team_size,
                    "max_team_size": max_team_size,
                    "scenario_key": scenario_key,
                }
            )
            row = SimpleNamespace(
                id=f"run-{len(rows) + 1}",
                run_kind="simulation_live",
                scenario_key=scenario_key,
                status="running",
                policy_ref=policy_ref,
                seed=seed,
                max_rounds=max_rounds,
                rounds_completed=0,
                winner="",
                reward=None,
                telemetry={},
                report_text="",
                created_at=None,
                metadata_={
                    "tick_interval_seconds": tick_interval_seconds,
                    "timeout_ticks": timeout_ticks,
                    "roster_min_team_size": min_team_size,
                    "roster_max_team_size": max_team_size,
                    "roster_mode": "mirror_10v10" if mirror_full_roster else "random_draft",
                    "skill_profile": skill_profile,
                    "blue_imprints": [f"blue-{seed}"],
                    "red_imprints": [f"red-{seed}"],
                    "policy_source_run_id": policy_source_run_id or "",
                    **(policy_metadata or {}),
                },
            )
            rows.append(row)
            return row

    db_session = FakeDbSession()
    arq = FakeArqQueue()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(combat_ai_simulation_arq=arq)))
    monkeypatch.setattr(ai_simulation_router_module, "_service", lambda _db_session: FakeService())

    result = await run_live_demo_simulation_batch(
        request,
        db_session,
        count=3,
        seed=999_998,
        max_rounds=500,
        tick_interval_seconds=0.05,
        timeout_ticks=8,
        min_team_size=2,
        max_team_size=4,
        scenario_key="starter_presets_random_draft_live",
    )

    assert db_session.commit_calls == 1
    assert [call["seed"] for call in scheduled_calls] == [999_998, 999_999, 0]
    assert [row.seed for row in result.runs] == [999_998, 999_999, 0]
    assert [payload["seed"] for _, payload in arq.enqueued] == [999_998, 999_999, 0]
    assert [payload["run_id"] for _, payload in arq.enqueued] == ["run-1", "run-2", "run-3"]
    assert [payload["min_team_size"] for _, payload in arq.enqueued] == [2, 2, 2]
    assert [payload["max_team_size"] for _, payload in arq.enqueued] == [4, 4, 4]
    assert [payload["blue_imprints"] for _, payload in arq.enqueued] == [["blue-999998"], ["blue-999999"], ["blue-0"]]
    assert [payload["red_imprints"] for _, payload in arq.enqueued] == [["red-999998"], ["red-999999"], ["red-0"]]
    assert {name for name, _ in arq.enqueued} == {COMBAT_AI_LIVE_SIMULATION_TASK}


@pytest.mark.asyncio
async def test_scheduled_live_demo_row_does_not_materialize_roster(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_roster_build(**_kwargs):
        raise AssertionError("scheduled live rows must not build combat actors")

    monkeypatch.setattr(ai_simulation_service_module, "_build_starter_roster", fail_roster_build)

    repository = FakeSimulationRunRepository()
    service = CombatAiSimulationRunService(repository)
    row = await service.schedule_live_starter_presets_demo(
        seed=7,
        max_rounds=500,
        tick_interval_seconds=0.05,
        timeout_ticks=8,
        min_team_size=5,
        max_team_size=5,
        scenario_key="starter_presets_5v5_live",
        mirror_full_roster=False,
        skill_profile=STARTER_SKILL_PROFILE_BASELINE,
    )

    assert row.status == "running"
    assert row.metadata_["participants"] == []
    assert row.metadata_["live_snapshot"]["actors"] == []
    assert len(row.metadata_["blue_imprints"]) == 5
    assert len(row.metadata_["red_imprints"]) == 5


@pytest.mark.asyncio
async def test_family_pressure_route_only_schedules_worker_job(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDbSession:
        def __init__(self) -> None:
            self.commit_calls = 0

        async def commit(self) -> None:
            self.commit_calls += 1

    class FakeProgressStore:
        def __init__(self) -> None:
            self.saved: dict[str, dict] = {}

        async def set_progress(self, run_id: str, payload: dict) -> None:
            self.saved[run_id] = payload

    def fail_monster_repository(_db_session):
        raise AssertionError("family pressure route must not load generated monsters")

    def fail_service(_db_session):
        raise AssertionError("family pressure route must not create DB reports")

    db_session = FakeDbSession()
    arq = FakeArqQueue()
    progress_store = FakeProgressStore()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(combat_arq=arq)))
    monkeypatch.setattr(ai_simulation_router_module, "_service", fail_service)
    monkeypatch.setattr(ai_simulation_router_module, "_progress_store_from_request", lambda _request: progress_store)
    monkeypatch.setattr(
        ai_simulation_router_module,
        "MonsterGenerationRepository",
        fail_monster_repository,
        raising=False,
    )

    result = await run_family_pressure_simulation(
        request,
        db_session,
        family_id="rat_swarm",
        seed=17,
        trials=5,
        max_rounds=80,
        max_minions=6,
        max_scenarios=24,
    )

    assert db_session.commit_calls == 0
    assert result.status == "running"
    assert result.metadata["family_pressure"] is True
    assert result.metadata["storage"] == "redis_only"
    assert result.metadata["imprint_key"] == "starter_breaker_01"
    assert set(progress_store.saved) == {result.id}
    assert arq.enqueued == [
        (
            COMBAT_FAMILY_PRESSURE_TASK,
            {
                "run_id": result.id,
                "family_id": "rat_swarm",
                "imprint_key": "starter_breaker_01",
                "seed": 17,
                "trials": 5,
                "max_rounds": 80,
                "max_minions": 6,
                "max_scenarios": 24,
                "created_at": result.created_at.isoformat(),
            },
        )
    ]


@pytest.mark.asyncio
async def test_family_pressure_batch_route_schedules_one_job_per_imprint(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDbSession:
        async def commit(self) -> None:
            raise AssertionError("family pressure batch must not create DB reports")

    class FakeProgressStore:
        def __init__(self) -> None:
            self.saved: dict[str, dict] = {}

        async def set_progress(self, run_id: str, payload: dict) -> None:
            self.saved[run_id] = payload

    arq = FakeArqQueue()
    progress_store = FakeProgressStore()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(combat_arq=arq)))
    monkeypatch.setattr(ai_simulation_router_module, "_progress_store_from_request", lambda _request: progress_store)

    result = await run_family_pressure_batch_simulation(
        request,
        FakeDbSession(),
        family_id="rat_swarm",
        imprint_keys=["starter_guard_01", "starter_breaker_01"],
        seed=31,
        trials=5,
        max_rounds=80,
        max_minions=6,
        max_scenarios=24,
    )

    assert len(result.runs) == 2
    assert [row.metadata["imprint_key"] for row in result.runs] == ["starter_guard_01", "starter_breaker_01"]
    assert [row.seed for row in result.runs] == [31, 32]
    assert set(progress_store.saved) == {row.id for row in result.runs}
    assert [name for name, _ in arq.enqueued] == [COMBAT_FAMILY_PRESSURE_TASK, COMBAT_FAMILY_PRESSURE_TASK]
    assert [payload["imprint_key"] for _, payload in arq.enqueued] == ["starter_guard_01", "starter_breaker_01"]


@pytest.mark.asyncio
async def test_family_pressure_enqueue_uses_combat_runtime_queue() -> None:
    arq = FakeArqQueue()
    payload = {"run_id": "family-run-1", "family_id": "rat_swarm"}

    await _enqueue_family_pressure_job(arq, payload)

    assert arq.enqueued == [(COMBAT_FAMILY_PRESSURE_TASK, payload)]


@pytest.mark.asyncio
async def test_family_pressure_get_reads_redis_when_db_row_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeService:
        async def get(self, run_id: str):
            assert run_id == "family-run-1"
            return None

    class FakeProgressStore:
        async def get_progress(self, run_id: str):
            assert run_id == "family-run-1"
            return {
                "id": "family-run-1",
                "run_kind": "simulation",
                "scenario_key": "family_pressure:rat_swarm",
                "status": "completed",
                "policy_ref": "runtime_default",
                "seed": 5,
                "max_rounds": 80,
                "rounds_completed": 30,
                "created_at": "2026-05-31T20:54:50+00:00",
                "telemetry": {"run_kind": "family_pressure"},
                "metadata": {"family_pressure": True, "storage": "redis_only"},
            }

    monkeypatch.setattr(ai_simulation_router_module, "_service", lambda _db_session: FakeService())
    monkeypatch.setattr(ai_simulation_router_module, "_progress_store_from_request", lambda _request: FakeProgressStore())

    result = await get_simulation_run(
        "family-run-1",
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace())),
        SimpleNamespace(),
    )

    assert result.id == "family-run-1"
    assert result.status == "completed"
    assert result.metadata["storage"] == "redis_only"


@pytest.mark.asyncio
async def test_family_pressure_list_includes_redis_only_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeService:
        async def list_recent(self, *, limit: int, run_kind: str | None):
            assert limit == 50
            assert run_kind is None
            return []

    class FakeProgressStore:
        async def list_progress(self):
            return [
                {
                    "id": "family-run-1",
                    "run_kind": "simulation",
                    "scenario_key": "family_pressure:rat_swarm",
                    "status": "completed",
                    "policy_ref": "runtime_default",
                    "seed": 5,
                    "max_rounds": 80,
                    "rounds_completed": 30,
                    "created_at": "2026-05-31T20:54:50+00:00",
                    "telemetry": {"run_kind": "family_pressure"},
                    "metadata": {"family_pressure": True, "storage": "redis_only"},
                }
            ]

    monkeypatch.setattr(ai_simulation_router_module, "_service", lambda _db_session: FakeService())
    monkeypatch.setattr(ai_simulation_router_module, "_progress_store_from_request", lambda _request: FakeProgressStore())

    result = await list_simulation_runs(
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace())),
        SimpleNamespace(),
        limit=50,
        run_kind=None,
    )

    assert [run.id for run in result.runs] == ["family-run-1"]
    assert result.runs[0].metadata["storage"] == "redis_only"


@pytest.mark.asyncio
async def test_family_pressure_worker_writes_completed_report_only_to_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProgressStore:
        def __init__(self) -> None:
            self.saved: list[tuple[str, dict]] = []

        async def set_progress(self, run_id: str, payload: dict) -> None:
            self.saved.append((run_id, payload))

    class FakeSessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeMonsterRepository:
        def __init__(self, _session) -> None:
            pass

        async def list_generated_clans_page(self, *, family_id: str, limit: int):
            assert family_id == "rat_swarm"
            assert limit == 100
            return [SimpleNamespace(members=[SimpleNamespace(family_id=family_id)])]

    report = FamilyPressureReport(
        family_id="rat_swarm",
        imprint_key="starter_breaker_01",
        imprint_title="Breaker",
        player_gear_score=281,
        player_start_hp=61,
        trials_per_composition=2,
        reports=[
            FamilyPressureCompositionReport(
                composition=FamilyPressureComposition(key="minionx1", role_counts={"minion": 1}),
                member_variants=["rat_minion"],
                member_roles=["minion"],
                member_gear_scores=[188],
                raw_gear_score=188,
                effective_gear_score=188.0,
                effective_ratio=0.669,
                trials=2,
                player_wins=2,
                monster_wins=0,
                draws=0,
                player_win_rate=1.0,
                avg_player_hp=59.0,
                avg_rounds=12.0,
                first_player_death_trial=None,
            )
        ],
    )

    class FakeSimulator:
        async def run(self, **kwargs):
            assert kwargs["family_id"] == "rat_swarm"
            assert kwargs["imprint_key"] == "starter_breaker_01"
            assert kwargs["seed"] == 5
            await kwargs["progress"](report)
            return report

    async def fail_mark_failed(*_args, **_kwargs):
        raise AssertionError("family pressure Redis-only worker must not mark DB rows")

    progress_store = FakeProgressStore()
    monkeypatch.setattr(ai_simulation_task_module, "_progress_store", lambda _ctx: progress_store)
    monkeypatch.setattr(ai_simulation_task_module, "get_session_context", lambda: FakeSessionContext())
    monkeypatch.setattr(ai_simulation_task_module, "MonsterGenerationRepository", FakeMonsterRepository)
    monkeypatch.setattr(ai_simulation_task_module, "FamilyPressureSimulator", lambda: FakeSimulator())
    monkeypatch.setattr(ai_simulation_task_module, "_mark_failed", fail_mark_failed)

    await combat_family_pressure_task(
        {"redis_service": object()},
        {
            "run_id": "family-run-1",
            "family_id": "rat_swarm",
            "imprint_key": "starter_breaker_01",
            "seed": 5,
            "trials": 2,
            "max_rounds": 80,
            "max_minions": 1,
            "max_scenarios": 1,
            "created_at": "2026-05-31T20:54:50+00:00",
        },
    )

    assert [status for _, doc in progress_store.saved for status in [doc["status"]]] == ["running", "completed"]
    run_id, completed = progress_store.saved[-1]
    assert run_id == "family-run-1"
    assert completed["id"] == "family-run-1"
    assert completed["status"] == "completed"
    assert completed["rounds_completed"] == 2
    assert completed["telemetry"]["run_kind"] == "family_pressure"
    assert completed["telemetry"]["first_losing_composition"] == {}
    assert completed["metadata"]["storage"] == "redis_only"
    assert completed["metadata"]["completion_reason"] == "completed"
    assert completed["metadata"]["composition_reports"][0]["member_roles"] == ["minion"]


def test_family_pressure_ladder_uses_encounter_profiles_for_swarm() -> None:
    members = [
        SimpleNamespace(role="minion", family_id="rat_swarm"),
        SimpleNamespace(role="veteran", family_id="rat_swarm"),
        SimpleNamespace(role="elite", family_id="rat_swarm"),
        SimpleNamespace(role="boss", family_id="rat_swarm"),
    ]

    rows = build_family_pressure_compositions(
        "rat_swarm",
        members=members,
        max_minions=6,
        max_scenarios=24,
    )
    role_counts = [row.role_counts for row in rows]

    assert {"minion": 3} in role_counts
    assert {"minion": 4} in role_counts
    assert {"minion": 5} in role_counts
    assert {"minion": 6} in role_counts
    assert {"minion": 1} not in role_counts
    assert {"minion": 2} not in role_counts
    assert {"minion": 5, "veteran": 1} in role_counts
    assert {"veteran": 6} in role_counts
    assert {"veteran": 4, "elite": 2} in role_counts
    assert {"veteran": 3, "elite": 3} in role_counts
    assert {"elite": 6} not in role_counts
    assert all(sum(row.values()) <= 6 for row in role_counts)
    assert [row.grade for row in rows[:4]] == ["ordinary:easy", "ordinary:easy", "ordinary:easy", "ordinary:easy"]


def test_family_pressure_ladder_uses_family_profile_body_caps() -> None:
    goblin_members = [
        SimpleNamespace(role="minion", family_id="goblin_tribe"),
        SimpleNamespace(role="veteran", family_id="goblin_tribe"),
        SimpleNamespace(role="elite", family_id="goblin_tribe"),
        SimpleNamespace(role="boss", family_id="goblin_tribe"),
    ]
    bandit_members = [
        SimpleNamespace(role="minion", family_id="bandit_gang"),
        SimpleNamespace(role="veteran", family_id="bandit_gang"),
        SimpleNamespace(role="elite", family_id="bandit_gang"),
        SimpleNamespace(role="boss", family_id="bandit_gang"),
    ]

    goblin_rows = build_family_pressure_compositions(
        "goblin_tribe",
        members=goblin_members,
        max_minions=6,
        max_scenarios=50,
    )
    bandit_rows = build_family_pressure_compositions(
        "bandit_gang",
        members=bandit_members,
        max_minions=6,
        max_scenarios=50,
    )
    goblin_counts = [row.role_counts for row in goblin_rows]
    bandit_counts = [row.role_counts for row in bandit_rows]

    assert {"minion": 5} in goblin_counts
    assert {"veteran": 5} in goblin_counts
    assert {"veteran": 3, "elite": 2} in goblin_counts
    assert {"minion": 6} not in goblin_counts
    assert {"veteran": 6} not in goblin_counts
    assert {"elite": 6} not in goblin_counts
    assert all(sum(row.values()) <= 5 for row in goblin_counts)

    assert {"minion": 3} in bandit_counts
    assert {"veteran": 3} in bandit_counts
    assert {"minion": 2, "veteran": 1} in bandit_counts
    assert {"minion": 4} not in bandit_counts
    assert {"veteran": 6} not in bandit_counts
    assert all(sum(row.values()) <= 3 for row in bandit_counts)


def test_family_pressure_uses_live_tick_simulator_by_default() -> None:
    simulator = FamilyPressureSimulator()

    assert isinstance(simulator.simulator, LiveInMemoryCombatSimulator)


@pytest.mark.asyncio
async def test_synthetic_training_enqueue_uses_combat_ai_simulation_queue() -> None:
    arq = FakeArqQueue()
    payload = {
        "run_id": "run-1",
        "generations": 60,
        "population": 32,
        "seed": 0,
        "sigma": 0.25,
    }

    await _enqueue_synthetic_training_job(arq, payload)

    assert arq.enqueued == [(COMBAT_AI_SYNTHETIC_TRAINING_TASK, payload)]


@pytest.mark.asyncio
async def test_battle_training_enqueue_uses_combat_ai_simulation_queue() -> None:
    arq = FakeArqQueue()
    payload = {
        "run_id": "run-1",
        "source_policy_run_id": "training-1",
        "generations": 12,
        "population": 8,
        "seed": 0,
        "sigma": 0.15,
    }

    await _enqueue_battle_training_job(arq, payload)

    assert arq.enqueued == [(COMBAT_AI_BATTLE_TRAINING_TASK, payload)]


def test_combat_ai_simulation_worker_registers_ai_admin_tasks() -> None:
    task_by_name = {getattr(task, "name", getattr(task, "__name__", "")): task for task in COMBAT_AI_SIMULATION_TASKS}
    assert task_by_name["combat_ai_live_simulation_task"].coroutine is combat_ai_live_simulation_task
    assert task_by_name["combat_ai_live_simulation_task"].timeout_s == AI_LIVE_SIMULATION_JOB_TIMEOUT_SECONDS
    assert "combat_family_pressure_task" not in task_by_name
    assert task_by_name["combat_ai_synthetic_training_task"].coroutine is combat_ai_synthetic_training_task
    assert task_by_name["combat_ai_synthetic_training_task"].timeout_s == AI_SYNTHETIC_TRAINING_JOB_TIMEOUT_SECONDS
    assert task_by_name["combat_ai_battle_training_task"].coroutine is combat_ai_battle_training_task
    assert task_by_name["combat_ai_battle_training_task"].timeout_s == AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS


def test_live_simulation_worker_concurrency_matches_admin_batch_size() -> None:
    assert LIVE_SIMULATION_WORKER_CONCURRENCY == 3
    assert FAMILY_PRESSURE_WORKER_CONCURRENCY == 1
    assert CombatAiSimulationArqSettings.max_jobs == COMBAT_AI_SIMULATION_WORKER_MAX_JOBS == 1
    assert CombatAiSimulationArqSettings.job_timeout == AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS


def test_combat_runtime_worker_keeps_runtime_tasks_and_has_more_slots() -> None:
    task_by_name = {getattr(task, "name", getattr(task, "__name__", "")): task for task in COMBAT_TASKS}
    task_names = set(task_by_name)

    assert "combat_ai_live_simulation_task" not in task_names
    assert "combat_ai_synthetic_training_task" not in task_names
    assert "combat_ai_battle_training_task" not in task_names
    assert task_by_name["combat_family_pressure_task"].coroutine is combat_family_pressure_task
    assert task_by_name["combat_family_pressure_task"].timeout_s == PVE_FAMILY_PRESSURE_JOB_TIMEOUT_SECONDS
    assert "execute_batch_task" in task_names
    assert "combat_collector_task" in task_names
    assert CombatArqSettings.max_jobs == COMBAT_RUNTIME_MAX_JOBS == 30
    assert CombatArqSettings.job_timeout == 60


@pytest.mark.asyncio
async def test_battle_training_task_marks_run_failed_when_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    marked_failed: dict[str, object] = {}
    policy_payload = Policy.with_defaults(policy_id="source-policy").model_dump(mode="json")

    async def fake_policy_payload_from_training_run(raw_run_id: str):
        assert raw_run_id == "source-run"
        return policy_payload, {}

    async def fake_execute_battle_training(**_kwargs):
        raise asyncio.CancelledError()

    async def fake_mark_failed(run_id: str, *, error: dict[str, object]) -> None:
        marked_failed["run_id"] = run_id
        marked_failed["error"] = error

    monkeypatch.setattr(
        ai_simulation_task_module,
        "_policy_payload_from_training_run",
        fake_policy_payload_from_training_run,
    )
    monkeypatch.setattr(ai_simulation_task_module, "execute_battle_training", fake_execute_battle_training)
    monkeypatch.setattr(ai_simulation_task_module, "_mark_failed", fake_mark_failed)

    with pytest.raises(asyncio.CancelledError):
        await combat_ai_battle_training_task(
            {},
            {
                "run_id": "battle-run",
                "source_policy_run_id": "source-run",
            },
        )

    assert marked_failed == {
        "run_id": "battle-run",
        "error": {
            "type": "CancelledError",
            "message": "Battle training worker task was cancelled or timed out.",
        },
    }


@pytest.mark.asyncio
async def test_ai_simulation_service_runs_mvp_demo_and_persists_report() -> None:
    repo = FakeSimulationRunRepository()

    row = await CombatAiSimulationRunService(repo).run_mvp_demo(seed=0, max_rounds=2)

    assert row.run_kind == "simulation"
    assert row.scenario_key == "mvp_1v1_player_model_vs_trainer_bot"
    assert row.status == "completed"
    assert row.policy_ref == "runtime_default"
    assert row.metadata_["live_policy_activation"] is False
    assert "winner:" in row.report_text
    assert isinstance(row.telemetry["damage_by_actor"], dict)


@pytest.mark.asyncio
async def test_ai_simulation_service_runs_starter_presets_demo() -> None:
    repo = FakeSimulationRunRepository()

    row = await CombatAiSimulationRunService(repo).run_starter_presets_demo(seed=0, max_rounds=1)

    assert row.run_kind == "simulation"
    assert row.scenario_key == "starter_presets_5v5"
    assert row.status == "completed"
    assert row.metadata_["simulation_actor_source"] == "character_starting_imprints"
    assert row.metadata_["live_policy_activation"] is False
    assert len(row.metadata_["participants"]) == 10
    assert row.metadata_["roster_mode"] == "seeded_random_5v5_split"
    assert row.metadata_["roster_seed"] == 0
    assert len(row.metadata_["imprint_pool"]) == len(DEFAULT_STARTER_SIMULATION_IMPRINTS)
    assert len(row.metadata_["blue_imprints"]) == 5
    assert len(row.metadata_["red_imprints"]) == 5
    assert row.metadata_["participants"][0]["combat_stats"]["damage"] > 0
    assert "winner:" in row.report_text


@pytest.mark.asyncio
async def test_ai_simulation_service_runs_random_draft_demo() -> None:
    repo = FakeSimulationRunRepository()

    row = await CombatAiSimulationRunService(repo).run_demo(
        seed=3,
        max_rounds=1,
        scenario_key="starter_presets_random_draft",
    )

    assert row.run_kind == "simulation"
    assert row.scenario_key == "starter_presets_random_draft"
    assert row.metadata_["roster_mode"] == "seeded_random_draft"
    assert row.metadata_["roster_min_team_size"] == 2
    assert row.metadata_["roster_max_team_size"] == 4
    assert 2 <= row.metadata_["roster_team_size"] <= 4
    assert len(row.metadata_["blue_imprints"]) == row.metadata_["roster_team_size"]
    assert len(row.metadata_["red_imprints"]) == row.metadata_["roster_team_size"]
    assert row.metadata_["unused_imprints"]


@pytest.mark.asyncio
async def test_ai_simulation_service_runs_mirror_10v10_demo() -> None:
    repo = FakeSimulationRunRepository()

    row = await CombatAiSimulationRunService(repo).run_demo(
        seed=0,
        max_rounds=1,
        scenario_key="starter_presets_mirror_10v10",
    )

    assert row.run_kind == "simulation"
    assert row.scenario_key == "starter_presets_mirror_10v10"
    assert row.metadata_["roster_mode"] == "mirror_full_roster"
    assert row.metadata_["roster_team_size"] == len(DEFAULT_STARTER_SIMULATION_IMPRINTS)
    assert len(row.metadata_["imprint_pool"]) == len(DEFAULT_STARTER_SIMULATION_IMPRINTS)
    assert len(row.metadata_["participants"]) == len(DEFAULT_STARTER_SIMULATION_IMPRINTS) * 2
    assert len(row.metadata_["blue_imprints"]) == len(DEFAULT_STARTER_SIMULATION_IMPRINTS)
    assert row.metadata_["blue_imprints"] == row.metadata_["red_imprints"]
    assert row.metadata_["unused_imprints"] == []


@pytest.mark.asyncio
async def test_ai_simulation_service_starts_live_starter_presets_demo() -> None:
    repo = FakeSimulationRunRepository()

    row = await CombatAiSimulationRunService(repo).start_live_starter_presets_demo(
        seed=0,
        timeout_ticks=8,
    )

    assert row.run_kind == "simulation_live"
    assert row.scenario_key == "starter_presets_5v5_live"
    assert row.status == "running"
    assert row.max_rounds == LIVE_DEFAULT_MAX_EXCHANGES
    assert row.metadata_["simulation_mode"] == "live_tick"
    assert row.metadata_["completion_reason"] == "running"
    assert row.metadata_["tick_interval_seconds"] == LIVE_DEFAULT_TICK_INTERVAL_SECONDS
    assert row.metadata_["roster_mode"] == "seeded_random_5v5_split"
    assert len(row.metadata_["imprint_pool"]) == len(DEFAULT_STARTER_SIMULATION_IMPRINTS)
    assert len(row.metadata_["participants"]) == 10
    assert len(row.metadata_["live_snapshot"]["actors"]) == 10


@pytest.mark.asyncio
async def test_ai_simulation_service_starts_live_starter_presets_with_maxed_existing_skills() -> None:
    repo = FakeSimulationRunRepository()

    row = await CombatAiSimulationRunService(repo).start_live_starter_presets_demo(
        seed=0,
        timeout_ticks=8,
        scenario_key="starter_presets_5v5_live_full_skills",
        skill_profile=STARTER_SKILL_PROFILE_MAXED_EXISTING,
    )

    assert row.scenario_key == "starter_presets_5v5_live_full_skills"
    assert row.metadata_["skill_profile"] == STARTER_SKILL_PROFILE_MAXED_EXISTING
    participants = row.metadata_["participants"]
    assert len(participants) == 10
    for participant in participants:
        assert participant["skill_profile"] == STARTER_SKILL_PROFILE_MAXED_EXISTING
        assert participant["skills"]
        assert set(participant["skills"].values()) == {1.0}


def test_live_skill_profile_is_selected_by_full_skills_scenario_suffix() -> None:
    assert _live_skill_profile_from_scenario("starter_presets_5v5_live") == STARTER_SKILL_PROFILE_BASELINE
    assert (
        _live_skill_profile_from_scenario("starter_presets_mirror_10v10_live_full_skills")
        == STARTER_SKILL_PROFILE_MAXED_EXISTING
    )


@pytest.mark.asyncio
async def test_ai_simulation_service_starts_live_demo_with_latest_training_policy() -> None:
    policy = Policy.with_defaults(policy_id="trained-live-test", weights={"multi_target": 2.0})
    repo = FakeSimulationRunRepository()
    repo.recent = [
        SimpleNamespace(
            id="training-1",
            run_kind="training",
            status="completed",
            reward=21.8,
            metadata_={"best_policy": policy.model_dump(mode="json")},
        )
    ]

    row = await CombatAiSimulationRunService(repo).start_live_starter_presets_demo_with_latest_training_file(
        seed=0,
        timeout_ticks=8,
    )

    assert row.run_kind == "simulation_live"
    assert row.scenario_key == "starter_presets_5v5_live_latest_training_file"
    assert row.status == "running"
    assert row.policy_ref == "training:training-1"
    assert row.metadata_["policy_source"] == "training_run"
    assert row.metadata_["policy_source_run_id"] == "training-1"
    assert row.metadata_["policy_found"] is True
    assert row.metadata_["policy_id"] == "trained-live-test"
    assert row.metadata_["live_policy_activation"] is False


@pytest.mark.asyncio
async def test_ai_simulation_service_starts_live_demo_with_selected_training_policy() -> None:
    policy = Policy.with_defaults(policy_id="selected-live-test", weights={"multi_target": 1.5})
    repo = FakeSimulationRunRepository()
    repo.recent = [
        SimpleNamespace(
            id="training-selected",
            run_kind="training",
            status="completed",
            reward=22.2,
            metadata_={"best_policy": policy.model_dump(mode="json")},
        )
    ]

    row = await CombatAiSimulationRunService(repo).start_live_starter_presets_demo_with_training_policy(
        policy_run_id="training-selected",
        seed=0,
        timeout_ticks=8,
        scenario_key="starter_presets_mirror_10v10_live",
        mirror_full_roster=True,
    )

    assert row.run_kind == "simulation_live"
    assert row.scenario_key == "starter_presets_mirror_10v10_live"
    assert row.status == "running"
    assert row.policy_ref == "training:training-selected"
    assert row.metadata_["policy_source_run_id"] == "training-selected"
    assert row.metadata_["policy_id"] == "selected-live-test"
    assert row.metadata_["roster_mode"] == "mirror_full_roster"


@pytest.mark.asyncio
async def test_ai_simulation_service_starts_battle_training_from_selected_policy() -> None:
    policy = Policy.with_defaults(policy_id="source-policy", weights={"multi_target": 1.5})
    repo = FakeSimulationRunRepository()
    repo.recent = [
        SimpleNamespace(
            id="training-source",
            run_kind="training",
            status="completed",
            reward=22.2,
            metadata_={"best_policy": policy.model_dump(mode="json")},
        )
    ]

    row = await CombatAiSimulationRunService(repo).start_battle_training(
        source_policy_run_id="training-source",
        generations=12,
        population=8,
        seed=0,
    )

    assert row.run_kind == "training"
    assert row.scenario_key == "battle_policy_finetune"
    assert row.status == "running"
    assert row.policy_ref == "training:training-source"
    assert row.telemetry["run_kind"] == "battle_training"
    assert row.metadata_["training_stage"] == "battle_finetune"
    assert row.metadata_["source_policy_run_id"] == "training-source"
    assert row.metadata_["policy_id"] == "source-policy"
    assert row.metadata_["live_policy_activation"] is False


@pytest.mark.asyncio
async def test_execute_battle_training_smoke_persists_candidate_policy_in_result(tmp_path) -> None:
    progress_updates: list[dict] = []

    async def progress(payload: dict) -> None:
        progress_updates.append(payload)

    result = await execute_battle_training(
        source_policy=Policy.with_defaults(policy_id="smoke-source"),
        source_policy_run_id="training-source",
        generations=1,
        population=2,
        seed=0,
        sigma=0.05,
        progress=progress,
    )

    assert result["rounds_completed"] == 1
    assert result["metadata"]["training_stage"] == "battle_finetune"
    assert result["metadata"]["source_policy_run_id"] == "training-source"
    assert result["metadata"]["storage"] == "database"
    assert result["metadata"]["best_policy"]["policy_id"]
    assert "output_dir" not in result["metadata"]
    assert "metrics_path" not in result["metadata"]
    assert result["telemetry"]["scenario_rewards"]
    assert result["telemetry"]["metrics"]
    assert result["telemetry"]["leaderboard"]
    assert list(tmp_path.rglob("*")) == []
    assert progress_updates
    assert progress_updates[-1]["status"] == "running"
    assert progress_updates[-1]["telemetry"]["run_kind"] == "battle_training"
    assert progress_updates[-1]["telemetry"]["battles_done"] == 24
    assert progress_updates[-1]["telemetry"]["battles_total"] == 24
    assert "battle policy fine-tune" in progress_updates[-1]["report_text"]


def test_battle_training_scenario_set_covers_seed_variance_and_mirror_modes() -> None:
    scenarios = _battle_training_scenarios(0)
    names = {scenario.name for scenario in scenarios}

    assert len(scenarios) == 12
    assert {
        "random_5v5_baseline_blue",
        "random_5v5_seed31_baseline_blue",
        "random_5v5_seed43_full_skills_red",
        "mirror_10v10_baseline_blue",
        "mirror_10v10_full_skills_red",
    } <= names
    assert {scenario.candidate_team for scenario in scenarios} == {"blue", "red"}
    assert {scenario.skill_profile for scenario in scenarios} == {
        STARTER_SKILL_PROFILE_BASELINE,
        STARTER_SKILL_PROFILE_MAXED_EXISTING,
    }
    assert sum(1 for scenario in scenarios if scenario.mirror_full_roster) == 4


@pytest.mark.asyncio
async def test_ai_simulation_service_executes_live_demo_with_redis_progress_and_final_persist() -> None:
    updates = []
    progress_updates = []

    async def persist(status, rounds_completed, winner, reward, telemetry, report_text, metadata):
        updates.append(
            {
                "status": status,
                "rounds_completed": rounds_completed,
                "winner": winner,
                "reward": reward,
                "telemetry": telemetry,
                "report_text": report_text,
                "metadata": metadata,
            }
        )

    async def progress(payload):
        progress_updates.append(payload)

    await CombatAiSimulationRunService(FakeSimulationRunRepository()).execute_live_starter_presets_demo(
        "run-1",
        seed=0,
        max_rounds=1,
        tick_interval_seconds=0,
        timeout_ticks=2,
        persist=persist,
        progress=progress,
    )

    assert updates
    assert all(update["status"] == "completed" for update in updates)
    assert progress_updates
    assert all(update["status"] == "running" for update in progress_updates)
    assert progress_updates[-1]["metadata"]["simulation_mode"] == "live_tick"
    assert updates[-1]["status"] == "completed"
    assert updates[-1]["rounds_completed"] <= 1
    assert updates[-1]["winner"] is None
    assert updates[-1]["metadata"]["simulation_mode"] == "live_tick"
    assert updates[-1]["metadata"]["completion_reason"] == "max_exchanges_reached"
    assert "live_snapshot" in updates[-1]["metadata"]


@pytest.mark.asyncio
async def test_ai_simulation_service_executes_live_demo_with_policy_payload_metadata() -> None:
    policy = Policy.with_defaults(policy_id="trained-live-exec", weights={"team_focus": 1.0})
    updates = []

    async def persist(status, rounds_completed, winner, reward, telemetry, report_text, metadata):
        updates.append(
            {
                "status": status,
                "rounds_completed": rounds_completed,
                "winner": winner,
                "reward": reward,
                "telemetry": telemetry,
                "report_text": report_text,
                "metadata": metadata,
            }
        )

    await CombatAiSimulationRunService(FakeSimulationRunRepository()).execute_live_starter_presets_demo(
        "run-1",
        seed=0,
        max_rounds=1,
        tick_interval_seconds=0,
        timeout_ticks=2,
        policy_payload=policy.model_dump(mode="json"),
        policy_metadata={"policy_source": "training_run", "policy_source_run_id": "training-1", "policy_id": policy.policy_id},
        persist=persist,
        progress=None,
    )

    assert updates
    assert updates[-1]["metadata"]["policy_source"] == "training_run"
    assert updates[-1]["metadata"]["policy_source_run_id"] == "training-1"
    assert updates[-1]["metadata"]["policy_id"] == "trained-live-exec"
    assert updates[-1]["metadata"]["live_policy_activation"] is False


@pytest.mark.asyncio
async def test_ai_simulation_service_executes_live_demo_with_preselected_roster() -> None:
    updates = []

    async def persist(status, rounds_completed, winner, reward, telemetry, report_text, metadata):
        updates.append(
            {
                "status": status,
                "rounds_completed": rounds_completed,
                "winner": winner,
                "reward": reward,
                "telemetry": telemetry,
                "report_text": report_text,
                "metadata": metadata,
            }
        )

    blue = (
        "starter_guard_01",
        "starter_tactician_01",
        "starter_heavy_guard_01",
        "starter_breaker_01",
        "starter_hunter_01",
    )
    red = (
        "starter_rift_survivor_01",
        "starter_dual_blades_01",
        "starter_dual_sword_01",
        "starter_dual_mace_01",
        "starter_archer_01",
    )

    await CombatAiSimulationRunService(FakeSimulationRunRepository()).execute_live_starter_presets_demo(
        "run-1",
        seed=999,
        max_rounds=1,
        tick_interval_seconds=0,
        timeout_ticks=2,
        blue_imprints=blue,
        red_imprints=red,
        min_team_size=5,
        max_team_size=5,
        persist=persist,
        progress=None,
    )

    assert updates
    assert updates[-1]["metadata"]["blue_imprints"] == list(blue)
    assert updates[-1]["metadata"]["red_imprints"] == list(red)
    assert updates[-1]["metadata"]["roster_mode"] == "seeded_random_5v5_split"


@pytest.mark.asyncio
async def test_live_worker_loads_policy_payload_from_training_run_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = Policy.with_defaults(policy_id="trained-worker-exec", weights={"team_focus": 1.0})
    training_row = SimpleNamespace(
        id="training-1",
        run_kind="training",
        status="completed",
        reward=21.8,
        metadata_={"best_policy": policy.model_dump(mode="json")},
    )

    class FakeSessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeRepository:
        def __init__(self, _session) -> None:
            pass

        async def get(self, run_id: str):
            assert run_id == "training-1"
            return training_row

    monkeypatch.setattr(ai_simulation_task_module, "get_session_context", lambda: FakeSessionContext())
    monkeypatch.setattr(ai_simulation_task_module, "CombatAiSimulationRunRepository", FakeRepository)

    payload, metadata = await _policy_payload_from_training_run("training-1")

    assert payload is not None
    assert payload["policy_id"] == "trained-worker-exec"
    assert metadata["policy_source"] == "training_run"
    assert metadata["policy_source_run_id"] == "training-1"
    assert metadata["policy_id"] == "trained-worker-exec"
    assert "best_policy_path" not in metadata


@pytest.mark.asyncio
async def test_ai_simulation_service_can_run_starter_presets_with_latest_training_policy() -> None:
    policy = Policy.with_defaults(policy_id="trained-test", weights={"expected_damage": 2.5})
    repo = FakeSimulationRunRepository()
    repo.recent = [
        SimpleNamespace(
            id="training-1",
            run_kind="training",
            status="completed",
            reward=21.8,
            metadata_={"best_policy": policy.model_dump(mode="json")},
        )
    ]

    row = await CombatAiSimulationRunService(repo).run_demo(
        seed=0,
        max_rounds=1,
        scenario_key="starter_presets_5v5_latest_training_file",
    )

    assert row.run_kind == "simulation"
    assert row.scenario_key == "starter_presets_5v5_latest_training_file"
    assert row.status == "completed"
    assert row.policy_ref == "training:training-1"
    assert row.metadata_["policy_found"] is True
    assert row.metadata_["policy_source_run_id"] == "training-1"
    assert row.metadata_["policy_id"] == "trained-test"
    assert row.metadata_["live_policy_activation"] is False


@pytest.mark.asyncio
async def test_ai_simulation_service_runs_synthetic_training_without_live_activation() -> None:
    repo = FakeSimulationRunRepository()

    row = await CombatAiSimulationRunService(repo).run_synthetic_training(generations=2, population=4, seed=0)

    assert row.run_kind == "training"
    assert row.scenario_key == "synthetic_policy_training"
    assert row.policy_ref == "candidate_not_activated"
    assert row.rounds_completed == 2
    assert row.metadata_["live_policy_activation"] is False
    assert row.metadata_["storage"] == "database"
    assert "output_dir" not in row.metadata_
    assert "best_policy" in row.metadata_
    assert row.telemetry["generations"] == 2
    assert row.telemetry["population"] == 4
    assert isinstance(row.telemetry["top_weight_deltas"], list)
    assert isinstance(row.telemetry["weight_deltas_count"], int)
    assert "training: synthetic policy weights" in row.report_text


def test_ai_simulation_view_exposes_storage_fields() -> None:
    row = SimpleNamespace(
        id="run-1",
        run_kind="simulation",
        scenario_key="mvp",
        status="completed",
        policy_ref="runtime_default",
        seed=0,
        max_rounds=5,
        rounds_completed=1,
        winner="red",
        reward=42.0,
        telemetry={"action_count": 2},
        report_text="winner: red",
        metadata_={"live_policy_activation": False},
        created_at=None,
    )

    dto = _view(row)

    assert dto.id == "run-1"
    assert dto.telemetry == {"action_count": 2}
    assert dto.metadata["live_policy_activation"] is False


def test_ai_simulation_view_can_overlay_hot_progress() -> None:
    row = SimpleNamespace(
        id="run-1",
        run_kind="simulation_live",
        scenario_key="live",
        status="running",
        policy_ref="runtime_default",
        seed=0,
        max_rounds=500,
        rounds_completed=0,
        winner=None,
        reward=None,
        telemetry={"status_message": "scheduled"},
        report_text="scheduled",
        metadata_={"completion_reason": "running"},
        created_at=None,
    )

    dto = _view(
        row,
        {
            "status": "running",
            "rounds_completed": 12,
            "winner": None,
            "reward": 4.5,
            "telemetry": {"damage_by_actor": {"a": 10}},
            "report_text": "hot progress",
            "metadata": {"completion_reason": "running", "tick_index": 99},
        },
    )

    assert dto.rounds_completed == 12
    assert dto.reward == 4.5
    assert dto.telemetry == {"damage_by_actor": {"a": 10}}
    assert dto.report_text == "hot progress"
    assert dto.metadata["tick_index"] == 99


@pytest.mark.asyncio
async def test_ai_simulation_service_clears_saved_reports() -> None:
    repo = FakeSimulationRunRepository()
    repo.recent = [
        SimpleNamespace(id="run-1", run_kind="simulation"),
        SimpleNamespace(id="run-2", run_kind="simulation_live"),
        SimpleNamespace(id="training-1", run_kind="training"),
    ]

    deleted = await CombatAiSimulationRunService(repo).clear_reports()

    assert deleted == 2
    assert [row.id for row in repo.recent] == ["training-1"]


@pytest.mark.asyncio
async def test_ai_simulation_service_clears_training_runs_only() -> None:
    repo = FakeSimulationRunRepository()
    repo.recent = [
        SimpleNamespace(id="run-1", run_kind="simulation"),
        SimpleNamespace(id="run-2", run_kind="simulation_live"),
        SimpleNamespace(id="training-1", run_kind="training"),
        SimpleNamespace(id="training-2", run_kind="training"),
    ]

    deleted = await CombatAiSimulationRunService(repo).clear_training_runs()

    assert deleted == 2
    assert [row.id for row in repo.recent] == ["run-1", "run-2"]


@pytest.mark.asyncio
async def test_ai_simulation_service_marks_stale_running_reports() -> None:
    from datetime import UTC, datetime, timedelta

    repo = FakeSimulationRunRepository()
    repo.recent = [
        SimpleNamespace(id="stale", status="running", created_at=datetime.now(UTC) - timedelta(hours=1), metadata_={}),
        SimpleNamespace(id="fresh", status="running", created_at=datetime.now(UTC), metadata_={}),
        SimpleNamespace(id="done", status="completed", created_at=datetime.now(UTC) - timedelta(hours=1), metadata_={}),
    ]

    updated = await CombatAiSimulationRunService(repo).cleanup_stale_running_reports(older_than_minutes=20)

    assert updated == 1
    assert repo.recent[0].status == "failed"
    assert repo.recent[0].metadata_["completion_reason"] == "stale_running_cleanup"
    assert repo.recent[1].status == "running"
    assert repo.recent[2].status == "completed"


def test_simulation_reward_is_winner_neutral() -> None:
    participants = [
        {"actor_id": "blue_a", "team": "blue"},
        {"actor_id": "red_a", "team": "red"},
    ]
    telemetry = {
        "damage_by_actor": {"blue_a": 80, "red_a": 50},
        "resource_spent_by_actor": {"blue_a": 10},
    }

    reward = _simulation_reward(
        "blue",
        telemetry,
        participants,
        final_hp_by_actor={"blue_a": 20, "red_a": 0},
    )

    assert reward == pytest.approx(134.0)
