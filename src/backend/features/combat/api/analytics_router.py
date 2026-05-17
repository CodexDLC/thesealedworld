from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request

from src.backend.features.combat.dependencies import CombatAnalyticsDashboardServiceDep  # noqa: TC001
from src.backend.features.combat.dto.analytics_dashboard import (
    CombatAnalyticsDrilldownResponseDTO,
    CombatAnalyticsFiltersDTO,
    CombatAnalyticsRawDebugDTO,
    CombatAnalyticsRollupResponseDTO,
)
from src.backend.features.combat.services.analytics_dashboard_service import ROLLUP_DIMENSION_KEYS

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
