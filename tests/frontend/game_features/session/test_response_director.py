from types import SimpleNamespace

import pytest

from src.frontend.game_features.session.services.response_director import ResponseDirector
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, StateTransitionDTO
from src.shared.schemas.exploration import ExplorationHudDTO, NavigationGridDTO, WorldNavigationDTO
from src.shared.schemas.world_theme import WorldThemeDTO


class FakeSessionContextBuilder:
    async def build(
        self,
        request,
        *,
        state,
        char_id,
        quest_key=None,
        transition_context=None,
        transition_metadata=None,
    ):
        return {
            "domain": state,
            "char_id": char_id,
            "quest_key": quest_key,
            "transition_context": transition_context,
            "transition_metadata": transition_metadata,
            "scenario": None,
            "exploration": SimpleNamespace(title="Loaded"),
        }

    async def build_from_response(self, request, response, *, char_id):
        return {
            "domain": "SCENARIO",
            "char_id": char_id,
            "scenario": response.payload,
            "session_ui": {"left_open": True, "right_open": True},
        }

    async def build_exploration_response(self, request, response, *, char_id):
        return {
            "domain": CoreDomain.EXPLORATION.value,
            "char_id": char_id,
            "exploration": response.payload,
            "payload_type": response.payload_type,
            "world_theme": getattr(response.payload, "world_theme", None),
            "status_seed": {"symbiote_name": "SYSTEM"},
        }


@pytest.mark.asyncio
async def test_response_director_loads_target_state_on_transition():
    director = ResponseDirector(context_builder=FakeSessionContextBuilder())
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.EXPLORATION, previous_state=CoreDomain.SCENARIO),
        payload=StateTransitionDTO(char_id=7, target_state=CoreDomain.EXPLORATION, reason="scenario_finalized"),
        payload_type="state_transition",
    )

    template, context = await director.resolve(
        SimpleNamespace(),
        response,
        source_state=CoreDomain.SCENARIO,
        char_id=7,
    )

    assert template == "game/session_content.html"
    assert context["domain"] == CoreDomain.EXPLORATION
    assert context["char_id"] == 7


@pytest.mark.asyncio
async def test_response_director_can_redirect_state_transition_to_session_shell():
    director = ResponseDirector(context_builder=FakeSessionContextBuilder())
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.EXPLORATION, previous_state=CoreDomain.SCENARIO),
        payload=StateTransitionDTO(char_id=7, target_state=CoreDomain.EXPLORATION, reason="scenario_finalized"),
        payload_type="state_transition",
    )

    template, context = await director.resolve(
        SimpleNamespace(),
        response,
        source_state=CoreDomain.SCENARIO,
        char_id=7,
        redirect_transitions=True,
    )

    assert template == "__session_redirect__"
    assert context == {"char_id": 7}


@pytest.mark.asyncio
async def test_response_director_builds_arena_transition_before_redirect():
    director = ResponseDirector(context_builder=FakeSessionContextBuilder())
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.ARENA, previous_state=CoreDomain.EXPLORATION),
        payload=StateTransitionDTO(char_id=7, target_state=CoreDomain.ARENA, reason="exploration_service_entry"),
        payload_type="state_transition",
    )

    template, context = await director.resolve(
        SimpleNamespace(),
        response,
        source_state=CoreDomain.EXPLORATION,
        char_id=7,
        redirect_transitions=True,
    )

    assert template == "game/session_content.html"
    assert context["domain"] == CoreDomain.ARENA
    assert context["char_id"] == 7


@pytest.mark.asyncio
async def test_response_director_builds_tavern_transition_before_redirect():
    director = ResponseDirector(context_builder=FakeSessionContextBuilder())
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.TAVERN, previous_state=CoreDomain.EXPLORATION),
        payload=StateTransitionDTO(
            char_id=7,
            target_state=CoreDomain.TAVERN,
            reason="exploration_service_entry",
            context={"return_context": {"return_screen": "bar"}},
            metadata={"tavern_id": "last_refuge"},
        ),
        payload_type="state_transition",
    )

    template, context = await director.resolve(
        SimpleNamespace(),
        response,
        source_state=CoreDomain.EXPLORATION,
        char_id=7,
        redirect_transitions=True,
    )

    assert template == "game/session_content.html"
    assert context["domain"] == CoreDomain.TAVERN
    assert context["transition_context"] == {"return_context": {"return_screen": "bar"}}
    assert context["transition_metadata"] == {"tavern_id": "last_refuge"}


@pytest.mark.asyncio
async def test_response_director_renders_exploration_center_for_same_state_payload():
    director = ResponseDirector(context_builder=FakeSessionContextBuilder())
    payload = WorldNavigationDTO(
        loc_id="52_52",
        title="Crossroads",
        description="A quiet node.",
        world_theme=WorldThemeDTO(accent="#ffffff"),
        grid=NavigationGridDTO(),
        hud=ExplorationHudDTO(),
    )
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.EXPLORATION),
        payload=payload,
        payload_type="exploration_navigation",
    )

    template, context = await director.resolve(
        SimpleNamespace(),
        response,
        source_state=CoreDomain.EXPLORATION,
        char_id=7,
    )

    assert template == "game/domains/exploration/viewport/main.html"
    assert context["exploration"] == payload
    assert context["payload_type"] == "exploration_navigation"
    assert context["world_theme"].accent == "#ffffff"
    assert context["status_seed"]["symbiote_name"] == "SYSTEM"
    assert context["oob_panels"] is True


@pytest.mark.asyncio
async def test_response_director_renders_scenario_center_with_inner_oob_panels():
    director = ResponseDirector(context_builder=FakeSessionContextBuilder())
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO),
        payload=SimpleNamespace(node_key="rift_entry_01"),
        payload_type="scenario_screen",
    )

    template, context = await director.resolve(
        SimpleNamespace(),
        response,
        source_state=CoreDomain.SCENARIO,
        char_id=7,
    )

    assert template == "game/domains/scenario/viewport/main.html"
    assert context["oob_panels"] is True
    assert context["session_ui"] == {"left_open": True, "right_open": True}


@pytest.mark.asyncio
async def test_response_director_renders_tavern_center_for_same_state_payload():
    director = ResponseDirector(context_builder=FakeSessionContextBuilder())
    payload = SimpleNamespace(screen="bar")
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.TAVERN),
        payload=payload,
        payload_type="tavern_screen",
    )

    template, context = await director.resolve(
        SimpleNamespace(),
        response,
        source_state=CoreDomain.TAVERN,
        char_id=7,
    )

    assert template == "game/domains/tavern/viewport/main.html"
    assert context["tavern"] == payload
    assert context["payload_type"] == "tavern_screen"
    assert context["oob_panels"] is True
