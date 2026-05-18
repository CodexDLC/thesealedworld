from __future__ import annotations

from datetime import datetime  # noqa: TC003 - repository filters use runtime datetime values.
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.infrastructure.combat.repositories import CombatAnalyticsRepository


class CombatAnalyticsDashboardIntegration:
    def __init__(self, repository: CombatAnalyticsRepository) -> None:
        self.repository = repository

    async def latest_aggregate_version(self) -> int | None:
        return await self.repository.latest_aggregate_version()

    async def rollup_filter_rows(self, *, aggregate_version: int) -> list[dict[str, Any]]:
        return await self.repository.rollup_filter_rows(aggregate_version=aggregate_version)

    async def query_rollups(
        self,
        *,
        aggregate_version: int,
        bucket_grain: str,
        start: datetime | None,
        end: datetime | None,
        metric_key: str | None,
        dimensions: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return await self.repository.query_rollups(
            aggregate_version=aggregate_version,
            bucket_grain=bucket_grain,
            start=start,
            end=end,
            metric_key=metric_key,
            dimensions=dimensions,
        )

    async def query_exchange_facts(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
        dimensions: dict[str, Any],
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        return await self.repository.query_exchange_facts(
            start=start,
            end=end,
            dimensions=dimensions,
            limit=limit,
            offset=offset,
        )

    async def get_raw_analytics(self, combat_id: str) -> dict[str, Any] | None:
        return await self.repository.get_finalization_analytics(combat_id)

    async def query_combats_per_day(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict[str, Any]]:
        return await self.repository.query_combats_per_day(start=start, end=end)

    async def query_win_stats(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict[str, Any]]:
        return await self.repository.query_win_stats(start=start, end=end)

    async def query_avg_rounds(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> dict[str, Any]:
        return await self.repository.query_avg_rounds(start=start, end=end)
