# src/backend/features/exploration/services/exploration_service.py
import logging

from src.backend.features.exploration.dto.config import ExplorationConfig
from src.backend.features.exploration.integrations.system_integrator import ExplorationSystemIntegrator
from src.backend.features.exploration.resources.service_registry import get_service_entry
from src.backend.features.exploration.runtime.encounter import EncounterEngine
from src.backend.features.exploration.runtime.navigation import NavigationEngine
from src.shared.enums.domain import CoreDomain
from src.shared.schemas.exploration import (
    AlertHudDTO,
    EncounterDTO,
    ExplorationHudDTO,
    ExplorationListDTO,
    ListItemDTO,
    WorldNavigationDTO,
)
from src.shared.schemas.response import ServiceResult
from src.shared.schemas.world_theme import WorldThemeDTO

log = logging.getLogger(__name__)


class ExplorationService:
    """
    Основной сервис домена Exploration.
    Координирует перемещение, генерацию событий и сборку UI.
    """

    def __init__(
        self,
        integrator: ExplorationSystemIntegrator,
        encounter_engine: EncounterEngine,
    ):
        self._integrator = integrator
        self._encounter_engine = encounter_engine

    # =========================================================================
    # CORE ACTIONS
    # =========================================================================

    async def move(
        self, char_id: int, direction: str | None = None, target_id: str | None = None
    ) -> WorldNavigationDTO | EncounterDTO:
        """
        Попытка перемещения.
        Принимает либо direction (legacy n, s, w, e), либо target_id (52_51).
        """
        current_loc_id = await self._integrator.get_player_location_id(char_id)
        if not current_loc_id:
            current_loc_id = ExplorationConfig.DEFAULT_SPAWN_POINT

        loc_data = await self._integrator.get_location_data(current_loc_id)

        if not loc_data:
            log.error("ExplorationService | loc_not_found char_id=%s loc=%s", char_id, current_loc_id)
            return await self._build_navigation_dto(char_id, current_loc_id, {})

        exits = loc_data.get("exits", {})
        target_loc_id = None

        # 1. Resolve Target ID
        if target_id:
            # Check if exit exists
            if f"nav:{target_id}" in exits or target_id in exits:
                target_loc_id = target_id
        elif direction:
            # Legacy direction resolve could be implemented here if needed
            pass

        if not target_loc_id:
            log.warning("ExplorationService | invalid_move char_id=%s target=%s dir=%s", char_id, target_id, direction)
            return await self._build_navigation_dto(char_id, current_loc_id, loc_data)

        # 2. Encounter Check (before moving)
        target_loc_data = await self._integrator.get_location_data(target_loc_id)
        if target_loc_data:
            skills = await self._integrator.get_actor_skills(char_id)
            scouting = skills.get("survival", 0.0)

            encounter = await self._encounter_engine.try_generate_encounter(
                char_id=char_id,
                location_data=target_loc_data,
                scouting_skill=scouting,
                trigger="move",
                loc_id=target_loc_id,
            )

            if encounter:
                # Still move the player to the target location where encounter happens
                await self._integrator.move_player(char_id, current_loc_id, target_loc_id)
                return encounter

        # 3. Finalize Move
        await self._integrator.move_player(char_id, current_loc_id, target_loc_id)
        return await self.look_around(char_id)

    async def look_around(self, char_id: int) -> WorldNavigationDTO:
        """
        Обновление данных текущей локации (без движения).
        """
        loc_id = await self._integrator.get_player_location_id(char_id)
        if not loc_id:
            loc_id = ExplorationConfig.DEFAULT_SPAWN_POINT

        loc_data = await self._integrator.get_location_data(loc_id) or {}

        return await self._build_navigation_dto(char_id, loc_id, loc_data)

    async def interact(
        self, char_id: int, action: str, target_id: str | None = None
    ) -> WorldNavigationDTO | EncounterDTO | ExplorationListDTO | ServiceResult:
        """
        Обработка контекстных действий (Search, Battles, Bypass, etc).
        """
        loc_id = await self._integrator.get_player_location_id(char_id)
        if not loc_id:
            loc_id = ExplorationConfig.DEFAULT_SPAWN_POINT

        loc_data = await self._integrator.get_location_data(loc_id) or {}

        # --- Encounter Reactions ---
        if action == "attack":
            # For now, we assume Combat session was already created by EncounterEngine
            # This action just transitions the client state.
            return ServiceResult(data={"status": "entering_combat"}, next_state=CoreDomain.COMBAT)

        if action == "bypass":
            return await self.look_around(char_id)

        # --- Exploration Actions ---
        if action == "search":
            skills = await self._integrator.get_actor_skills(char_id)
            scouting = skills.get("survival", 0.0)

            encounter = await self._encounter_engine.try_generate_encounter(
                char_id=char_id, location_data=loc_data, scouting_skill=scouting, trigger="search", loc_id=loc_id
            )
            if encounter:
                return encounter

            # Empty search -> Alert HUD
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="Вы ничего не нашли.", style="info")
            return dto

        if action == "battles":
            return await self._scan_battles(char_id, loc_id, loc_data)

        # Default fallback
        return await self.look_around(char_id)

    async def use_service(self, char_id: int, service_id: str) -> WorldNavigationDTO | ServiceResult:
        loc_id = await self._integrator.get_player_location_id(char_id)
        if not loc_id:
            loc_id = ExplorationConfig.DEFAULT_SPAWN_POINT

        loc_data = await self._integrator.get_location_data(loc_id) or {}
        if not self._service_allowed_in_location(loc_data, service_id):
            log.warning("ExplorationService | service_denied char_id=%s loc=%s service=%s", char_id, loc_id, service_id)
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="Сервис недоступен из этой локации.", style="danger")
            return dto

        entry = get_service_entry(service_id)
        if entry is None:
            log.warning(
                "ExplorationService | service_unknown char_id=%s loc=%s service=%s", char_id, loc_id, service_id
            )
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="Сервис пока не подключен.", style="info")
            return dto

        if entry.access_policy != "public":
            log.warning(
                "ExplorationService | service_access_not_implemented char_id=%s loc=%s service=%s policy=%s",
                char_id,
                loc_id,
                service_id,
                entry.access_policy,
            )
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="Доступ к сервису пока не подключен.", style="info")
            return dto

        return ServiceResult(
            data={
                "service_id": service_id,
                "location_id": loc_id,
                "label": entry.label,
                **entry.metadata,
            },
            next_state=entry.target_state,
        )

    # =========================================================================
    # LOGIC: Battle Scanner
    # =========================================================================

    async def _scan_battles(self, char_id: int, loc_id: str, loc_data: dict) -> WorldNavigationDTO | ExplorationListDTO:
        """
        Сканирует бои в локации.
        """
        battles = await self._integrator.get_battles(loc_id)

        if not battles:
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="В локации тихо. Боев не обнаружено.", style="info")
            return dto

        items = []
        for bid, desc in battles.items():
            items.append(ListItemDTO(id=bid, text=desc, action=f"spectate:{bid}"))

        return ExplorationListDTO(
            title="⚔️ Активные бои",
            items=items,
            page=1,
            total_pages=1,
            back_action="look_around",
        )

    @staticmethod
    def _service_allowed_in_location(loc_data: dict, service_id: str) -> bool:
        services = loc_data.get("services")
        if isinstance(services, list) and service_id in {str(item) for item in services}:
            return True

        exits = loc_data.get("exits", {})
        if not isinstance(exits, dict):
            return False
        return f"svc:{service_id}" in exits or service_id in exits

    # =========================================================================
    # HELPERS: DTO Builder
    # =========================================================================

    async def _build_navigation_dto(self, char_id: int, loc_id: str, loc_data: dict) -> WorldNavigationDTO:
        """
        Сборка DTO для клиента (Карта).
        """
        players_count = await self._integrator.get_players_count(loc_id, exclude_char_id=char_id)
        battles = await self._integrator.get_battles(loc_id)
        battles_count = len(battles)

        flags = loc_data.get("flags", {})
        anchor_influence = loc_data.get("anchor_influence", {})
        if not isinstance(anchor_influence, dict):
            anchor_influence = {}
        world_theme = WorldThemeDTO.model_validate(loc_data.get("world_theme") or {})
        if world_theme.loc_id is None:
            world_theme.loc_id = loc_id

        # Используем NavigationEngine для сборки сетки
        exits = loc_data.get("exits", {})
        grid = NavigationEngine.build_grid(loc_id, exits, flags)
        navigation = NavigationEngine.build_actions(loc_id, exits, flags)

        is_safe_zone = NavigationEngine.is_safe_context(flags)

        hud = ExplorationHudDTO(
            threat_tier=float(flags.get("threat_tier", 0)),
            players_count=players_count,
            battles_count=battles_count,
            is_safe_zone=is_safe_zone,
            dominant_anchor=anchor_influence.get("dominant_anchor"),
            ambient_tags=anchor_influence.get("tags", []),
        )

        dto = WorldNavigationDTO(
            loc_id=loc_id,
            title=loc_data.get("name", "Unknown"),
            description=loc_data.get("description", "..."),
            background_url=loc_data.get("background_url"),
            anchor_influence=anchor_influence,
            world_theme=world_theme,
            visual_objects=[],
            players_nearby=players_count,
            grid=grid,
            navigation=navigation,
            hud=hud,
            threat_tier=float(flags.get("threat_tier", 0)),
            is_safe_zone=is_safe_zone,
        )
        await self._integrator.set_world_theme(char_id, dto.world_theme.model_dump(mode="json"))
        return dto
