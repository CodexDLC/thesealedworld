from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class SiteAnalyticsSnapshot:
    visits: int
    registrations: int
    lobby_visits: int
    game_joins: int


class SiteAnalyticsCabinetService:
    async def get_snapshot(self, request: Request) -> SiteAnalyticsSnapshot:
        counters: dict[str, int] = getattr(request.app.state, "site_analytics", {})
        return SiteAnalyticsSnapshot(
            visits=counters.get("visits", 0),
            registrations=counters.get("registrations", 0),
            lobby_visits=counters.get("lobby_visits", 0),
            game_joins=counters.get("game_joins", 0),
        )
