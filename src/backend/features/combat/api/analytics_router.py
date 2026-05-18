from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.features.combat.dependencies import CombatAnalyticsDashboardServiceDep  # noqa: TC001
from src.backend.features.combat.dto.analytics_dashboard import (
    CombatAnalyticsDrilldownResponseDTO,
    CombatAnalyticsFiltersDTO,
    CombatAnalyticsRawDebugDTO,
    CombatAnalyticsRollupResponseDTO,
)
from src.backend.features.combat.runtime.analytics.ingestion import CombatAnalyticsIngestionService
from src.backend.features.combat.services.analytics_dashboard_service import ROLLUP_DIMENSION_KEYS
from src.backend.infrastructure.combat.repositories import CombatFinalizationRepository

router = APIRouter(prefix="/api/game/combat/analytics", tags=["combat-analytics"])


@router.get("/filters", response_model=CombatAnalyticsFiltersDTO)
async def get_combat_analytics_filters(
    service: CombatAnalyticsDashboardServiceDep,
    aggregate_version: Annotated[int | None, Query(ge=1)] = None,
) -> CombatAnalyticsFiltersDTO:
    return await service.filters(aggregate_version=aggregate_version)


@router.get("/rollups", response_model=CombatAnalyticsRollupResponseDTO)
async def get_combat_analytics_rollups(
    request: Request,
    service: CombatAnalyticsDashboardServiceDep,
    bucket_grain: str = "day",
    date_from: str | None = None,
    date_to: str | None = None,
    metric_key: str | None = None,
    aggregate_version: Annotated[int | None, Query(ge=1)] = None,
) -> CombatAnalyticsRollupResponseDTO:
    try:
        return await service.rollups(
            bucket_grain=bucket_grain,
            date_from=date_from,
            date_to=date_to,
            metric_key=metric_key,
            aggregate_version=aggregate_version,
            dimensions=_dimension_filters(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/drilldown", response_model=CombatAnalyticsDrilldownResponseDTO)
async def get_combat_analytics_drilldown(
    request: Request,
    service: CombatAnalyticsDashboardServiceDep,
    date_from: str | None = None,
    date_to: str | None = None,
    aggregate_version: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CombatAnalyticsDrilldownResponseDTO:
    try:
        return await service.drilldown(
            date_from=date_from,
            date_to=date_to,
            aggregate_version=aggregate_version,
            dimensions=_dimension_filters(request),
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/combat-summary")
async def get_combat_summary(
    service: CombatAnalyticsDashboardServiceDep,
    date_from: str | None = None,
    date_to: str | None = None,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> dict[str, Any]:
    return await service.combat_summary(date_from=date_from, date_to=date_to, days=days)


@router.get("/debug/raw/{combat_id}", response_model=CombatAnalyticsRawDebugDTO)
async def get_combat_analytics_raw_debug(
    combat_id: str,
    service: CombatAnalyticsDashboardServiceDep,
) -> CombatAnalyticsRawDebugDTO:
    payload = await service.raw_debug(combat_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Combat finalization analytics not found")
    return payload


def _dimension_filters(request: Request) -> dict[str, Any]:
    ignored = {"bucket_grain", "date_from", "date_to", "metric_key", "aggregate_version", "limit", "offset"}
    filters: dict[str, Any] = {}
    for key in ROLLUP_DIMENSION_KEYS:
        if key in ignored:
            continue
        value = request.query_params.get(key)
        if value not in (None, ""):
            filters[key] = value
    return filters


@router.post("/backfill")
async def backfill_combat_analytics(
    db_session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> dict[str, int]:
    rows = await CombatFinalizationRepository(db_session).get_all_for_backfill(limit=limit)
    processed = skipped = errors = 0
    for row in rows:
        analytics = row.analytics if isinstance(row.analytics, dict) else {}
        if not analytics:
            skipped += 1
            continue
        finished_at = int(row.finished_at.timestamp()) if row.finished_at else None
        finalization = {
            "combat_id": row.combat_id,
            "analytics": analytics,
            "finished_at": finished_at,
            "meta": {"battle_type": row.battle_type, "location_id": row.location_id},
        }
        try:
            await CombatAnalyticsIngestionService.ingest_finalization(db_session, finalization, aggregate_version=1)
            processed += 1
        except Exception:
            errors += 1
    return {"processed": processed, "skipped": skipped, "errors": errors}
