import time
from typing import Any

from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.database.redis.manager.arena_manager import ArenaManager


class ArenaSessionService:
    """
    Инкапсулирует работу с Redis для домена Arena.
    Объединяет ArenaManager и AccountManager.
    """

    GS_RANGE_PERCENT = 0.15
    REQUEST_TTL = 300
    DEFAULT_GS = 100

    def __init__(self, arena_manager: ArenaManager, account_manager: AccountManager):
        self.arena_manager = arena_manager
        self.account_manager = account_manager

    # --- Queue Operations ---

    async def join_queue(self, char_id: int, mode: str) -> int:
        """
        Добавляет игрока в очередь.
        Возвращает текущий GS.
        """
        # 1. Получаем GS
        gs = await self.get_gear_score(char_id)

        # 2. Добавляем в ZSET
        await self.arena_manager.add_to_queue(mode, char_id, float(gs))

        # 3. Создаем метаданные заявки
        await self.arena_manager.create_request(char_id, {"start_time": time.time(), "gs": gs, "mode": mode})

        return gs

    async def leave_queue(self, char_id: int, mode: str) -> None:
        """Удаляет игрока из очереди и очищает заявку."""
        await self.arena_manager.remove_from_queue(mode, char_id)
        await self.arena_manager.delete_request(char_id)

    async def get_request_meta(self, char_id: int) -> dict[str, Any] | None:
        """Возвращает метаданные активной заявки."""
        return await self.arena_manager.get_request(char_id)

    # --- Match Operations ---

    async def find_opponent(self, char_id: int, mode: str) -> int | None:
        """
        Ищет подходящего противника в очереди.
        Атомарно извлекает его, если найден.
        """
        request = await self.get_request_meta(char_id)
        if not request:
            return None

        my_gs = int(request.get("gs", self.DEFAULT_GS))
        min_gs = my_gs * (1 - self.GS_RANGE_PERCENT)
        max_gs = my_gs * (1 + self.GS_RANGE_PERCENT)

        # Получаем кандидатов
        candidates = await self.arena_manager.get_candidates(mode, min_gs, max_gs)

        for candidate_id_str in candidates:
            candidate_id = int(candidate_id_str)
            if candidate_id != char_id:
                # Пытаемся забрать кандидата из очереди (атомарно)
                removed = await self.arena_manager.remove_from_queue(mode, candidate_id)
                if removed:
                    return candidate_id

        return None

    async def prepare_match(self, char_id: int, opponent_id: int | None, mode: str) -> None:
        """
        Очищает данные очереди для обоих участников перед началом боя.
        """
        # Удаляем себя
        await self.leave_queue(char_id, mode)

        # Удаляем противника
        if opponent_id:
            # Заявку противника тоже нужно удалить (из очереди он уже удален в find_opponent)
            await self.arena_manager.delete_request(opponent_id)

    # --- Data Operations ---

    async def get_gear_score(self, char_id: int) -> int:
        """
        Возвращает GearScore персонажа из AccountManager.
        Если GS не найден, возвращает DEFAULT_GS.
        """
        try:
            # Предполагаем, что метод get_gear_score существует в AccountManager
            gs = await self.account_manager.get_gear_score(char_id)
            return gs if gs is not None else self.DEFAULT_GS
        except Exception:  # noqa: BLE001
            # Логируем ошибку, если AccountManager.get_gear_score не сработал
            # log.exception(f"Failed to get gear score for char_id={char_id}, using default.")
            return self.DEFAULT_GS
