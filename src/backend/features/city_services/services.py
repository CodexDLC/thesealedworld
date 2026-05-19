from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.shared.enums import CoreDomain
from src.shared.schemas import ScenarioReturnContextDTO, StateTransitionDTO
from src.shared.schemas.city_services import (
    CityServiceActionEnum,
    CityServiceButtonDTO,
    CityServiceScreenEnum,
    CityServiceSectionDTO,
    CityServiceUIPayloadDTO,
)

if TYPE_CHECKING:
    from src.backend.features.city_services.integrations import CityServiceSystemIntegrator
    from src.backend.features.city_services.models import CharacterTavernRoom
    from src.backend.features.city_services.resources import CityServiceDefinition


class CityService:
    def __init__(self, *, integrator: CityServiceSystemIntegrator) -> None:
        self.integrator = integrator

    async def view(
        self,
        char_id: int,
        *,
        service_id: str | None = None,
        screen: CityServiceScreenEnum | str | None = None,
        section_id: str | None = None,
        location_id: str | None = None,
        tavern_id: str | None = None,
    ) -> CityServiceUIPayloadDTO:
        definition, resolved_location_id = await self.integrator.resolve_service_definition(
            char_id,
            service_id=service_id,
            tavern_id=tavern_id,
            location_id=location_id,
        )
        await self.integrator.enter_city_service(char_id)
        return await self._payload(
            definition=definition,
            char_id=char_id,
            screen=_screen(screen, section_id),
            section_id=section_id,
            location_id=resolved_location_id,
        )

    async def show_screen(
        self,
        char_id: int,
        *,
        service_id: str,
        screen: CityServiceScreenEnum,
        section_id: str | None = None,
        location_id: str | None = None,
        notice: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CityServiceUIPayloadDTO:
        definition, resolved_location_id = await self.integrator.resolve_service_definition(
            char_id,
            service_id=service_id,
            location_id=location_id,
        )
        return await self._payload(
            definition=definition,
            char_id=char_id,
            screen=screen,
            section_id=section_id,
            location_id=resolved_location_id,
            notice=notice,
            metadata=metadata,
        )

    async def start_dialogue(
        self,
        char_id: int,
        *,
        service_id: str,
        section_id: str | None = None,
        location_id: str | None = None,
    ) -> StateTransitionDTO:
        definition, resolved_location_id = await self.integrator.resolve_service_definition(
            char_id,
            service_id=service_id,
            location_id=location_id,
        )
        quest_key = str(definition.metadata.get("dialogue_quest_key") or "")
        if not quest_key:
            raise ValueError(f"City service has no dialogue configured: {service_id}")

        tavern_id = _optional_str(definition.metadata.get("tavern_id"))
        dialogue_section_id = str(section_id or definition.metadata.get("dialogue_section_id") or "bar")
        npc_key = _optional_str(definition.metadata.get("npc_key"))
        return_context = ScenarioReturnContextDTO(
            source_state=CoreDomain.CITY_SERVICES,
            return_state=CoreDomain.CITY_SERVICES,
            return_screen=CityServiceScreenEnum.SECTION.value,
            source_service_id=definition.service_id,
            location_id=resolved_location_id,
            tavern_id=tavern_id,
            npc_key=npc_key,
            metadata={"section_id": dialogue_section_id},
        )
        return StateTransitionDTO(
            char_id=char_id,
            target_state=CoreDomain.SCENARIO,
            reason="city_service_start_dialogue",
            quest_key=quest_key,
            location_id=resolved_location_id,
            context={"return_context": return_context.model_dump(mode="json")},
            metadata={
                "service_id": definition.service_id,
                "service_type": definition.service_type,
                "npc_key": npc_key,
                "location_id": resolved_location_id,
                "section_id": dialogue_section_id,
                "tavern_id": tavern_id,
            },
        )

    async def rest(
        self,
        char_id: int,
        *,
        service_id: str,
        location_id: str | None = None,
    ) -> CityServiceUIPayloadDTO:
        definition, resolved_location_id = await self.integrator.resolve_service_definition(
            char_id,
            service_id=service_id,
            location_id=location_id,
        )
        if definition.service_type != "tavern":
            raise ValueError(f"City service cannot rest: {definition.service_id}")

        tavern_id = str(definition.metadata["tavern_id"])
        room = await self.integrator.get_tavern_room(char_id=char_id, tavern_id=tavern_id)
        if room is None:
            return await self._payload(
                definition=definition,
                char_id=char_id,
                screen=CityServiceScreenEnum.SECTION,
                section_id="room",
                location_id=resolved_location_id,
                notice="Комната еще не закреплена за персонажем.",
                metadata={"room": self._room_payload(definition, None)},
            )

        vitals = await self.integrator.restore_vitals(
            char_id=char_id,
            reason=f"city_services:tavern:{tavern_id}:rest",
        )
        return await self._payload(
            definition=definition,
            char_id=char_id,
            screen=CityServiceScreenEnum.SECTION,
            section_id="room",
            location_id=resolved_location_id,
            notice="Отдых восстановил силы.",
            metadata={"room": self._room_payload(definition, room), "vitals": vitals},
        )

    async def leave(self, char_id: int) -> StateTransitionDTO:
        await self.integrator.leave_city_service(char_id)
        return StateTransitionDTO(
            char_id=char_id,
            target_state=CoreDomain.EXPLORATION,
            reason="city_service_leave",
        )

    async def grant_tavern_room(
        self,
        *,
        char_id: int,
        tavern_id: str,
        room_key: str | None = None,
    ) -> tuple[CharacterTavernRoom, bool]:
        definition, _ = await self.integrator.resolve_service_definition(char_id, tavern_id=tavern_id)
        return await self.integrator.grant_tavern_room(
            char_id=char_id,
            tavern_id=str(definition.metadata["tavern_id"]),
            room_key=room_key or str(definition.metadata["room_key"]),
        )

    async def _payload(
        self,
        *,
        definition: CityServiceDefinition,
        char_id: int,
        screen: CityServiceScreenEnum,
        section_id: str | None,
        location_id: str | None,
        notice: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CityServiceUIPayloadDTO:
        _ = char_id
        section_id = section_id if screen == CityServiceScreenEnum.SECTION else None
        room = None
        if definition.service_type == "tavern":
            room = await self.integrator.get_tavern_room(
                char_id=char_id,
                tavern_id=str(definition.metadata["tavern_id"]),
            )
        service_metadata = dict(metadata or {})
        if definition.metadata.get("npc_key"):
            service_metadata.setdefault("npc_key", definition.metadata.get("npc_key"))
        if isinstance(definition.metadata.get("npc"), dict):
            service_metadata.setdefault("npc", dict(definition.metadata["npc"]))
        if definition.service_type == "tavern" and section_id == "room" and "room" not in service_metadata:
            service_metadata["room"] = self._room_payload(definition, room)
        if definition.service_type == "tavern" and section_id == "bar":
            service_metadata.setdefault(
                "npc",
                {
                    "bartender_key": definition.metadata.get("bartender_key"),
                    "npc_key": definition.metadata.get("npc_key"),
                    "dialogue_quest_key": definition.metadata.get("dialogue_quest_key"),
                },
            )
        if definition.service_type == "tavern" and section_id == "common_hall":
            service_metadata.setdefault("common_hall", {"occupants_count": 0, "group_requests": [], "notices": []})

        return CityServiceUIPayloadDTO(
            service_id=definition.service_id,
            service_type=definition.service_type,
            location_id=location_id,
            screen=screen,
            section_id=section_id,
            title=self._title(definition, section_id),
            description=self._description(definition, section_id, service_metadata),
            background_url=definition.background_url,
            sections=[
                CityServiceSectionDTO(
                    id=section.id,
                    title=section.title,
                    description=section.description,
                    icon=section.icon,
                    metadata=section.metadata,
                )
                for section in definition.sections
            ],
            buttons=self._buttons(definition, section_id, service_metadata),
            notice=notice,
            metadata=service_metadata,
        )

    @staticmethod
    def _title(definition: CityServiceDefinition, section_id: str | None) -> str:
        if section_id:
            for section in definition.sections:
                if section.id == section_id:
                    return section.title
        return definition.title

    @staticmethod
    def _description(definition: CityServiceDefinition, section_id: str | None, metadata: dict[str, Any]) -> str:
        if definition.service_type == "tavern" and section_id == "room":
            room = metadata.get("room") if isinstance(metadata.get("room"), dict) else {}
            if room.get("is_owned"):
                return "Небольшая закрытая комната наверху. Здесь можно восстановить силы."
            return "Комната еще не закреплена. Кормчий может выдать ключ первым прибывшим."
        if section_id:
            for section in definition.sections:
                if section.id == section_id:
                    return section.description
        return definition.description

    @staticmethod
    def _buttons(
        definition: CityServiceDefinition, section_id: str | None, metadata: dict[str, Any]
    ) -> list[CityServiceButtonDTO]:
        if definition.service_type == "portal":
            return [
                CityServiceButtonDTO(
                    label="Войти в портал",
                    action=CityServiceActionEnum.PLACEHOLDER,
                    icon="portal",
                    is_disabled=True,
                ),
                CityServiceButtonDTO(label="Выйти", action=CityServiceActionEnum.LEAVE, icon="back"),
            ]
        buttons = [
            CityServiceButtonDTO(label="Главный зал", action=CityServiceActionEnum.MENU_MAIN, icon="home"),
            *[
                CityServiceButtonDTO(
                    label=section.title,
                    action=CityServiceActionEnum.OPEN_SECTION,
                    icon=section.icon,
                    section_id=section.id,
                )
                for section in definition.sections
            ],
            CityServiceButtonDTO(label="Выйти", action=CityServiceActionEnum.LEAVE, icon="back"),
        ]
        if definition.service_type == "tavern" and section_id == "bar":
            buttons.insert(
                1,
                CityServiceButtonDTO(
                    label="Поговорить с кормчим",
                    action=CityServiceActionEnum.START_DIALOGUE,
                    icon="talk",
                    section_id="bar",
                ),
            )
        if definition.service_type == "tavern" and section_id == "room":
            room = metadata.get("room") if isinstance(metadata.get("room"), dict) else {}
            buttons.insert(
                1,
                CityServiceButtonDTO(
                    label="Отдохнуть",
                    action=CityServiceActionEnum.REST,
                    icon="bed",
                    section_id="room",
                    is_disabled=not bool(room.get("can_rest")),
                ),
            )
        if not definition.sections and len(buttons) == 2:
            buttons.insert(
                1,
                CityServiceButtonDTO(
                    label="В разработке",
                    action=CityServiceActionEnum.PLACEHOLDER,
                    icon="journal",
                    is_disabled=True,
                ),
            )
        return buttons

    @staticmethod
    def _room_payload(definition: CityServiceDefinition, room: CharacterTavernRoom | None) -> dict[str, Any]:
        tavern_id = str(definition.metadata.get("tavern_id") or "")
        if room is None:
            return {
                "tavern_id": tavern_id,
                "room_key": None,
                "status": "unclaimed",
                "is_owned": False,
                "can_rest": False,
            }
        return {
            "tavern_id": tavern_id,
            "room_key": room.room_key,
            "status": room.status,
            "is_owned": True,
            "can_rest": room.status == "active",
        }


def _screen(value: CityServiceScreenEnum | str | None, section_id: str | None) -> CityServiceScreenEnum:
    if isinstance(value, CityServiceScreenEnum):
        return value
    if value:
        return CityServiceScreenEnum(str(value))
    return CityServiceScreenEnum.SECTION if section_id else CityServiceScreenEnum.MAIN


def _optional_str(value: Any) -> str | None:
    return str(value) if value else None
