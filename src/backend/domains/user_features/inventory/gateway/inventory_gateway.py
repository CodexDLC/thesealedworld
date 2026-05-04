from typing import Any

from loguru import logger as log

from src.backend.domains.user_features.inventory.services.inventory_service import InventoryService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.inventory import InventoryUIPayloadDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader, ServiceResult


class InventoryGateway:
    """
    Единая точка входа в домен Инвентаря со стороны API.
    Изолирует HTTP-слой от бизнес-логики и выполняет маршрутизацию запросов.
    """

    def __init__(self, service: InventoryService):
        self.service = service

    async def get_view(self, char_id: int, view_type: str, **kwargs: Any) -> CoreResponseDTO[InventoryUIPayloadDTO]:
        """
        Обрабатывает GET запросы на получение данных (View).

        Args:
            char_id: ID персонажа.
            view_type: Тип представления (main, bag, details).
            **kwargs: Дополнительные параметры (page, section, category, item_id).
        """
        log.debug(f"InventoryGateway | action=get_view char_id={char_id} type={view_type} args={kwargs}")

        try:
            if view_type == "main":
                result = await self.service.get_main_menu(char_id)
            elif view_type == "bag":
                section = kwargs.get("section", "all")
                category = kwargs.get("category")
                page = int(kwargs.get("page", 0))
                result = await self.service.get_bag_view(char_id, section, category, page)
            elif view_type == "details":
                item_id = int(kwargs.get("item_id", 0))
                result = await self.service.get_item_details(char_id, item_id)
            else:
                raise ValueError(f"Unknown view type: {view_type}")

            return self._wrap_response(result)

        except Exception as e:
            log.exception(f"InventoryGateway | action=get_view status=failed error={e}")
            # В случае ошибки возвращаем пользователя в главное меню инвентаря с ошибкой
            # Или можно вернуть 500, если это API
            raise e

    async def handle_action(
        self, char_id: int, action_type: str, **kwargs: Any
    ) -> CoreResponseDTO[InventoryUIPayloadDTO]:
        """
        Обрабатывает POST запросы на изменение состояния (Action).

        Args:
            char_id: ID персонажа.
            action_type: Тип действия (equip, unequip, use, move).
            **kwargs: Параметры действия (item_id, slot, target).
        """
        log.debug(f"InventoryGateway | action=handle_action char_id={char_id} type={action_type} args={kwargs}")

        try:
            item_id = int(kwargs.get("item_id", 0))

            if action_type == "equip":
                slot = kwargs.get("slot")
                result = await self.service.equip_item(char_id, item_id, slot)
            elif action_type == "unequip":
                result = await self.service.unequip_item(char_id, item_id)
            # elif action_type == "use":
            #     result = await self.service.use_item(char_id, item_id)
            # elif action_type == "move":
            #     target = kwargs.get("target")
            #     position = int(kwargs.get("position", 0))
            #     result = await self.service.move_item(char_id, item_id, target, position)
            else:
                raise ValueError(f"Unknown action type: {action_type}")

            return self._wrap_response(result)

        except Exception as e:
            log.exception(f"InventoryGateway | action=handle_action status=failed error={e}")
            raise e

    async def handle_delete(self, char_id: int, item_id: int) -> CoreResponseDTO[InventoryUIPayloadDTO]:
        """
        Обрабатывает DELETE запросы (Drop Item).
        """
        log.debug(f"InventoryGateway | action=handle_delete char_id={char_id} item_id={item_id}")
        try:
            result = await self.service.drop_item(char_id, item_id)
            return self._wrap_response(result)
        except Exception as e:
            log.exception(f"InventoryGateway | action=handle_delete status=failed error={e}")
            raise e

    def _wrap_response(self, result: Any) -> CoreResponseDTO[InventoryUIPayloadDTO]:
        """
        Упаковывает результат сервиса в CoreResponseDTO.
        """
        # Если сервис вернул ServiceResult (смена стейта, например, телепорт свитком)
        if isinstance(result, ServiceResult):
            return CoreResponseDTO(
                header=GameStateHeader(
                    current_state=result.next_state or CoreDomain.INVENTORY,
                ),
                payload=result.data,
            )

        # По умолчанию остаемся в INVENTORY
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.INVENTORY),
            payload=result,
        )
