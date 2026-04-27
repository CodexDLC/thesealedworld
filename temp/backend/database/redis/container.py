

# Managers
from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.database.redis.manager.arena_manager import ArenaManager
from src.backend.database.redis.manager.combat_manager import CombatManager
from src.backend.database.redis.manager.context_manager import ContextRedisManager
from src.backend.database.redis.manager.inventory_manager import InventoryManager
from src.backend.database.redis.manager.scenario_manager import ScenarioManager
from src.backend.database.redis.manager.world_manager import WorldManager
from src.backend.database.redis.redis_service import RedisService


class RedisContainer:
    """
    Контейнер для всех Redis-менеджеров.
    Обеспечивает единую точку доступа к слою данных Redis.
    """

    def __init__(self, redis_client: Redis):
        """
        Инициализирует контейнер с менеджерами.

        Args:
            redis_client: Экземпляр клиента Redis.
        """
        # 1. Base Service (Wrapper)
        self.service = RedisService(redis_client)

        # 2. Managers
        self.account = AccountManager(self.service)
        self.arena = ArenaManager(self.service)
        self.combat = CombatManager(self.service)
        self.context = ContextRedisManager(self.service)
        self.scenario = ScenarioManager(self.service)
        self.inventory = InventoryManager(self.service)
        self.world = WorldManager(self.service)
