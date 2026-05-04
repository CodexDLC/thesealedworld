from typing import Annotated

from fastapi import Depends

from src.backend.dependencies.base import RedisContainerDep
from src.backend.domains.internal_systems.context_assembler.service import ContextAssemblerService


async def get_context_assembler_service(
    redis_container: RedisContainerDep,
) -> ContextAssemblerService:
    """
    Dependency provider for ContextAssemblerService.
    """
    return ContextAssemblerService(
        account_manager=redis_container.account,
        context_manager=redis_container.context,
        inventory_manager=redis_container.inventory,  # Добавляем зависимость
    )


ContextAssemblerServiceDep = Annotated[ContextAssemblerService, Depends(get_context_assembler_service)]
