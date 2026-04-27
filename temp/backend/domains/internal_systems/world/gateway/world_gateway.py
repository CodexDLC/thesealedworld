# src/backend/domains/internal_systems/world/gateway/world_gateway.py
"""
Gateway для домена World.
Точка входа для SystemDispatcher.
"""

from typing import Any

from loguru import logger as log

from backend.domains.internal_systems.world.services.world_service import WorldService


class WorldGateway:
    """
    Фасад домена World для внешних вызовов.
    """

    def __init__(self, service: WorldService):
        self._service = service

    async def handle(self, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Роутинг действий.

        Actions:
            - init_cache: Загрузка мира из PostgreSQL в Redis
            - get_location: Получить данные локации
            - register_battle: Зарегистрировать бой в локации
            - unregister_battle: Удалить бой из локации
        """
        log.debug(f"WorldGateway | action={action}")

        try:
            match action:
                case "init_cache":
                    count = await self._service.init_world_cache()
                    return self._success_response({"loaded_count": count})

                case "get_location":
                    loc_id = context.get("loc_id", "")
                    data = await self._service.get_location(loc_id)
                    if data:
                        return self._success_response(data)
                    return self._error_response(f"Локация {loc_id} не найдена")

                case "register_battle":
                    loc_id = context.get("loc_id", "")
                    battle_id = context.get("battle_id", "")
                    description = context.get("description", "Бой")
                    await self._service.register_battle(loc_id, battle_id, description)
                    return self._success_response({"registered": True})

                case "unregister_battle":
                    loc_id = context.get("loc_id", "")
                    battle_id = context.get("battle_id", "")
                    await self._service.unregister_battle(loc_id, battle_id)
                    return self._success_response({"unregistered": True})

                case _:
                    return self._error_response(f"Неизвестный action: {action}")

        except (KeyError, ValueError, TypeError) as e:
            log.exception(f"WorldGateway | error action={action}")
            return self._error_response(str(e))

    @staticmethod
    def _success_response(data: Any) -> dict[str, Any]:
        return {
            "success": True,
            "data": data,
            "error": None,
        }

    @staticmethod
    def _error_response(message: str) -> dict[str, Any]:
        return {
            "success": False,
            "data": None,
            "error": message,
        }
