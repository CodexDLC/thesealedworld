from loguru import logger as log
from pydantic import ValidationError

from src.backend.database.redis.manager.inventory_manager import InventoryManager
from src.backend.database.redis.redis_key import RedisKeys as Rk
from src.backend.domains.internal_systems.context_assembler.dtos import ContextRequestDTO
from src.backend.domains.internal_systems.context_assembler.service import ContextAssemblerService
from src.shared.schemas.inventory import InventorySessionDTO


class InventorySessionService:
    """
    Сервис управления сессией инвентаря.
    Отвечает за:
    1. Lazy Loading (Redis -> Miss -> ContextAssembler -> Redis).
    2. Предоставление доступа к данным сессии для бизнес-логики.
    """

    def __init__(
        self,
        inventory_manager: InventoryManager,
        context_assembler: ContextAssemblerService,
    ):
        self.manager = inventory_manager
        self.assembler = context_assembler

    async def get_session(self, char_id: int) -> InventorySessionDTO:
        """
        Получает сессию инвентаря.
        Если в Redis пусто, загружает из БД через ContextAssembler.
        """
        # 1. Попытка загрузить из Redis
        session_data = await self.manager.get_session(char_id)

        if session_data:
            try:
                return InventorySessionDTO(**session_data)
            except (ValidationError, TypeError) as e:
                log.error(f"InventorySessionService | Invalid session data in Redis: {e}")
                # Если данные битые, пересобираем

        # 2. Fallback: Сборка через ContextAssembler
        log.info(f"InventorySessionService | Session miss, assembling for char_id={char_id}")
        return await self._assemble_and_cache_session(char_id)

    async def _assemble_and_cache_session(self, char_id: int) -> InventorySessionDTO:
        """
        Запрашивает сборку контекста.
        ContextAssembler (через ContextSessionManager) сам сохранит данные в Redis по нужному ключу.
        Нам остается только прочитать их.
        """
        # 1. Запрос к Assembler
        request = ContextRequestDTO(
            player_ids=[char_id],
            scope="inventory",  # Использует InventoryTempContext и сохраняет в ac:{char_id}:inventory
        )

        response = await self.assembler.assemble(request)

        # 2. Проверка успеха
        # В response.player[char_id] должен лежать ключ, куда сохранились данные.
        # Для scope="inventory" это должен быть Rk.get_inventory_key(char_id).

        if not response.player or char_id not in response.player:
            log.error(f"InventorySessionService | Assembler failed for char_id={char_id}")
            return self._create_empty_session(char_id)

        target_key = response.player[char_id]
        expected_key = Rk.get_inventory_key(char_id)

        if target_key != expected_key:
            log.warning(f"InventorySessionService | Key mismatch: got {target_key}, expected {expected_key}")
            # Это может случиться, если Assembler не настроен на прямой save для inventory.
            # В таком случае нам пришлось бы делать rename, но мы уже настроили Assembler.

        # 3. Чтение данных из Redis (теперь они точно там)
        session_data = await self.manager.get_session(char_id)

        if session_data:
            try:
                return InventorySessionDTO(**session_data)
            except (ValidationError, TypeError) as e:
                log.error(f"InventorySessionService | Validation failed after assembly: {e}")

        return self._create_empty_session(char_id)

    def _create_empty_session(self, char_id: int) -> InventorySessionDTO:
        """
        Создает пустую сессию (fallback).
        """
        return InventorySessionDTO(char_id=char_id)

    async def save_session(self, session: InventorySessionDTO) -> None:
        """
        Явное сохранение сессии (если меняли DTO в памяти).
        """
        await self.manager.save_session(session.char_id, session.model_dump())
