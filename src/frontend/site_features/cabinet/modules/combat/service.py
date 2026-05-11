from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from fastapi import Request

from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.game_config import ConfigEntryDTO, GameConfigApi


@dataclass(frozen=True)
class CombatStats:
    active: int
    completed: int
    total: int
    recent: list[dict[str, object]] = field(default_factory=list)


class CombatCabinetService:
    async def get_stats(self, request: Request) -> CombatStats:
        counters: dict[str, int] = getattr(request.app.state, "site_analytics", {})
        return CombatStats(
            active=counters.get("combat_active", 0),
            completed=counters.get("combat_completed", 0),
            total=counters.get("combat_total", 0),
        )

    async def get_config(self, request: Request) -> list[ConfigEntryDTO]:
        client: httpx.AsyncClient = request.app.state.backend_http_client
        api = GameConfigApi(client=client, base_url=settings.backend_base_url)
        try:
            return await api.list_namespace("combat")
        except (httpx.HTTPStatusError, httpx.RequestError):
            return []
