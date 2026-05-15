from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.shared.enums import CoreDomain
from src.shared.schemas import ScenarioReturnContextDTO, StateTransitionDTO
from src.shared.schemas.tavern import (
    TavernActionEnum,
    TavernBarDTO,
    TavernButtonDTO,
    TavernCommonHallDTO,
    TavernRoomDTO,
    TavernScreenEnum,
    TavernUIPayloadDTO,
)

if TYPE_CHECKING:
    from src.backend.features.tavern.integrations import TavernSystemIntegrator
    from src.backend.features.tavern.models import CharacterTavernRoom
    from src.backend.features.tavern.resources import TavernConfig


class TavernService:
    def __init__(self, *, integrator: TavernSystemIntegrator) -> None:
        self.integrator = integrator

    async def view(
        self,
        char_id: int,
        *,
        screen: TavernScreenEnum | str | None = None,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
    ) -> TavernUIPayloadDTO:
        config, resolved_location_id = await self.integrator.resolve_tavern_config(
            char_id,
            tavern_id=tavern_id,
            service_id=service_id,
            location_id=location_id,
        )
        await self.integrator.enter_tavern(char_id)
        room = await self.integrator.get_room(char_id=char_id, tavern_id=config.tavern_id)
        return self._payload(
            config=config,
            char_id=char_id,
            screen=_screen(screen),
            location_id=resolved_location_id,
            room=room,
        )

    async def show_screen(
        self,
        char_id: int,
        *,
        screen: TavernScreenEnum,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
        notice: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TavernUIPayloadDTO:
        config, resolved_location_id = await self.integrator.resolve_tavern_config(
            char_id,
            tavern_id=tavern_id,
            service_id=service_id,
            location_id=location_id,
        )
        room = await self.integrator.get_room(char_id=char_id, tavern_id=config.tavern_id)
        return self._payload(
            config=config,
            char_id=char_id,
            screen=screen,
            location_id=resolved_location_id,
            room=room,
            notice=notice,
            metadata=metadata,
        )

    async def rest(
        self,
        char_id: int,
        *,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
    ) -> TavernUIPayloadDTO:
        config, resolved_location_id = await self.integrator.resolve_tavern_config(
            char_id,
            tavern_id=tavern_id,
            service_id=service_id,
            location_id=location_id,
        )
        room = await self.integrator.get_room(char_id=char_id, tavern_id=config.tavern_id)
        if room is None:
            return self._payload(
                config=config,
                char_id=char_id,
                screen=TavernScreenEnum.ROOM,
                location_id=resolved_location_id,
                room=None,
                notice="Комната еще не закреплена за персонажем.",
            )

        vitals = await self.integrator.restore_vitals(char_id=char_id, reason=f"tavern:{config.tavern_id}:rest")
        return self._payload(
            config=config,
            char_id=char_id,
            screen=TavernScreenEnum.ROOM,
            location_id=resolved_location_id,
            room=room,
            notice="Отдых восстановил силы.",
            metadata={"vitals": vitals},
        )

    async def leave(self, char_id: int) -> StateTransitionDTO:
        await self.integrator.leave_tavern(char_id)
        return StateTransitionDTO(
            char_id=char_id,
            target_state=CoreDomain.EXPLORATION,
            reason="tavern_leave",
        )

    async def bartender_transition(
        self,
        char_id: int,
        *,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
    ) -> StateTransitionDTO:
        config, resolved_location_id = await self.integrator.resolve_tavern_config(
            char_id,
            tavern_id=tavern_id,
            service_id=service_id,
            location_id=location_id,
        )
        return_context = ScenarioReturnContextDTO(
            source_state=CoreDomain.TAVERN,
            return_state=CoreDomain.TAVERN,
            return_screen=TavernScreenEnum.BAR.value,
            source_service_id=service_id or config.service_id,
            location_id=resolved_location_id,
            tavern_id=config.tavern_id,
        )
        return StateTransitionDTO(
            char_id=char_id,
            target_state=CoreDomain.SCENARIO,
            reason="tavern_talk_bartender",
            quest_key=config.dialogue_quest_key,
            location_id=resolved_location_id,
            context={"return_context": return_context.model_dump(mode="json")},
            metadata={
                "tavern_id": config.tavern_id,
                "service_id": service_id or config.service_id,
                "location_id": resolved_location_id,
            },
        )

    async def grant_room(
        self,
        *,
        char_id: int,
        tavern_id: str,
        room_key: str | None = None,
    ) -> tuple[CharacterTavernRoom, bool]:
        config, _ = await self.integrator.resolve_tavern_config(char_id, tavern_id=tavern_id)
        return await self.integrator.grant_room(
            char_id=char_id,
            tavern_id=config.tavern_id,
            room_key=room_key or config.room_key,
        )

    def _payload(
        self,
        *,
        config: TavernConfig,
        char_id: int,
        screen: TavernScreenEnum,
        location_id: str | None,
        room: CharacterTavernRoom | None,
        notice: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TavernUIPayloadDTO:
        _ = char_id
        room_payload = self._room_payload(config, room)
        return TavernUIPayloadDTO(
            tavern_id=config.tavern_id,
            service_id=config.service_id,
            location_id=location_id,
            screen=screen,
            title=self._title(config, screen),
            description=self._description(config, screen, room_payload),
            buttons=self._buttons(screen, room_payload),
            bar=TavernBarDTO(
                bartender_key=config.bartender_key,
                dialogue_quest_key=config.dialogue_quest_key,
            )
            if screen == TavernScreenEnum.BAR
            else None,
            room=room_payload if screen == TavernScreenEnum.ROOM else None,
            common_hall=TavernCommonHallDTO() if screen == TavernScreenEnum.COMMON_HALL else None,
            notice=notice,
            metadata=metadata or {},
        )

    @staticmethod
    def _room_payload(config: TavernConfig, room: CharacterTavernRoom | None) -> TavernRoomDTO:
        if room is None:
            return TavernRoomDTO(tavern_id=config.tavern_id)
        return TavernRoomDTO(
            tavern_id=config.tavern_id,
            room_key=room.room_key,
            status=room.status,
            is_owned=True,
            can_rest=room.status == "active",
        )

    @staticmethod
    def _title(config: TavernConfig, screen: TavernScreenEnum) -> str:
        if screen == TavernScreenEnum.BAR:
            return "Барная стойка"
        if screen == TavernScreenEnum.ROOM:
            return "Личная комната"
        if screen == TavernScreenEnum.COMMON_HALL:
            return "Общий зал"
        return config.title

    @staticmethod
    def _description(config: TavernConfig, screen: TavernScreenEnum, room: TavernRoomDTO) -> str:
        if screen == TavernScreenEnum.BAR:
            return "За стойкой держат первые слухи, ключи и простые договоренности."
        if screen == TavernScreenEnum.ROOM:
            if room.is_owned:
                return "Небольшая закрытая комната наверху. Здесь можно восстановить силы."
            return "Комната еще не закреплена. Бармен может выдать ключ первым прибывшим."
        if screen == TavernScreenEnum.COMMON_HALL:
            return "Свободные столы ждут заявок групп, объявлений и местной активности."
        return config.description

    @staticmethod
    def _buttons(screen: TavernScreenEnum, room: TavernRoomDTO) -> list[TavernButtonDTO]:
        base = [
            TavernButtonDTO(label="Главный зал", action=TavernActionEnum.MENU_MAIN, icon="home"),
            TavernButtonDTO(label="Барная стойка", action=TavernActionEnum.GO_BAR, icon="talk"),
            TavernButtonDTO(label="Комната", action=TavernActionEnum.GO_ROOMS, icon="bed"),
            TavernButtonDTO(label="Общий зал", action=TavernActionEnum.GO_COMMON_HALL, icon="users"),
            TavernButtonDTO(label="Выйти", action=TavernActionEnum.LEAVE, icon="back"),
        ]
        if screen == TavernScreenEnum.BAR:
            base.insert(
                1,
                TavernButtonDTO(
                    label="Поговорить с барменом",
                    action=TavernActionEnum.TALK_BARTENDER,
                    icon="talk",
                ),
            )
        if screen == TavernScreenEnum.ROOM:
            base.insert(
                1,
                TavernButtonDTO(
                    label="Отдохнуть",
                    action=TavernActionEnum.REST,
                    icon="bed",
                    is_disabled=not room.can_rest,
                ),
            )
        return base


def _screen(value: TavernScreenEnum | str | None) -> TavernScreenEnum:
    if isinstance(value, TavernScreenEnum):
        return value
    if value:
        return TavernScreenEnum(str(value))
    return TavernScreenEnum.MAIN
