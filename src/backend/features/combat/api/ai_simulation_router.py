from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.arq import COMBAT_AI_SIMULATION_ARQ_QUEUE, COMBAT_ARQ_QUEUE, clear_arq_queue
from src.backend.core.database import get_db
from src.backend.features.combat.dto.ai_simulation import CombatAiSimulationRunDTO, CombatAiSimulationRunListDTO
from src.backend.features.combat.runtime.simulation import (
    STARTER_SKILL_PROFILE_BASELINE,
    STARTER_SKILL_PROFILE_MAXED_EXISTING,
)
from src.backend.features.combat.services.ai_simulation_service import (
    LIVE_DEFAULT_MAX_EXCHANGES,
    LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
    CombatAiSimulationRunService,
)
from src.backend.features.combat.workers.tasks.ai_simulation_task import (
    COMBAT_AI_BATTLE_TRAINING_TASK,
    COMBAT_AI_LIVE_SIMULATION_TASK,
    COMBAT_AI_SYNTHETIC_TRAINING_TASK,
    COMBAT_FAMILY_PRESSURE_TASK,
)
from src.backend.infrastructure.combat.managers import CombatAiSimulationProgressManager
from src.backend.infrastructure.combat.repositories import CombatAiSimulationRunRepository

if TYPE_CHECKING:
    from src.backend.infrastructure.combat.models import CombatAiSimulationRun

router = APIRouter(prefix="/api/admin/combat-ai", tags=["combat-ai-admin"])


def _service(db_session: AsyncSession) -> CombatAiSimulationRunService:
    return CombatAiSimulationRunService(CombatAiSimulationRunRepository(db_session))


@router.get("/simulation-runs", response_model=CombatAiSimulationRunListDTO)
async def list_simulation_runs(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    run_kind: str | None = None,
) -> CombatAiSimulationRunListDTO:
    rows = await _service(db_session).list_recent(limit=limit, run_kind=run_kind)
    progress_store = _progress_store_from_request(request)
    progress_by_run = await _progress_for_rows(progress_store, rows)
    return CombatAiSimulationRunListDTO(runs=[_view(row, progress_by_run.get(row.id)) for row in rows])


@router.post("/simulation-runs/clear")
async def clear_simulation_runs(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    deleted = await _service(db_session).clear_reports()
    runtime_deleted = await _clear_combat_ai_simulation_runtime_state(request)
    await db_session.commit()
    return {"deleted": deleted, **runtime_deleted}


@router.post("/simulation-runs/clear-training")
async def clear_training_runs(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    deleted = await _service(db_session).clear_training_runs()
    runtime_deleted = await _clear_combat_ai_simulation_runtime_state(request)
    await db_session.commit()
    return {"deleted": deleted, **runtime_deleted}


@router.post("/simulation-runs/cleanup-stale")
async def cleanup_stale_simulation_runs(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    older_than_minutes: Annotated[int | None, Query(ge=1, le=24 * 60)] = None,
) -> dict[str, int]:
    if older_than_minutes is None:
        game_config = getattr(request.app.state, "game_config", None)
        if game_config:
            older_than_minutes = await game_config.get_int("combat_ai", "STALE_RUNNING_REPORT_MINUTES", default=20)
        else:
            older_than_minutes = 20
    updated = await _service(db_session).cleanup_stale_running_reports(older_than_minutes=older_than_minutes)
    await db_session.commit()
    return {"updated": updated}


@router.get("/simulation-runs/{run_id}", response_model=CombatAiSimulationRunDTO)
async def get_simulation_run(
    run_id: str,
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> CombatAiSimulationRunDTO:
    row = await _service(db_session).get(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Combat AI simulation run not found")
    progress_store = _progress_store_from_request(request)
    progress = (
        await progress_store.get_progress(run_id) if progress_store is not None and row.status == "running" else None
    )
    return _view(row, progress)


@router.post("/simulation-runs/demo", response_model=CombatAiSimulationRunDTO)
async def run_demo_simulation(
    db_session: Annotated[AsyncSession, Depends(get_db)],
    seed: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    max_rounds: Annotated[int, Query(ge=1, le=50)] = 5,
    scenario_key: str = "starter_presets_5v5",
) -> CombatAiSimulationRunDTO:
    row = await _service(db_session).run_demo(seed=seed, max_rounds=max_rounds, scenario_key=scenario_key)
    await db_session.commit()
    return _view(row)


@router.post("/simulation-runs/family-pressure", response_model=CombatAiSimulationRunDTO)
async def run_family_pressure_simulation(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    family_id: Annotated[str, Query(min_length=1, max_length=80)] = "rat_swarm",
    imprint_key: Annotated[str, Query(max_length=120)] = "",
    seed: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    trials: Annotated[int, Query(ge=1, le=100)] = 30,
    max_rounds: Annotated[int, Query(ge=1, le=200)] = 80,
    max_minions: Annotated[int, Query(ge=1, le=10)] = 6,
    max_scenarios: Annotated[int, Query(ge=1, le=50)] = 12,
) -> CombatAiSimulationRunDTO:
    row = await _service(db_session).start_family_pressure_probe(
        family_id=family_id,
        imprint_key=imprint_key,
        seed=seed,
        trials=trials,
        max_rounds=max_rounds,
        max_minions=max_minions,
        max_scenarios=max_scenarios,
    )
    await db_session.commit()
    try:
        await _enqueue_family_pressure_job(
            getattr(request.app.state, "combat_arq", None),
            _family_pressure_payload(row),
        )
    except Exception as exc:
        failed = await CombatAiSimulationRunRepository(db_session).mark_failed(
            row.id,
            error={"type": exc.__class__.__name__, "message": str(exc)},
        )
        await db_session.commit()
        return _view(failed or row)
    return _view(row)


@router.post("/simulation-runs/live-demo", response_model=CombatAiSimulationRunDTO)
async def run_live_demo_simulation(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    seed: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    max_rounds: Annotated[int, Query(ge=1, le=2000)] = LIVE_DEFAULT_MAX_EXCHANGES,
    tick_interval_seconds: Annotated[float, Query(ge=0.0, le=5.0)] = LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
    timeout_ticks: Annotated[int, Query(ge=1, le=100)] = 8,
    min_team_size: Annotated[int, Query(ge=1, le=6)] = 6,
    max_team_size: Annotated[int, Query(ge=1, le=6)] = 6,
    scenario_key: str = "starter_presets_5v5_live",
    policy_run_id: str = "",
) -> CombatAiSimulationRunDTO:
    if min_team_size > max_team_size:
        raise HTTPException(status_code=400, detail="min_team_size must be <= max_team_size")
    service = _service(db_session)
    row = await _start_live_demo_row(
        service,
        seed=seed,
        max_rounds=max_rounds,
        tick_interval_seconds=tick_interval_seconds,
        timeout_ticks=timeout_ticks,
        min_team_size=min_team_size,
        max_team_size=max_team_size,
        scenario_key=scenario_key,
        policy_run_id=policy_run_id,
    )
    await db_session.commit()
    if row.status != "running":
        return _view(row)
    try:
        await _enqueue_live_demo_job(
            getattr(request.app.state, "combat_ai_simulation_arq", None),
            _live_demo_payload(row, seed=seed),
        )
    except Exception as exc:
        failed = await CombatAiSimulationRunRepository(db_session).mark_failed(
            row.id,
            error={"type": exc.__class__.__name__, "message": str(exc)},
        )
        await db_session.commit()
        return _view(failed or row)
    return _view(row)


@router.post("/simulation-runs/live-demo-batch", response_model=CombatAiSimulationRunListDTO)
async def run_live_demo_simulation_batch(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    count: Annotated[int, Query(ge=1, le=100)] = 10,
    seed: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    max_rounds: Annotated[int, Query(ge=1, le=2000)] = LIVE_DEFAULT_MAX_EXCHANGES,
    tick_interval_seconds: Annotated[float, Query(ge=0.0, le=5.0)] = LIVE_DEFAULT_TICK_INTERVAL_SECONDS,
    timeout_ticks: Annotated[int, Query(ge=1, le=100)] = 8,
    min_team_size: Annotated[int, Query(ge=1, le=6)] = 6,
    max_team_size: Annotated[int, Query(ge=1, le=6)] = 6,
    scenario_key: str = "starter_presets_5v5_live",
    policy_run_id: str = "",
) -> CombatAiSimulationRunListDTO:
    if min_team_size > max_team_size:
        raise HTTPException(status_code=400, detail="min_team_size must be <= max_team_size")
    service = _service(db_session)
    rows: list[CombatAiSimulationRun] = []
    for index in range(int(count)):
        run_seed = (int(seed) + index) % 1_000_000
        rows.append(
            await _schedule_live_demo_row(
                service,
                seed=run_seed,
                max_rounds=max_rounds,
                tick_interval_seconds=tick_interval_seconds,
                timeout_ticks=timeout_ticks,
                min_team_size=min_team_size,
                max_team_size=max_team_size,
                scenario_key=scenario_key,
                policy_run_id=policy_run_id,
            )
        )
    await db_session.commit()
    running_rows = [row for row in rows if row.status == "running"]
    try:
        arq = getattr(request.app.state, "combat_ai_simulation_arq", None)
        await asyncio.gather(
            *[_enqueue_live_demo_job(arq, _live_demo_payload(row, seed=row.seed)) for row in running_rows]
        )
    except Exception as exc:
        repository = CombatAiSimulationRunRepository(db_session)
        for row in running_rows:
            await repository.mark_failed(row.id, error={"type": exc.__class__.__name__, "message": str(exc)})
        await db_session.commit()
    return CombatAiSimulationRunListDTO(runs=[_view(row) for row in rows])


@router.post("/simulation-runs/train-synthetic", response_model=CombatAiSimulationRunDTO)
async def run_synthetic_training(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    generations: Annotated[int, Query(ge=1, le=500)] = 60,
    population: Annotated[int, Query(ge=2, le=64)] = 32,
    seed: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    sigma: Annotated[float, Query(gt=0.0, le=2.0)] = 0.25,
) -> CombatAiSimulationRunDTO:
    row = await _service(db_session).start_synthetic_training(
        generations=generations,
        population=population,
        seed=seed,
        sigma=sigma,
    )
    await db_session.commit()
    try:
        await _enqueue_synthetic_training_job(
            getattr(request.app.state, "combat_ai_simulation_arq", None),
            {
                "run_id": row.id,
                "generations": generations,
                "population": population,
                "seed": seed,
                "sigma": sigma,
            },
        )
    except Exception as exc:
        failed = await CombatAiSimulationRunRepository(db_session).mark_failed(
            row.id,
            error={"type": exc.__class__.__name__, "message": str(exc)},
        )
        await db_session.commit()
        return _view(failed or row)
    return _view(row)


@router.post("/simulation-runs/train-battle", response_model=CombatAiSimulationRunDTO)
async def run_battle_training(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    source_policy_run_id: Annotated[str, Query(min_length=1)],
    generations: Annotated[int, Query(ge=1, le=40)] = 12,
    population: Annotated[int, Query(ge=2, le=16)] = 8,
    seed: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    sigma: Annotated[float, Query(gt=0.0, le=1.0)] = 0.15,
) -> CombatAiSimulationRunDTO:
    try:
        row = await _service(db_session).start_battle_training(
            source_policy_run_id=source_policy_run_id,
            generations=generations,
            population=population,
            seed=seed,
            sigma=sigma,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db_session.commit()
    try:
        await _enqueue_battle_training_job(
            getattr(request.app.state, "combat_ai_simulation_arq", None),
            {
                "run_id": row.id,
                "source_policy_run_id": source_policy_run_id,
                "generations": generations,
                "population": population,
                "seed": seed,
                "sigma": sigma,
            },
        )
    except Exception as exc:
        failed = await CombatAiSimulationRunRepository(db_session).mark_failed(
            row.id,
            error={"type": exc.__class__.__name__, "message": str(exc)},
        )
        await db_session.commit()
        return _view(failed or row)
    return _view(row)


async def _start_live_demo_row(
    service: CombatAiSimulationRunService,
    *,
    seed: int,
    max_rounds: int,
    tick_interval_seconds: float,
    timeout_ticks: int,
    min_team_size: int,
    max_team_size: int,
    scenario_key: str,
    policy_run_id: str = "",
) -> CombatAiSimulationRun:
    mirror_full_roster = scenario_key.startswith("starter_presets_mirror_10v10_live")
    skill_profile = _live_skill_profile_from_scenario(scenario_key)
    if policy_run_id:
        return await service.start_live_starter_presets_demo_with_training_policy(
            policy_run_id=policy_run_id,
            seed=seed,
            max_rounds=max_rounds,
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            scenario_key=scenario_key,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
        )
    if scenario_key.endswith("_latest_training_file"):
        return await service.start_live_starter_presets_demo_with_latest_training_file(
            seed=seed,
            max_rounds=max_rounds,
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            scenario_key=scenario_key,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
        )
    return await service.start_live_starter_presets_demo(
        seed=seed,
        max_rounds=max_rounds,
        tick_interval_seconds=tick_interval_seconds,
        timeout_ticks=timeout_ticks,
        min_team_size=min_team_size,
        max_team_size=max_team_size,
        scenario_key=scenario_key,
        mirror_full_roster=mirror_full_roster,
        skill_profile=skill_profile,
    )


async def _schedule_live_demo_row(
    service: CombatAiSimulationRunService,
    *,
    seed: int,
    max_rounds: int,
    tick_interval_seconds: float,
    timeout_ticks: int,
    min_team_size: int,
    max_team_size: int,
    scenario_key: str,
    policy_run_id: str = "",
) -> CombatAiSimulationRun:
    mirror_full_roster = scenario_key.startswith("starter_presets_mirror_10v10_live")
    skill_profile = _live_skill_profile_from_scenario(scenario_key)
    if policy_run_id:
        return await service.schedule_live_starter_presets_demo_with_training_policy(
            policy_run_id=policy_run_id,
            seed=seed,
            max_rounds=max_rounds,
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            scenario_key=scenario_key,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
        )
    if scenario_key.endswith("_latest_training_file"):
        return await service.schedule_live_starter_presets_demo_with_latest_training_file(
            seed=seed,
            max_rounds=max_rounds,
            tick_interval_seconds=tick_interval_seconds,
            timeout_ticks=timeout_ticks,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            scenario_key=scenario_key,
            mirror_full_roster=mirror_full_roster,
            skill_profile=skill_profile,
        )
    return await service.schedule_live_starter_presets_demo(
        seed=seed,
        max_rounds=max_rounds,
        tick_interval_seconds=tick_interval_seconds,
        timeout_ticks=timeout_ticks,
        min_team_size=min_team_size,
        max_team_size=max_team_size,
        scenario_key=scenario_key,
        mirror_full_roster=mirror_full_roster,
        skill_profile=skill_profile,
    )


def _live_demo_payload(row: CombatAiSimulationRun, *, seed: int) -> dict[str, Any]:
    metadata = dict(row.metadata_ or {})
    return {
        "run_id": row.id,
        "seed": seed,
        "max_rounds": row.max_rounds,
        "tick_interval_seconds": float(metadata.get("tick_interval_seconds") or LIVE_DEFAULT_TICK_INTERVAL_SECONDS),
        "timeout_ticks": int(metadata.get("timeout_ticks") or 8),
        "min_team_size": int(metadata.get("roster_min_team_size") or 6),
        "max_team_size": int(metadata.get("roster_max_team_size") or 6),
        "mirror_full_roster": str(metadata.get("roster_mode") or "") in {"mirror_10v10", "mirror_full_roster"},
        "skill_profile": str(metadata.get("skill_profile") or STARTER_SKILL_PROFILE_BASELINE),
        "blue_imprints": list(metadata.get("blue_imprints") or []),
        "red_imprints": list(metadata.get("red_imprints") or []),
        "policy_source_run_id": str(metadata.get("policy_source_run_id") or ""),
    }


def _family_pressure_payload(row: CombatAiSimulationRun) -> dict[str, Any]:
    metadata = dict(row.metadata_ or {})
    return {
        "run_id": row.id,
        "family_id": str(metadata.get("family_id") or "").strip(),
        "imprint_key": str(metadata.get("imprint_key") or "").strip(),
        "seed": int(row.seed),
        "trials": int(metadata.get("trials_per_composition") or 30),
        "max_rounds": int(row.max_rounds),
        "max_minions": int(metadata.get("max_minions") or 6),
        "max_scenarios": int(metadata.get("max_scenarios") or 12),
    }


async def _enqueue_live_demo_job(arq: Any | None, payload: dict[str, Any]) -> None:
    if arq is None:
        raise RuntimeError("Combat AI simulation ARQ service is not available")
    await arq.enqueue_job(COMBAT_AI_LIVE_SIMULATION_TASK, payload)


async def _enqueue_family_pressure_job(arq: Any | None, payload: dict[str, Any]) -> None:
    if arq is None:
        raise RuntimeError("Combat ARQ service is not available")
    await arq.enqueue_job(COMBAT_FAMILY_PRESSURE_TASK, payload)


def _live_skill_profile_from_scenario(scenario_key: str) -> str:
    if scenario_key.endswith("_full_skills"):
        return STARTER_SKILL_PROFILE_MAXED_EXISTING
    return STARTER_SKILL_PROFILE_BASELINE


async def _enqueue_synthetic_training_job(arq: Any | None, payload: dict[str, Any]) -> None:
    if arq is None:
        raise RuntimeError("Combat AI simulation ARQ service is not available")
    await arq.enqueue_job(COMBAT_AI_SYNTHETIC_TRAINING_TASK, payload)


async def _enqueue_battle_training_job(arq: Any | None, payload: dict[str, Any]) -> None:
    if arq is None:
        raise RuntimeError("Combat AI simulation ARQ service is not available")
    await arq.enqueue_job(COMBAT_AI_BATTLE_TRAINING_TASK, payload)


def _view(row: CombatAiSimulationRun, progress: dict[str, Any] | None = None) -> CombatAiSimulationRunDTO:
    progress = progress if isinstance(progress, dict) else None
    status = progress.get("status") if progress else row.status
    rounds_completed = progress.get("rounds_completed") if progress else row.rounds_completed
    telemetry = progress.get("telemetry") if progress else row.telemetry
    metadata = progress.get("metadata") if progress else row.metadata_
    report_text = progress.get("report_text") if progress else row.report_text
    return CombatAiSimulationRunDTO(
        id=row.id,
        run_kind=row.run_kind,
        scenario_key=row.scenario_key,
        status=str(status or row.status),
        policy_ref=row.policy_ref,
        seed=row.seed,
        max_rounds=row.max_rounds,
        rounds_completed=int(rounds_completed or 0),
        winner=progress.get("winner") if progress else row.winner,
        reward=progress.get("reward") if progress else row.reward,
        telemetry=dict(telemetry if isinstance(telemetry, dict) else {}),
        report_text=str(report_text or ""),
        metadata=dict(metadata if isinstance(metadata, dict) else {}),
        created_at=row.created_at,
    )


def _progress_store_from_request(request: Request) -> CombatAiSimulationProgressManager | None:
    redis_service = getattr(request.app.state, "redis", None)
    if redis_service is None:
        return None
    return CombatAiSimulationProgressManager(redis_service)


async def _clear_combat_ai_simulation_runtime_state(request: Request) -> dict[str, int]:
    redis_client = getattr(request.app.state, "redis_client", None)
    ai_queue_deleted = await clear_arq_queue(redis_client, COMBAT_AI_SIMULATION_ARQ_QUEUE)
    combat_queue_deleted = await clear_arq_queue(redis_client, COMBAT_ARQ_QUEUE)
    progress_store = _progress_store_from_request(request)
    progress_deleted = await progress_store.clear_all_progress() if progress_store is not None else 0
    return {
        "queued_deleted": ai_queue_deleted + combat_queue_deleted,
        "ai_queue_deleted": ai_queue_deleted,
        "combat_queue_deleted": combat_queue_deleted,
        "progress_deleted": progress_deleted,
    }


async def _progress_for_rows(
    progress_store: CombatAiSimulationProgressManager | None,
    rows: list[CombatAiSimulationRun],
) -> dict[str, dict[str, Any]]:
    if progress_store is None:
        return {}
    progress_by_run: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.status != "running":
            continue
        progress = await progress_store.get_progress(row.id)
        if progress is not None:
            progress_by_run[row.id] = progress
    return progress_by_run
