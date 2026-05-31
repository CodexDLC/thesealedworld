from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from src.backend.features.combat.api import ai_simulation_router as ai_simulation_router_module
from src.backend.features.combat.api.ai_simulation_router import (
    COMBAT_AI_BATTLE_TRAINING_TASK,
    COMBAT_AI_LIVE_SIMULATION_TASK,
    COMBAT_AI_SYNTHETIC_TRAINING_TASK,
    _enqueue_battle_training_job,
    _enqueue_live_demo_job,
    _enqueue_synthetic_training_job,
    _live_skill_profile_from_scenario,
    _view,
    run_live_demo_simulation_batch,
)
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.simulation import (
    BALANCE_TEST_SIMULATION_IMPRINTS,
    DEFAULT_STARTER_SIMULATION_IMPRINTS,
    STARTER_SKILL_PROFILE_BASELINE,
    STARTER_SKILL_PROFILE_MAXED_EXISTING,
)
from src.backend.features.combat.services.ai_simulation_service import (
    LIVE_DEFAULT_MAX_EXCHANGES,
    LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
    CombatAiSimulationRunService,
    _battle_training_scenarios,
    _simulation_reward,
    execute_battle_training,
)
from src.backend.features.combat.workers.arq import (
    AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS,
    AI_LIVE_SIMULATION_JOB_TIMEOUT_SECONDS,
    AI_SYNTHETIC_TRAINING_JOB_TIMEOUT_SECONDS,
    COMBAT_TASKS,
    CombatArqSettings,
)
from src.backend.features.combat.workers.tasks import ai_simulation_task as ai_simulation_task_module
from src.backend.features.combat.workers.tasks.ai_simulation_task import (
    LIVE_SIMULATION_WORKER_CONCURRENCY,
    _policy_payload_from_training_run,
    combat_ai_battle_training_task,
    combat_ai_live_simulation_task,
    combat_ai_synthetic_training_task,
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


class FakeArqQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, dict]] = []

    async def enqueue_job(self, name: str, payload: dict) -> None:
        self.enqueued.append((name, payload))


@pytest.mark.asyncio
async def test_live_demo_enqueue_uses_combat_worker_queue() -> None:
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
    with pytest.raises(RuntimeError, match="Combat ARQ service is not available"):
        await _enqueue_live_demo_job(None, {"run_id": "run-1"})


@pytest.mark.asyncio
async def test_live_demo_batch_creates_rows_once_and_enqueues_all(monkeypatch: pytest.MonkeyPatch) -> None:
    rows: list[SimpleNamespace] = []

    class FakeDbSession:
        def __init__(self) -> None:
            self.commit_calls = 0

        async def commit(self) -> None:
            self.commit_calls += 1

    class FakeService:
        async def start_live_starter_presets_demo(
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
            policy_source_run_id: str | None = None,
        ):
            row = SimpleNamespace(
                id=f"run-{len(rows) + 1}",
                run_kind="simulation_live",
                scenario_key=scenario_key,
                status="running",
                policy_ref="runtime_default",
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
                    "policy_source_run_id": policy_source_run_id or "",
                },
            )
            rows.append(row)
            return row

    db_session = FakeDbSession()
    arq = FakeArqQueue()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(combat_arq=arq)))
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
    assert [row.seed for row in result.runs] == [999_998, 999_999, 0]
    assert [payload["seed"] for _, payload in arq.enqueued] == [999_998, 999_999, 0]
    assert [payload["run_id"] for _, payload in arq.enqueued] == ["run-1", "run-2", "run-3"]
    assert [payload["min_team_size"] for _, payload in arq.enqueued] == [2, 2, 2]
    assert [payload["max_team_size"] for _, payload in arq.enqueued] == [4, 4, 4]
    assert {name for name, _ in arq.enqueued} == {COMBAT_AI_LIVE_SIMULATION_TASK}


@pytest.mark.asyncio
async def test_synthetic_training_enqueue_uses_combat_worker_queue() -> None:
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
async def test_battle_training_enqueue_uses_combat_worker_queue() -> None:
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


def test_combat_worker_registers_ai_admin_tasks() -> None:
    task_by_name = {getattr(task, "name", getattr(task, "__name__", "")): task for task in COMBAT_TASKS}
    assert task_by_name["combat_ai_live_simulation_task"].coroutine is combat_ai_live_simulation_task
    assert task_by_name["combat_ai_live_simulation_task"].timeout_s == AI_LIVE_SIMULATION_JOB_TIMEOUT_SECONDS
    assert task_by_name["combat_ai_synthetic_training_task"].coroutine is combat_ai_synthetic_training_task
    assert task_by_name["combat_ai_synthetic_training_task"].timeout_s == AI_SYNTHETIC_TRAINING_JOB_TIMEOUT_SECONDS
    assert task_by_name["combat_ai_battle_training_task"].coroutine is combat_ai_battle_training_task
    assert task_by_name["combat_ai_battle_training_task"].timeout_s == AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS


def test_live_simulation_worker_concurrency_matches_admin_batch_size() -> None:
    assert LIVE_SIMULATION_WORKER_CONCURRENCY == 3
    assert CombatArqSettings.max_jobs == LIVE_SIMULATION_WORKER_CONCURRENCY
    assert CombatArqSettings.job_timeout == AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS


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
    assert len(row.metadata_["imprint_pool"]) == len(BALANCE_TEST_SIMULATION_IMPRINTS)
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
    assert row.metadata_["roster_mode"] == "mirror_10v10"
    assert row.metadata_["roster_team_size"] == 10
    assert len(row.metadata_["imprint_pool"]) == len(DEFAULT_STARTER_SIMULATION_IMPRINTS)
    assert len(row.metadata_["participants"]) == 20
    assert len(row.metadata_["blue_imprints"]) == 10
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
    assert len(row.metadata_["imprint_pool"]) == len(BALANCE_TEST_SIMULATION_IMPRINTS)
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
    assert row.metadata_["roster_mode"] == "mirror_10v10"


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
        "starter_breaker_01",
        "starter_duelist_01",
        "starter_dual_blades_01",
        "starter_hunter_01",
    )
    red = (
        "starter_archer_01",
        "starter_staff_01",
        "starter_heavy_guard_01",
        "starter_tactician_01",
        "starter_rift_survivor_01",
    )

    await CombatAiSimulationRunService(FakeSimulationRunRepository()).execute_live_starter_presets_demo(
        "run-1",
        seed=999,
        max_rounds=1,
        tick_interval_seconds=0,
        timeout_ticks=2,
        blue_imprints=blue,
        red_imprints=red,
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
