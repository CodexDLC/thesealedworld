from types import SimpleNamespace

import pytest

from src.backend.features.city_services.gateway import CityServiceGateway
from src.backend.features.city_services.resources import get_city_service_definition
from src.backend.features.city_services.services import CityService
from src.shared.enums import CoreDomain
from src.shared.schemas.city_services import CityServiceActionDTO, CityServiceActionEnum, CityServiceScreenEnum


class FakeCityServiceIntegrator:
    def __init__(self, *, room=None) -> None:
        self.room = room
        self.entered: list[int] = []
        self.left: list[int] = []
        self.restored: list[tuple[int, str]] = []
        self.grants: list[tuple[int, str, str]] = []

    async def resolve_service_definition(
        self,
        char_id: int,
        *,
        service_id: str | None = None,
        location_id: str | None = None,
        tavern_id: str | None = None,
    ):
        _ = char_id, tavern_id
        return get_city_service_definition(service_id or "svc_tavern_hub"), location_id or "53_53"

    async def enter_city_service(self, char_id: int) -> None:
        self.entered.append(char_id)

    async def leave_city_service(self, char_id: int) -> None:
        self.left.append(char_id)

    async def get_tavern_room(self, *, char_id: int, tavern_id: str):
        _ = char_id, tavern_id
        return self.room

    async def restore_vitals(self, *, char_id: int, reason: str):
        self.restored.append((char_id, reason))
        return {"hp": {"cur": 100, "max": 100}}

    async def grant_tavern_room(self, *, char_id: int, tavern_id: str, room_key: str):
        self.grants.append((char_id, tavern_id, room_key))
        if self.room is None:
            self.room = _room(room_key=room_key, tavern_id=tavern_id)
            return self.room, True
        return self.room, False


def _room(*, room_key: str = "last_refuge_private_room", tavern_id: str = "last_refuge"):
    return SimpleNamespace(id=10, tavern_id=tavern_id, room_key=room_key, status="active")


@pytest.mark.unit
async def test_city_service_view_returns_tavern_main_screen_and_enters_domain() -> None:
    integrator = FakeCityServiceIntegrator()
    service = CityService(integrator=integrator)

    payload = await service.view(7, service_id="svc_tavern_hub")

    assert payload.service_id == "svc_tavern_hub"
    assert payload.service_type == "tavern"
    assert payload.screen == CityServiceScreenEnum.MAIN
    assert payload.location_id == "53_53"
    assert payload.background_url == "/static/images/scenes/tavern.png"
    assert integrator.entered == [7]


@pytest.mark.unit
async def test_city_service_placeholder_returns_live_text_screen() -> None:
    service = CityService(integrator=FakeCityServiceIntegrator())

    payload = await service.view(7, service_id="svc_market_hub", location_id="53_51")

    assert payload.service_id == "svc_market_hub"
    assert payload.service_type == "market"
    assert payload.screen == CityServiceScreenEnum.MAIN
    assert payload.background_url == "/static/images/exploration/terrain/market_ruins_01.webp"
    assert "аукционные доски" in payload.description.lower()
    assert payload.buttons


@pytest.mark.unit
async def test_city_service_portal_returns_service_view_background_and_portal_actions() -> None:
    service = CityService(integrator=FakeCityServiceIntegrator())

    payload = await service.view(7, service_id="svc_portal_hub", location_id="52_52")

    assert payload.service_id == "svc_portal_hub"
    assert payload.service_type == "portal"
    assert payload.location_id == "52_52"
    assert payload.background_url == "/static/images/exploration/city/d4/52_52_runic_circle_plaza.png"
    assert payload.sections == []
    assert payload.metadata["npc_key"] == "portal_pad_guide"
    assert payload.metadata["npc"]["id"] == "portal_first_contact"
    assert payload.metadata["npc"]["npc_key"] == "portal_pad_guide"
    assert payload.metadata["npc"]["stage_position"] == "bottom-right"
    assert payload.metadata["npc"]["dialogue_quest_key"] == "portal_guide_dialogue"
    assert [button.label for button in payload.buttons] == ["Войти в портал", "Выйти"]
    assert payload.buttons[0].is_disabled is True


@pytest.mark.unit
async def test_city_service_portal_contact_starts_dialogue() -> None:
    service = CityService(integrator=FakeCityServiceIntegrator())

    transition = await service.start_dialogue(
        7,
        service_id="svc_portal_hub",
        location_id="52_52",
        section_id="portal_contact",
    )

    assert transition.target_state == CoreDomain.SCENARIO
    assert transition.quest_key == "portal_guide_dialogue"
    assert transition.metadata["npc_key"] == "portal_pad_guide"
    assert transition.context["return_context"]["npc_key"] == "portal_pad_guide"
    assert transition.metadata["section_id"] == "portal_contact"
    assert transition.context["return_context"]["metadata"]["section_id"] == "portal_contact"


@pytest.mark.unit
async def test_city_service_tavern_dialogue_returns_scenario_transition_with_return_context() -> None:
    service = CityService(integrator=FakeCityServiceIntegrator())

    transition = await service.start_dialogue(7, service_id="svc_tavern_hub", location_id="53_53", section_id="bar")

    assert transition.target_state == CoreDomain.SCENARIO
    assert transition.quest_key == "tavern_bartender_dialogue"
    assert transition.location_id == "53_53"
    assert transition.metadata["service_id"] == "svc_tavern_hub"
    assert transition.metadata["npc_key"] == "tavern_bartender"
    return_context = transition.context["return_context"]
    assert return_context["source_state"] == CoreDomain.CITY_SERVICES.value
    assert return_context["return_state"] == CoreDomain.CITY_SERVICES.value
    assert return_context["return_screen"] == CityServiceScreenEnum.SECTION.value
    assert return_context["source_service_id"] == "svc_tavern_hub"
    assert return_context["npc_key"] == "tavern_bartender"


@pytest.mark.unit
async def test_city_service_tavern_rest_requires_owned_room() -> None:
    integrator = FakeCityServiceIntegrator(room=None)
    service = CityService(integrator=integrator)

    payload = await service.rest(7, service_id="svc_tavern_hub")

    assert payload.screen == CityServiceScreenEnum.SECTION
    assert payload.section_id == "room"
    assert payload.metadata["room"]["is_owned"] is False
    assert payload.notice == "Комната еще не закреплена за персонажем."
    assert integrator.restored == []


@pytest.mark.unit
async def test_city_service_tavern_rest_restores_vitals_for_owned_room() -> None:
    integrator = FakeCityServiceIntegrator(room=_room())
    service = CityService(integrator=integrator)

    payload = await service.rest(7, service_id="svc_tavern_hub")

    assert payload.section_id == "room"
    assert payload.metadata["room"]["can_rest"] is True
    assert payload.metadata["vitals"]["hp"]["cur"] == 100
    assert integrator.restored == [(7, "city_services:tavern:last_refuge:rest")]


@pytest.mark.unit
async def test_city_service_grant_tavern_room_is_idempotent_at_service_boundary() -> None:
    integrator = FakeCityServiceIntegrator(room=_room())
    service = CityService(integrator=integrator)

    room, created = await service.grant_tavern_room(char_id=7, tavern_id="last_refuge")

    assert room.id == 10
    assert created is False
    assert integrator.grants == [(7, "last_refuge", "last_refuge_private_room")]


@pytest.mark.unit
async def test_city_service_leave_returns_exploration_transition() -> None:
    integrator = FakeCityServiceIntegrator()
    service = CityService(integrator=integrator)

    transition = await service.leave(7)

    assert transition.target_state == CoreDomain.EXPLORATION
    assert transition.reason == "city_service_leave"
    assert integrator.left == [7]


@pytest.mark.unit
async def test_city_service_gateway_handles_unknown_action_safely() -> None:
    gateway = CityServiceGateway(service=CityService(integrator=FakeCityServiceIntegrator()))
    body = CityServiceActionDTO.model_construct(action="unknown_action", service_id="svc_tavern_hub")

    response = await gateway.handle_action(SimpleNamespace(), 7, body)

    assert response.payload is None
    assert response.payload_type == "city_service_error"
    assert "Unknown city service action" in response.header.error


@pytest.mark.unit
async def test_city_service_gateway_start_dialogue_returns_transition_response() -> None:
    gateway = CityServiceGateway(service=CityService(integrator=FakeCityServiceIntegrator()))
    body = CityServiceActionDTO(
        action=CityServiceActionEnum.START_DIALOGUE,
        service_id="svc_tavern_hub",
        location_id="53_53",
        section_id="bar",
    )

    response = await gateway.handle_action(SimpleNamespace(), 7, body)

    assert response.payload_type == "state_transition"
    assert response.payload.target_state == CoreDomain.SCENARIO
