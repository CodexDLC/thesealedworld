from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from src.backend.features.city_services.gateway.responses import (
    city_service_error,
    city_service_response,
    city_service_transition,
)
from src.shared.schemas import CoreResponseDTO
from src.shared.schemas.city_services import CityServiceActionDTO, CityServiceActionEnum, CityServiceScreenEnum

if TYPE_CHECKING:
    from src.backend.core.auth import User
    from src.backend.features.city_services.services import CityService

ActionHandler = Callable[[int, CityServiceActionDTO], Awaitable[CoreResponseDTO[Any]]]


class CityServiceGateway:
    def __init__(self, *, service: CityService) -> None:
        self.service = service
        self._actions: dict[str, ActionHandler] = {
            CityServiceActionEnum.MENU_MAIN.value: self._main,
            CityServiceActionEnum.OPEN_SECTION.value: self._section,
            CityServiceActionEnum.START_DIALOGUE.value: self._start_dialogue,
            CityServiceActionEnum.REST.value: self._rest,
            CityServiceActionEnum.LEAVE.value: self._leave,
            CityServiceActionEnum.PLACEHOLDER.value: self._placeholder,
        }

    async def get_view(
        self,
        user: User,
        char_id: int,
        *,
        service_id: str | None = None,
        screen: str | None = None,
        section_id: str | None = None,
        location_id: str | None = None,
        tavern_id: str | None = None,
    ) -> CoreResponseDTO[Any]:
        _ = user
        try:
            payload = await self.service.view(
                char_id,
                service_id=service_id,
                screen=screen,
                section_id=section_id,
                location_id=location_id,
                tavern_id=tavern_id,
            )
            return city_service_response(payload)
        except ValueError as exc:
            return city_service_error(str(exc))

    async def handle_action(self, user: User, char_id: int, body: CityServiceActionDTO) -> CoreResponseDTO[Any]:
        _ = user
        handler = self._actions.get(str(body.action))
        if handler is None:
            return city_service_error(f"Unknown city service action: {body.action}")
        try:
            return await handler(char_id, body)
        except ValueError as exc:
            return city_service_error(str(exc))

    async def _main(self, char_id: int, body: CityServiceActionDTO) -> CoreResponseDTO[Any]:
        return city_service_response(
            await self.service.show_screen(
                char_id,
                service_id=body.service_id,
                screen=CityServiceScreenEnum.MAIN,
                location_id=body.location_id,
            )
        )

    async def _section(self, char_id: int, body: CityServiceActionDTO) -> CoreResponseDTO[Any]:
        return city_service_response(
            await self.service.show_screen(
                char_id,
                service_id=body.service_id,
                screen=CityServiceScreenEnum.SECTION,
                section_id=body.section_id,
                location_id=body.location_id,
            )
        )

    async def _start_dialogue(self, char_id: int, body: CityServiceActionDTO) -> CoreResponseDTO[Any]:
        transition = await self.service.start_dialogue(
            char_id,
            service_id=body.service_id,
            section_id=body.section_id,
            location_id=body.location_id,
        )
        return city_service_transition(transition)

    async def _rest(self, char_id: int, body: CityServiceActionDTO) -> CoreResponseDTO[Any]:
        payload = await self.service.rest(
            char_id,
            service_id=body.service_id,
            location_id=body.location_id,
        )
        return city_service_response(payload)

    async def _leave(self, char_id: int, body: CityServiceActionDTO) -> CoreResponseDTO[Any]:
        _ = body
        return city_service_transition(await self.service.leave(char_id))

    async def _placeholder(self, char_id: int, body: CityServiceActionDTO) -> CoreResponseDTO[Any]:
        return city_service_response(
            await self.service.show_screen(
                char_id,
                service_id=body.service_id,
                screen=body.screen or CityServiceScreenEnum.MAIN,
                section_id=body.section_id,
                location_id=body.location_id,
                notice="Этот раздел еще обустраивается.",
            )
        )
