import time

import pytest

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaQueueRequestDTO
from src.backend.features.arena.integrations import ArenaSystemIntegrator
from src.backend.features.arena.services import ArenaService, ArenaSessionService
from src.shared.schemas.arena import ArenaActionEnum, ArenaScreenEnum


class FakeStore:
    def __init__(self) -> None:
        self.requests: dict[int, ArenaQueueRequestDTO] = {}
        self.matches: dict[str, ArenaCombatRequestDTO] = {}
        self.char_matches: dict[int, str] = {}
        self.queue: dict[str, set[int]] = {}

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

    async def get_candidates(self, mode: str, min_gs: float, max_gs: float) -> list[int]:
        _ = min_gs, max_gs
        return sorted(self.queue.get(mode, set()))

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

    async def publish(self, event_type, data, correlation_id=None):
        self.published.append((event_type, data, correlation_id))
        return "1-0"


class FakeCharacterSessions:
    def __init__(self):
        self.combat = {}
        self.state = None

    async def set_combat_session(self, char_id, combat_id):
        self.combat[char_id] = combat_id

    async def set_state(self, char_id, state):
        self.state = (char_id, state)


def build_service(store: FakeStore, events: FakeEvents) -> ArenaService:
    sessions = FakeCharacterSessions()
    return ArenaService(
        session_service=ArenaSessionService(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
    )


@pytest.mark.asyncio
async def test_join_queue_returns_searching_screen():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)

    payload = await service.join_queue(1, "one_vs_one")

    assert payload.screen == ArenaScreenEnum.SEARCHING
    assert payload.gs == 100
    assert store.requests[1].mode == "one_vs_one"


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


@pytest.mark.asyncio
async def test_check_match_timeout_creates_shadow_request():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    await service.join_queue(1, "one_vs_one")
    store.requests[1].start_time = time.time() - 50

    payload = await service.check_match(1, "one_vs_one")

    assert payload.screen == ArenaScreenEnum.SHADOW_OFFER
    assert payload.title == "Тень готова"
    assert payload.metadata["awaiting_player_choice"] is True
    assert events.published[0][1]["battle_type"] == "shadow"
    assert events.published[0][1]["participants"] == {"team_1": [1], "team_2": []}
    assert events.published[0][1]["ttl"] == 900
    assert {button.action for button in payload.buttons} == {
        ArenaActionEnum.ACCEPT_SHADOW,
        ArenaActionEnum.CONTINUE_SEARCH,
    }


@pytest.mark.asyncio
async def test_continue_search_discards_shadow_offer_and_requeues():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    await service.join_queue(1, "one_vs_one")
    store.requests[1].start_time = time.time() - 50
    offer = await service.check_match(1, "one_vs_one")

    payload = await service.continue_search(1, "one_vs_one", arena_session_id=offer.arena_session_id)

    assert payload.screen == ArenaScreenEnum.SEARCHING
    assert offer.arena_session_id not in store.matches
    assert store.char_matches == {}
    assert 1 in store.queue["one_vs_one"]


@pytest.mark.asyncio
async def test_accept_shadow_starts_combat_ready_polling():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    await service.join_queue(1, "one_vs_one")
    store.requests[1].start_time = time.time() - 50
    offer = await service.check_match(1, "one_vs_one")

    payload = await service.accept_shadow(1, "one_vs_one", arena_session_id=offer.arena_session_id)

    assert payload.screen == ArenaScreenEnum.COMBAT_PENDING
    assert payload.metadata["polling"] is True
    assert payload.metadata["awaiting_player_choice"] is False


@pytest.mark.asyncio
async def test_check_combat_ready_starts_pending_polling():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    await service.join_queue(1, "one_vs_one")
    store.requests[1].start_time = time.time() - 50
    first_payload = await service.check_match(1, "one_vs_one")
    await service.accept_shadow(1, "one_vs_one", arena_session_id=first_payload.arena_session_id)

    payload = await service.check_combat_ready(1, arena_session_id=first_payload.arena_session_id)

    assert payload.screen == ArenaScreenEnum.COMBAT_PENDING
    assert payload.metadata["polling"] is True


@pytest.mark.asyncio
async def test_check_combat_ready_enters_ready_shadow_combat():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    service = ArenaService(
        session_service=ArenaSessionService(store),
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

    payload = await service.check_combat_ready(1, arena_session_id=match.arena_session_id)

    assert payload.combat_id == "combat:shadow"
    assert sessions.combat[1] == "combat:shadow"
