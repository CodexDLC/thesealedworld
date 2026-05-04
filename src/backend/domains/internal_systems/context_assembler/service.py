import asyncio

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_session_context
from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.database.redis.manager.context_manager import ContextRedisManager
from src.backend.database.redis.manager.inventory_manager import InventoryManager
from src.backend.domains.internal_systems.context_assembler.dtos import ContextRequestDTO, ContextResponseDTO
from src.backend.domains.internal_systems.context_assembler.logic.monster_assembler import MonsterAssembler
from src.backend.domains.internal_systems.context_assembler.logic.player_assembler import PlayerAssembler


class ContextAssemblerService:
    """
    Сервис сборки контекста (Stateless).
    Сам управляет жизненным циклом сессии БД.
    Инжектится напрямую в другие сервисы.
    """

    def __init__(
        self,
        account_manager: AccountManager,
        context_manager: ContextRedisManager,
        inventory_manager: InventoryManager,  # Добавляем зависимость
    ):
        self.account_manager = account_manager
        self.context_manager = context_manager
        self.inventory_manager = inventory_manager

    async def assemble(self, request: ContextRequestDTO) -> ContextResponseDTO:
        """
        Главная точка входа.
        Создает сессию БД, выполняет сборку, закрывает сессию.
        """
        log.info(f"ContextAssembler | Assemble request: {request.model_dump_json(exclude_defaults=True)}")

        # Используем get_session_context для управления сессией
        async with get_session_context() as session:
            try:
                return await self._execute_strategies(session, request)
            except Exception as e:
                log.error(f"ContextAssembler | Error during assembly: {e}")
                raise

    async def _execute_strategies(self, session: AsyncSession, request: ContextRequestDTO) -> ContextResponseDTO:
        """
        Внутренняя логика распределения задач по стратегиям.
        """
        # Инициализируем стратегии с текущей сессией и менеджерами
        strategies = {
            "player": PlayerAssembler(session, self.account_manager, self.context_manager, self.inventory_manager),
            "monster": MonsterAssembler(session, self.account_manager, self.context_manager),
        }

        tasks = []
        task_mapping = []

        request_dict = request.model_dump()
        for entity_type, ids_list in request_dict.items():
            if not isinstance(ids_list, list) or not ids_list:
                continue

            clean_entity_type = entity_type.removesuffix("_ids")

            assembler = strategies.get(clean_entity_type)
            if assembler:
                tasks.append(assembler.process_batch(ids_list, request.scope))
                task_mapping.append(clean_entity_type)

        if not tasks:
            return ContextResponseDTO()

        results_list = await asyncio.gather(*tasks)

        final_response = ContextResponseDTO()
        for entity_type, result_tuple in zip(task_mapping, results_list, strict=False):
            success_map, error_list = result_tuple

            if hasattr(final_response, entity_type):
                setattr(final_response, entity_type, success_map)

            if error_list:
                final_response.errors[entity_type] = error_list

        log.info("ContextAssembler | Response ready")
        return final_response
