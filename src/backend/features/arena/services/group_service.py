from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.arena.resources import ArenaResources
from src.shared.schemas.arena import ArenaModeEnum, ArenaScreenEnum, ArenaUIPayloadDTO

if TYPE_CHECKING:
    from src.backend.features.arena.services.arena_service import ArenaService

GROUP_MODE = ArenaModeEnum.GROUP.value


class ArenaGroupService:
    def __init__(self, *, arena: ArenaService) -> None:
        self.arena = arena
        self.session = arena.session

    async def view(self, char_id: int) -> ArenaUIPayloadDTO:
        return await self.show_lobby(char_id)

    async def show_lobby(self, char_id: int) -> ArenaUIPayloadDTO:
        runtime_session = await self.arena.ensure_runtime_session(char_id)
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.MODE_MENU,
            mode=GROUP_MODE,
            active_match_id="",
            combat_id="",
            metadata={"group_lobby_open": True},
        )
        return await self.get_lobby()

    async def get_lobby(self) -> ArenaUIPayloadDTO:
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MODE_MENU,
            mode=GROUP_MODE,
            title=ArenaResources.get_mode_title(GROUP_MODE),
            description=ArenaResources.get_mode_description(GROUP_MODE),
            buttons=ArenaResources.get_mode_buttons(GROUP_MODE),
            metadata={"group_lobby": ArenaResources.get_group_lobby_mock()},
        )

    async def handle_action(self, action: str, *, char_id: int, item_id: str | None = None) -> ArenaUIPayloadDTO:
        runtime_session = await self.arena.ensure_runtime_session(char_id)
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.MODE_MENU,
            mode=GROUP_MODE,
            metadata={"group_action": action, "group_item_id": item_id or ""},
        )
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MODE_MENU,
            mode=GROUP_MODE,
            title=ArenaResources.get_mode_title(GROUP_MODE),
            description=ArenaResources.get_mode_description(GROUP_MODE),
            buttons=ArenaResources.get_mode_buttons(GROUP_MODE),
            metadata={
                "group_lobby": ArenaResources.get_group_lobby_mock(),
                "group_action": ArenaResources.get_group_action_mock(action, item_id),
            },
        )
