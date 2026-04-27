# backend/domains/user_features/exploration/services/exploration_service.py
from typing import TYPE_CHECKING

from loguru import logger as log

from src.backend.domains.user_features.exploration.engine.dispatcher_bridge import ExplorationDispatcherBridge
from src.backend.domains.user_features.exploration.engine.encounter_engine import EncounterEngine
from src.backend.domains.user_features.exploration.engine.navigation_engine import NavigationEngine
from src.backend.domains.user_features.exploration.services.exploration_session_service import ExplorationSessionService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.exploration import (
    AlertHudDTO,
    EncounterDTO,
    ExplorationHudDTO,
    ExplorationListDTO,
    ListItemDTO,
    WorldNavigationDTO,
)
from src.shared.schemas.response import ServiceResult

if TYPE_CHECKING:
    pass


class ExplorationService:
    """
    Основной сервис домена Exploration.
    Координирует перемещение, генерацию событий и сборку UI.
    """

    def __init__(
        self,
        session_service: ExplorationSessionService,
        encounter_engine: EncounterEngine,
        dispatcher_bridge: ExplorationDispatcherBridge,
    ):
        self._session = session_service
        self._encounter_engine = encounter_engine
        self._bridge = dispatcher_bridge

    # =========================================================================
    # CORE ACTIONS
    # =========================================================================

    async def move(
        self, char_id: int, direction: str | None = None, target_id: str | None = None
    ) -> WorldNavigationDTO | EncounterDTO:
        """
        Попытка перемещения.
        Принимает либо direction (n, s, w, e), либо target_id (52_51).
        """
        current_loc_id = await self._session.get_player_location_id(char_id)
        loc_data = await self._session.get_location_data(current_loc_id)

        if not loc_data:
            log.error(f"ExplorationService | loc_not_found char_id={char_id} loc={current_loc_id}")
            return await self._build_navigation_dto(char_id, current_loc_id, {})

        exits = loc_data.get("exits", {})
        target_loc_id = None

        # 1. Resolve Target ID
        if target_id:
            # Проверяем, есть ли такой выход
            # Ключ в exits может быть "nav:52_51" или просто "52_51"
            # Или мы должны искать по target_id внутри ключа

            # Простой поиск по ключу
            if f"nav:{target_id}" in exits or target_id in exits:
                target_loc_id = target_id
            else:
                # Если не нашли по ключу, ищем по target_id внутри ключа (если ключ сложный)
                # Но обычно ключ это nav:ID
                pass

        elif direction:
            # Legacy: поиск по направлению (если вдруг кто-то вызывает по-старому)
            # Но мы переходим на target_id
            # Для совместимости можно оставить логику поиска, но она сложная и ненадежная
            pass

        if not target_loc_id:
            # Если не удалось определить цель, остаемся на месте
            log.warning(f"ExplorationService | invalid_move char_id={char_id} target={target_id} dir={direction}")
            return await self._build_navigation_dto(char_id, current_loc_id, loc_data)

        # 2. Проверка Энкаунтера
        target_loc_data = await self._session.get_location_data(target_loc_id)
        if target_loc_data:
            scouting = await self._session.get_actor_skill(char_id, "survival")

            encounter = await self._encounter_engine.try_generate_encounter(
                char_id=char_id,
                location_data=target_loc_data,
                scouting_skill=scouting,
                trigger="move",
                loc_id=target_loc_id,
            )

            if encounter:
                await self._session.move_player(char_id, target_loc_id)
                return encounter

        await self._session.move_player(char_id, target_loc_id)
        return await self.look_around(char_id)

    async def look_around(self, char_id: int) -> WorldNavigationDTO:
        """
        Обновление данных текущей локации (без движения).
        """
        loc_id = await self._session.get_player_location_id(char_id)
        loc_data = await self._session.get_location_data(loc_id) or {}

        return await self._build_navigation_dto(char_id, loc_id, loc_data)

    async def interact(
        self, char_id: int, action: str, target_id: str | None = None
    ) -> WorldNavigationDTO | EncounterDTO | ExplorationListDTO | ServiceResult:
        """
        Обработка контекстных действий (Search, Scan, Attack, Bypass, etc).
        """
        loc_id = await self._session.get_player_location_id(char_id)
        loc_data = await self._session.get_location_data(loc_id) or {}

        # --- Encounter Reactions ---
        if action == "attack":
            # Вступить в бой: запрашиваем dashboard через Bridge
            combat_dto = await self._bridge.get_combat_dashboard(char_id)
            return ServiceResult(data=combat_dto, next_state=CoreDomain.COMBAT)

        if action == "bypass":
            # Обойти врага: просто возвращаем navigation
            return await self.look_around(char_id)

        # --- Exploration Actions ---
        if action == "search":
            scouting = await self._session.get_actor_skill(char_id, "survival")
            encounter = await self._encounter_engine.try_generate_encounter(
                char_id=char_id, location_data=loc_data, scouting_skill=scouting, trigger="search", loc_id=loc_id
            )
            if encounter:
                return encounter

            # Пустой поиск -> Alert HUD
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="Вы ничего не нашли.", style="info")
            return dto

        if action == "scan_battles":
            return await self._scan_battles(char_id, loc_id, loc_data)

        # Default fallback
        return await self._build_navigation_dto(char_id, loc_id, loc_data)

    # =========================================================================
    # LOGIC: Battle Scanner
    # =========================================================================

    async def _scan_battles(self, char_id: int, loc_id: str, loc_data: dict) -> WorldNavigationDTO | ExplorationListDTO:
        """
        Сканирует бои в локации.
        Если пусто -> Alert HUD.
        Если есть -> ExplorationListDTO.
        """
        battles = await self._session.get_battles(loc_id)

        if not battles:
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="В локации тихо. Боев не обнаружено.", style="info")
            return dto

        # Если бои есть -> Строим список
        items = []
        for bid, desc in battles.items():
            items.append(ListItemDTO(id=bid, text=desc, action=f"spectate:{bid}"))

        return ExplorationListDTO(
            title="⚔️ Активные бои",
            items=items,
            page=1,
            total_pages=1,  # TODO: Реализовать пагинацию
            back_action="look_around",
        )

    # =========================================================================
    # HELPERS: DTO Builder
    # =========================================================================

    async def _build_navigation_dto(self, char_id: int, loc_id: str, loc_data: dict) -> WorldNavigationDTO:
        """
        Сборка DTO для клиента (Карта).
        """
        players_count = await self._session.get_players_count_in_location(loc_id, exclude_char_id=char_id)
        battles_count = await self._session.get_active_battles_count(loc_id)
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
