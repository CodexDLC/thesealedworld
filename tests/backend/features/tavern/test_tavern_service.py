from types import SimpleNamespace

import pytest

from src.backend.features.tavern.gateway import TavernGateway
from src.backend.features.tavern.resources import get_tavern_config
from src.backend.features.tavern.services import TavernService
from src.shared.enums import CoreDomain
from src.shared.schemas.tavern import TavernActionDTO, TavernActionEnum, TavernScreenEnum


class FakeTavernIntegrator:
    def __init__(self, *, room=None) -> None:
        self.room = room
        self.entered: list[int] = []
        self.left: list[int] = []
        self.restored: list[tuple[int, str]] = []
        self.grants: list[tuple[int, str, str]] = []

    async def resolve_tavern_config(
        self,
        char_id: int,
        *,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
    ):
        _ = char_id, service_id
        return get_tavern_config(tavern_id or "last_refuge"), location_id or "52_53"

    async def enter_tavern(self, char_id: int) -> None:
        self.entered.append(char_id)

    async def leave_tavern(self, char_id: int) -> None:
        self.left.append(char_id)

    async def get_room(self, *, char_id: int, tavern_id: str):
        _ = char_id, tavern_id
        return self.room

    async def restore_vitals(self, *, char_id: int, reason: str):
        self.restored.append((char_id, reason))
        return {"hp": {"cur": 100, "max": 100}}

    async def grant_room(self, *, char_id: int, tavern_id: str, room_key: str):
        self.grants.append((char_id, tavern_id, room_key))
        if self.room is None:
            self.room = _room(room_key=room_key, tavern_id=tavern_id)
            return self.room, True
        return self.room, False


def _room(*, room_key: str = "last_refuge_private_room", tavern_id: str = "last_refuge"):
    return SimpleNamespace(id=10, tavern_id=tavern_id, room_key=room_key, status="active")


@pytest.mark.unit
async def test_tavern_view_returns_main_screen_and_enters_domain() -> None:
    integrator = FakeTavernIntegrator()
    service = TavernService(integrator=integrator)

    payload = await service.view(7, tavern_id="last_refuge")

    assert payload.tavern_id == "last_refuge"
    assert payload.screen == TavernScreenEnum.MAIN
    assert payload.location_id == "52_53"
    assert integrator.entered == [7]


@pytest.mark.unit
async def test_tavern_bartender_action_returns_scenario_transition_with_return_context() -> None:
    service = TavernService(integrator=FakeTavernIntegrator())

    transition = await service.bartender_transition(7, tavern_id="last_refuge", location_id="52_53")

    assert transition.target_state == CoreDomain.SCENARIO
    assert transition.quest_key == "tavern_bartender_dialogue"
    assert transition.location_id == "52_53"
    assert transition.metadata["tavern_id"] == "last_refuge"
    return_context = transition.context["return_context"]
    assert return_context["source_state"] == CoreDomain.TAVERN.value
    assert return_context["return_state"] == CoreDomain.TAVERN.value
    assert return_context["return_screen"] == TavernScreenEnum.BAR.value
    assert return_context["source_service_id"] == "svc_tavern_hub"


@pytest.mark.unit
async def test_tavern_rest_requires_owned_room() -> None:
    integrator = FakeTavernIntegrator(room=None)
    service = TavernService(integrator=integrator)

    payload = await service.rest(7, tavern_id="last_refuge")

    assert payload.screen == TavernScreenEnum.ROOM
    assert payload.room is not None
    assert payload.room.is_owned is False
    assert payload.notice == "Комната еще не закреплена за персонажем."
    assert integrator.restored == []


@pytest.mark.unit
async def test_tavern_rest_restores_vitals_for_owned_room() -> None:
    integrator = FakeTavernIntegrator(room=_room())
    service = TavernService(integrator=integrator)

    payload = await service.rest(7, tavern_id="last_refuge")

    assert payload.screen == TavernScreenEnum.ROOM
    assert payload.room is not None
    assert payload.room.can_rest is True
    assert payload.metadata["vitals"]["hp"]["cur"] == 100
    assert integrator.restored == [(7, "tavern:last_refuge:rest")]


@pytest.mark.unit
async def test_tavern_grant_room_is_idempotent_at_service_boundary() -> None:
    integrator = FakeTavernIntegrator(room=_room())
    service = TavernService(integrator=integrator)

    room, created = await service.grant_room(char_id=7, tavern_id="last_refuge")

    assert room.id == 10
    assert created is False
    assert integrator.grants == [(7, "last_refuge", "last_refuge_private_room")]


@pytest.mark.unit
async def test_tavern_leave_returns_exploration_transition() -> None:
    integrator = FakeTavernIntegrator()
    service = TavernService(integrator=integrator)

    transition = await service.leave(7)

    assert transition.target_state == CoreDomain.EXPLORATION
    assert transition.reason == "tavern_leave"
    assert integrator.left == [7]


@pytest.mark.unit
async def test_tavern_gateway_handles_unknown_action_safely() -> None:
    gateway = TavernGateway(tavern=TavernService(integrator=FakeTavernIntegrator()))
    body = TavernActionDTO.model_construct(action="unknown_action")

    response = await gateway.handle_tavern_action(SimpleNamespace(), 7, body)

    assert response.payload is None
    assert response.payload_type == "tavern_error"
    assert "Unknown tavern action" in response.header.error


@pytest.mark.unit
async def test_tavern_gateway_talk_bartender_returns_transition_response() -> None:
    gateway = TavernGateway(tavern=TavernService(integrator=FakeTavernIntegrator()))
    body = TavernActionDTO(action=TavernActionEnum.TALK_BARTENDER, tavern_id="last_refuge", location_id="52_53")

    response = await gateway.handle_tavern_action(SimpleNamespace(), 7, body)

    assert response.payload_type == "state_transition"
    assert response.payload.target_state == CoreDomain.SCENARIO
