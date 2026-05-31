from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger as log

from src.backend.core.database import get_session_context
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.services.ai_simulation_service import (
    STARTER_SKILL_PROFILE_BASELINE,
    CombatAiSimulationRunService,
    _policy_from_training_row,
    execute_battle_training,
    execute_synthetic_training,
)
from src.backend.infrastructure.combat.managers import CombatAiSimulationProgressManager
from src.backend.infrastructure.combat.repositories import CombatAiSimulationRunRepository
from src.shared.infrastructure.log_task_wrapper import logged_task

COMBAT_AI_LIVE_SIMULATION_TASK = "combat_ai_live_simulation_task"
COMBAT_AI_SYNTHETIC_TRAINING_TASK = "combat_ai_synthetic_training_task"
COMBAT_AI_BATTLE_TRAINING_TASK = "combat_ai_battle_training_task"
LIVE_SIMULATION_WORKER_CONCURRENCY = 3
SYNTHETIC_TRAINING_WORKER_CONCURRENCY = 1
_LIVE_SIMULATION_SEMAPHORE = asyncio.Semaphore(LIVE_SIMULATION_WORKER_CONCURRENCY)
_SYNTHETIC_TRAINING_SEMAPHORE = asyncio.Semaphore(SYNTHETIC_TRAINING_WORKER_CONCURRENCY)


@logged_task
async def combat_ai_live_simulation_task(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    run_id = str(payload["run_id"])
    progress_store = _progress_store(ctx)
    policy_payload, policy_metadata = await _policy_payload_from_training_run(payload.get("policy_source_run_id"))

    async def persist(
        status: str,
        rounds_completed: int,
        winner: str | None,
        reward: float | None,
        telemetry: dict[str, Any],
        report_text: str,
        metadata: dict[str, Any],
    ) -> None:
        async with get_session_context() as session:
            repo = CombatAiSimulationRunRepository(session)
            if status == "completed":
                await repo.mark_completed(
                    run_id,
                    rounds_completed=rounds_completed,
                    reward=reward,
                    telemetry=telemetry,
                    report_text=report_text,
                    metadata=metadata,
                    winner=winner,
                )
                if progress_store is not None:
                    await progress_store.delete_progress(run_id)
            else:
                await repo.update_running(
                    run_id,
                    rounds_completed=rounds_completed,
                    winner=winner,
                    reward=reward,
                    telemetry=telemetry,
                    report_text=report_text,
                    metadata=metadata,
                )

    try:
        async with _LIVE_SIMULATION_SEMAPHORE:
            await CombatAiSimulationRunService.execute_live_starter_presets_demo(
                run_id,
                seed=int(payload.get("seed", 0)),
                max_rounds=int(payload.get("max_rounds", 500)),
                tick_interval_seconds=float(payload.get("tick_interval_seconds", 0.05)),
                timeout_ticks=int(payload.get("timeout_ticks", 8)),
                min_team_size=int(payload.get("min_team_size", 5)),
                max_team_size=int(payload.get("max_team_size", 5)),
                mirror_full_roster=bool(payload.get("mirror_full_roster", False)),
                skill_profile=str(payload.get("skill_profile") or STARTER_SKILL_PROFILE_BASELINE),
                blue_imprints=_imprint_list(payload.get("blue_imprints")),
                red_imprints=_imprint_list(payload.get("red_imprints")),
                policy_payload=policy_payload,
                policy_metadata=policy_metadata,
                persist=persist,
                progress=None,
            )
    except asyncio.CancelledError as exc:
        log.bind(run_id=run_id).warning("CombatAiLiveSimulationWorkerCancelled")
        await asyncio.shield(
            _mark_failed(
                run_id,
                error={"type": exc.__class__.__name__, "message": "Simulation worker task was cancelled."},
            )
        )
        if progress_store is not None:
            await asyncio.shield(progress_store.delete_progress(run_id))
        raise
    except Exception as exc:
        log.bind(run_id=run_id).exception("CombatAiLiveSimulationWorkerFailed")
        await _mark_failed(run_id, error={"type": exc.__class__.__name__, "message": str(exc)})
        if progress_store is not None:
            await progress_store.delete_progress(run_id)


@logged_task
async def combat_ai_synthetic_training_task(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    run_id = str(payload["run_id"])
    try:
        async with _SYNTHETIC_TRAINING_SEMAPHORE:
            result = await asyncio.to_thread(
                execute_synthetic_training,
                generations=int(payload.get("generations", 60)),
                population=int(payload.get("population", 32)),
                seed=int(payload.get("seed", 0)),
                sigma=float(payload.get("sigma", 0.25)),
            )
        async with get_session_context() as session:
            await CombatAiSimulationRunRepository(session).mark_completed(
                run_id,
                rounds_completed=int(result["rounds_completed"]),
                reward=float(result["reward"]),
                telemetry=result["telemetry"],
                report_text=str(result["report_text"]),
                metadata=result["metadata"],
            )
    except asyncio.CancelledError as exc:
        log.bind(run_id=run_id).warning("CombatAiSyntheticTrainingWorkerCancelled")
        await asyncio.shield(
            _mark_failed(
                run_id,
                error={
                    "type": exc.__class__.__name__,
                    "message": "Synthetic training worker task was cancelled or timed out.",
                },
            )
        )
        raise
    except Exception as exc:
        log.bind(run_id=run_id).exception("CombatAiSyntheticTrainingWorkerFailed")
        await _mark_failed(run_id, error={"type": exc.__class__.__name__, "message": str(exc)})


@logged_task
async def combat_ai_battle_training_task(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    run_id = str(payload["run_id"])
    progress_store = _progress_store(ctx)
    try:
        source_run_id = str(payload["source_policy_run_id"])
        source_policy_payload, _source_metadata = await _policy_payload_from_training_run(source_run_id)
        if source_policy_payload is None:
            raise ValueError(f"Combat AI training policy run not found: {source_run_id}")

        async def progress(snapshot: dict[str, Any]) -> None:
            if progress_store is not None:
                await progress_store.set_progress(run_id, snapshot)

        async with _SYNTHETIC_TRAINING_SEMAPHORE:
            result = await execute_battle_training(
                source_policy=_policy_from_payload(source_policy_payload),
                source_policy_run_id=source_run_id,
                generations=int(payload.get("generations", 12)),
                population=int(payload.get("population", 8)),
                seed=int(payload.get("seed", 0)),
                sigma=float(payload.get("sigma", 0.15)),
                progress=progress,
            )
        async with get_session_context() as session:
            await CombatAiSimulationRunRepository(session).mark_completed(
                run_id,
                rounds_completed=int(result["rounds_completed"]),
                reward=float(result["reward"]),
                telemetry=result["telemetry"],
                report_text=str(result["report_text"]),
                metadata=result["metadata"],
            )
        if progress_store is not None:
            await progress_store.delete_progress(run_id)
    except asyncio.CancelledError as exc:
        log.bind(run_id=run_id).warning("CombatAiBattleTrainingWorkerCancelled")
        await asyncio.shield(
            _mark_failed(
                run_id,
                error={
                    "type": exc.__class__.__name__,
                    "message": "Battle training worker task was cancelled or timed out.",
                },
            )
        )
        if progress_store is not None:
            await asyncio.shield(progress_store.delete_progress(run_id))
        raise
    except Exception as exc:
        log.bind(run_id=run_id).exception("CombatAiBattleTrainingWorkerFailed")
        await _mark_failed(run_id, error={"type": exc.__class__.__name__, "message": str(exc)})


def _progress_store(ctx: dict[str, Any]) -> CombatAiSimulationProgressManager | None:
    redis_service = ctx.get("redis_service")
    if redis_service is None:
        return None
    return CombatAiSimulationProgressManager(redis_service)


async def _policy_payload_from_training_run(raw_run_id: Any) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    run_id = str(raw_run_id or "")
    if not run_id:
        return None, {}
    async with get_session_context() as session:
        row = await CombatAiSimulationRunRepository(session).get(run_id)
        if row is None or row.run_kind != "training" or row.status != "completed":
            raise ValueError(f"Combat AI training policy run not found: {run_id}")
        policy, metadata = _policy_from_training_row(row)
        return policy.model_dump(mode="json"), metadata


def _policy_from_payload(payload: dict[str, Any]) -> Policy:
    return Policy.model_validate(payload)


def _imprint_list(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    imprints = tuple(str(item) for item in value if item)
    return imprints or None


async def _mark_failed(run_id: str, *, error: dict[str, Any]) -> None:
    async with get_session_context() as session:
        await CombatAiSimulationRunRepository(session).mark_failed(run_id, error=error)
