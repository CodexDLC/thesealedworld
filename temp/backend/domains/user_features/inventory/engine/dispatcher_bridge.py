from typing import Any

from loguru import logger as log

from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher
from src.shared.enums.domain_enums import CoreDomain


class InventoryDispatcherBridge:
    """
    Мост для взаимодействия с другими доменами через SystemDispatcher.
    Изолирует InventoryService от прямых вызовов других сервисов.
    """

    def __init__(self, dispatcher: SystemDispatcher):
        self.dispatcher = dispatcher

    async def get_main_menu(self, char_id: int, context: str) -> Any:
        """
        Запрашивает данные для главного меню (HUD) у домена Menu/UI.
        """
        try:
            # Вызываем метод 'get_menu' у сервиса меню
            # Ожидаем, что он вернет MenuDTO или dict, совместимый с ним
            return await self.dispatcher.dispatch(
                domain=CoreDomain.MENU, char_id=char_id, action="get_menu", context={"ui_context": context}
            )
        except Exception as e:  # noqa: BLE001
            log.error(f"Bridge | Failed to get HUD: {e}")
            # Возвращаем пустой объект, чтобы не крашить инвентарь
            return None

    async def use_item_effect(self, char_id: int, item_id: int, item_data: dict) -> Any:
        """
        Делегирует применение эффекта предмета (если он сложный).
        """
        # TODO: Реализовать вызов EffectsEngine
        log.debug(f"Bridge | Delegating effect for item={item_id}")
        return None
