from __future__ import annotations

import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto import ActorLoadoutDTO, ActorMetaDTO, ActorRawDTO, ActorSnapshot, FeintHandDTO
from src.backend.features.combat.dto.actor import ActorStats
from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain
from src.backend.features.combat.runtime.ai.policy import DEFAULT_WEIGHT_KEYS, Policy
from src.backend.features.combat.runtime.ai.training import TrainArgs, train
from src.backend.features.combat.runtime.ai.training.environment import ScoringEnvironment
from src.backend.features.combat.runtime.ai.training.scenarios import default_scenario_set
from src.backend.features.combat.runtime.simulation import (
    DEFAULT_STARTER_SIMULATION_IMPRINTS,
    STARTER_SKILL_PROFILE_BASELINE,
    STARTER_SKILL_PROFILE_MAXED_EXISTING,
    AiSimulationIntentProvider,
    FamilyPressureReport,
    InMemoryBattleFactory,
    InMemoryBattleLimits,
    InMemoryCombatSimulator,
    LiveInMemoryCombatSimulator,
    LiveSimulationStepResult,
    LiveSimulationTiming,
    StartingImprintSimulationActorBuilder,
    random_starter_6v6_imprints,
    random_starter_roster_imprints,
    render_simulation_report,
)
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO

if TYPE_CHECKING:
    from src.backend.infrastructure.combat.models import CombatAiSimulationRun
    from src.backend.infrastructure.combat.repositories import CombatAiSimulationRunRepository

LivePersistCallback = Callable[
    [str, int, str | None, float | None, dict[str, Any], str, dict[str, Any]], Awaitable[None]
]
LiveProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]
LIVE_DEFAULT_MAX_EXCHANGES = 500
LIVE_DEFAULT_TICK_INTERVAL_SECONDS = 0.05


class CombatAiSimulationRunService:
    def __init__(self, repository: CombatAiSimulationRunRepository) -> None:
        self.repository = repository

    async def list_recent(self, *, limit: int = 50, run_kind: str | None = None) -> list[CombatAiSimulationRun]:
        return await self.repository.list_recent(limit=limit, run_kind=run_kind)

    async def get(self, run_id: str) -> CombatAiSimulationRun | None:
        return await self.repository.get(run_id)

    async def clear_reports(self) -> int:
        return await self.repository.clear_run_kinds(["simulation", "simulation_live"])

    async def clear_training_runs(self) -> int:
        return await self.repository.clear_run_kinds(["training"])

    async def cleanup_stale_running_reports(self, *, older_than_minutes: int = 20) -> int:
        cutoff = datetime.now(UTC) - timedelta(minutes=int(older_than_minutes))
        return await self.repository.mark_running_stale(before=cutoff)

    async def run_mvp_demo(self, *, seed: int = 0, max_rounds: int = 5) -> CombatAiSimulationRun:
        return await self.run_demo(seed=seed, max_rounds=max_rounds, scenario_key="mvp_1v1_player_model_vs_trainer_bot")

    async def run_demo(
        self,
        *,
        seed: int = 0,
        max_rounds: int = 5,
        scenario_key: str = "starter_presets_5v5",
    ) -> CombatAiSimulationRun:
        if scenario_key == "mvp_1v1_player_model_vs_trainer_bot":
            return await self._run_smoke_demo(seed=seed, max_rounds=max_rounds)
        if scenario_key == "starter_presets_5v5_latest_training_file":
            return await self.run_starter_presets_demo_with_latest_training_file(seed=seed, max_rounds=max_rounds)
        if scenario_key == "starter_presets_random_draft":
            return await self._run_starter_presets_demo(
                seed=seed,
                max_rounds=max_rounds,
                scenario_key="starter_presets_random_draft",
                policy_ref="runtime_default",
                policy=None,
                policy_metadata={},
                min_team_size=2,
                max_team_size=4,
            )
        if scenario_key == "starter_presets_mirror_10v10":
            return await self._run_starter_presets_demo(
                seed=seed,
                max_rounds=max_rounds,
                scenario_key="starter_presets_mirror_10v10",
                policy_ref="runtime_default",
                policy=None,
                policy_metadata={},
                mirror_full_roster=True,
            )
        return await self.run_starter_presets_demo(seed=seed, max_rounds=max_rounds)

    async def run_starter_presets_demo(self, *, seed: int = 0, max_rounds: int = 8) -> CombatAiSimulationRun:
        return await self._run_starter_presets_demo(
            seed=seed,
            max_rounds=max_rounds,
            scenario_key="starter_presets_5v5",
            policy_ref="runtime_default",
            policy=None,
            policy_metadata={},
        )

    async def start_live_starter_presets_demo(
        self,
        *,
        seed: int = 0,
        max_rounds: int = LIVE_DEFAULT_MAX_EXCHANGES,
        tick_interval_seconds: float = LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
        timeout_ticks: int = 8,
        min_team_size: int = 6,
        max_team_size: int = 6,
        scenario_key: str = "starter_presets_5v5_live",
        mirror_full_roster: bool = False,
        skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
        policy_ref: str = "runtime_default",
        policy_metadata: dict[str, Any] | None = None,
    ) -> CombatAiSimulationRun:
        actors, participants, roster_metadata = _build_starter_roster(
            seed=seed,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
        )
        return await self.repository.create(
            run_kind="simulation_live",
            scenario_key=scenario_key,
            status="running",
            policy_ref=policy_ref,
            seed=seed,
            max_rounds=max_rounds,
            rounds_completed=0,
            winner=None,
            reward=None,
            telemetry={"status_message": "live simulation scheduled", "action_count": 0, "round_events": []},
            report_text="live simulation scheduled\nlive_policy_activation: false",
            metadata={
                "source": "admin_cabinet",
                "purpose": "live_testing_report",
                "simulation_actor_source": "character_starting_imprints",
                "simulation_mode": "live_tick",
                "skill_profile": skill_profile,
                "completion_reason": "running",
                "tick_interval_seconds": tick_interval_seconds,
                "timeout_ticks": timeout_ticks,
                "participants": participants,
                **roster_metadata,
                **(policy_metadata or {}),
                "team_labels": {"blue": "Стартовые пресеты A", "red": "Стартовые пресеты B"},
                "final_hp_by_actor": {str(actor.meta.id): actor.meta.hp for actor in actors},
                "live_snapshot": _live_snapshot_from_actors(actors, targets={}),
                "live_policy_activation": False,
            },
        )

    async def schedule_live_starter_presets_demo(
        self,
        *,
        seed: int = 0,
        max_rounds: int = LIVE_DEFAULT_MAX_EXCHANGES,
        tick_interval_seconds: float = LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
        timeout_ticks: int = 8,
        min_team_size: int = 6,
        max_team_size: int = 6,
        scenario_key: str = "starter_presets_5v5_live",
        mirror_full_roster: bool = False,
        skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
        policy_ref: str = "runtime_default",
        policy_metadata: dict[str, Any] | None = None,
    ) -> CombatAiSimulationRun:
        roster_metadata = _scheduled_roster_metadata(
            seed=seed,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            mirror_full_roster=mirror_full_roster,
        )
        return await self.repository.create(
            run_kind="simulation_live",
            scenario_key=scenario_key,
            status="running",
            policy_ref=policy_ref,
            seed=seed,
            max_rounds=max_rounds,
            rounds_completed=0,
            winner=None,
            reward=None,
            telemetry={"status_message": "live simulation scheduled", "action_count": 0, "round_events": []},
            report_text="live simulation scheduled\nlive_policy_activation: false",
            metadata={
                "source": "admin_cabinet",
                "purpose": "live_testing_report",
                "simulation_actor_source": "character_starting_imprints",
                "simulation_mode": "live_tick",
                "skill_profile": skill_profile,
                "completion_reason": "running",
                "tick_interval_seconds": tick_interval_seconds,
                "timeout_ticks": timeout_ticks,
                "participants": [],
                **roster_metadata,
                **(policy_metadata or {}),
                "team_labels": {"blue": "Стартовые пресеты A", "red": "Стартовые пресеты B"},
                "final_hp_by_actor": {},
                "live_snapshot": {"actors": []},
                "live_policy_activation": False,
            },
        )

    async def schedule_live_starter_presets_demo_with_latest_training_file(
        self,
        *,
        seed: int = 0,
        max_rounds: int = LIVE_DEFAULT_MAX_EXCHANGES,
        tick_interval_seconds: float = LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
        timeout_ticks: int = 8,
        min_team_size: int = 6,
        max_team_size: int = 6,
        scenario_key: str = "starter_presets_5v5_live_latest_training_file",
        mirror_full_roster: bool = False,
        skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
    ) -> CombatAiSimulationRun:
        training_row = await self.repository.latest_completed_training_with_policy()
        if training_row is None:
            return await self.repository.create(
                run_kind="simulation_live",
                scenario_key=scenario_key,
                status="failed",
                policy_ref="training:not_found",
                seed=seed,
                max_rounds=max_rounds,
                rounds_completed=0,
                winner=None,
                reward=None,
                telemetry={},
                report_text=(
                    "training policy version not found\n"
                    "Run synthetic training first, then start this scenario again.\n"
                    "live_policy_activation: false"
                ),
                metadata={
                    "source": "admin_cabinet",
                    "purpose": "live_testing_report",
                    "simulation_actor_source": "character_starting_imprints",
                    "simulation_mode": "live_tick",
                    "policy_source": "training_run",
                    "policy_found": False,
                    "completion_reason": "training_policy_not_found",
                    "live_policy_activation": False,
                },
            )

        _policy, policy_metadata = _policy_from_training_row(training_row)
        return await self.schedule_live_starter_presets_demo(
            seed=seed,
            max_rounds=max_rounds,
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            scenario_key=scenario_key,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
            policy_ref=f"training:{training_row.id}",
            policy_metadata=policy_metadata,
        )

    async def schedule_live_starter_presets_demo_with_training_policy(
        self,
        *,
        policy_run_id: str,
        seed: int = 0,
        max_rounds: int = LIVE_DEFAULT_MAX_EXCHANGES,
        tick_interval_seconds: float = LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
        timeout_ticks: int = 8,
        min_team_size: int = 6,
        max_team_size: int = 6,
        scenario_key: str = "starter_presets_5v5_live",
        mirror_full_roster: bool = False,
        skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
    ) -> CombatAiSimulationRun:
        training_row = await self.repository.get(str(policy_run_id))
        if (
            training_row is None
            or training_row.run_kind != "training"
            or training_row.status != "completed"
            or not isinstance(dict(training_row.metadata_ or {}).get("best_policy"), dict)
        ):
            return await self.repository.create(
                run_kind="simulation_live",
                scenario_key=scenario_key,
                status="failed",
                policy_ref=f"training:{policy_run_id}:not_found",
                seed=seed,
                max_rounds=max_rounds,
                rounds_completed=0,
                winner=None,
                reward=None,
                telemetry={},
                report_text=(
                    "selected training policy version not found\n"
                    "Choose a completed training run with metadata.best_policy, then start this scenario again.\n"
                    "live_policy_activation: false"
                ),
                metadata={
                    "source": "admin_cabinet",
                    "purpose": "live_testing_report",
                    "simulation_actor_source": "character_starting_imprints",
                    "simulation_mode": "live_tick",
                    "policy_source": "training_run",
                    "policy_source_run_id": str(policy_run_id),
                    "policy_found": False,
                    "completion_reason": "training_policy_not_found",
                    "live_policy_activation": False,
                },
            )

        _policy, policy_metadata = _policy_from_training_row(training_row)
        return await self.schedule_live_starter_presets_demo(
            seed=seed,
            max_rounds=max_rounds,
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            scenario_key=scenario_key,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
            policy_ref=f"training:{training_row.id}",
            policy_metadata=policy_metadata,
        )

    async def start_live_starter_presets_demo_with_latest_training_file(
        self,
        *,
        seed: int = 0,
        max_rounds: int = LIVE_DEFAULT_MAX_EXCHANGES,
        tick_interval_seconds: float = LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
        timeout_ticks: int = 8,
        min_team_size: int = 6,
        max_team_size: int = 6,
        scenario_key: str = "starter_presets_5v5_live_latest_training_file",
        mirror_full_roster: bool = False,
        skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
    ) -> CombatAiSimulationRun:
        training_row = await self.repository.latest_completed_training_with_policy()
        if training_row is None:
            return await self.repository.create(
                run_kind="simulation_live",
                scenario_key=scenario_key,
                status="failed",
                policy_ref="training:not_found",
                seed=seed,
                max_rounds=max_rounds,
                rounds_completed=0,
                winner=None,
                reward=None,
                telemetry={},
                report_text=(
                    "training policy version not found\n"
                    "Run synthetic training first, then start this scenario again.\n"
                    "live_policy_activation: false"
                ),
                metadata={
                    "source": "admin_cabinet",
                    "purpose": "live_testing_report",
                    "simulation_actor_source": "character_starting_imprints",
                    "simulation_mode": "live_tick",
                    "policy_source": "training_run",
                    "policy_found": False,
                    "completion_reason": "training_policy_not_found",
                    "live_policy_activation": False,
                },
            )

        policy, policy_metadata = _policy_from_training_row(training_row)
        return await self.start_live_starter_presets_demo(
            seed=seed,
            max_rounds=max_rounds,
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            scenario_key=scenario_key,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
            policy_ref=f"training:{training_row.id}",
            policy_metadata=policy_metadata,
        )

    async def start_live_starter_presets_demo_with_training_policy(
        self,
        *,
        policy_run_id: str,
        seed: int = 0,
        max_rounds: int = LIVE_DEFAULT_MAX_EXCHANGES,
        tick_interval_seconds: float = LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
        timeout_ticks: int = 8,
        min_team_size: int = 6,
        max_team_size: int = 6,
        scenario_key: str = "starter_presets_5v5_live",
        mirror_full_roster: bool = False,
        skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
    ) -> CombatAiSimulationRun:
        training_row = await self.repository.get(str(policy_run_id))
        if (
            training_row is None
            or training_row.run_kind != "training"
            or training_row.status != "completed"
            or not isinstance(dict(training_row.metadata_ or {}).get("best_policy"), dict)
        ):
            return await self.repository.create(
                run_kind="simulation_live",
                scenario_key=scenario_key,
                status="failed",
                policy_ref=f"training:{policy_run_id}:not_found",
                seed=seed,
                max_rounds=max_rounds,
                rounds_completed=0,
                winner=None,
                reward=None,
                telemetry={},
                report_text=(
                    "selected training policy version not found\n"
                    "Choose a completed training run with metadata.best_policy, then start this scenario again.\n"
                    "live_policy_activation: false"
                ),
                metadata={
                    "source": "admin_cabinet",
                    "purpose": "live_testing_report",
                    "simulation_actor_source": "character_starting_imprints",
                    "simulation_mode": "live_tick",
                    "policy_source": "training_run",
                    "policy_source_run_id": str(policy_run_id),
                    "policy_found": False,
                    "completion_reason": "training_policy_not_found",
                    "live_policy_activation": False,
                },
            )

        policy, policy_metadata = _policy_from_training_row(training_row)
        return await self.start_live_starter_presets_demo(
            seed=seed,
            max_rounds=max_rounds,
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            scenario_key=scenario_key,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
            policy_ref=f"training:{training_row.id}",
            policy_metadata=policy_metadata,
        )

    @staticmethod
    async def execute_live_starter_presets_demo(
        run_id: str,
        *,
        seed: int = 0,
        max_rounds: int = LIVE_DEFAULT_MAX_EXCHANGES,
        tick_interval_seconds: float = LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
        timeout_ticks: int = 8,
        min_team_size: int = 6,
        max_team_size: int = 6,
        mirror_full_roster: bool = False,
        skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
        blue_imprints: tuple[str, ...] | None = None,
        red_imprints: tuple[str, ...] | None = None,
        policy_payload: dict[str, Any] | None = None,
        policy_metadata: dict[str, Any] | None = None,
        persist: LivePersistCallback,
        progress: LiveProgressCallback | None = None,
    ) -> None:
        policy = _policy_from_payload(policy_payload)
        policy_metadata = dict(policy_metadata or {})
        actors, participants, roster_metadata = _build_starter_roster(
            seed=seed,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
            blue_imprints=blue_imprints,
            red_imprints=red_imprints,
        )
        limits = InMemoryBattleLimits(
            max_rounds=max_rounds,
            candidate_limit=5,
            max_actions_per_round=1,
            force_unanswered_exchange=False,
        )
        state = InMemoryBattleFactory.from_actors(
            actors,
            session_id=f"ai-sim-live-starter-presets-5v5-{seed}",
            limits=limits,
            seed=seed,
            battle_type="simulation_live",
            location_id="admin-ai-testing",
        )
        timing = LiveSimulationTiming(
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
        )
        simulator = LiveInMemoryCombatSimulator(
            timing=timing,
            brain=MonsterCombatBrain(policy=policy) if policy is not None else None,
        )

        async def on_step(step: LiveSimulationStepResult, _state) -> None:
            if progress is None:
                return
            telemetry = asdict(_state.telemetry)
            metadata = _live_metadata(
                state=_state,
                participants=participants,
                tick_interval_seconds=tick_interval_seconds,
                timeout_ticks=timeout_ticks,
                status="running",
                tick_index=step.tick_index,
                completion_reason="running",
                roster_metadata=roster_metadata,
                policy_metadata=policy_metadata,
            )
            report_text = render_simulation_report(
                type(
                    "_LivePartialResult",
                    (),
                    {
                        "winner": step.winner or "running",
                        "completion_reason": "running",
                        "rounds_completed": _state.ctx.meta.step_counter,
                        "telemetry": _state.telemetry,
                        "final_hp_by_actor": metadata["final_hp_by_actor"],
                    },
                )()
            )
            if progress is None:
                return
            await progress(
                {
                    "status": "running",
                    "rounds_completed": _state.ctx.meta.step_counter,
                    "winner": step.winner,
                    "reward": None,
                    "telemetry": telemetry,
                    "report_text": report_text,
                    "metadata": metadata,
                }
            )

        result = await simulator.run(state, on_step=on_step)
        telemetry = asdict(result.telemetry)
        winner_for_storage = result.winner if result.completion_reason == "victory" else None
        metadata = _live_metadata(
            state=state,
            participants=participants,
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
            status="completed",
            tick_index=result.final_tick_index,
            completion_reason=result.completion_reason,
            roster_metadata=roster_metadata,
            policy_metadata=policy_metadata,
        )
        reward = _simulation_reward(
            winner_for_storage,
            telemetry,
            participants,
            final_hp_by_actor=metadata["final_hp_by_actor"],
        )
        await persist(
            "completed",
            result.rounds_completed,
            winner_for_storage,
            reward,
            telemetry,
            render_simulation_report(result),
            metadata,
        )

    async def run_starter_presets_demo_with_latest_training_file(
        self,
        *,
        seed: int = 0,
        max_rounds: int = 8,
    ) -> CombatAiSimulationRun:
        training_row = await self.repository.latest_completed_training_with_policy()
        if training_row is None:
            return await self.repository.create(
                run_kind="simulation",
                scenario_key="starter_presets_5v5_latest_training_file",
                status="failed",
                policy_ref="training:not_found",
                seed=seed,
                max_rounds=max_rounds,
                rounds_completed=0,
                winner=None,
                reward=None,
                telemetry={},
                report_text=(
                    "training policy version not found\n"
                    "Run synthetic training first, then start this scenario again.\n"
                    "live_policy_activation: false"
                ),
                metadata={
                    "source": "admin_cabinet",
                    "purpose": "testing_report",
                    "simulation_actor_source": "character_starting_imprints",
                    "policy_source": "training_run",
                    "policy_found": False,
                    "live_policy_activation": False,
                },
            )

        policy, policy_metadata = _policy_from_training_row(training_row)
        return await self._run_starter_presets_demo(
            seed=seed,
            max_rounds=max_rounds,
            scenario_key="starter_presets_5v5_latest_training_file",
            policy_ref=f"training:{training_row.id}",
            policy=policy,
            policy_metadata=policy_metadata,
        )

    async def _run_starter_presets_demo(
        self,
        *,
        seed: int,
        max_rounds: int,
        scenario_key: str,
        policy_ref: str,
        policy: Policy | None,
        policy_metadata: dict[str, Any],
        min_team_size: int = 6,
        max_team_size: int = 6,
        mirror_full_roster: bool = False,
    ) -> CombatAiSimulationRun:
        actors, participants, roster_metadata = _build_starter_roster(
            seed=seed,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            mirror_full_roster=mirror_full_roster,
        )
        limits = InMemoryBattleLimits(max_rounds=max_rounds, candidate_limit=5, max_actions_per_round=50)
        state = InMemoryBattleFactory.from_actors(
            actors,
            session_id=f"ai-sim-starter-presets-5v5-{seed}",
            limits=limits,
            seed=seed,
            battle_type="simulation",
            location_id="admin-ai-testing",
        )
        simulator = InMemoryCombatSimulator(
            intent_provider=AiSimulationIntentProvider(brain=MonsterCombatBrain(policy=policy)) if policy else None
        )
        result = await simulator.run(state)
        telemetry = asdict(result.telemetry)
        report_text = render_simulation_report(result)
        reward = _simulation_reward(result.winner, telemetry, participants, final_hp_by_actor=result.final_hp_by_actor)
        return await self.repository.create(
            run_kind="simulation",
            scenario_key=scenario_key,
            status="completed",
            policy_ref=policy_ref,
            seed=seed,
            max_rounds=max_rounds,
            rounds_completed=result.rounds_completed,
            winner=result.winner,
            reward=reward,
            telemetry=telemetry,
            report_text=report_text,
            metadata={
                "source": "admin_cabinet",
                "purpose": "testing_report",
                "simulation_actor_source": "character_starting_imprints",
                "final_hp_by_actor": result.final_hp_by_actor,
                "participants": participants,
                **roster_metadata,
                "team_labels": {"blue": "Стартовые пресеты A", "red": "Стартовые пресеты B"},
                "live_policy_activation": False,
                **policy_metadata,
            },
        )

    async def _run_smoke_demo(self, *, seed: int = 0, max_rounds: int = 5) -> CombatAiSimulationRun:
        limits = InMemoryBattleLimits(max_rounds=max_rounds, candidate_limit=3, max_actions_per_round=20)
        state = InMemoryBattleFactory.from_actors(
            [
                _simulation_actor(
                    "player_model",
                    "blue",
                    actor_type="player",
                    hp=45,
                    damage=13.0,
                    ai_archetype="balanced",
                ),
                _simulation_actor(
                    "trainer_bot",
                    "red",
                    actor_type="monster",
                    hp=42,
                    damage=15.0,
                    ai_archetype="berserker",
                ),
            ],
            session_id=f"ai-sim-demo-{seed}",
            limits=limits,
            seed=seed,
            battle_type="simulation",
            location_id="admin-ai-testing",
        )
        result = await InMemoryCombatSimulator().run(state)
        telemetry = asdict(result.telemetry)
        report_text = render_simulation_report(result)
        participants = [
            {
                "actor_id": "player_model",
                "label": "Player model",
                "team": "blue",
                "type": "player-model",
                "ai_archetype": "balanced",
                "start_hp": 45,
            },
            {
                "actor_id": "trainer_bot",
                "label": "Trainer bot",
                "team": "red",
                "type": "monster",
                "ai_archetype": "berserker",
                "start_hp": 42,
            },
        ]
        reward = _simulation_reward(result.winner, telemetry, participants, final_hp_by_actor=result.final_hp_by_actor)
        return await self.repository.create(
            run_kind="simulation",
            scenario_key="mvp_1v1_player_model_vs_trainer_bot",
            status="completed",
            policy_ref="runtime_default",
            seed=seed,
            max_rounds=max_rounds,
            rounds_completed=result.rounds_completed,
            winner=result.winner,
            reward=reward,
            telemetry=telemetry,
            report_text=report_text,
            metadata={
                "source": "admin_cabinet",
                "purpose": "testing_report",
                "final_hp_by_actor": result.final_hp_by_actor,
                "participants": participants,
                "live_policy_activation": False,
            },
        )

    async def run_synthetic_training(
        self,
        *,
        generations: int,
        population: int,
        seed: int = 0,
        sigma: float = 0.25,
    ) -> CombatAiSimulationRun:
        result = execute_synthetic_training(
            generations=generations,
            population=population,
            seed=seed,
            sigma=sigma,
        )
        return await self.repository.create(
            run_kind="training",
            scenario_key="synthetic_policy_training",
            status="completed",
            policy_ref="candidate_not_activated",
            seed=seed,
            max_rounds=generations,
            rounds_completed=int(result["rounds_completed"]),
            winner=None,
            reward=float(result["reward"]),
            telemetry=result["telemetry"],
            report_text=str(result["report_text"]),
            metadata=result["metadata"],
        )

    async def start_synthetic_training(
        self,
        *,
        generations: int,
        population: int,
        seed: int = 0,
        sigma: float = 0.25,
    ) -> CombatAiSimulationRun:
        return await self.repository.create(
            run_kind="training",
            scenario_key="synthetic_policy_training",
            status="running",
            policy_ref="candidate_not_activated",
            seed=seed,
            max_rounds=generations,
            rounds_completed=0,
            winner=None,
            reward=None,
            telemetry={
                "generations": generations,
                "population": population,
                "seed": seed,
                "sigma": sigma,
                "metrics": [],
                "status_message": "training scheduled",
            },
            report_text=(
                "training: synthetic policy weights\n"
                f"seed: {seed}\n"
                f"generations_requested: {generations}\n"
                f"population: {population}\n"
                "status: running\n"
                "live_policy_activation: false"
            ),
            metadata=_training_metadata(best_policy_payload=None),
        )

    async def complete_synthetic_training(
        self,
        run_id: str,
        *,
        generations: int,
        population: int,
        seed: int = 0,
        sigma: float = 0.25,
    ) -> CombatAiSimulationRun | None:
        result = execute_synthetic_training(
            generations=generations,
            population=population,
            seed=seed,
            sigma=sigma,
        )
        return await self.repository.mark_completed(
            run_id,
            rounds_completed=int(result["rounds_completed"]),
            reward=float(result["reward"]),
            telemetry=result["telemetry"],
            report_text=str(result["report_text"]),
            metadata=result["metadata"],
        )

    async def start_battle_training(
        self,
        *,
        source_policy_run_id: str,
        generations: int,
        population: int,
        seed: int = 0,
        sigma: float = 0.15,
    ) -> CombatAiSimulationRun:
        source_row = await self.repository.get(source_policy_run_id)
        if source_row is None or source_row.run_kind != "training" or source_row.status != "completed":
            raise ValueError(f"Combat AI training policy run not found: {source_policy_run_id}")
        policy, policy_metadata = _policy_from_training_row(source_row)
        return await self.repository.create(
            run_kind="training",
            scenario_key="battle_policy_finetune",
            status="running",
            policy_ref=f"training:{source_policy_run_id}",
            seed=seed,
            max_rounds=generations,
            rounds_completed=0,
            winner=None,
            reward=None,
            telemetry={
                "run_kind": "battle_training",
                "generations": generations,
                "population": population,
                "seed": seed,
                "sigma": sigma,
                "source_policy_run_id": source_policy_run_id,
                "source_policy_id": policy.policy_id,
                "metrics": [],
                "status_message": "battle fine-tune scheduled",
            },
            report_text=(
                "training: battle policy fine-tune\n"
                f"source_policy_run_id: {source_policy_run_id}\n"
                f"source_policy_id: {policy.policy_id}\n"
                f"seed: {seed}\n"
                f"generations_requested: {generations}\n"
                f"population: {population}\n"
                "status: running\n"
                "live_policy_activation: false"
            ),
            metadata={
                **_training_metadata(best_policy_payload=None),
                "training_stage": "battle_finetune",
                "source_policy_run_id": source_policy_run_id,
                **policy_metadata,
            },
        )


def execute_synthetic_training(
    *,
    generations: int,
    population: int,
    seed: int = 0,
    sigma: float = 0.25,
) -> dict[str, Any]:
    args = TrainArgs(
        generations=generations,
        population=population,
        seed=seed,
        sigma=sigma,
    )
    run = train(args)
    seed_policy = Policy.with_defaults(policy_id="train_seed")
    scenarios = default_scenario_set(seed=seed)
    scenario_eval = ScoringEnvironment(scenarios).evaluate(run.best_policy)
    best_policy_payload = run.best_policy.model_dump(mode="json")
    metrics = [asdict(metric) for metric in run.metrics]
    leaderboard = [
        {"policy_id": entry.policy_id, "reward": entry.reward, "weights": entry.weights}
        for entry in run.leaderboard[:10]
    ]
    deltas = _weight_deltas(seed_policy, run.best_policy)
    final_reward = float(run.best_policy.metadata.get("final_reward") or 0.0)
    initial_reward = float(metrics[0]["best_reward"]) if metrics else None
    mean_reward = float(metrics[-1]["mean_reward"]) if metrics else None
    report_text = _render_training_report(
        generations=generations,
        population=population,
        seed=seed,
        final_reward=final_reward,
        initial_reward=initial_reward,
        mean_reward=mean_reward,
        metrics=metrics,
        deltas=deltas,
        scenario_rewards=scenario_eval.per_scenario,
    )
    return {
        "rounds_completed": len(metrics),
        "reward": final_reward,
        "telemetry": {
            "generations": generations,
            "population": population,
            "seed": seed,
            "sigma": sigma,
            "initial_best_reward": initial_reward,
            "final_best_reward": final_reward,
            "final_mean_reward": mean_reward,
            "metrics": metrics,
            "metrics_count": len(metrics),
            "leaderboard": leaderboard,
            "top_weight_deltas": deltas[:40],
            "weight_deltas_count": len(deltas),
            "scenario_rewards": scenario_eval.per_scenario,
        },
        "report_text": report_text,
        "metadata": _training_metadata(best_policy_payload=best_policy_payload),
    }


async def execute_battle_training(
    *,
    source_policy: Policy,
    source_policy_run_id: str,
    generations: int,
    population: int,
    seed: int = 0,
    sigma: float = 0.15,
    progress: LiveProgressCallback | None = None,
) -> dict[str, Any]:
    rng = random.Random(seed)
    started = time.monotonic()
    generation_count = int(max(1, generations))
    population_count = int(max(2, population))
    source_policy = Policy.with_defaults(
        weights=dict(source_policy.weights),
        policy_id=source_policy.policy_id,
        version=source_policy.version,
        metadata=dict(source_policy.metadata),
    )
    population_members = [
        source_policy,
        *[
            _mutated_policy(source_policy, rng=rng, sigma=sigma, policy_id=f"battle_seed_g0_{index}")
            for index in range(1, population_count)
        ],
    ]
    best_policy = source_policy
    best_reward = float("-inf")
    metrics: list[dict[str, Any]] = []
    leaderboard: list[dict[str, Any]] = []
    latest_scenarios: dict[str, float] = {}
    scenarios_per_policy = len(_battle_training_scenarios(seed))
    battles_done = 0
    battles_total = generation_count * population_count * scenarios_per_policy

    async def publish_progress(
        *,
        generation: int,
        candidate_index: int,
        stage: str,
        current_scenario: str = "",
        last_scenario_reward: float | None = None,
        mean_reward: float | None = None,
    ) -> None:
        if progress is None:
            return
        best_so_far = None if best_reward == float("-inf") else float(best_reward)
        telemetry = {
            "run_kind": "battle_training",
            "generations": generation_count,
            "population": population_count,
            "seed": seed,
            "sigma": sigma,
            "source_policy_run_id": source_policy_run_id,
            "source_policy_id": source_policy.policy_id,
            "current_generation": generation,
            "current_candidate_index": candidate_index,
            "current_scenario": current_scenario,
            "last_scenario_reward": last_scenario_reward,
            "battles_done": battles_done,
            "battles_total": battles_total,
            "progress_stage": stage,
            "best_reward_so_far": best_so_far,
            "final_best_reward": best_so_far,
            "final_mean_reward": mean_reward,
            "metrics": list(metrics),
            "metrics_count": len(metrics),
            "scenario_rewards": dict(latest_scenarios),
        }
        report_text = (
            "training: battle policy fine-tune\n"
            f"status: running\n"
            f"generation: {min(generation + 1, generation_count)}/{generation_count}\n"
            f"candidate: {min(candidate_index + 1, population_count)}/{population_count}\n"
            f"battles: {battles_done}/{battles_total}\n"
            f"best_reward_so_far: {best_so_far if best_so_far is not None else '—'}\n"
            f"current_scenario: {current_scenario or '—'}\n"
        )
        await progress(
            {
                "status": "running",
                "rounds_completed": len(metrics),
                "winner": None,
                "reward": best_so_far,
                "telemetry": telemetry,
                "report_text": report_text,
                "metadata": {
                    "training_stage": "battle_finetune",
                    "source_policy_run_id": source_policy_run_id,
                    "source_policy_id": source_policy.policy_id,
                    "live_policy_activation": False,
                },
            }
        )

    for generation in range(generation_count):
        scored: list[tuple[float, Policy, dict[str, float]]] = []
        for index, member in enumerate(population_members):
            await publish_progress(generation=generation, candidate_index=index, stage="evaluating_policy")

            async def on_scenario_result(
                scenario_name: str,
                scenario_reward: float,
                *,
                bound_generation: int = generation,
                bound_index: int = index,
            ) -> None:
                nonlocal battles_done
                battles_done += 1
                await publish_progress(
                    generation=bound_generation,
                    candidate_index=bound_index,
                    stage="scenario_completed",
                    current_scenario=scenario_name,
                    last_scenario_reward=scenario_reward,
                )

            reward, per_scenario = await _evaluate_policy_in_battles(
                member,
                baseline=source_policy,
                seed=seed + generation * 101 + index * 17,
                on_scenario_result=on_scenario_result,
            )
            scored.append((reward, member, per_scenario))

        scored.sort(key=lambda item: item[0], reverse=True)
        generation_best_reward, generation_best_policy, latest_scenarios = scored[0]
        mean_reward = sum(item[0] for item in scored) / len(scored)
        if generation_best_reward >= best_reward:
            best_reward = generation_best_reward
            best_policy = generation_best_policy
        metrics.append(
            {
                "generation": generation,
                "best_reward": float(best_reward),
                "mean_reward": float(mean_reward),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        )
        await publish_progress(
            generation=generation,
            candidate_index=population_count - 1,
            stage="generation_completed",
            mean_reward=float(mean_reward),
        )
        leaderboard = [
            {"policy_id": policy.policy_id, "reward": reward, "weights": dict(policy.weights)}
            for reward, policy, _per_scenario in scored[:10]
        ]
        parents = [policy for _reward, policy, _per_scenario in scored[: max(1, min(4, population_count // 4))]]
        population_members = [best_policy]
        while len(population_members) < population_count:
            parent = rng.choice(parents)
            population_members.append(
                _mutated_policy(
                    parent,
                    rng=rng,
                    sigma=sigma,
                    policy_id=f"battle_seed_g{generation + 1}_{len(population_members)}",
                )
            )

    best_policy = Policy.with_defaults(
        weights=dict(best_policy.weights),
        policy_id=str(best_policy.policy_id),
        version=int(best_policy.version),
        metadata={
            **dict(best_policy.metadata),
            "training_stage": "battle_finetune",
            "source_policy_run_id": source_policy_run_id,
            "final_reward": float(best_reward),
        },
    )
    deltas = _weight_deltas(source_policy, best_policy)
    report_text = _render_battle_training_report(
        generations=generation_count,
        population=population_count,
        seed=seed,
        source_policy_run_id=source_policy_run_id,
        source_policy_id=source_policy.policy_id,
        final_reward=float(best_reward),
        initial_reward=float(metrics[0]["best_reward"]) if metrics else None,
        mean_reward=float(metrics[-1]["mean_reward"]) if metrics else None,
        metrics=metrics,
        deltas=deltas,
        scenario_rewards=latest_scenarios,
    )
    best_policy_payload = best_policy.model_dump(mode="json")
    return {
        "rounds_completed": len(metrics),
        "reward": float(best_reward),
        "telemetry": {
            "run_kind": "battle_training",
            "generations": generation_count,
            "population": population_count,
            "seed": seed,
            "sigma": sigma,
            "source_policy_run_id": source_policy_run_id,
            "source_policy_id": source_policy.policy_id,
            "initial_best_reward": float(metrics[0]["best_reward"]) if metrics else None,
            "final_best_reward": float(best_reward),
            "final_mean_reward": float(metrics[-1]["mean_reward"]) if metrics else None,
            "metrics": metrics,
            "metrics_count": len(metrics),
            "leaderboard": leaderboard,
            "top_weight_deltas": deltas[:40],
            "weight_deltas_count": len(deltas),
            "scenario_rewards": latest_scenarios,
        },
        "report_text": report_text,
        "metadata": {
            **_training_metadata(best_policy_payload=best_policy_payload),
            "training_stage": "battle_finetune",
            "source_policy_run_id": source_policy_run_id,
            "source_policy_id": source_policy.policy_id,
        },
    }


def _mutated_policy(parent: Policy, *, rng: random.Random, sigma: float, policy_id: str) -> Policy:
    weights = {key: parent.get(key) + rng.gauss(0.0, float(sigma)) for key in DEFAULT_WEIGHT_KEYS}
    return Policy.with_defaults(
        weights=weights,
        policy_id=policy_id,
        version=int(parent.version) + 1,
        metadata=dict(parent.metadata),
    )


class _TeamPolicyBrain(MonsterCombatBrain):
    def __init__(self, *, candidate_policy: Policy, baseline_policy: Policy, candidate_team: str) -> None:
        super().__init__()
        self.candidate_team = candidate_team
        self.candidate_brain = MonsterCombatBrain(policy=candidate_policy)
        self.baseline_brain = MonsterCombatBrain(policy=baseline_policy)

    def decide_turn(self, actor: Any, ctx: Any, candidates: list[Any]) -> list[dict[str, Any]]:
        brain = self.candidate_brain if str(actor.meta.team) == self.candidate_team else self.baseline_brain
        return brain.decide_turn(actor, ctx, candidates)


@dataclass(frozen=True)
class _BattleTrainingScenarioSpec:
    name: str
    seed: int
    skill_profile: str
    candidate_team: str
    mirror_full_roster: bool = False


def _battle_training_scenarios(seed: int) -> list[_BattleTrainingScenarioSpec]:
    return [
        _BattleTrainingScenarioSpec(
            "random_5v5_baseline_blue",
            seed,
            STARTER_SKILL_PROFILE_BASELINE,
            "blue",
        ),
        _BattleTrainingScenarioSpec(
            "random_5v5_baseline_red",
            seed,
            STARTER_SKILL_PROFILE_BASELINE,
            "red",
        ),
        _BattleTrainingScenarioSpec(
            "random_5v5_full_skills_blue",
            seed + 7,
            STARTER_SKILL_PROFILE_MAXED_EXISTING,
            "blue",
        ),
        _BattleTrainingScenarioSpec(
            "random_5v5_full_skills_red",
            seed + 7,
            STARTER_SKILL_PROFILE_MAXED_EXISTING,
            "red",
        ),
        _BattleTrainingScenarioSpec(
            "random_5v5_seed31_baseline_blue",
            seed + 31,
            STARTER_SKILL_PROFILE_BASELINE,
            "blue",
        ),
        _BattleTrainingScenarioSpec(
            "random_5v5_seed31_baseline_red",
            seed + 31,
            STARTER_SKILL_PROFILE_BASELINE,
            "red",
        ),
        _BattleTrainingScenarioSpec(
            "random_5v5_seed43_full_skills_blue",
            seed + 43,
            STARTER_SKILL_PROFILE_MAXED_EXISTING,
            "blue",
        ),
        _BattleTrainingScenarioSpec(
            "random_5v5_seed43_full_skills_red",
            seed + 43,
            STARTER_SKILL_PROFILE_MAXED_EXISTING,
            "red",
        ),
        _BattleTrainingScenarioSpec(
            "mirror_10v10_baseline_blue",
            seed + 101,
            STARTER_SKILL_PROFILE_BASELINE,
            "blue",
            mirror_full_roster=True,
        ),
        _BattleTrainingScenarioSpec(
            "mirror_10v10_baseline_red",
            seed + 101,
            STARTER_SKILL_PROFILE_BASELINE,
            "red",
            mirror_full_roster=True,
        ),
        _BattleTrainingScenarioSpec(
            "mirror_10v10_full_skills_blue",
            seed + 109,
            STARTER_SKILL_PROFILE_MAXED_EXISTING,
            "blue",
            mirror_full_roster=True,
        ),
        _BattleTrainingScenarioSpec(
            "mirror_10v10_full_skills_red",
            seed + 109,
            STARTER_SKILL_PROFILE_MAXED_EXISTING,
            "red",
            mirror_full_roster=True,
        ),
    ]


async def _evaluate_policy_in_battles(
    policy: Policy,
    *,
    baseline: Policy,
    seed: int,
    on_scenario_result: Callable[[str, float], Awaitable[None]] | None = None,
) -> tuple[float, dict[str, float]]:
    rewards: dict[str, float] = {}
    for scenario in _battle_training_scenarios(seed):
        rewards[scenario.name] = await _run_policy_battle_reward(
            policy,
            baseline=baseline,
            seed=scenario.seed,
            skill_profile=scenario.skill_profile,
            candidate_team=scenario.candidate_team,
            mirror_full_roster=scenario.mirror_full_roster,
        )
        if on_scenario_result is not None:
            await on_scenario_result(scenario.name, rewards[scenario.name])
    return sum(rewards.values()), rewards


async def _run_policy_battle_reward(
    policy: Policy,
    *,
    baseline: Policy,
    seed: int,
    skill_profile: str,
    candidate_team: str,
    mirror_full_roster: bool = False,
) -> float:
    actors, participants, _metadata = _build_starter_roster(
        seed=seed,
        min_team_size=6,
        max_team_size=6,
        mirror_full_roster=mirror_full_roster,
        skill_profile=skill_profile,
    )
    state = InMemoryBattleFactory.from_actors(
        actors,
        session_id=f"ai-battle-training-{seed}-{candidate_team}",
        limits=InMemoryBattleLimits(
            max_rounds=220,
            candidate_limit=5,
            max_actions_per_round=1,
            force_unanswered_exchange=False,
        ),
        seed=seed,
        battle_type="simulation_live",
        location_id="admin-ai-battle-training",
    )
    simulator = LiveInMemoryCombatSimulator(
        timing=LiveSimulationTiming(
            tick_interval_seconds=0.0,
            max_ticks=6600,
            timeout_ticks=8,
            use_wall_clock_delay=False,
        ),
        brain=_TeamPolicyBrain(candidate_policy=policy, baseline_policy=baseline, candidate_team=candidate_team),
    )
    result = await simulator.run(state)
    return _battle_policy_reward(
        result.winner,
        asdict(result.telemetry),
        participants,
        final_hp_by_actor=result.final_hp_by_actor,
        candidate_team=candidate_team,
    )


def _battle_policy_reward(
    winner: str,
    telemetry: dict[str, Any],
    participants: list[dict[str, Any]],
    *,
    final_hp_by_actor: dict[str, int],
    candidate_team: str,
) -> float:
    team_by_actor = {str(row.get("actor_id") or ""): str(row.get("team") or "") for row in participants}
    candidate_actors = {actor_id for actor_id, team in team_by_actor.items() if team == candidate_team}
    opponent_actors = set(team_by_actor) - candidate_actors
    candidate_damage = _sum_for_actor_set(telemetry.get("damage_by_actor"), candidate_actors)
    opponent_damage = _sum_for_actor_set(telemetry.get("damage_by_actor"), opponent_actors)
    candidate_taken = _sum_for_actor_set(telemetry.get("damage_taken_by_actor"), candidate_actors)
    opponent_taken = _sum_for_actor_set(telemetry.get("damage_taken_by_actor"), opponent_actors)
    candidate_resource = _sum_for_actor_set(telemetry.get("resource_spent_by_actor"), candidate_actors)
    candidate_overkill = _sum_for_actor_set(telemetry.get("overkill_by_actor"), candidate_actors)
    candidate_failed = _sum_for_actor_set(telemetry.get("failed_by_actor"), candidate_actors)
    candidate_tactical = (
        _sum_nested_for_actor_set(telemetry.get("tactical_damage_by_actor"), candidate_actors)
        + _sum_nested_for_actor_set(telemetry.get("tactical_reflected_by_actor"), candidate_actors)
        + _sum_nested_for_actor_set(telemetry.get("tactical_prevented_by_actor"), candidate_actors) * 0.5
        + _sum_nested_for_actor_set(telemetry.get("tactical_chain_hits_by_actor"), candidate_actors) * 2.0
    )
    start_hp_by_actor = {str(row.get("actor_id") or ""): _safe_int(row.get("start_hp")) for row in participants}
    candidate_hp_ratio = _team_hp_ratio(candidate_actors, final_hp_by_actor, start_hp_by_actor)
    opponent_hp_ratio = _team_hp_ratio(opponent_actors, final_hp_by_actor, start_hp_by_actor)
    deaths = {str(actor_id) for actor_id in telemetry.get("deaths") or []}
    candidate_deaths = len(candidate_actors & deaths)
    opponent_deaths = len(opponent_actors & deaths)
    reward = 0.0
    if winner == candidate_team:
        reward += 80.0
    elif winner and winner != "draw":
        reward -= 80.0
    reward += (candidate_damage - opponent_damage) * 0.25
    reward += (opponent_taken - candidate_taken) * 0.08
    reward += (candidate_hp_ratio - opponent_hp_ratio) * 35.0
    reward += (opponent_deaths - candidate_deaths) * 12.0
    reward += candidate_tactical * 0.03
    reward -= candidate_resource * 0.04
    reward -= candidate_overkill * 0.08
    reward -= candidate_failed * 2.0
    return round(reward, 4)


def _sum_for_actor_set(values: Any, actor_ids: set[str]) -> float:
    if not isinstance(values, dict):
        return 0.0
    return sum(float(value or 0) for actor_id, value in values.items() if str(actor_id) in actor_ids)


def _sum_nested_for_actor_set(values: Any, actor_ids: set[str]) -> float:
    if not isinstance(values, dict):
        return 0.0
    total = 0.0
    for actor_id, nested in values.items():
        if str(actor_id) not in actor_ids or not isinstance(nested, dict):
            continue
        total += sum(float(value or 0) for value in nested.values())
    return total


def _team_hp_ratio(actor_ids: set[str], final_hp_by_actor: dict[str, int], start_hp_by_actor: dict[str, int]) -> float:
    max_hp = sum(max(0, int(start_hp_by_actor.get(actor_id, 0))) for actor_id in actor_ids)
    if max_hp <= 0:
        return 0.0
    final_hp = sum(max(0, int(final_hp_by_actor.get(actor_id, 0))) for actor_id in actor_ids)
    return final_hp / max_hp


def _simulation_actor(
    actor_id: str,
    team: str,
    *,
    actor_type: str,
    hp: int,
    damage: float,
    ai_archetype: str,
) -> ActorSnapshot:
    return ActorSnapshot(
        meta=ActorMetaDTO(
            id=actor_id,
            name=actor_id,
            type=actor_type,
            team=team,
            is_ai=True,
            hp=hp,
            max_hp=hp,
            stamina=100,
            max_stamina=100,
            ai_archetype=ai_archetype,
            feints=FeintHandDTO(hand={}, arsenal=[]),
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
            ),
            skills=CombatSkillsDTO(skill_swords=1.0),
        ),
    )


def _simulation_reward(
    winner: str | None,
    telemetry: dict[str, Any],
    participants: list[dict[str, Any]],
    *,
    final_hp_by_actor: dict[str, Any] | None = None,
) -> float:
    team_damage = _team_damage(telemetry, participants)
    resource_waste = sum(int(value) for value in telemetry.get("resource_spent_by_actor", {}).values())
    winner_key = str(winner or "")
    if winner_key:
        winner_damage = team_damage.get(winner_key, 0)
        opponent_damage = max((damage for team, damage in team_damage.items() if team != winner_key), default=0)
        alive_bonus = _alive_bonus(winner_key, participants, final_hp_by_actor or {})
        return float(100 + winner_damage - opponent_damage + alive_bonus - resource_waste * 0.1)
    if not team_damage:
        return float(-resource_waste * 0.1)
    damage_values = list(team_damage.values())
    damage_spread = max(damage_values) - min(damage_values) if len(damage_values) > 1 else damage_values[0]
    return float(damage_spread * 0.1 - resource_waste * 0.1)


def _alive_bonus(winner: str, participants: list[dict[str, Any]], final_hp_by_actor: dict[str, Any]) -> int:
    if not final_hp_by_actor:
        return 0
    bonus = 0
    for row in participants:
        actor_id = str(row.get("actor_id") or "")
        if not actor_id:
            continue
        hp = _safe_int(final_hp_by_actor.get(actor_id))
        if str(row.get("team") or "") == winner and hp > 0:
            bonus += 5
        elif str(row.get("team") or "") != winner and hp > 0:
            bonus -= 2
    return bonus


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _team_damage(telemetry: dict[str, Any], participants: list[dict[str, Any]]) -> dict[str, int]:
    team_by_actor = {str(row.get("actor_id") or ""): str(row.get("team") or "") for row in participants}
    raw_damage = telemetry.get("damage_by_actor")
    damage_by_actor = raw_damage if isinstance(raw_damage, dict) else {}
    totals: dict[str, int] = {}
    for actor_id, damage in damage_by_actor.items():
        team = team_by_actor.get(str(actor_id))
        if not team:
            continue
        totals[team] = totals.get(team, 0) + int(damage or 0)
    return totals


def _live_metadata(
    *,
    state,
    participants: list[dict[str, Any]],
    tick_interval_seconds: float,
    timeout_ticks: int,
    status: str,
    tick_index: int,
    completion_reason: str,
    roster_metadata: dict[str, Any] | None = None,
    policy_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source": "admin_cabinet",
        "purpose": "live_testing_report",
        "simulation_actor_source": "character_starting_imprints",
        "simulation_mode": "live_tick",
        "status": status,
        "completion_reason": completion_reason,
        "tick_index": tick_index,
        "tick_interval_seconds": tick_interval_seconds,
        "timeout_ticks": timeout_ticks,
        "participants": participants,
        **(roster_metadata or {}),
        **(policy_metadata or {}),
        "team_labels": {"blue": "Стартовые пресеты A", "red": "Стартовые пресеты B"},
        "final_hp_by_actor": {str(actor_id): actor.meta.hp for actor_id, actor in state.ctx.actors.items()},
        "live_snapshot": _live_snapshot_from_actors(list(state.ctx.actors.values()), targets=state.ctx.targets),
        "moves_cache": dict(state.ctx.moves_cache),
        "live_policy_activation": False,
    }


def _build_starter_roster(
    *,
    seed: int,
    min_team_size: int,
    max_team_size: int,
    mirror_full_roster: bool,
    skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
    blue_imprints: tuple[str, ...] | None = None,
    red_imprints: tuple[str, ...] | None = None,
) -> tuple[list[ActorSnapshot], list[dict[str, Any]], dict[str, Any]]:
    if blue_imprints and red_imprints:
        actors, participants = StartingImprintSimulationActorBuilder().build_roster(
            blue_imprints=blue_imprints,
            red_imprints=red_imprints,
            behavior_seed=seed,
            skill_profile=skill_profile,
        )
        metadata = _fixed_roster_metadata(
            seed,
            participants,
            blue_imprints=blue_imprints,
            red_imprints=red_imprints,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            mirror_full_roster=mirror_full_roster,
        )
        metadata["skill_profile"] = skill_profile
        return actors, participants, metadata
    if mirror_full_roster:
        actors, participants = StartingImprintSimulationActorBuilder().build_roster(
            blue_imprints=DEFAULT_STARTER_SIMULATION_IMPRINTS,
            red_imprints=DEFAULT_STARTER_SIMULATION_IMPRINTS,
            behavior_seed=seed,
            skill_profile=skill_profile,
        )
        metadata = _mirror_roster_metadata(seed, participants)
        metadata["skill_profile"] = skill_profile
        return actors, participants, metadata
    actors, participants = StartingImprintSimulationActorBuilder().build_roster(
        seed=seed,
        behavior_seed=seed,
        min_team_size=min_team_size,
        max_team_size=max_team_size,
        skill_profile=skill_profile,
    )
    metadata = _random_roster_metadata(
        seed,
        participants,
        min_team_size=min_team_size,
        max_team_size=max_team_size,
    )
    metadata["skill_profile"] = skill_profile
    return actors, participants, metadata


def _scheduled_roster_metadata(
    *,
    seed: int,
    min_team_size: int,
    max_team_size: int,
    mirror_full_roster: bool,
) -> dict[str, Any]:
    if mirror_full_roster:
        blue = DEFAULT_STARTER_SIMULATION_IMPRINTS
        red = DEFAULT_STARTER_SIMULATION_IMPRINTS
        mode = "mirror_full_roster"
    elif min_team_size == 6 and max_team_size == 6:
        blue, red = random_starter_6v6_imprints(seed=seed)
        mode = "seeded_random_6v6_split"
    else:
        blue, red = random_starter_roster_imprints(
            seed=seed,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
        )
        mode = "seeded_random_draft"
    used = set(blue + red)
    pool = DEFAULT_STARTER_SIMULATION_IMPRINTS
    return {
        "roster_mode": mode,
        "roster_seed": seed,
        "roster_min_team_size": min_team_size if not mirror_full_roster else len(pool),
        "roster_max_team_size": max_team_size if not mirror_full_roster else len(pool),
        "roster_team_size": len(blue),
        "imprint_pool": list(pool),
        "blue_imprints": list(blue),
        "red_imprints": list(red),
        "unused_imprints": []
        if mirror_full_roster
        else [imprint_key for imprint_key in pool if imprint_key not in used],
    }


def _mirror_roster_metadata(seed: int, participants: list[dict[str, Any]]) -> dict[str, Any]:
    pool = DEFAULT_STARTER_SIMULATION_IMPRINTS
    team_size = len(pool)
    return {
        "roster_mode": "mirror_full_roster",
        "roster_seed": seed,
        "roster_min_team_size": team_size,
        "roster_max_team_size": team_size,
        "roster_team_size": team_size,
        "imprint_pool": list(pool),
        "blue_imprints": [str(row.get("imprint_key") or "") for row in participants if row.get("team") == "blue"],
        "red_imprints": [str(row.get("imprint_key") or "") for row in participants if row.get("team") == "red"],
        "unused_imprints": [],
    }


def _random_roster_metadata(
    seed: int,
    participants: list[dict[str, Any]],
    *,
    min_team_size: int = 6,
    max_team_size: int = 6,
) -> dict[str, Any]:
    if min_team_size == 6 and max_team_size == 6:
        blue, red = random_starter_6v6_imprints(seed=seed)
        mode = "seeded_random_6v6_split"
    else:
        blue, red = random_starter_roster_imprints(
            seed=seed,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
        )
        mode = "seeded_random_draft"
    used = set(blue + red)
    pool = DEFAULT_STARTER_SIMULATION_IMPRINTS
    return {
        "roster_mode": mode,
        "roster_seed": seed,
        "roster_min_team_size": min_team_size,
        "roster_max_team_size": max_team_size,
        "roster_team_size": len(blue),
        "imprint_pool": list(pool),
        "blue_imprints": [str(row.get("imprint_key") or "") for row in participants if row.get("team") == "blue"],
        "red_imprints": [str(row.get("imprint_key") or "") for row in participants if row.get("team") == "red"],
        "unused_imprints": [imprint_key for imprint_key in pool if imprint_key not in used],
    }


def _fixed_roster_metadata(
    seed: int,
    participants: list[dict[str, Any]],
    *,
    blue_imprints: tuple[str, ...],
    red_imprints: tuple[str, ...],
    min_team_size: int,
    max_team_size: int,
    mirror_full_roster: bool,
) -> dict[str, Any]:
    if mirror_full_roster:
        mode = "mirror_full_roster"
    elif min_team_size == 6 and max_team_size == 6 and len(blue_imprints) == 6 and len(red_imprints) == 6:
        mode = "seeded_random_6v6_split"
    else:
        mode = "seeded_random_draft"
    pool = DEFAULT_STARTER_SIMULATION_IMPRINTS
    used = set(blue_imprints + red_imprints)
    return {
        "roster_mode": mode,
        "roster_seed": seed,
        "roster_min_team_size": min_team_size,
        "roster_max_team_size": max_team_size,
        "roster_team_size": len(blue_imprints),
        "imprint_pool": list(pool),
        "blue_imprints": [str(row.get("imprint_key") or "") for row in participants if row.get("team") == "blue"],
        "red_imprints": [str(row.get("imprint_key") or "") for row in participants if row.get("team") == "red"],
        "unused_imprints": [imprint_key for imprint_key in pool if imprint_key not in used],
    }


def _live_snapshot_from_actors(actors: list[ActorSnapshot], *, targets: dict[Any, list[Any]]) -> dict[str, Any]:
    return {
        "actors": [
            {
                "actor_id": str(actor.meta.id),
                "name": actor.meta.name,
                "team": actor.meta.team,
                "type": actor.meta.type,
                "ai_archetype": actor.meta.ai_archetype,
                "hp": actor.meta.hp,
                "max_hp": actor.meta.max_hp,
                "stamina": actor.meta.stamina,
                "max_stamina": actor.meta.max_stamina,
                "tokens": dict(actor.meta.tokens),
                "is_dead": actor.meta.is_dead,
                "target_queue": [str(target_id) for target_id in targets.get(actor.meta.id, [])],
                "feint_hand": dict(actor.meta.feints.hand),
            }
            for actor in actors
        ]
    }


def _policy_from_payload(payload: dict[str, Any] | None) -> Policy | None:
    if not isinstance(payload, dict):
        return None
    return Policy.model_validate(payload)


def _family_pressure_completion_payload(
    report: FamilyPressureReport,
    *,
    max_minions: int,
    max_scenarios: int,
) -> dict[str, Any]:
    rows = [asdict(row) for row in report.reports]
    trials_total = sum(int(row["trials"]) for row in rows)
    breakpoints = [row for row in rows if float(row.get("player_win_rate") or 0.0) < 0.5]
    return {
        "trials_total": trials_total,
        "telemetry": {
            "run_kind": "family_pressure",
            "family_id": report.family_id,
            "imprint_key": report.imprint_key,
            "player_gear_score": report.player_gear_score,
            "player_start_hp": report.player_start_hp,
            "trials_per_composition": report.trials_per_composition,
            "composition_count": len(rows),
            "trials_total": trials_total,
            "first_losing_composition": breakpoints[0] if breakpoints else {},
            "pressure_rows": rows,
        },
        "metadata": {
            "source": "admin_cabinet",
            "purpose": "family_pressure_balance_report",
            "simulation_mode": "family_pressure",
            "simulation_actor_source": "character_starting_imprints_and_generated_monsters",
            "family_pressure": True,
            "family_id": report.family_id,
            "imprint_key": report.imprint_key,
            "imprint_title": report.imprint_title,
            "player_gear_score": report.player_gear_score,
            "player_start_hp": report.player_start_hp,
            "trials_per_composition": report.trials_per_composition,
            "max_minions": max_minions,
            "max_scenarios": max_scenarios,
            "composition_reports": rows,
            "team_labels": {"blue": "Стартовый слепок", "red": f"Семья {report.family_id}"},
        },
    }


def _policy_from_training_row(row: Any) -> tuple[Policy, dict[str, Any]]:
    metadata = dict(getattr(row, "metadata_", None) or {})
    payload = metadata.get("best_policy")
    if not isinstance(payload, dict):
        raise ValueError(f"Training run {getattr(row, 'id', '<unknown>')} has no metadata.best_policy")
    policy = Policy.model_validate(payload)
    return policy, _policy_training_metadata(row, policy)


def _policy_training_metadata(row: Any, policy: Policy) -> dict[str, Any]:
    return {
        "policy_source": "training_run",
        "policy_found": True,
        "policy_source_run_id": str(getattr(row, "id", "")),
        "policy_training_reward": getattr(row, "reward", None),
        "policy_id": policy.policy_id,
        "policy_version": policy.version,
    }


def _training_metadata(*, best_policy_payload: dict[str, Any] | None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source": "admin_cabinet",
        "purpose": "weight_training",
        "storage": "database",
        "live_policy_activation": False,
    }
    if best_policy_payload is not None:
        metadata["best_policy"] = best_policy_payload
    return metadata


def _weight_deltas(seed_policy: Policy, trained_policy: Policy) -> list[dict[str, float | str]]:
    deltas: list[dict[str, float | str]] = []
    keys = sorted(set(seed_policy.weights) | set(trained_policy.weights))
    for key in keys:
        before = seed_policy.get(key)
        after = trained_policy.get(key)
        delta = after - before
        if abs(delta) < 0.000001:
            continue
        deltas.append({"weight": key, "before": before, "after": after, "delta": delta})
    return sorted(deltas, key=lambda item: abs(float(item["delta"])), reverse=True)


def _render_training_report(
    *,
    generations: int,
    population: int,
    seed: int,
    final_reward: float,
    initial_reward: float | None,
    mean_reward: float | None,
    metrics: list[dict[str, Any]],
    deltas: list[dict[str, float | str]],
    scenario_rewards: dict[str, float],
) -> str:
    lines = [
        "training: synthetic policy weights",
        f"seed: {seed}",
        f"generations_requested: {generations}",
        f"generations_completed: {len(metrics)}",
        f"population: {population}",
        f"initial_best_reward: {initial_reward}",
        f"final_best_reward: {final_reward}",
        f"final_mean_reward: {mean_reward}",
        "storage: database",
        "live_policy_activation: false",
        "top_weight_deltas:",
    ]
    for item in deltas[:12]:
        lines.append(
            f"  {item['weight']}: {float(item['before']):.4f} -> {float(item['after']):.4f} "
            f"delta={float(item['delta']):+.4f}"
        )
    lines.append("scenario_rewards:")
    for name, reward in sorted(scenario_rewards.items()):
        lines.append(f"  {name}: {reward:.3f}")
    return "\n".join(lines)


def _render_battle_training_report(
    *,
    generations: int,
    population: int,
    seed: int,
    source_policy_run_id: str,
    source_policy_id: str,
    final_reward: float,
    initial_reward: float | None,
    mean_reward: float | None,
    metrics: list[dict[str, Any]],
    deltas: list[dict[str, float | str]],
    scenario_rewards: dict[str, float],
) -> str:
    lines = [
        "training: battle policy fine-tune",
        f"source_policy_run_id: {source_policy_run_id}",
        f"source_policy_id: {source_policy_id}",
        f"seed: {seed}",
        f"generations_requested: {generations}",
        f"generations_completed: {len(metrics)}",
        f"population: {population}",
        f"initial_best_reward: {initial_reward}",
        f"final_best_reward: {final_reward}",
        f"final_mean_reward: {mean_reward}",
        "storage: database",
        "live_policy_activation: false",
        "battle_stage:",
        "  mode: candidate policy vs selected source policy",
        "  scenarios: random 5v5 baseline/full-skills, blue/red side swap",
        "top_weight_deltas:",
    ]
    for item in deltas[:12]:
        lines.append(
            f"  {item['weight']}: {float(item['before']):.4f} -> {float(item['after']):.4f} "
            f"delta={float(item['delta']):+.4f}"
        )
    lines.append("scenario_rewards:")
    for name, reward in sorted(scenario_rewards.items()):
        lines.append(f"  {name}: {reward:.3f}")
    return "\n".join(lines)
