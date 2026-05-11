import time

import pytest

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaQueueRequestDTO, ArenaRuntimeSessionDTO
from src.backend.features.arena.integrations import ArenaSessionIntegration, ArenaSystemIntegrator
from src.backend.features.arena.services import ArenaService
from src.shared.enums import CoreDomain
from src.shared.schemas.arena import ArenaScreenEnum


class FakeStore:
    def __init__(self) -> None:
        self.requests: dict[int, ArenaQueueRequestDTO] = {}
        self.matches: dict[str, ArenaCombatRequestDTO] = {}
        self.runtime_sessions: dict[str, ArenaRuntimeSessionDTO] = {}
        self.char_matches: dict[int, str] = {}
        self.queue: dict[str, set[int]] = {}
        self.locks: set[int] = set()

    async def add_to_queue(self, request: ArenaQueueRequestDTO) -> None:
        self.requests[request.char_id] = request
        self.queue.setdefault(request.mode, set()).add(request.char_id)

    async def remove_from_queue(self, mode: str, char_id: int) -> bool:
        values = self.queue.setdefault(mode, set())
        existed = char_id in values
        values.discard(char_id)
        return existed

    async def delete_request(self, char_id: int) -> None:
        self.requests.pop(char_id, None)

    async def get_request(self, char_id: int) -> ArenaQueueRequestDTO | None:
        return self.requests.get(char_id)

    async def create_runtime_session(self, session: ArenaRuntimeSessionDTO) -> None:
        self.runtime_sessions[session.arena_id] = session

    async def get_runtime_session(self, arena_id: str) -> ArenaRuntimeSessionDTO | None:
        return self.runtime_sessions.get(arena_id)

    async def update_runtime_session(self, session: ArenaRuntimeSessionDTO) -> None:
        self.runtime_sessions[session.arena_id] = session

    async def delete_runtime_session(self, arena_id: str) -> None:
        self.runtime_sessions.pop(arena_id, None)

    async def get_candidates(self, mode: str, min_gs: float, max_gs: float) -> list[int]:
        _ = min_gs, max_gs
        return sorted(self.queue.get(mode, set()))

    async def claim_opponent(self, mode: str, char_id: int, min_gs: float, max_gs: float) -> int | None:
        _ = min_gs, max_gs
        for candidate_id in sorted(self.queue.get(mode, set())):
            if candidate_id == char_id or candidate_id not in self.requests:
                continue
            self.queue[mode].discard(candidate_id)
            self.queue[mode].discard(char_id)
            return candidate_id
        return None

    async def acquire_match_lock(self, char_id: int, token: str) -> bool:
        _ = token
        if char_id in self.locks:
            return False
        self.locks.add(char_id)
        return True

    async def release_match_lock(self, char_id: int, token: str) -> None:
        _ = token
        self.locks.discard(char_id)

    async def create_match(self, request: ArenaCombatRequestDTO) -> None:
        self.matches[request.arena_session_id] = request
        for team in request.participants.values():
            for char_id in team:
                self.char_matches[char_id] = request.arena_session_id

    async def get_match(self, arena_session_id: str) -> ArenaCombatRequestDTO | None:
        return self.matches.get(arena_session_id)

    async def get_match_for_char(self, char_id: int) -> ArenaCombatRequestDTO | None:
        match_id = self.char_matches.get(char_id)
        return self.matches.get(match_id) if match_id else None

    async def update_match(self, match: ArenaCombatRequestDTO) -> None:
        self.matches[match.arena_session_id] = match

    async def delete_match(self, match: ArenaCombatRequestDTO) -> None:
        self.matches.pop(match.arena_session_id, None)
        for participants in match.participants.values():
            for char_id in participants:
                self.char_matches.pop(char_id, None)


class FakeEvents:
    def __init__(self) -> None:
        self.published = []
        self.requests = []

    async def publish(self, event_type, data, correlation_id=None):
        self.published.append((event_type, data, correlation_id))
        return "1-0"

    async def request(self, event_type, data, timeout=30.0, correlation_id=None):
        import json

        self.requests.append((event_type, data, timeout, correlation_id))
        session_id = data["scope_id"]
        player_ids = json.loads(data["player_ids"])
        return {
            "status": "ok",
            "commitments": {f"player:{char_id}": f"actor:{session_id}:player:{char_id}" for char_id in player_ids},
        }


class FailingSnapshotEvents(FakeEvents):
    async def request(self, event_type, data, timeout=30.0, correlation_id=None):
        self.requests.append((event_type, data, timeout, correlation_id))
        return {"status": "error", "error": "character commitments unavailable"}


class FakeCharacterSessions:
    def __init__(self):
        self.combat = {}
        self.arena = {}
        self.state = None

    async def get_session(self, char_id):
        return {"char_id": char_id, "sessions": {"arena_id": self.arena.get(char_id)}}

    async def set_combat_session(self, char_id, combat_id):
        self.combat[char_id] = combat_id

    async def set_arena_session(self, char_id, arena_id):
        self.arena[char_id] = arena_id

    async def clear_arena_session(self, char_id):
        self.arena[char_id] = None

    async def set_state(self, char_id, state, *, prev_state=None):
        self.state = (char_id, state, prev_state)


class FakeRatingView:
    async def player_metadata(self, *, char_id: int, mode_size: int = 1):
        return {
            "char_id": char_id,
            "mode_size": mode_size,
            "rating": 1000,
            "rank": 1000,
            "tier": 1,
            "league_name": "Bronze",
            "matches_played": 0,
            "placement_left": 5,
        }


def build_service(store: FakeStore, events: FakeEvents) -> ArenaService:
    sessions = FakeCharacterSessions()
    return ArenaService(
        session_service=ArenaSessionIntegration(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
    )


@pytest.mark.asyncio
async def test_view_creates_arena_runtime_session_and_attaches_active_character_ref():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    service = ArenaService(
        session_service=ArenaSessionIntegration(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
    )

    payload = await service.view(1)

    arena_id = sessions.arena[1]
    assert payload.screen == ArenaScreenEnum.MAIN_MENU
    assert arena_id.startswith("arena:runtime:")
    assert store.runtime_sessions[arena_id].char_id == 1
    assert sessions.state == (1, CoreDomain.ARENA, None)


@pytest.mark.asyncio
async def test_view_includes_rating_metadata_when_rating_view_is_configured():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    service = ArenaService(
        session_service=ArenaSessionIntegration(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
        rating_view=FakeRatingView(),
    )

    payload = await service.view(1)

    assert payload.metadata["rating"] == 1000
    assert payload.metadata["rank"] == 1000
    assert payload.metadata["tier"] == 1
    assert payload.metadata["league_name"] == "Bronze"


@pytest.mark.asyncio
async def test_show_mode_menu_updates_arena_runtime_position():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    service = ArenaService(
        session_service=ArenaSessionIntegration(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
    )

    payload = await service.show_mode_menu(1, "group")

    session = store.runtime_sessions[sessions.arena[1]]
    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert session.screen == ArenaScreenEnum.MODE_MENU
    assert session.mode == "group"


@pytest.mark.asyncio
async def test_join_queue_returns_searching_screen():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)

    payload = await service.join_queue(1, "one_vs_one")

    assert payload.screen == ArenaScreenEnum.SEARCHING
    assert payload.gs == 100
    assert store.requests[1].mode == "one_vs_one"
    assert store.requests[1].commitment_id.endswith(":player:1")
    assert events.requests[0][0] == "character.combat_commitments_requested"
    assert events.requests[0][1]["ttl"] == 660


@pytest.mark.asyncio
async def test_join_queue_does_not_queue_without_combat_commitment():
    store = FakeStore()
    events = FailingSnapshotEvents()
    service = build_service(store, events)

    payload = await service.join_queue(1, "one_vs_one")

    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert payload.metadata["commitment_status"] == "failed"
    assert store.requests == {}


@pytest.mark.asyncio
async def test_group_mode_menu_returns_mock_lobby_contract():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)

    payload = await service.get_mode_menu("group")

    lobby = payload.metadata["group_lobby"]
    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert lobby["primary_actions"][0]["action"] == "group_ranked"
    assert [tab["id"] for tab in lobby["tabs"]] == ["current", "chaos", "requests"]


@pytest.mark.asyncio
async def test_group_action_returns_mock_action_notice():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)

    payload = await service.group_action("group_pick_team", item_id="mock-request-3x3")

    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert payload.metadata["group_action"]["title"] == "Выбор команды"
    assert payload.metadata["group_action"]["item_id"] == "mock-request-3x3"


@pytest.mark.asyncio
async def test_check_match_creates_pvp_combat_request():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    await service.join_queue(1, "one_vs_one")
    await service.join_queue(2, "one_vs_one")

    payload = await service.check_match(1, "one_vs_one")

    assert payload.screen == ArenaScreenEnum.COMBAT_PENDING
    assert payload.title == "Противник найден"
    assert payload.arena_session_id
    assert payload.metadata["polling"] is False
    assert events.published[0][0] == "combat.session_requested"
    assert events.published[0][1]["battle_type"] == "pvp"
    assert events.published[0][1]["participants"] == {"team_1": [1], "team_2": [2]}
    assert set(events.published[0][1]["commitments"]) == {"player:1", "player:2"}
    assert events.published[0][1]["commitments"]["player:1"].endswith(":player:1")
    assert events.published[0][1]["commitments"]["player:2"].endswith(":player:2")


@pytest.mark.asyncio
async def test_check_match_returns_searching_when_match_lock_is_busy():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    await service.join_queue(1, "one_vs_one")
    await store.acquire_match_lock(1, "already-running")

    payload = await service.check_match(1, "one_vs_one")

    assert payload.screen == ArenaScreenEnum.SEARCHING
    assert payload.metadata["match_lock"] == "busy"
    assert events.published == []


@pytest.mark.asyncio
async def test_check_match_timeout_returns_mode_menu_without_shadow_request():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    await service.join_queue(1, "one_vs_one")
    store.requests[1].start_time = time.time() - 70

    payload = await service.check_match(1, "one_vs_one")

    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert payload.title == "Противник не найден"
    assert events.published == []
    assert 1 not in store.queue["one_vs_one"]


@pytest.mark.asyncio
async def test_continue_search_discards_shadow_offer_and_requeues():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    offer = await service.start_shadow(1, "one_vs_one")

    payload = await service.continue_search(1, "one_vs_one", arena_session_id=offer.arena_session_id)

    assert payload.screen == ArenaScreenEnum.SEARCHING
    assert offer.arena_session_id not in store.matches
    assert store.char_matches == {}
    assert 1 in store.queue["one_vs_one"]


@pytest.mark.asyncio
async def test_start_shadow_prepares_combat_without_linking_player_state():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)

    payload = await service.start_shadow(1, "one_vs_one")

    assert payload.screen == ArenaScreenEnum.COMBAT_PENDING
    assert payload.title == "Арена готова"
    assert payload.description == "Тень материализована и готова вступить в бой."
    assert payload.metadata["polling"] is False
    assert payload.metadata["awaiting_player_confirmation"] is True
    assert events.published[0][0] == "combat.session_requested"
    assert events.published[0][1]["metadata"]["awaiting_player_confirmation"] is True
    assert [button.action for button in payload.buttons] == ["check_combat_ready", "cancel_queue"]
    assert payload.buttons[0].value["confirm"] is True


@pytest.mark.asyncio
async def test_check_combat_ready_keeps_pending_without_auto_redirect():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    first_payload = await service.start_shadow(1, "one_vs_one")

    payload = await service.check_combat_ready(1, arena_session_id=first_payload.arena_session_id)

    assert payload.screen == ArenaScreenEnum.COMBAT_PENDING
    assert payload.metadata["polling"] is False
    assert [button.action for button in payload.buttons] == ["check_combat_ready", "cancel_queue"]


@pytest.mark.asyncio
async def test_check_combat_ready_does_not_enter_ready_shadow_without_confirm():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    service = ArenaService(
        session_service=ArenaSessionIntegration(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
    )
    match = ArenaCombatRequestDTO(
        mode="one_vs_one",
        battle_type="shadow",
        requested_by=1,
        participants={"team_1": [1], "team_2": []},
        status="ready",
        combat_id="combat:shadow",
        metadata={"awaiting_player_confirmation": True},
    )
    await store.create_match(match)

    payload = await service.check_combat_ready(1, arena_session_id=match.arena_session_id)

    assert payload.combat_id is None
    assert sessions.combat == {}
    assert payload.screen == ArenaScreenEnum.COMBAT_PENDING


@pytest.mark.asyncio
async def test_check_combat_ready_enters_ready_shadow_combat_with_confirm():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    service = ArenaService(
        session_service=ArenaSessionIntegration(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
    )
    match = ArenaCombatRequestDTO(
        mode="one_vs_one",
        battle_type="shadow",
        requested_by=1,
        participants={"team_1": [1], "team_2": []},
        status="ready",
        combat_id="combat:shadow",
    )
    await store.create_match(match)

    payload = await service.check_combat_ready(1, arena_session_id=match.arena_session_id, confirm=True)

    assert payload.combat_id == "combat:shadow"
    assert sessions.combat[1] == "combat:shadow"
