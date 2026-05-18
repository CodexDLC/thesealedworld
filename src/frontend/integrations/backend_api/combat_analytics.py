from src.frontend.core.api import BaseApiClient


class CombatAnalyticsApi(BaseApiClient):
    async def get_rollups(
        self,
        *,
        bucket_grain: str = "day",
        date_from: str | None = None,
        date_to: str | None = None,
        metric_key: str | None = None,
        aggregate_version: int | None = None,
    ) -> dict:
        params: dict = {"bucket_grain": bucket_grain}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if metric_key:
            params["metric_key"] = metric_key
        if aggregate_version is not None:
            params["aggregate_version"] = aggregate_version
        raw = await self._request("GET", "/api/game/combat/analytics/rollups", params=params)
        return raw if isinstance(raw, dict) else {"rows": []}

    async def get_combat_summary(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        days: int = 30,
    ) -> dict:
        params: dict = {"days": days}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        raw = await self._request("GET", "/api/game/combat/analytics/combat-summary", params=params)
        return raw if isinstance(raw, dict) else {}

    async def get_drilldown(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        raw = await self._request("GET", "/api/game/combat/analytics/drilldown", params=params)
        return raw if isinstance(raw, dict) else {"rows": [], "limit": limit, "offset": offset}
