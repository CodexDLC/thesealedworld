from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from src.backend.features.exploration.dto.result import ExplorationTransition
from src.backend.features.exploration.resources.service_registry import get_service_entry
from src.shared.enums import CoreDomain
from src.shared.schemas.exploration import (
    AlertHudDTO,
    EncounterDTO,
    ExplorationListDTO,
    ExplorationLocalMapDTO,
    ExplorationScreenContentDTO,
    ExplorationScreenContextDTO,
    ExplorationScreenDTO,
    WorldNavigationDTO,
)
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader, StateTransitionDTO

log = logging.getLogger(__name__)

ExplorationPayload = ExplorationScreenDTO | StateTransitionDTO

if TYPE_CHECKING:
    from src.backend.features.exploration.services.encounter_service import ExplorationEncounterService
    from src.backend.features.exploration.services.navigation_service import ExplorationNavigationService


class ExplorationGateway:
    """High-level exploration facade for API routes."""

    def __init__(
        self,
        *,
        navigation: ExplorationNavigationService,
        encounters: ExplorationEncounterService,
    ) -> None:
        self._navigation = navigation
        self._encounters = encounters

    async def move(
        self,
        char_id: int,
        direction: str | None = None,
        target_id: str | None = None,
    ) -> CoreResponseDTO[ExplorationPayload]:
        active = await self._encounters.active_payload(char_id)
        if active is not None:
            return await self._screen_response(char_id, active, content_kind="encounter")

        resolution = await self._navigation.resolve_move(char_id, direction=direction, target_id=target_id)
        if not resolution.allowed or resolution.target_loc_id is None or resolution.target_loc_data is None:
            alert = AlertHudDTO(message=resolution.message or "Переход недоступен.", style="warning")
            navigation = await self._navigation.build_navigation(
                char_id,
                resolution.current_loc_id,
                resolution.current_loc_data,
                alert=alert,
            )
            return await self._screen_response(char_id, navigation, content_kind="navigation")

        encounter = await self._encounters.roll_travel(
            char_id=char_id,
            loc_id=resolution.target_loc_id,
            loc_data=resolution.target_loc_data,
        )
        await self._navigation.move_player(char_id, resolution)
        if encounter is not None:
            encounter = await self._navigation.attach_navigation_snapshot(
                char_id,
                resolution.target_loc_id,
                resolution.target_loc_data,
                encounter,
            )
            await self._encounters.persist(char_id, encounter)
            return await self._screen_response(char_id, encounter, content_kind="encounter")

        navigation = await self._navigation.build_navigation(
            char_id,
            resolution.target_loc_id,
            resolution.target_loc_data,
        )
        return await self._screen_response(char_id, navigation, content_kind="navigation")

    async def look_around(self, char_id: int) -> CoreResponseDTO[ExplorationPayload]:
        active = await self._encounters.active_payload(char_id)
        if active is not None:
            return await self._screen_response(char_id, active, content_kind="encounter")
        navigation = await self._navigation.build_current_navigation(char_id)
        return await self._screen_response(char_id, navigation, content_kind="navigation")

    async def local_map(self, char_id: int, *, radius: int = 2) -> ExplorationLocalMapDTO:
        return await self._navigation.build_local_map(char_id, radius=radius)

    async def interact(
        self,
        char_id: int,
        action: str,
        target_id: str | None = None,
    ) -> CoreResponseDTO[ExplorationPayload]:
        del target_id
        active = await self._encounters.active_payload(char_id)
        if action == "attack" and active is not None:
            result = await self._encounters.attack(char_id, active)
            if isinstance(result, ExplorationTransition):
                return self._transition_response(result)
            return await self._screen_response(char_id, result, content_kind="encounter")
        if action == "bypass" and active is not None:
            bypassed, encounter, _chance_percent = await self._encounters.attempt_bypass(char_id, active)
            if not bypassed and encounter is not None:
                result = await self._encounters.attack(char_id, encounter)
                if isinstance(result, ExplorationTransition):
                    return self._transition_response(result)
                return await self._screen_response(char_id, encounter, content_kind="encounter")
            navigation = await self._navigation.build_current_navigation(
                char_id,
                alert=AlertHudDTO(message="Опасность миновала. Вы решили обойти угрозу.", style="info"),
            )
            return await self._screen_response(char_id, navigation, content_kind="navigation")
        if action == "continue" and active is not None:
            await self._encounters.continue_from_placeholder(char_id, active)
            navigation = await self._navigation.build_current_navigation(char_id)
            return await self._screen_response(char_id, navigation, content_kind="navigation")
        if active is not None:
            return await self._screen_response(char_id, active, content_kind="encounter")

        if action == "search":
            loc_id = await self._navigation.current_loc_id(char_id)
            loc_data = await self._navigation.location_data(loc_id)
            encounter = await self._encounters.roll_scouting(char_id=char_id, loc_id=loc_id, loc_data=loc_data)
            if encounter is not None:
                encounter = await self._navigation.attach_navigation_snapshot(char_id, loc_id, loc_data, encounter)
                await self._encounters.persist(char_id, encounter)
                return await self._screen_response(char_id, encounter, content_kind="encounter")
            navigation = await self._navigation.build_navigation(
                char_id,
                loc_id,
                loc_data,
                alert=AlertHudDTO(message="Вы ничего не нашли.", style="info"),
            )
            return await self._screen_response(char_id, navigation, content_kind="navigation")

        if action == "battles":
            navigation = await self._navigation.build_current_navigation(
                char_id,
                alert=AlertHudDTO(message="В локации тихо. Боев не обнаружено.", style="info"),
            )
            return await self._screen_response(char_id, navigation, content_kind="navigation")

        return await self.look_around(char_id)

    async def use_service(self, char_id: int, service_id: str) -> CoreResponseDTO[ExplorationPayload]:
        active = await self._encounters.active_payload(char_id)
        if active is not None:
            return await self._screen_response(char_id, active, content_kind="encounter")

        loc_id = await self._navigation.current_loc_id(char_id)
        loc_data = await self._navigation.location_data(loc_id)
        if not self._service_allowed_in_location(loc_data, service_id):
            navigation = await self._navigation.build_navigation(
                char_id,
                loc_id,
                loc_data,
                alert=AlertHudDTO(message="Сервис недоступен из этой локации.", style="danger"),
            )
            return await self._screen_response(char_id, navigation, content_kind="navigation")
        entry = get_service_entry(service_id)
        if entry is None:
            navigation = await self._navigation.build_navigation(
                char_id,
                loc_id,
                loc_data,
                alert=AlertHudDTO(message="Сервис пока не подключен.", style="info"),
            )
            return await self._screen_response(char_id, navigation, content_kind="navigation")
        transition = ExplorationTransition(
            char_id=char_id,
            target_state=entry.target_state,
            reason="exploration_service_entry",
            metadata={
                "service_id": service_id,
                "location_id": loc_id,
                "label": entry.label,
                **entry.metadata,
            },
        )
        return self._transition_response(transition)

    async def _screen_response(
        self,
        char_id: int,
        content: WorldNavigationDTO | EncounterDTO | ExplorationListDTO,
        *,
        content_kind: str,
    ) -> CoreResponseDTO[ExplorationPayload]:
        context_source = content
        if isinstance(content, EncounterDTO) and isinstance(content.metadata.get("navigation"), dict):
            context_source = WorldNavigationDTO.model_validate(content.metadata["navigation"])
        elif not isinstance(content, WorldNavigationDTO):
            context_source = await self._navigation.build_current_navigation(char_id)

        context = self._screen_context(cast("WorldNavigationDTO", context_source))
        payload = ExplorationScreenDTO(
            context=context,
            content=ExplorationScreenContentDTO(kind=content_kind, data=content),
        )
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.EXPLORATION),
            payload=payload,
            payload_type=f"exploration_{content_kind}",
        )

    @staticmethod
    def _transition_response(transition: ExplorationTransition) -> CoreResponseDTO[ExplorationPayload]:
        payload = StateTransitionDTO(
            char_id=transition.char_id,
            target_state=transition.target_state,
            reason=transition.reason,
            combat_id=transition.combat_id,
            location_id=str((transition.metadata or {}).get("location_id") or "") or None,
            metadata=transition.metadata or {},
        )
        return CoreResponseDTO(
            header=GameStateHeader(current_state=transition.target_state, previous_state=CoreDomain.EXPLORATION),
            payload=payload,
            payload_type="state_transition",
        )

    @staticmethod
    def _screen_context(source: WorldNavigationDTO) -> ExplorationScreenContextDTO:
        return ExplorationScreenContextDTO(
            loc_id=source.loc_id,
            title=source.title,
            description=source.description,
            background_url=source.background_url,
            anchor_influence=source.anchor_influence,
            world_theme=source.world_theme,
            hud=source.hud,
            threat_tier=source.threat_tier,
            is_safe_zone=source.is_safe_zone,
            city_map=source.city_map,
            metadata=source.metadata,
        )

    @staticmethod
    def _service_allowed_in_location(loc_data: dict[str, Any], service_id: str) -> bool:
        services = loc_data.get("services")
        if isinstance(services, list) and service_id in {str(item) for item in services}:
            return True
        exits = loc_data.get("exits", {})
        if not isinstance(exits, dict):
            return False
        return f"svc:{service_id}" in exits or service_id in exits
