from __future__ import annotations

import pytest

from src.backend.features.exploration.services.exploration_service import ExplorationService
from src.shared.enums import CoreDomain
from src.shared.schemas.exploration import EncounterDTO, EncounterType
from src.shared.schemas.response import ServiceResult


class FakeExplorationIntegrator:
    def __init__(self, *, loc_id: str = "51_51", loc_data: dict | None = None) -> None:
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

    async def get_actor_skills(self, char_id: int) -> dict[str, float]:
        return {"skill_scouting": 0.0, "skill_pathfinder": 0.0, "skill_hunting": 0.0}

    async def set_world_theme(self, char_id: int, world_theme: dict) -> None:
        return None


class FakeEncounterIntegration:
    def __init__(self, *, encounter: EncounterDTO | None = None) -> None:
        self.encounter = encounter
        self.attached: tuple[int, str] | None = None
        self.cleared: list[str] = []
        self.detached: list[int] = []
        self.created: dict | None = None
        self.patched: list[tuple[str, dict]] = []

    async def get_active_encounter_id(self, char_id: int) -> str | None:
        return self.encounter.id if self.encounter is not None else None

    async def get_encounter_session(self, encounter_id: str) -> dict | None:
        if self.encounter is None:
            return None
        return {"encounter_id": encounter_id, "payload": self.encounter.model_dump(mode="json")}

    async def create_encounter_session(self, encounter_id: str, payload: dict) -> dict:
        self.created = {"encounter_id": encounter_id, **payload}
        return self.created

    async def patch_encounter_session(self, encounter_id: str, updates: dict) -> None:
        self.patched.append((encounter_id, updates))

    async def attach_encounter_session(self, char_id: int, encounter_id: str) -> None:
        self.attached = (char_id, encounter_id)

    async def clear_encounter_session(self, encounter_id: str) -> None:
        self.cleared.append(encounter_id)

    async def detach_encounter_session(self, char_id: int) -> None:
        self.detached.append(char_id)


def _encounter() -> EncounterDTO:
    return EncounterDTO(
        id="enc-1",
        type=EncounterType.COMBAT,
        title="Threat",
        description="Something waits.",
        options=[],
    )


@pytest.mark.asyncio
async def test_use_service_returns_backend_owned_arena_transition():
    service = ExplorationService(FakeExplorationIntegrator(), encounter_engine=object())

    result = await service.use_service(7, "svc_arena_main")

    assert isinstance(result, ServiceResult)
    assert result.next_state == CoreDomain.ARENA
    assert result.data["service_id"] == "svc_arena_main"
    assert result.data["location_id"] == "51_51"


@pytest.mark.asyncio
async def test_use_service_returns_backend_owned_city_services_transition():
    service = ExplorationService(
        FakeExplorationIntegrator(
            loc_id="53_53",
            loc_data={"services": ["svc_tavern_hub"], "exits": {}},
        ),
        encounter_engine=object(),
    )

    result = await service.use_service(7, "svc_tavern_hub")

    assert isinstance(result, ServiceResult)
    assert result.next_state == CoreDomain.CITY_SERVICES
    assert result.data["service_id"] == "svc_tavern_hub"
    assert result.data["location_id"] == "53_53"
    assert result.data["service_type"] == "tavern"
    assert result.data["tavern_id"] == "last_refuge"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service_id", "service_type"),
    [
        ("svc_portal_hub", "portal"),
        ("svc_town_hall_hub", "town_hall"),
        ("svc_blacksmith_repair", "workshop.blacksmith"),
        ("svc_market_hub", "market"),
    ],
)
async def test_use_service_routes_start_city_placeholders_to_city_services(service_id: str, service_type: str):
    service = ExplorationService(
        FakeExplorationIntegrator(
            loc_id="52_52",
            loc_data={"services": [service_id], "exits": {}},
        ),
        encounter_engine=object(),
    )

    result = await service.use_service(7, service_id)

    assert isinstance(result, ServiceResult)
    assert result.next_state == CoreDomain.CITY_SERVICES
    assert result.data["service_id"] == service_id
    assert result.data["service_type"] == service_type


@pytest.mark.asyncio
async def test_use_service_denies_service_not_present_in_current_location():
    service = ExplorationService(
        FakeExplorationIntegrator(loc_data={"services": ["svc_tavern_hub"], "exits": {}}),
        encounter_engine=object(),
    )

    result = await service.use_service(7, "svc_arena_main")

    assert not isinstance(result, ServiceResult)
    assert result.hud.message == "Сервис недоступен из этой локации."


@pytest.mark.asyncio
async def test_active_encounter_gates_exploration_actions():
    encounter = _encounter()
    service = ExplorationService(
        FakeExplorationIntegrator(),
        encounter_engine=object(),
        encounter_integration=FakeEncounterIntegration(encounter=encounter),
    )

    move_result = await service.move(7, target_id="52_52")
    search_result = await service.interact(7, "search")
    service_result = await service.use_service(7, "svc_arena_main")

    assert isinstance(move_result, EncounterDTO)
    assert isinstance(search_result, EncounterDTO)
    assert isinstance(service_result, EncounterDTO)
    assert move_result.id == encounter.id
    assert search_result.id == encounter.id
    assert service_result.id == encounter.id
    assert move_result.metadata["navigation"]["loc_id"] == "52_51"


@pytest.mark.asyncio
async def test_bypass_clears_active_encounter_and_returns_navigation_notice(monkeypatch):
    monkeypatch.setattr(
        "src.backend.features.exploration.services.exploration_service.random.random",
        lambda: 0.0,
    )
    encounter_integration = FakeEncounterIntegration(encounter=_encounter())
    service = ExplorationService(
        FakeExplorationIntegrator(),
        encounter_engine=object(),
        encounter_integration=encounter_integration,
    )

    result = await service.interact(7, "bypass")

    assert not isinstance(result, ServiceResult)
    assert result.hud.message == "Опасность миновала. Вы решили обойти угрозу."
    assert encounter_integration.cleared == ["enc-1"]
    assert encounter_integration.detached == [7]


@pytest.mark.asyncio
async def test_failed_bypass_routes_to_combat_with_roll_result(monkeypatch):
    monkeypatch.setattr(
        "src.backend.features.exploration.services.exploration_service.random.random",
        lambda: 0.99,
    )
    encounter_integration = FakeEncounterIntegration(encounter=_encounter())
    service = ExplorationService(
        FakeExplorationIntegrator(),
        encounter_engine=object(),
        encounter_integration=encounter_integration,
    )

    result = await service.interact(7, "bypass")

    assert isinstance(result, ServiceResult)
    assert result.next_state == CoreDomain.COMBAT
    assert result.data["status"] == "bypass_failed_entering_combat"
    assert result.data["encounter_id"] == "enc-1"
    assert result.data["bypass_result"]["success"] is False
    assert encounter_integration.cleared == []
    assert encounter_integration.detached == []
    assert encounter_integration.patched
