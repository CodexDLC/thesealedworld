from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto.analytics_dashboard import (
    CombatAnalyticsDrilldownResponseDTO,
    CombatAnalyticsExchangeFactDTO,
    CombatAnalyticsFiltersDTO,
    CombatAnalyticsFilterValueDTO,
    CombatAnalyticsRawDebugDTO,
    CombatAnalyticsRollupPointDTO,
    CombatAnalyticsRollupResponseDTO,
)

if TYPE_CHECKING:
    from src.backend.features.combat.integrations import CombatAnalyticsDashboardIntegration

ROLLUP_DIMENSION_KEYS = (
    "weapon_base_id",
    "weapon_tier",
    "armor_class",
    "armor_tier",
    "feint_id",
    "trigger_id",
    "source_combatant_key",
    "target_combatant_key",
    "battle_type",
    "location_id",
    "source_type",
)
INT_DIMENSION_KEYS = {"weapon_tier", "armor_tier"}
VALID_BUCKET_GRAINS = {"day", "week", "month"}
DEFAULT_BUCKET_GRAIN = "day"


class CombatAnalyticsDashboardService:
    def __init__(self, integration: CombatAnalyticsDashboardIntegration) -> None:
        self.integration = integration

    async def filters(self, *, aggregate_version: int | None = None) -> CombatAnalyticsFiltersDTO:
        version = await self._aggregate_version(aggregate_version)
        if version is None:
            return CombatAnalyticsFiltersDTO()

        rows = await self.integration.rollup_filter_rows(aggregate_version=version)
        dimension_counts: dict[str, dict[Any, int]] = {key: defaultdict(int) for key in ROLLUP_DIMENSION_KEYS}
        metric_keys: set[str] = set()
        bucket_grains: set[str] = set()
        bucket_start_min: datetime | None = None
        bucket_start_max: datetime | None = None

        for row in rows:
            metric_key = row.get("metric_key")
            if metric_key:
                metric_keys.add(str(metric_key))
            bucket_grain = row.get("bucket_grain")
            if bucket_grain:
                bucket_grains.add(str(bucket_grain))
            bucket_start = row.get("bucket_start")
            if isinstance(bucket_start, datetime):
                bucket_start_min = bucket_start if bucket_start_min is None else min(bucket_start_min, bucket_start)
                bucket_start_max = bucket_start if bucket_start_max is None else max(bucket_start_max, bucket_start)

            dimensions = row.get("dimensions") if isinstance(row.get("dimensions"), dict) else {}
            source_count = int(row.get("source_count") or 0)
            for key in ROLLUP_DIMENSION_KEYS:
                value = dimensions.get(key)
                if value is not None:
                    dimension_counts[key][value] += source_count

        dimensions_response = {
            key: [
                CombatAnalyticsFilterValueDTO(value=value, source_count=count)
                for value, count in sorted(values.items(), key=lambda item: str(item[0]))
            ]
            for key, values in dimension_counts.items()
        }
        return CombatAnalyticsFiltersDTO(
            aggregate_version=version,
            dimensions=dimensions_response,
            metric_keys=sorted(metric_keys),
            bucket_grains=sorted(bucket_grains),
            bucket_start_min=bucket_start_min,
            bucket_start_max=bucket_start_max,
        )

    async def rollups(
        self,
        *,
        bucket_grain: str | None,
        date_from: str | None,
        date_to: str | None,
        metric_key: str | None,
        aggregate_version: int | None,
        dimensions: dict[str, Any],
    ) -> CombatAnalyticsRollupResponseDTO:
        grain = self._bucket_grain(bucket_grain)
        start = _parse_datetime_bound(date_from, is_end=False)
        end = _parse_datetime_bound(date_to, is_end=True)
        version = await self._aggregate_version(aggregate_version)
        filters = self._normalize_dimensions(dimensions)
        if version is None:
            return CombatAnalyticsRollupResponseDTO(
                aggregate_version=None,
                bucket_grain=grain,
                metric_key=metric_key,
                date_from=start,
                date_to=end,
                filters=filters,
            )

        rows = await self.integration.query_rollups(
            aggregate_version=version,
            bucket_grain=grain,
            start=start,
            end=end,
            metric_key=metric_key,
            dimensions=filters,
        )
        return CombatAnalyticsRollupResponseDTO(
            aggregate_version=version,
            bucket_grain=grain,
            metric_key=metric_key,
            date_from=start,
            date_to=end,
            filters=filters,
            rows=[CombatAnalyticsRollupPointDTO.model_validate(row) for row in rows],
        )

    async def drilldown(
        self,
        *,
        date_from: str | None,
        date_to: str | None,
        aggregate_version: int | None,
        dimensions: dict[str, Any],
        limit: int,
        offset: int,
        max_limit: int = 500,
    ) -> CombatAnalyticsDrilldownResponseDTO:
        start = _parse_datetime_bound(date_from, is_end=False)
        end = _parse_datetime_bound(date_to, is_end=True)
        version = await self._aggregate_version(aggregate_version)
        filters = self._normalize_dimensions(dimensions)
        normalized_limit = max(1, min(int(limit), max_limit))
        normalized_offset = max(0, int(offset))
        rows = await self.integration.query_exchange_facts(
            start=start,
            end=end,
            dimensions=filters,
            limit=normalized_limit,
            offset=normalized_offset,
        )
        return CombatAnalyticsDrilldownResponseDTO(
            aggregate_version=version,
            date_from=start,
            date_to=end,
            filters=filters,
            limit=normalized_limit,
            offset=normalized_offset,
            rows=[CombatAnalyticsExchangeFactDTO.model_validate(row) for row in rows],
        )

    async def combat_summary(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        if date_from is None and date_to is None:
            end = datetime.now(tz=UTC)
            start = end - timedelta(days=days)
        else:
            start = _parse_datetime_bound(date_from, is_end=False)
            end = _parse_datetime_bound(date_to, is_end=True)

        combats_per_day = await self.integration.query_combats_per_day(start=start, end=end)
        win_stats = await self.integration.query_win_stats(start=start, end=end)
        avg_rounds = await self.integration.query_avg_rounds(start=start, end=end)

        total_combats = sum(row["total"] for row in combats_per_day)
        pve_total = sum(row["pve_total"] for row in combats_per_day)
        pve_wins = sum(row["pve_wins"] for row in combats_per_day)
        pvp_total = sum(row["pvp_total"] for row in combats_per_day)

        pve_win_rate_pct = round(pve_wins / pve_total * 100, 1) if pve_total > 0 else 0.0

        # Group win_stats by battle_type for the table
        by_type: dict[str, dict[str, Any]] = {}
        for row in win_stats:
            bt = row.get("battle_type") or "unknown"
            key = bt
            if key not in by_type:
                by_type[key] = {"battle_type": bt, "total": 0, "team_wins": {}}
            by_type[key]["total"] += row["cnt"]
            team = row.get("winner_team") or "draw"
            by_type[key]["team_wins"][team] = by_type[key]["team_wins"].get(team, 0) + row["cnt"]

        win_stats_out = [
            {
                "battle_type": v["battle_type"],
                "total": v["total"],
                "team_wins": v["team_wins"],
            }
            for v in sorted(by_type.values(), key=lambda x: -x["total"])
        ]

        return {
            "pve_win_rate_pct": pve_win_rate_pct,
            "pve_total": pve_total,
            "pve_wins": pve_wins,
            "pvp_total": pvp_total,
            "avg_rounds": avg_rounds.get("avg", 0.0),
            "min_rounds": avg_rounds.get("min", 0),
            "max_rounds": avg_rounds.get("max", 0),
            "total_combats": total_combats,
            "combats_per_day": combats_per_day,
            "win_stats": win_stats_out,
        }

    async def raw_debug(self, combat_id: str) -> CombatAnalyticsRawDebugDTO | None:
        row = await self.integration.get_raw_analytics(combat_id)
        if row is None:
            return None
        analytics = row.get("analytics") if isinstance(row.get("analytics"), dict) else {}
        profile_entry = analytics.get("_profile") if isinstance(analytics.get("_profile"), dict) else {}
        profile = profile_entry.get("_profile") if isinstance(profile_entry.get("_profile"), dict) else profile_entry
        return CombatAnalyticsRawDebugDTO(
            combat_id=str(row.get("combat_id") or combat_id),
            analytics_schema_version=_optional_int(profile.get("analytics_schema_version")),
            combat_math_version=str(profile["combat_math_version"]) if profile.get("combat_math_version") else None,
            analytics=analytics,
        )

    async def _aggregate_version(self, requested: int | None) -> int | None:
        if requested is not None:
            return int(requested)
        return await self.integration.latest_aggregate_version()

    @staticmethod
    def _bucket_grain(value: str | None) -> str:
        grain = str(value or DEFAULT_BUCKET_GRAIN).lower()
        if grain not in VALID_BUCKET_GRAINS:
            raise ValueError(f"Unsupported bucket_grain: {grain}")
        return grain

    @staticmethod
    def _normalize_dimensions(values: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key in ROLLUP_DIMENSION_KEYS:
            value = values.get(key)
            if value in (None, ""):
                continue
            if key in INT_DIMENSION_KEYS:
                normalized[key] = int(value)
            else:
                normalized[key] = str(value)
        return normalized


def _parse_datetime_bound(value: str | None, *, is_end: bool) -> datetime | None:
    if value in (None, ""):
        return None
    raw = str(value)
    try:
        if len(raw) == 10:
            parsed_date = date.fromisoformat(raw)
            parsed = datetime.combine(parsed_date, time.min, tzinfo=UTC)
            return parsed + timedelta(days=1) if is_end else parsed
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid datetime bound: {raw}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
