import time

import pytest

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaQueueRequestDTO, ArenaRuntimeSessionDTO
from src.backend.features.arena.integrations import ArenaSessionIntegration, ArenaSystemIntegrator
from src.backend.features.arena.services import ArenaDuelService, ArenaGroupService, ArenaService
from src.shared.enums import CoreDomain
from src.shared.schemas.arena import ArenaScreenEnum


class FakeStore:
    def __init__(self) -> None:
        self.requests: dict[int, ArenaQueueRequestDTO] = {}
        self.matches: dict[str, ArenaCombatRequestDTO] = {}
        self.runtime_sessions: dict[str, ArenaRuntimeSessionDTO] = {}
        self.char_matches: dict[int, str] = {}
        self.queue: dict[str, set[int]] = {}
        self.locks: set[tuple[str, int]] = set()

    async def add_to_queue(self, mode: str, request: ArenaQueueRequestDTO, *, mode_size: int = 1) -> None:
        _ = mode_size
        self.requests[request.char_id] = request
        self.queue.setdefault(mode, set()).add(request.char_id)

    async def remove_from_queue(self, mode: str, char_id: int, *, mode_size: int = 1) -> bool:
        _ = mode_size
        values = self.queue.setdefault(mode, set())
        existed = char_id in values
        values.discard(char_id)
        return existed

    async def queue_waiting_count(self, mode: str, *, mode_size: int = 1) -> int:
        _ = mode_size
        return len(self.queue.get(mode, set()))

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

    async def get_candidates(self, mode: str, min_gs: float, max_gs: float, *, mode_size: int = 1) -> list[int]:
        _ = min_gs, max_gs, mode_size
        return sorted(self.queue.get(mode, set()))

    async def claim_opponent(
        self, mode: str, char_id: int, min_gs: float, max_gs: float, *, mode_size: int = 1
    ) -> int | None:
        _ = min_gs, max_gs, mode_size
        for candidate_id in sorted(self.queue.get(mode, set())):
            if candidate_id == char_id or candidate_id not in self.requests:
                continue
            self.queue[mode].discard(candidate_id)
            self.queue[mode].discard(char_id)
            return candidate_id
        return None

    async def acquire_match_lock(self, entity_type: str, entity_id: int, token: str) -> bool:
        _ = token
        lock = (entity_type, entity_id)
        if lock in self.locks:
            return False
        self.locks.add(lock)
        return True

    async def release_match_lock(self, entity_type: str, entity_id: int, token: str) -> None:
        _ = token
        self.locks.discard((entity_type, entity_id))

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
        player_ids = json.loads(data["player_ids"])
        return {
            "status": "ok",
            "commitments": {f"player:{char_id}": f"actor:arena-test:player:{char_id}" for char_id in player_ids},
        }


class FailingSnapshotEvents(FakeEvents):
    async def request(self, event_type, data, timeout=30.0, correlation_id=None):
        self.requests.append((event_type, data, timeout, correlation_id))
        return {"status": "error", "error": "character commitments unavailable"}


class FakeCharacterSessions:
    def __init__(self):
        self.combat = {}
        self.finalization = {}
        self.arena = {}
        self.state = None

    async def get_session(self, char_id):
        return {
            "char_id": char_id,
            "sessions": {
                "arena_id": self.arena.get(char_id),
                "combat_id": self.combat.get(char_id),
                "combat_finalization_id": self.finalization.get(char_id),
            },
        }

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
async def test_group_lobby_updates_arena_runtime_position():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    service = ArenaService(
        session_service=ArenaSessionIntegration(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
    )

    payload = await ArenaGroupService(arena=service).show_lobby(1)

    session = store.runtime_sessions[sessions.arena[1]]
    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert session.screen == ArenaScreenEnum.MODE_MENU
    assert session.mode == "group"


@pytest.mark.asyncio
async def test_join_queue_returns_searching_screen():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)

    payload = await ArenaDuelService(arena=service).join_queue(1)

    assert payload.screen == ArenaScreenEnum.SEARCHING
    assert payload.gs == 100
    assert store.requests[1].mode == "one_vs_one"
    assert store.requests[1].commitment_id.endswith(":player:1")
    assert store.requests[1].wait_limit_sec == 60
    assert payload.metadata["queue_waiting_count"] == 1
    assert payload.metadata["wait_limit_sec"] == 60
    assert events.requests[0][0] == "character.combat_commitments_requested"
    assert events.requests[0][1]["ttl"] == 660


@pytest.mark.asyncio
async def test_join_queue_extends_wait_limit_from_waiting_players_up_to_five_minutes():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    duel = ArenaDuelService(arena=service)

    await duel.join_queue(10)
    second = await duel.join_queue(11)
    await duel.join_queue(12)
    payload = await duel.join_queue(1)

    assert store.requests[11].wait_limit_sec == 180
    assert second.metadata["wait_limit_sec"] == 180
    assert store.requests[1].wait_limit_sec == 300
    assert payload.metadata["wait_limit_sec"] == 300
    assert payload.metadata["queue_waiting_count"] == 4
    assert events.requests[-1][1]["ttl"] == 900


@pytest.mark.asyncio
async def test_join_queue_does_not_queue_without_combat_commitment():
    store = FakeStore()
    events = FailingSnapshotEvents()
    service = build_service(store, events)

    payload = await ArenaDuelService(arena=service).join_queue(1)

    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert payload.metadata["commitment_status"] == "failed"
    assert store.requests == {}


@pytest.mark.asyncio
async def test_group_mode_menu_returns_mock_lobby_contract():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)

    payload = await ArenaGroupService(arena=service).get_lobby()

    lobby = payload.metadata["group_lobby"]
    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert lobby["primary_actions"][0]["action"] == "group_ranked"
    assert [tab["id"] for tab in lobby["tabs"]] == ["current", "chaos", "requests"]


@pytest.mark.asyncio
async def test_group_action_returns_mock_action_notice():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)

    payload = await ArenaGroupService(arena=service).handle_action(
        "group_pick_team",
        char_id=1,
        item_id="mock-request-3x3",
    )

    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert payload.metadata["group_action"]["title"] == "Выбор команды"
    assert payload.metadata["group_action"]["item_id"] == "mock-request-3x3"


@pytest.mark.asyncio
async def test_check_match_creates_pvp_combat_request():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    duel = ArenaDuelService(arena=service)
    await duel.join_queue(1)
    await duel.join_queue(2)

    payload = await duel.check_match(1)

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
    duel = ArenaDuelService(arena=service)
    await duel.join_queue(1)
    await store.acquire_match_lock("match", 1, "already-running")

    payload = await duel.check_match(1)

    assert payload.screen == ArenaScreenEnum.SEARCHING
    assert payload.metadata["match_lock"] == "busy"
    assert events.published == []


@pytest.mark.asyncio
async def test_check_match_timeout_returns_mode_menu_without_shadow_request():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    duel = ArenaDuelService(arena=service)
    await duel.join_queue(1)
    store.requests[1].start_time = time.time() - 70

    payload = await duel.check_match(1)

    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert payload.title == "Противник не найден"
    assert events.published == []
    assert 1 not in store.queue["one_vs_one"]


@pytest.mark.asyncio
async def test_continue_search_discards_shadow_offer_and_requeues():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)
    duel = ArenaDuelService(arena=service)
    offer = await duel.start_shadow(1)

    payload = await duel.continue_search(1, arena_session_id=offer.arena_session_id)

    assert payload.screen == ArenaScreenEnum.SEARCHING
    assert offer.arena_session_id not in store.matches
    assert store.char_matches == {}
    assert 1 in store.queue["one_vs_one"]


@pytest.mark.asyncio
async def test_start_shadow_prepares_combat_without_linking_player_state():
    store = FakeStore()
    events = FakeEvents()
    service = build_service(store, events)

    payload = await ArenaDuelService(arena=service).start_shadow(1)

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
    duel = ArenaDuelService(arena=service)
    first_payload = await duel.start_shadow(1)

    payload = await duel.check_combat_ready(1, arena_session_id=first_payload.arena_session_id)

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

    payload = await ArenaDuelService(arena=service).check_combat_ready(1, arena_session_id=match.arena_session_id)

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

    payload = await ArenaDuelService(arena=service).check_combat_ready(
        1,
        arena_session_id=match.arena_session_id,
        confirm=True,
    )

    assert payload.combat_id == "combat:shadow"
    assert sessions.combat[1] == "combat:shadow"


@pytest.mark.asyncio
async def test_view_clears_entered_shadow_match_after_combat_return():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    service = ArenaService(
        session_service=ArenaSessionIntegration(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
    )
    runtime = await service.ensure_runtime_session(1)
    match = ArenaCombatRequestDTO(
        mode="one_vs_one",
        battle_type="shadow",
        requested_by=1,
        participants={"team_1": [1], "team_2": []},
        status="ready",
        combat_id="combat:shadow",
    )
    await store.create_match(match)
    await service.session.set_runtime_screen(
        runtime,
        ArenaScreenEnum.COMBAT_PENDING,
        mode="one_vs_one",
        active_match_id=match.arena_session_id,
        combat_id=match.combat_id,
        metadata={"battle_type": "shadow", "entered_combat": True},
    )

    payload = await service.view(1)

    assert payload.screen == ArenaScreenEnum.MODE_MENU
    assert payload.title != "Бой готов"
    assert payload.title != "Арена готова"
    assert match.arena_session_id not in store.matches
    assert store.char_matches == {}
    assert store.runtime_sessions[runtime.arena_id].active_match_id is None
    assert store.runtime_sessions[runtime.arena_id].combat_id is None


@pytest.mark.asyncio
async def test_view_keeps_entered_shadow_match_while_combat_is_active():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    sessions.combat[1] = "combat:shadow"
    service = ArenaService(
        session_service=ArenaSessionIntegration(store),
        integrator=ArenaSystemIntegrator(events=events, character_sessions=sessions),
    )
    runtime = await service.ensure_runtime_session(1)
    match = ArenaCombatRequestDTO(
        mode="one_vs_one",
        battle_type="shadow",
        requested_by=1,
        participants={"team_1": [1], "team_2": []},
        status="ready",
        combat_id="combat:shadow",
    )
    await store.create_match(match)
    await service.session.set_runtime_screen(
        runtime,
        ArenaScreenEnum.COMBAT_PENDING,
        mode="one_vs_one",
        active_match_id=match.arena_session_id,
        combat_id=match.combat_id,
        metadata={"battle_type": "shadow", "entered_combat": True},
    )

    payload = await service.view(1)

    assert payload.screen == ArenaScreenEnum.COMBAT_PENDING
    assert payload.title == "Арена готова"
    assert match.arena_session_id in store.matches
