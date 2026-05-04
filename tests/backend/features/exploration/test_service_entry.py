from __future__ import annotations

import pytest

from src.backend.features.exploration.services.exploration_service import ExplorationService
from src.shared.enums import CoreDomain
from src.shared.schemas.response import ServiceResult


class FakeExplorationIntegrator:
    def __init__(self, *, loc_id: str = "52_51", loc_data: dict | None = None) -> None:
        self.loc_id = loc_id
        self.loc_data = loc_data or {"services": ["svc_arena_main"], "exits": {}}

    async def get_player_location_id(self, char_id: int) -> str:
        return self.loc_id

    async def get_location_data(self, loc_id: str) -> dict:
        return self.loc_data

    async def get_players_count(self, loc_id: str, exclude_char_id: int | None = None) -> int:
        return 0

    async def get_battles(self, loc_id: str) -> dict[str, str]:
        return {}

    async def set_world_theme(self, char_id: int, world_theme: dict) -> None:
        return None


@pytest.mark.asyncio
async def test_use_service_returns_backend_owned_arena_transition():
    service = ExplorationService(FakeExplorationIntegrator(), encounter_engine=object())

    result = await service.use_service(7, "svc_arena_main")

    assert isinstance(result, ServiceResult)
    assert result.next_state == CoreDomain.ARENA
    assert result.data["service_id"] == "svc_arena_main"
    assert result.data["location_id"] == "52_51"


@pytest.mark.asyncio
async def test_use_service_denies_service_not_present_in_current_location():
    service = ExplorationService(
        FakeExplorationIntegrator(loc_data={"services": ["svc_tavern_hub"], "exits": {}}),
        encounter_engine=object(),
    )

    result = await service.use_service(7, "svc_arena_main")

    assert not isinstance(result, ServiceResult)
    assert result.hud.message == "Сервис недоступен из этой локации."
