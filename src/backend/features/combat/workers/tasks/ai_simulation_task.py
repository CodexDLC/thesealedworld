from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from loguru import logger as log

from src.backend.core.database import get_session_context
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.simulation import (
    FamilyPressureConfig,
    FamilyPressureReport,
    FamilyPressureSimulator,
    format_family_pressure_report,
)
from src.backend.features.combat.services.ai_simulation_service import (
    STARTER_SKILL_PROFILE_BASELINE,
    CombatAiSimulationRunService,
    _family_pressure_completion_payload,
    _policy_from_training_row,
    execute_battle_training,
    execute_synthetic_training,
)
from src.backend.features.monsters.repositories.monster_generation_repository import MonsterGenerationRepository
from src.backend.infrastructure.combat.managers import CombatAiSimulationProgressManager
from src.backend.infrastructure.combat.repositories import CombatAiSimulationRunRepository
from src.shared.infrastructure.log_task_wrapper import logged_task

COMBAT_AI_LIVE_SIMULATION_TASK = "combat_ai_live_simulation_task"
COMBAT_FAMILY_PRESSURE_TASK = "combat_family_pressure_task"
COMBAT_AI_SYNTHETIC_TRAINING_TASK = "combat_ai_synthetic_training_task"
COMBAT_AI_BATTLE_TRAINING_TASK = "combat_ai_battle_training_task"
LIVE_SIMULATION_WORKER_CONCURRENCY = 3
FAMILY_PRESSURE_WORKER_CONCURRENCY = 1
SYNTHETIC_TRAINING_WORKER_CONCURRENCY = 1
_LIVE_SIMULATION_SEMAPHORE = asyncio.Semaphore(LIVE_SIMULATION_WORKER_CONCURRENCY)
_FAMILY_PRESSURE_SEMAPHORE = asyncio.Semaphore(FAMILY_PRESSURE_WORKER_CONCURRENCY)
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
            log.bind(
                run_id=run_id,
                seed=int(payload.get("seed", 0)),
                max_rounds=int(payload.get("max_rounds", 500)),
            ).info("CombatAiLiveSimulationJobStarted")
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
            log.bind(run_id=run_id).info("CombatAiLiveSimulationJobFinished")
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
async def combat_family_pressure_task(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    run_id = str(payload["run_id"])
    family_id = str(payload.get("family_id") or "").strip()
    progress_store = _progress_store(ctx)
    try:
        async with _FAMILY_PRESSURE_SEMAPHORE:
            log.bind(
                run_id=run_id,
                family_id=family_id,
                seed=int(payload.get("seed", 0)),
                trials=int(payload.get("trials", 10)),
            ).info("CombatAiFamilyPressureJobStarted")
            async with get_session_context() as session:
                clans = await MonsterGenerationRepository(session).list_generated_clans_page(
                    family_id=family_id,
                    limit=100,
                )
                members = [member for clan in clans for member in clan.members]
                if not members:
                    raise ValueError(f"Generated family members not found: {family_id}")

                async def progress(report: FamilyPressureReport) -> None:
                    if progress_store is None:
                        return
                    await progress_store.set_progress(
                        run_id,
                        _family_pressure_progress_document(
                            payload,
                            report=report,
                            status="running",
                            status_message="family pressure running",
                            completion_reason="running",
                        ),
                    )

                report = await FamilyPressureSimulator().run(
                    family_id=family_id,
                    imprint_key=str(payload.get("imprint_key") or "").strip(),
                    members=members,
                    seed=int(payload.get("seed", 0)),
                    config=FamilyPressureConfig(
                        trials_per_composition=int(payload.get("trials", 10)),
                        max_rounds=int(payload.get("max_rounds", 80)),
                        max_minions=int(payload.get("max_minions", 6)),
                        max_scenarios=int(payload.get("max_scenarios", 24)),
                    ),
                    progress=progress,
                )
                if progress_store is not None:
                    await progress_store.set_progress(
                        run_id,
                        _family_pressure_progress_document(
                            payload,
                            report=report,
                            status="completed",
                            status_message="family pressure completed",
                            completion_reason="completed",
                        ),
                    )
        log.bind(run_id=run_id, family_id=family_id).info("CombatAiFamilyPressureJobFinished")
    except asyncio.CancelledError as exc:
        log.bind(run_id=run_id, family_id=family_id).warning("CombatAiFamilyPressureWorkerCancelled")
        error = {
            "type": exc.__class__.__name__,
            "message": "Family pressure worker task was cancelled or timed out.",
        }
        if progress_store is not None:
            await asyncio.shield(progress_store.set_progress(run_id, _failed_family_pressure_document(payload, error)))
        raise
    except Exception as exc:
        log.bind(run_id=run_id, family_id=family_id).exception("CombatAiFamilyPressureWorkerFailed")
        error = {"type": exc.__class__.__name__, "message": str(exc)}
        if progress_store is not None:
            await progress_store.set_progress(run_id, _failed_family_pressure_document(payload, error))


@logged_task
async def combat_ai_synthetic_training_task(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    run_id = str(payload["run_id"])
    try:
        async with _SYNTHETIC_TRAINING_SEMAPHORE:
            log.bind(
                run_id=run_id,
                generations=int(payload.get("generations", 60)),
                population=int(payload.get("population", 32)),
            ).info("CombatAiSyntheticTrainingJobStarted")
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
        log.bind(run_id=run_id).info("CombatAiSyntheticTrainingJobFinished")
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
            log.bind(
                run_id=run_id,
                source_run_id=source_run_id,
                generations=int(payload.get("generations", 12)),
                population=int(payload.get("population", 8)),
            ).info("CombatAiBattleTrainingJobStarted")
            async with get_session_context() as session:
                clans = await MonsterGenerationRepository(session).list_generated_clans_page(limit=200)
                monster_families = _battle_training_monster_families(clans)
            result = await execute_battle_training(
                source_policy=_policy_from_payload(source_policy_payload),
                source_policy_run_id=source_run_id,
                generations=int(payload.get("generations", 12)),
                population=int(payload.get("population", 8)),
                seed=int(payload.get("seed", 0)),
                sigma=float(payload.get("sigma", 0.15)),
                monster_families=monster_families,
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
        log.bind(run_id=run_id).info("CombatAiBattleTrainingJobFinished")
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


def _battle_training_monster_families(clans: list[Any]) -> dict[str, list[Any]]:
    families: dict[str, list[Any]] = {}
    for clan in clans:
        family_id = str(getattr(clan, "family_id", "") or "").strip()
        if not family_id:
            continue
        members = list(getattr(clan, "members", []) or [])
        if members:
            families.setdefault(family_id, []).extend(members)
    return families


def _family_pressure_progress_document(
    payload: dict[str, Any],
    *,
    report: FamilyPressureReport,
    status: str,
    status_message: str,
    completion_reason: str,
) -> dict[str, Any]:
    completion = _family_pressure_completion_payload(
        report,
        max_minions=int(payload.get("max_minions", 6)),
        max_scenarios=int(payload.get("max_scenarios", 24)),
    )
    telemetry = dict(completion["telemetry"])
    telemetry["status_message"] = status_message
    metadata = dict(completion["metadata"])
    metadata.update(
        {
            "storage": "redis_only",
            "completion_reason": completion_reason,
        }
    )
    if status in {"completed", "failed"}:
        metadata["completed_at"] = _utc_now_iso()
    return {
        "id": str(payload.get("run_id") or ""),
        "run_kind": "simulation",
        "scenario_key": f"family_pressure:{report.family_id}",
        "status": status,
        "policy_ref": "runtime_default",
        "seed": int(payload.get("seed", 0)),
        "max_rounds": int(payload.get("max_rounds", 80)),
        "rounds_completed": int(completion["trials_total"]),
        "winner": None,
        "reward": None,
        "created_at": str(payload.get("created_at") or ""),
        "telemetry": telemetry,
        "report_text": format_family_pressure_report(report),
        "metadata": metadata,
    }


def _failed_family_pressure_document(payload: dict[str, Any], error: dict[str, Any]) -> dict[str, Any]:
    family_id = str(payload.get("family_id") or "").strip()
    imprint_key = str(payload.get("imprint_key") or "").strip()
    finished_at = _utc_now_iso()
    return {
        "id": str(payload.get("run_id") or ""),
        "run_kind": "simulation",
        "scenario_key": f"family_pressure:{family_id}",
        "status": "failed",
        "policy_ref": "runtime_default",
        "seed": int(payload.get("seed", 0)),
        "max_rounds": int(payload.get("max_rounds", 80)),
        "rounds_completed": 0,
        "winner": None,
        "reward": None,
        "created_at": str(payload.get("created_at") or ""),
        "telemetry": {
            "run_kind": "family_pressure",
            "family_id": family_id,
            "imprint_key": imprint_key,
            "trials_per_composition": int(payload.get("trials", 10)),
            "composition_count": 0,
            "trials_total": 0,
            "status_message": "family pressure failed",
            "pressure_rows": [],
        },
        "report_text": f"family pressure failed\nfamily_id: {family_id}\nerror: {error.get('message') or ''}",
        "metadata": {
            "source": "admin_cabinet",
            "storage": "redis_only",
            "purpose": "family_pressure_balance_report",
            "simulation_mode": "family_pressure",
            "family_pressure": True,
            "family_id": family_id,
            "imprint_key": imprint_key,
            "trials_per_composition": int(payload.get("trials", 10)),
            "max_minions": int(payload.get("max_minions", 6)),
            "max_scenarios": int(payload.get("max_scenarios", 24)),
            "composition_reports": [],
            "completion_reason": "failed",
            "error": error,
            "completed_at": finished_at,
        },
    }


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


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
