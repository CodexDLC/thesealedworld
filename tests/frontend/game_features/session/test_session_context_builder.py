from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.integrations.backend_api.combat import CombatViewResponse
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, ScenarioPayloadDTO
from src.shared.schemas.arena import ArenaScreenEnum, ArenaUIPayloadDTO
from src.shared.schemas.character_status import CharacterActorCoreDTO
from src.shared.schemas.combat import CombatActorCardDTO, CombatActorVitalsDTO, CombatDashboardDTO, CombatResultDTO
from src.shared.schemas.exploration import (
    DetectionStatus,
    EncounterDTO,
    EncounterType,
    EnemyPreviewDTO,
    ExplorationHudDTO,
    NavigationGridDTO,
    WorldNavigationDTO,
)
from src.shared.schemas.inventory import InventoryWindowDTO
from src.shared.schemas.panel import PanelDTO
from src.shared.schemas.world_theme import WorldThemeDTO


class FakeCharacterStatusApi:
    def __init__(self, *, sessions=None):
        self.calls = []
        self.sessions = sessions or {}

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
                "sessions": self.sessions,
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


class FakeInventoryApi:
    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload

    async def view(self, token, *, char_id):
        self.calls.append(("inventory", char_id))
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.INVENTORY, transaction_id="tx-inventory"),
            payload=self.payload or inventory_window_payload(char_id),
            payload_type="inventory",
        )


class FakeExplorationApi:
    def __init__(self, calls, response: CoreResponseDTO | None = None):
        self.calls = calls
        self.response = response

    async def look_around(self, token, *, char_id):
        self.calls.append(("exploration", char_id))
        if self.response is not None:
            return self.response
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.EXPLORATION, transaction_id="tx-explore"),
            payload=WorldNavigationDTO(
                loc_id="52_52",
                title="Runic Circle",
                description="Safe hub.",
                world_theme=WorldThemeDTO(loc_id="52_52"),
                grid=NavigationGridDTO(),
                hud=ExplorationHudDTO(is_safe_zone=True),
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
    def __init__(self, payload=None, payload_type="CombatDashboard", current_state=CoreDomain.COMBAT):
        self.calls = []
        self.payload = payload
        self.payload_type = payload_type
        self.current_state = current_state

    async def view(self, token, *, char_id):
        self.calls.append(("combat", char_id))
        payload = self.payload or CombatDashboardDTO(
            session_id="combat-1",
            turn_number=3,
            status="active",
            hero=CombatActorCardDTO(
                actor_id=str(char_id),
                name="Ada",
                actor_type="player",
                team="team_1",
                avatar_url="/static/images/avatars/rook7.png",
                vitals=CombatActorVitalsDTO(
                    hp_current=70,
                    hp_max=100,
                    energy_current=40,
                    energy_max=90,
                    stamina_current=55,
                    stamina_max=120,
                    tactics=2,
                ),
            ),
            target=CombatActorCardDTO(
                actor_id=f"-{char_id}",
                name="Ada Shadow",
                actor_type="shadow",
                team="team_2",
                is_ai=True,
                vitals=CombatActorVitalsDTO(
                    hp_current=65,
                    hp_max=100,
                    energy_current=30,
                    energy_max=90,
                    stamina_current=50,
                    stamina_max=120,
                    tactics=1,
                ),
            ),
        )
        return CoreResponseDTO(
            header=GameStateHeader(current_state=self.current_state, transaction_id="tx-combat"),
            payload=payload,
            payload_type=self.payload_type,
        )


class FakeArenaApi:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def view(self, token, *, char_id):
        self.calls.append(("arena", char_id))
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.ARENA, transaction_id="tx-arena"),
            payload=self.payload,
            payload_type="arena_screen",
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


def inventory_window_payload(char_id: int = 7) -> InventoryWindowDTO:
    return InventoryWindowDTO.model_validate(
        {
            "char_id": char_id,
            "avatar_url": "/inventory-avatar.png",
            "avatar_name": "Inventory Ada",
            "stats": {"slots_total": 42, "slots_used": 1},
            "body_zones": [
                {
                    "zone_id": "head",
                    "label": "Head",
                    "position": "head",
                    "primary_slot": {"slot_id": "head_armor", "label": "Head", "layer": "armor"},
                }
            ],
            "weapon_slots": [],
            "accessory_rows": [],
            "quick_slots": [],
            "tabs": [{"tab_id": "items", "label": "Items", "icon": "I", "is_active": True}],
            "visible_rows": [],
        }
    )


def builder(response):
    return SessionContextBuilder(
        character_status_api=FakeCharacterStatusApi(),
        arena_api=SimpleNamespace(),
        exploration_api=SimpleNamespace(),
        scenario_api=FakeScenarioApi(response),
        game_session_api=FakeGameSessionApi(response),
        inventory_api=FakeInventoryApi(),
    )


def exploration_builder(calls):
    status_api = FakeCharacterStatusApi()
    return SessionContextBuilder(
        character_status_api=status_api,
        arena_api=SimpleNamespace(),
        exploration_api=FakeExplorationApi(calls),
        scenario_api=FakeScenarioApi(scenario_response()),
        game_session_api=FakeGameSessionApi(scenario_response()),
        inventory_api=FakeInventoryApi(),
    )


def exploration_builder_with_response(calls, response):
    status_api = FakeCharacterStatusApi()
    return SessionContextBuilder(
        character_status_api=status_api,
        arena_api=SimpleNamespace(),
        exploration_api=FakeExplorationApi(calls, response=response),
        scenario_api=FakeScenarioApi(scenario_response()),
        game_session_api=FakeGameSessionApi(scenario_response()),
        inventory_api=FakeInventoryApi(),
    )


def combat_builder(status_api, combat_api):
    return SessionContextBuilder(
        character_status_api=status_api,
        arena_api=SimpleNamespace(),
        exploration_api=SimpleNamespace(),
        scenario_api=FakeScenarioApi(scenario_response()),
        game_session_api=FakeGameSessionApi(scenario_response()),
        inventory_api=FakeInventoryApi(),
        combat_api=combat_api,
    )


def arena_builder(status_api, arena_api):
    return SessionContextBuilder(
        character_status_api=status_api,
        arena_api=arena_api,
        exploration_api=SimpleNamespace(),
        scenario_api=FakeScenarioApi(scenario_response()),
        game_session_api=FakeGameSessionApi(scenario_response()),
        inventory_api=FakeInventoryApi(),
    )


def test_combat_view_response_parses_result_before_dashboard():
    response = CombatViewResponse.model_validate(
        {
            "header": {"current_state": "combats", "error": "combat_result_from_archive_stub"},
            "payload_type": "CombatResult",
            "payload": {
                "char_id": 7,
                "title": "Итоги боя недоступны",
                "message": "Живая боевая сессия больше не найдена.",
            },
        }
    )

    assert isinstance(response.payload, CombatResultDTO)


@pytest.mark.asyncio
async def test_build_current_returns_full_scenario_shell_context():
    context = await builder(scenario_response()).build_current(request(), char_id=7)

    assert context["domain"] == "scenario"
    assert context["char_id"] == 7
    assert context["scenario"].node_key == "rift_entry_01"
    assert context["character_status"].panel is not None
    assert context["background_url"].endswith("background.png")
    assert context["session_ui"] == {"left_open": True, "right_open": True}
    assert context["status_seed"]["hp"] == 88
    assert context["status_seed"]["symbiote_name"] == "Mote"
    assert context["status_seed"]["symbiote"]["gift_rank"] == 1
    assert context["inventory_window"].avatar_url == "/avatar.png"
    assert context["inventory_window"].contract_state == "FRONTEND_CONTRACT_PENDING"
    assert len(context["inventory_window"].body_zones) == 6
    assert len(context["inventory_window"].accessory_rows) == 4
    assert len(context["inventory_window"].quick_slots) == 8
    assert context["nav"]["center"]["label"] == "SCENARIO"


@pytest.mark.asyncio
async def test_build_current_loads_scenario_when_session_enter_returns_state_decision():
    enter_response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.SCENARIO, transaction_id="tx-enter"),
        payload={"character_id": 7, "domain": "scenario", "source": "hot_ac"},
        payload_type="scenario_session",
    )
    scenario = scenario_response()
    scenario_api = FakeScenarioApi(scenario)
    service = SessionContextBuilder(
        character_status_api=FakeCharacterStatusApi(),
        arena_api=SimpleNamespace(),
        exploration_api=SimpleNamespace(),
        scenario_api=scenario_api,
        game_session_api=FakeGameSessionApi(enter_response),
        inventory_api=FakeInventoryApi(),
    )

    context = await service.build_current(request(), char_id=7)

    assert context["domain"] == "scenario"
    assert context["scenario"].node_key == "rift_entry_01"
    assert scenario_api.initialized is None


@pytest.mark.asyncio
async def test_build_current_redirects_to_lobby_when_session_enter_returns_lobby():
    enter_response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.LOBBY, transaction_id="tx-enter"),
        payload={"char_id": 7, "target_state": "lobby", "reason": "active_character_unavailable"},
        payload_type="state_transition",
    )
    service = SessionContextBuilder(
        character_status_api=FakeCharacterStatusApi(),
        arena_api=SimpleNamespace(),
        exploration_api=SimpleNamespace(),
        scenario_api=FakeScenarioApi(scenario_response()),
        game_session_api=FakeGameSessionApi(enter_response),
        inventory_api=FakeInventoryApi(),
    )

    with pytest.raises(HTTPException) as exc:
        await service.build_current(request(), char_id=7)

    assert exc.value.status_code == 303
    assert exc.value.headers == {"Location": "/game-lobby"}


@pytest.mark.asyncio
async def test_build_current_restores_open_inventory_window_from_active_character_ref():
    status_api = FakeCharacterStatusApi(sessions={"inventory_id": "game:inventory:7"})
    inventory_api = FakeInventoryApi()
    response = scenario_response()
    service = SessionContextBuilder(
        character_status_api=status_api,
        arena_api=SimpleNamespace(),
        exploration_api=SimpleNamespace(),
        scenario_api=FakeScenarioApi(response),
        game_session_api=FakeGameSessionApi(response),
        inventory_api=inventory_api,
    )

    context = await service.build_current(request(), char_id=7)

    assert context["initial_inventory_open"] is True
    assert inventory_api.calls == [("inventory", 7)]
    assert context["inventory_window"].contract_state == "SHARED_INVENTORY_CONTRACT_V1"
    assert context["inventory_window"].stats.slots_total == 42
    assert context["inventory_window"].avatar_url == "/inventory-avatar.png"


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

    assert context["domain"] == "scenario"
    assert context["scenario"] == response.payload
    assert context["session_ui"]["right_open"] is True


@pytest.mark.asyncio
async def test_build_state_restores_actor_core_before_exploration_lookup():
    calls = []
    service = exploration_builder(calls)
    service.character_status_api.calls = calls

    context = await service.build_state(request(), state=CoreDomain.EXPLORATION, char_id=7)

    assert calls == [("status", 7), ("exploration", 7)]
    assert context["domain"] == "exploration"
    assert context["exploration"].loc_id == "52_52"


@pytest.mark.asyncio
async def test_build_exploration_response_keeps_location_context_for_encounter():
    calls = []
    service = exploration_builder(calls)
    service.character_status_api.calls = calls
    encounter = EncounterDTO(
        id="combat_1",
        type=EncounterType.COMBAT,
        status=DetectionStatus.DETECTED,
        title="Threat",
        description="Rat appears.",
        enemies=[EnemyPreviewDTO(name="Rat", level=1, hp_percent=100)],
        session_id="stub_combat_7",
        metadata={"tier": 0},
    )
    response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.EXPLORATION, transaction_id="tx-encounter"),
        payload=encounter,
        payload_type="exploration_encounter",
    )

    context = await service.build_exploration_response(request(), response, char_id=7)

    assert calls == [("status", 7), ("exploration", 7)]
    assert context["payload_type"] == "exploration_encounter"
    assert context["encounter"] == encounter
    assert context["exploration"].loc_id == "52_52"


@pytest.mark.asyncio
async def test_build_exploration_response_uses_encounter_navigation_snapshot_when_lookup_is_gated():
    calls = []
    navigation = WorldNavigationDTO(
        loc_id="52_52",
        title="Runic Circle",
        description="Safe hub.",
        world_theme=WorldThemeDTO(loc_id="52_52"),
        grid=NavigationGridDTO(),
        hud=ExplorationHudDTO(is_safe_zone=True),
    )
    encounter = EncounterDTO(
        id="combat_1",
        type=EncounterType.COMBAT,
        status=DetectionStatus.AMBUSH,
        title="Threat",
        description="Rat appears.",
        enemies=[EnemyPreviewDTO(name="Rat", level=1, hp_percent=100)],
        metadata={"navigation": navigation.model_dump(mode="json")},
    )
    gated_response = CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.EXPLORATION, transaction_id="tx-encounter"),
        payload=encounter,
        payload_type="exploration_encounter",
    )
    service = exploration_builder_with_response(calls, gated_response)
    service.character_status_api.calls = calls

    context = await service.build_exploration_response(request(), gated_response, char_id=7)

    assert calls == [("status", 7)]
    assert context["payload_type"] == "exploration_encounter"
    assert context["encounter"] == encounter
    assert context["exploration"].loc_id == "52_52"
    assert context["exploration"].title == "Runic Circle"


@pytest.mark.asyncio
async def test_build_state_arena_normalizes_dict_payload_before_render_context():
    status_api = FakeCharacterStatusApi()
    arena_api = FakeArenaApi(
        {
            "screen": "main_menu",
            "title": "Ангар Арены",
            "description": "Выберите режим.",
            "buttons": [],
        }
    )
    service = arena_builder(status_api, arena_api)

    context = await service.build_state(request(), state=CoreDomain.ARENA, char_id=7)

    assert arena_api.calls == [("arena", 7)]
    assert isinstance(context["arena"], ArenaUIPayloadDTO)
    assert context["arena"].screen == ArenaScreenEnum.MAIN_MENU
    assert context["domain"] == "arena"
    assert context["character_status"].panel is not None


@pytest.mark.asyncio
async def test_build_state_combat_uses_combat_session_without_character_status_lookup():
    status_api = FakeCharacterStatusApi()
    combat_api = FakeCombatApi()
    service = combat_builder(status_api, combat_api)

    context = await service.build_state(request(), state=CoreDomain.COMBAT, char_id=7)

    assert combat_api.calls == [("combat", 7)]
    assert status_api.calls == []
    assert context["domain"] == "combats"
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
    assert context["nav"]["l2"]["is_disabled"] is True
    assert context["nav"]["r1"]["is_disabled"] is True
    assert context["status_seed"]["hp"] == 70
    assert context["status_seed"]["stamina"] == 55
    assert context["status_seed"]["max_stamina"] == 120
    assert context["status_seed"]["name"] == "Ada"


@pytest.mark.asyncio
async def test_build_state_combat_accepts_archived_result_payload():
    status_api = FakeCharacterStatusApi()
    combat_api = FakeCombatApi(
        payload=CombatResultDTO(char_id=7, title="Итоги боя недоступны"),
        payload_type="CombatResult",
    )
    service = combat_builder(status_api, combat_api)

    context = await service.build_state(request(), state=CoreDomain.COMBAT, char_id=7)

    assert combat_api.calls == [("combat", 7)]
    assert status_api.calls == []
    assert context["domain"] == "combats"
    assert context["combat_result"].title == "Итоги боя недоступны"
    assert context["combat_screen"].status == "finished"
    assert context["combat_screen"].action_state == "COMBAT_FINALIZED"
    assert context["payload_type"] == "CombatResult"
    assert context["status_seed"]["character_id"] == 7


@pytest.mark.asyncio
async def test_build_state_combat_result_uses_combat_layout_domain():
    status_api = FakeCharacterStatusApi()
    combat_api = FakeCombatApi(
        payload=CombatResultDTO(char_id=7, title="Победа"),
        payload_type="CombatResult",
        current_state=CoreDomain.COMBAT_RESULT,
    )
    service = combat_builder(status_api, combat_api)

    context = await service.build_state(request(), state=CoreDomain.COMBAT_RESULT, char_id=7)

    assert combat_api.calls == [("combat", 7)]
    assert context["domain"] == "combats"
    assert context["combat_result"].title == "Победа"
    assert context["session_ui"] == {"left_open": True, "right_open": True}
    assert context["nav"]["center"]["label"] == "COMBAT"
