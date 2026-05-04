from loguru import logger as log

from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher
from src.shared.enums.domain_enums import CoreDomain


class ScenarioDispatcherBridge:
    """
    Мост для взаимодействия Сценария с другими доменами через SystemDispatcher.
    Изолирует ScenarioService от прямых вызовов других сервисов.
    """

    def __init__(self, dispatcher: SystemDispatcher):
        self.dispatcher = dispatcher

    async def start_shadow_combat(self, char_id: int) -> bool:
        """
        Инициирует бой с тенью (Self-Test).
        """
        try:
            result = await self.dispatcher.dispatch(
                domain=CoreDomain.COMBAT_ENTRY,
                char_id=char_id,
                action="shadow_duel",
                context={"char_id": char_id},
            )
            return result.get("success", False)
        except Exception as e:  # noqa: BLE001
            log.error(f"ScenarioBridge | Failed to start shadow combat: {e}")
            return False

    async def start_pve_combat(self, char_id: int, teams_config: list[dict]) -> bool:
        """
        Инициирует PvE бой с заданными командами.
        """
        try:
            result = await self.dispatcher.dispatch(
                domain=CoreDomain.COMBAT_ENTRY,
                char_id=char_id,
                action="standard_pve",
                context={"teams": teams_config},
            )
            return result.get("success", False)
        except Exception as e:  # noqa: BLE001
            log.error(f"ScenarioBridge | Failed to start PvE combat: {e}")
            return False

    async def add_item(self, char_id: int, item_key: str, quantity: int = 1) -> bool:
        """
        Выдает предмет игроку (через Inventory Domain).
        """
        try:
            # TODO: Реализовать action="add_item" в InventoryGateway
            # Пока заглушка
            log.warning(f"ScenarioBridge | add_item not implemented yet. {item_key} x{quantity}")
            return True
        except Exception as e:  # noqa: BLE001
            log.error(f"ScenarioBridge | Failed to add item: {e}")
            return False
