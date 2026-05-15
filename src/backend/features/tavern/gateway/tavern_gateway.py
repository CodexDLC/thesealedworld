from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from src.backend.features.tavern.gateway.responses import tavern_error, tavern_response, tavern_transition
from src.shared.schemas import CoreResponseDTO
from src.shared.schemas.tavern import TavernActionDTO, TavernActionEnum, TavernScreenEnum, TavernUIPayloadDTO

if TYPE_CHECKING:
    from src.backend.core.auth import User
    from src.backend.features.tavern.services import TavernService

ActionHandler = Callable[[int, TavernActionDTO], Awaitable[CoreResponseDTO[Any]]]


class TavernGateway:
    def __init__(self, *, tavern: TavernService) -> None:
        self.tavern = tavern
        self._actions: dict[str, ActionHandler] = {
            TavernActionEnum.MENU_MAIN.value: self._main,
            TavernActionEnum.GO_BAR.value: self._bar,
            TavernActionEnum.GO_ROOMS.value: self._room,
            TavernActionEnum.GO_COMMON_HALL.value: self._common_hall,
            TavernActionEnum.TALK_BARTENDER.value: self._talk_bartender,
            TavernActionEnum.REST.value: self._rest,
            TavernActionEnum.LEAVE.value: self._leave,
        }

    async def get_tavern_view(
        self,
        user: User,
        char_id: int,
        *,
        screen: str | None = None,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
    ) -> CoreResponseDTO[Any]:
        _ = user
        try:
            payload = await self.tavern.view(
                char_id,
                screen=screen,
                tavern_id=tavern_id,
                service_id=service_id,
                location_id=location_id,
            )
            return tavern_response(payload)
        except ValueError as exc:
            return tavern_error(str(exc))

    async def handle_tavern_action(self, user: User, char_id: int, body: TavernActionDTO) -> CoreResponseDTO[Any]:
        _ = user
        handler = self._actions.get(str(body.action))
        if handler is None:
            return tavern_error(f"Unknown tavern action: {body.action}")
        try:
            return await handler(char_id, body)
        except ValueError as exc:
            return tavern_error(str(exc))

    async def _main(self, char_id: int, body: TavernActionDTO) -> CoreResponseDTO[Any]:
        return tavern_response(await self._show(char_id, body, TavernScreenEnum.MAIN))

    async def _bar(self, char_id: int, body: TavernActionDTO) -> CoreResponseDTO[Any]:
        return tavern_response(await self._show(char_id, body, TavernScreenEnum.BAR))

    async def _room(self, char_id: int, body: TavernActionDTO) -> CoreResponseDTO[Any]:
        return tavern_response(await self._show(char_id, body, TavernScreenEnum.ROOM))

    async def _common_hall(self, char_id: int, body: TavernActionDTO) -> CoreResponseDTO[Any]:
        return tavern_response(await self._show(char_id, body, TavernScreenEnum.COMMON_HALL))

    async def _talk_bartender(self, char_id: int, body: TavernActionDTO) -> CoreResponseDTO[Any]:
        transition = await self.tavern.bartender_transition(
            char_id,
            tavern_id=body.tavern_id,
            service_id=body.service_id,
            location_id=body.location_id,
        )
        return tavern_transition(transition)

    async def _rest(self, char_id: int, body: TavernActionDTO) -> CoreResponseDTO[Any]:
        payload = await self.tavern.rest(
            char_id,
            tavern_id=body.tavern_id,
            service_id=body.service_id,
            location_id=body.location_id,
        )
        return tavern_response(payload)

    async def _leave(self, char_id: int, body: TavernActionDTO) -> CoreResponseDTO[Any]:
        _ = body
        return tavern_transition(await self.tavern.leave(char_id))

    async def _show(self, char_id: int, body: TavernActionDTO, screen: TavernScreenEnum) -> TavernUIPayloadDTO:
        return await self.tavern.show_screen(
            char_id,
            screen=screen,
            tavern_id=body.tavern_id,
            service_id=body.service_id,
            location_id=body.location_id,
        )
