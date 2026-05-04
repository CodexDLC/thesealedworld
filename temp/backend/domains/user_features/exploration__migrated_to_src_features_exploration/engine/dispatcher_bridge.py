# backend/domains/user_features/exploration/engine/dispatcher_bridge.py
"""
Bridge для всех вызовов Dispatcher из домена Exploration.
Инкапсулирует межсервисное взаимодействие.
"""

from typing import TYPE_CHECKING, Any

from src.shared.enums.domain_enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher


class ExplorationDispatcherBridge:
    """
    Инкапсулирует все вызовы Dispatcher из домена Exploration.

    Позволяет:
    - Централизовать межсервисное взаимодействие
    - Легко тестировать (мокаем один класс)
    - Документировать зависимости от других доменов
    """

    def __init__(self, dispatcher: "SystemDispatcher"):
        self._dispatcher = dispatcher

    # =========================================================================
    # Combat Integration
    # =========================================================================

    async def create_combat_session(self, char_id: int, enemies: list, loc_id: str, ambush: bool = False) -> str | None:
        """
        Создаёт боевую сессию через COMBAT_ENTRY.

        Args:
            char_id: ID персонажа
            enemies: Список данных врагов
            loc_id: ID локации где происходит бой
            ambush: True если засада (враг атакует первым)

        Returns:
            session_id если сессия создана, иначе None
        """
        result = await self._dispatcher.route(
            domain=CoreDomain.COMBAT_ENTRY,
            char_id=char_id,
            action="create_pve_session",
            context={"enemies": enemies, "loc_id": loc_id, "ambush": ambush},
        )
        # Ожидаем что COMBAT_ENTRY вернёт session_id
        if result and isinstance(result, dict):
            return result.get("session_id")
        return result

    async def get_combat_dashboard(self, char_id: int) -> Any:
        """
        Получает текущий dashboard боя.
        Вызывается при нажатии кнопки "Атаковать".
        """
        return await self._dispatcher.route(
            domain=CoreDomain.COMBAT, char_id=char_id, action="get_dashboard", context={}
        )

    # =========================================================================
    # Monster Generation
    # =========================================================================

    async def generate_monster_group(self, tier: int, difficulty: str, count: int = 1) -> list[dict]:
        """
        Запрашивает генерацию группы монстров.

        Args:
            tier: Уровень локации (1-7)
            difficulty: Сложность ("easy", "mid", "hard")
            count: Количество монстров

        Returns:
            Список данных монстров для боя
        """
        # TODO: Когда будет Monster домен
        # result = await self._dispatcher.route(
        #     domain="monster",
        #     char_id=0,
        #     action="generate_group",
        #     context={"tier": tier, "difficulty": difficulty, "count": count}
        # )
        # return result or []

        # Пока заглушка
        return []

    # =========================================================================
    # Loot Integration
    # =========================================================================

    async def get_location_loot(self, loc_id: str, char_id: int) -> Any:
        """
        Запрашивает лут для локации (при исследовании).

        Returns:
            Данные о найденном луте
        """
        # TODO: Когда будет Loot домен
        # return await self._dispatcher.route(
        #     domain="loot",
        #     char_id=char_id,
        #     action="generate_location_loot",
        #     context={"loc_id": loc_id}
        # )
        return None

    # =========================================================================
    # NPC / Quest Integration (Future)
    # =========================================================================

    async def get_npc_dialog(self, npc_id: str, char_id: int) -> Any:
        """Запрашивает диалог NPC."""
        # TODO: Когда будет NPC/Dialog домен
        return None

    async def start_quest(self, quest_id: str, char_id: int) -> Any:
        """Запускает квест."""
        # TODO: Когда будет Quest домен
        return None
