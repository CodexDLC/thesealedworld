from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, ScenarioPayloadDTO
from src.shared.schemas.character_status import CharacterActorCoreDTO
from src.shared.schemas.combat import CombatActorCardDTO, CombatActorVitalsDTO, CombatDashboardDTO
from src.shared.schemas.panel import PanelDTO


class FakeCharacterStatusApi:
    def __init__(self):
        self.calls = []

    async def get_panel(self, token, *, char_id):
        self.calls.append(("status", char_id))
        return CharacterActorCoreDTO.model_validate(
            {
                "key": f"game:ac:{char_id}",
                "char_id": char_id,
                "user_id": uuid4(),
                "state": "SCENARIO",
                "bio": {"name": "Ada", "avatar": "/avatar.png"},
                "location": {"current": "52_52"},
                "vitals": {
                    "hp": {"cur": 88, "max": 100},
                    "energy": {"cur": 77, "max": 100},
                    "stamina": {"cur": 66, "max": 100},
                },
                "attributes": {},
                "sessions": {},
                "metrics": {},
                "skills": {},
                "symbiote": {"name": "Mote", "gift_rank": 1},
                "updated_at": datetime.now(UTC),
                "panel": PanelDTO(id="character_status", title="STATUS", widgets=[]),
            }
        )


class FakeGameSessionApi:
    def __init__(self, response):
        self.response = response
        self.dto = None

    async def enter(self, token, dto):
        self.dto = dto
        return self.response


class FakeExplorationApi:
    def __init__(self, calls):
        self.calls = calls

    async def look_around(self, token, *, char_id):
        self.calls.append(("exploration", char_id))
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.EXPLORATION, transaction_id="tx-explore"),
            payload=SimpleNamespace(
                loc_id="52_52",
                world_theme={"loc_id": "52_52"},
            ),
            payload_type="exploration_navigation",
        )


class FakeScenarioApi:
    def __init__(self, response):
        self.response = response
        self.initialized = None

    async def initialize(self, token, *, char_id, quest_key):
        self.initialized = (char_id, quest_key)
        return self.response

    async def resume(self, token, *, char_id):
        return self.response


class FakeCombatApi:
    def __init__(self):
        self.calls = []

    async def view(self, token, *, char_id):
        self.calls.append(("combat", char_id))
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.COMBAT, transaction_id="tx-combat"),
            payload=CombatDashboardDTO(
                session_id="combat-1",
                turn_number=3,
                status="active",
                hero=CombatActorCardDTO(
                    actor_id=str(char_id),
                    name="Ada",
                    actor_type="player",
                    team="team_1",
                    avatar_url="/static/images/avatars/rook7.png",
                    vitals=CombatActorVitalsDTO(hp_current=70, hp_max=100, energy_current=40, energy_max=90, tactics=2),
                ),
                target=CombatActorCardDTO(
                    actor_id=f"-{char_id}",
                    name="Ada Shadow",
                    actor_type="shadow",
                    team="team_2",
                    is_ai=True,
                    vitals=CombatActorVitalsDTO(hp_current=65, hp_max=100, energy_current=30, energy_max=90, tactics=1),
                ),
            ),
            payload_type="CombatDashboard",
        )


def request():
    return SimpleNamespace(cookies={"tbmmorpg_access_token": "token"})


def scenario_response() -> CoreResponseDTO[ScenarioPayloadDTO]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO, transaction_id="tx"),
        payload=ScenarioPayloadDTO(
            node_key="rift_entry_01",
            text="Wake up.",
            extra_data={
                "background_url": "/static/images/scenarios/awakening_rift/background.png",
                "show_left_sidebar": True,
                "show_right_sidebar": True,
                "quest_key": "awakening_rift",
            },
        ),
        payload_type="scenario_screen",
    )


def builder(response):
    return SessionContextBuilder(
        character_status_api=FakeCharacterStatusApi(),
        arena_api=SimpleNamespace(),
        exploration_api=SimpleNamespace(),
        scenario_api=FakeScenarioApi(response),
        game_session_api=FakeGameSessionApi(response),
    )


def exploration_builder(calls):
    status_api = FakeCharacterStatusApi()
    return SessionContextBuilder(
        character_status_api=status_api,
        arena_api=SimpleNamespace(),
        exploration_api=FakeExplorationApi(calls),
        scenario_api=FakeScenarioApi(scenario_response()),
        game_session_api=FakeGameSessionApi(scenario_response()),
    )


def combat_builder(status_api, combat_api):
    return SessionContextBuilder(
        character_status_api=status_api,
        arena_api=SimpleNamespace(),
        exploration_api=SimpleNamespace(),
        scenario_api=FakeScenarioApi(scenario_response()),
        game_session_api=FakeGameSessionApi(scenario_response()),
        combat_api=combat_api,
    )


@pytest.mark.asyncio
async def test_build_current_returns_full_scenario_shell_context():
    context = await builder(scenario_response()).build_current(request(), char_id=7)

    assert context["domain"] == "SCENARIO"
    assert context["char_id"] == 7
    assert context["scenario"].node_key == "rift_entry_01"
    assert context["character_status"].panel is not None
    assert context["background_url"].endswith("background.png")
    assert context["session_ui"] == {"left_open": True, "right_open": True}
    assert context["status_seed"]["hp"] == 88
    assert context["status_seed"]["symbiote_name"] == "Mote"
    assert context["status_seed"]["symbiote"]["gift_rank"] == 1
    assert context["nav"]["center"]["label"] == "SCENARIO"


@pytest.mark.asyncio
async def test_build_state_initializes_scenario_with_same_context_shape():
    response = scenario_response()
    service = builder(response)

    context = await service.build_state(
        request(),
        state=CoreDomain.SCENARIO,
        char_id=7,
        quest_key="awakening_rift",
    )

    assert context["domain"] == "SCENARIO"
    assert context["scenario"] == response.payload
    assert context["session_ui"]["right_open"] is True


@pytest.mark.asyncio
async def test_build_state_restores_actor_core_before_exploration_lookup():
    calls = []
    service = exploration_builder(calls)
    service.character_status_api.calls = calls

    context = await service.build_state(request(), state=CoreDomain.EXPLORATION, char_id=7)

    assert calls == [("status", 7), ("exploration", 7)]
    assert context["domain"] == "EXPLORATION"
    assert context["exploration"].loc_id == "52_52"


@pytest.mark.asyncio
async def test_build_state_combat_uses_combat_session_without_character_status_lookup():
    status_api = FakeCharacterStatusApi()
    combat_api = FakeCombatApi()
    service = combat_builder(status_api, combat_api)

    context = await service.build_state(request(), state=CoreDomain.COMBAT, char_id=7)

    assert combat_api.calls == [("combat", 7)]
    assert status_api.calls == []
    assert context["domain"] == "COMBAT"
    assert context["combat"].session_id == "combat-1"
    assert context["combat"].hero.avatar_url == "/static/images/avatars/rook7.png"
    assert context["combat_screen"].hero.avatar_url == "/static/images/avatars/rook7.png"
    assert context["combat_screen"].target.avatar_url == "/static/images/avatars/veil4.png"
    assert len(context["combat_screen"].hero.quick_belt) == 8
    assert context["character_status"] is None
    assert context["session_ui"] == {"left_open": True, "right_open": True}
    assert context["nav"]["center"]["label"] == "COMBAT"
    assert context["nav"]["l2"]["label"] == "STATUS"
    assert context["nav"]["l1"]["label"] == "BUILDS"
    assert context["nav"]["r1"]["label"] == "INVENTORY"
    assert context["nav"]["r2"]["label"] == "VIEW"
    assert context["status_seed"]["hp"] == 70
    assert context["status_seed"]["name"] == "Ada"
