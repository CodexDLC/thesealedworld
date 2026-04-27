from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class IScenarioRepository(ABC):
    """
    Интерфейс репозитория для управления данными системы сценариев.
    Объединяет работу с мастером, нодами и состояниями игроков.
    """

    # --- 1. Работа с Scenario_Master (Table A) ---

    @abstractmethod
    async def get_master(self, quest_key: str) -> dict[str, Any] | None:
        """Получает глобальные настройки квеста, init_sync и export_sync."""
        pass

    @abstractmethod
    async def upsert_master(self, master_data: dict[str, Any]) -> None:
        """Создает или обновляет мастер-запись квеста."""
        pass

    # --- 2. Работа с Scenario_Nodes (Table B) ---

    @abstractmethod
    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        """Получает данные конкретной сцены: текст, логику кнопок и условия входа."""
        pass

    @abstractmethod
    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        """Получает список нод по тегу для работы Smart Selection."""
        pass

    @abstractmethod
    async def get_all_quest_nodes(self, quest_key: str) -> list[dict[str, Any]]:
        """Загружает все ноды квеста (используется для первичного кэширования в Redis)."""
        pass

    @abstractmethod
    async def upsert_node(self, node_data: dict[str, Any]) -> None:
        """Создает или обновляет ноду."""
        pass

    @abstractmethod
    async def bulk_insert_nodes(self, nodes_data: list[dict[str, Any]]) -> None:
        """Массовая вставка нод (оптимизация загрузки)."""
        pass

    @abstractmethod
    async def delete_quest_nodes(self, quest_key: str) -> None:
        """Удаляет все ноды квеста (для перезаливки)."""
        pass

    # --- 3. Работа с Character_Quest_State (Table C) ---

    @abstractmethod
    async def get_active_state(self, char_id: int) -> dict[str, Any] | None:
        """Загружает сохраненное состояние сессии игрока (бэкап)."""
        pass

    @abstractmethod
    async def upsert_state(
        self, char_id: int, quest_key: str, node_key: str, context: dict[str, Any], session_id: UUID
    ) -> None:
        """Сохраняет или обновляет текущий прогресс игрока в БД."""
        pass

    @abstractmethod
    async def delete_state(self, char_id: int) -> None:
        """Удаляет запись о состоянии после завершения или провала квеста."""
        pass
