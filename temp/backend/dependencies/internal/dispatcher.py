from typing import Annotated

from fastapi import Depends

# Import dependencies from domains
from src.backend.dependencies.features.combat import CombatEntryOrchestratorDep, CombatGatewayDep
from src.backend.dependencies.features.game_menu import get_game_menu_service  # Import GameMenuService
from src.backend.dependencies.features.inventory import InventoryGatewayDep  # Import Inventory Gateway
from src.backend.dependencies.features.scenario import ScenarioGatewayDep
from src.backend.dependencies.internal.world import WorldGatewayDep
from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher
from src.shared.enums.domain_enums import CoreDomain


async def get_system_dispatcher(
    combat_entry: CombatEntryOrchestratorDep,
    combat_gateway: CombatGatewayDep,
    scenario_gateway: ScenarioGatewayDep,
    inventory_gateway: InventoryGatewayDep,
    world_gateway: WorldGatewayDep,
    game_menu_service=Depends(get_game_menu_service),
) -> SystemDispatcher:
    """
    Собирает SystemDispatcher и регистрирует в нем все доступные оркестраторы.
    """

    # 1. Создаем пустой диспетчер
    dispatcher = SystemDispatcher()

    # 2. Combat Entry (Создание боя)
    dispatcher.register(CoreDomain.COMBAT_ENTRY, lambda: combat_entry)

    # 3. Combat Runtime (Сам бой - Gateway)
    dispatcher.register(CoreDomain.COMBAT, lambda: combat_gateway)

    # 4. Scenario (Квесты)
    dispatcher.register(CoreDomain.SCENARIO, lambda: scenario_gateway)

    # 5. Game Menu (Меню)
    dispatcher.register(CoreDomain.MENU, lambda: game_menu_service)

    # 6. Inventory (Инвентарь)
    dispatcher.register(CoreDomain.INVENTORY, lambda: inventory_gateway)

    # 7. World (Мир, локации)
    dispatcher.register(CoreDomain.WORLD, lambda: world_gateway)

    # TODO: Register other domains (Lobby, etc.)

    return dispatcher


SystemDispatcherDep = Annotated[SystemDispatcher, Depends(get_system_dispatcher)]
