import pytest

from src.backend.features.arena.gateway import ArenaGateway
from src.shared.enums import CoreDomain
from src.shared.schemas.arena import ArenaActionDTO, ArenaActionEnum, ArenaScreenEnum, ArenaUIPayloadDTO


class FakeArenaService:
    def __init__(self) -> None:
        self.left_char_id: int | None = None

    async def view(self, char_id: int) -> ArenaUIPayloadDTO:
        _ = char_id
        return _payload(ArenaScreenEnum.MAIN_MENU)

    async def show_main_menu(self, char_id: int) -> ArenaUIPayloadDTO:
        _ = char_id
        return _payload(ArenaScreenEnum.MAIN_MENU)

    async def leave(self, char_id: int) -> None:
        self.left_char_id = char_id


class FakeDuelService:
    def __init__(self) -> None:
        self.join_args: tuple[int, int] | None = None

    async def view(self, char_id: int) -> ArenaUIPayloadDTO:
        _ = char_id
        return _payload(ArenaScreenEnum.MODE_MENU)

    async def show_menu(self, char_id: int) -> ArenaUIPayloadDTO:
        _ = char_id
        return _payload(ArenaScreenEnum.MODE_MENU)

    async def join_queue(self, char_id: int, *, wait_limit_sec: int = 60) -> ArenaUIPayloadDTO:
        self.join_args = (char_id, wait_limit_sec)
        return _payload(ArenaScreenEnum.SEARCHING)


class FakeGroupService:
    def __init__(self) -> None:
        self.action_args: tuple[str, int, str | None] | None = None

    async def view(self, char_id: int) -> ArenaUIPayloadDTO:
        _ = char_id
        return _payload(ArenaScreenEnum.MODE_MENU)

    async def handle_action(self, action: str, *, char_id: int, item_id: str | None = None) -> ArenaUIPayloadDTO:
        self.action_args = (action, char_id, item_id)
        return _payload(ArenaScreenEnum.MODE_MENU)


@pytest.mark.asyncio
async def test_gateway_dispatches_duel_action_to_duel_service():
    arena = FakeArenaService()
    duel = FakeDuelService()
    group = FakeGroupService()
    gateway = ArenaGateway(arena=arena, duel=duel, group=group)  # type: ignore[arg-type]

    response = await gateway.handle_duel_action(
        object(), 7, ArenaActionDTO(action=ArenaActionEnum.JOIN_QUEUE, value={"wait_limit_sec": 180})
    )

    assert duel.join_args == (7, 180)
    assert response.header.current_state == CoreDomain.ARENA
    assert response.payload_type == "arena_screen"


@pytest.mark.asyncio
async def test_gateway_rejects_unknown_duel_action_without_service_call():
    gateway = ArenaGateway(
        arena=FakeArenaService(), duel=FakeDuelService(), group=FakeGroupService()
    )  # type: ignore[arg-type]

    response = await gateway.handle_duel_action(object(), 7, ArenaActionDTO(action="missing"))

    assert response.header.error == "Unknown duel action: missing"
    assert response.payload_type == "arena_error"


@pytest.mark.asyncio
async def test_gateway_dispatches_group_action_to_group_service():
    group = FakeGroupService()
    gateway = ArenaGateway(
        arena=FakeArenaService(), duel=FakeDuelService(), group=group
    )  # type: ignore[arg-type]

    response = await gateway.handle_group_action(
        object(), 9, ArenaActionDTO(action="group_pick_team", value={"item_id": "request-3x3"})
    )

    assert group.action_args == ("group_pick_team", 9, "request-3x3")
    assert response.header.current_state == CoreDomain.ARENA


def _payload(screen: ArenaScreenEnum) -> ArenaUIPayloadDTO:
    return ArenaUIPayloadDTO(screen=screen, title="title", description="description", buttons=[])
