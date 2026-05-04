# src/backend/features/exploration/events/emitters.py
import logging
from typing import Any

log = logging.getLogger(__name__)


class ExplorationEvents:
    """
    Эмиттер событий домена Exploration.
    Здесь описываются контракты взаимодействия с другими доменами (Combat, Loot, Monsters).
    
    Методы пока содержат только заглушки, чтобы не потерять логику старого диспетчера.
    В будущем здесь будет отправка сообщений в Redis Streams.
    """

    @staticmethod
    async def create_combat_session(
        char_id: int, 
        enemies: list[dict[str, Any]], 
        loc_id: str, 
        ambush: bool = False
    ) -> str | None:
        """
        Запрос на создание боевой сессии.
        
        TODO: 
        1. Формировать пакет данных для Combat домена.
        2. Отправлять в Redis Stream 'combat:requests'.
        3. Ждать/получать ID созданной сессии.
        """
        log.info(
            "ExplorationEvents | action=create_combat_session char_id=%s loc=%s ambush=%s",
            char_id, loc_id, ambush
        )
        # Для первого сценария возвращаем заглушку ID, если нужно
        return f"stub_combat_{char_id}"

    @staticmethod
    async def generate_monster_group(tier: int, difficulty: str) -> list[dict[str, Any]]:
        """
        Запрос на генерацию группы монстров.
        
        TODO: Обратиться к MonsterGeneratorService (Domain: Monsters).
        """
        log.info("ExplorationEvents | action=generate_monsters tier=%s diff=%s", tier, difficulty)
        return []

    @staticmethod
    async def log_discovery(char_id: int, type: str, target_id: str) -> None:
        """
        Логирование обнаружения объекта (для квестов/статистики).
        """
        log.info("ExplorationEvents | action=discovery char_id=%s type=%s target=%s", char_id, type, target_id)
