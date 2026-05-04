# apps/game_core/system/context_assembler/logic/base_assembler.py
from abc import ABC, abstractmethod
from typing import Any


class BaseAssembler(ABC):
    """
    Абстрактный базовый класс для стратегий сборки контекста.
    Определяет интерфейс для массовой обработки сущностей.
    """

    @abstractmethod
    async def process_batch(self, ids: list[Any], scope: str) -> tuple[dict[Any, str], list[Any]]:
        """
        Обрабатывает пакет идентификаторов сущностей.

        Args:
            ids: Список ID сущностей для обработки (int для игроков, str для монстров).
            scope: Объем данных ('full', 'combats', 'exploration').

        Returns:
            Кортеж (success_map, error_list):
            - success_map: Словарь {entity_id: redis_key} для успешных операций.
            - error_list: Список ID сущностей, которые не удалось обработать.
        """
        pass
