# src/backend/features/exploration/services/exploration_service.py
import logging
from typing import Any

from src.backend.features.exploration.runtime.encounter import EncounterEngine
from src.backend.features.exploration.runtime.navigation import NavigationEngine
from src.backend.features.exploration.integrations.system_integrator import ExplorationSystemIntegrator
from src.backend.features.exploration.dto.config import ExplorationConfig
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
        self, 
        char_id: int, 
        direction: str | None = None, 
        target_id: str | None = None
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
        self, 
        char_id: int, 
        action: str, 
        target_id: str | None = None
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
                char_id=char_id, 
                location_data=loc_data, 
                scouting_skill=scouting, 
                trigger="search", 
                loc_id=loc_id
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

        # Используем NavigationEngine для сборки сетки
        grid = NavigationEngine.build_grid(loc_id, loc_data.get("exits", {}), flags)

        hud = ExplorationHudDTO(
            threat_tier=int(flags.get("threat_tier", 0)),
            players_count=players_count,
            battles_count=battles_count,
            is_safe_zone=flags.get("is_safe_zone", False),
        )

        return WorldNavigationDTO(
            loc_id=loc_id,
            title=loc_data.get("name", "Unknown"),
            description=loc_data.get("description", "..."),
            visual_objects=[],
            players_nearby=players_count,
            grid=grid,
            hud=hud,
            threat_tier=int(flags.get("threat_tier", 0)),
            is_safe_zone=flags.get("is_safe_zone", False),
        )
