from typing import Any

from loguru import logger as log

from src.backend.domains.internal_systems.dispatcher.system_dispatcher import SystemDispatcher
from src.backend.domains.user_features.game_menu.data.locales.menu_resources import MenuResources
from src.backend.domains.user_features.game_menu.services.menu_session_service import MenuSessionService
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.game_menu import GameMenuDTO, MenuButtonDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader


class GameMenuService:
    """
    Бизнес-логика Game Menu.
    Сборка DTO и маршрутизация действий.
    """

    def __init__(self, session_service: MenuSessionService, dispatcher: SystemDispatcher):
        self.session = session_service
        self.dispatcher = dispatcher

    async def get_entry_point(self, char_id: int, action: str, context: dict = None) -> Any:
        """
        Точка входа для SystemDispatcher.
        Позволяет другим доменам (Inventory, Exploration) получать данные меню.
        """
        if action == "get_view" or action == "get_menu":  # Добавил get_menu для совместимости
            return await self.get_menu_view(char_id)

        # Можно добавить другие экшены, если нужно
        return None

    async def get_menu_view(self, char_id: int) -> GameMenuDTO:
        """
        Собирает полное меню (HUD + Кнопки).
        """
        # 1. Получаем HUD (с регенерацией)
        hud_data = await self.session.get_player_context(char_id)

        # 2. Собираем кнопки (всегда стандартный лейаут)
        layout_ids = MenuResources.get_layout()
        buttons = []
        legend = {}

        for btn_id in layout_ids:
            label = MenuResources.get_label(btn_id)
            buttons.append(MenuButtonDTO(id=btn_id, text=label, is_active=True))
            # Заполняем легенду: "📦" -> "Inventory"
            legend[label] = MenuResources.get_description(btn_id)

        return GameMenuDTO(hud=hud_data, buttons=buttons, legend=legend)

    async def process_menu_action(self, char_id: int, action_id: str) -> CoreResponseDTO[Any]:
        """
        Обрабатывает нажатие кнопки меню.
        """
        current_state = await self.session.get_current_state(char_id)

        # 1. Валидация
        if not await self.session.can_perform_action(char_id, action_id):
            # Если действие запрещено (например, мы в бою),
            # мы перенаправляем пользователя на view ТЕКУЩЕГО стейта.

            try:
                payload = await self.dispatcher.process_action(domain=current_state, char_id=char_id, action="get_view")

                return CoreResponseDTO(
                    header=GameStateHeader(
                        current_state=current_state,  # type: ignore
                        previous_state=current_state,  # type: ignore
                    ),
                    payload=payload,
                )
            except Exception as e:  # noqa: BLE001
                log.error(f"Error redirecting to current state {current_state}: {e}")
                return CoreResponseDTO(
                    header=GameStateHeader(current_state=CoreDomain.LOBBY, error="action_not_allowed_redirect_failed"),
                    payload={},
                )

        # 2. Routing
        target_domain = action_id

        if action_id == "exploration":
            target_domain = CoreDomain.EXPLORATION
        elif action_id == "inventory":
            target_domain = CoreDomain.INVENTORY
        elif action_id == "status":
            target_domain = CoreDomain.STATUS

        # 3. Dispatch
        try:
            payload = await self.dispatcher.process_action(domain=target_domain, char_id=char_id, action="get_view")

            new_state = target_domain

            return CoreResponseDTO(
                header=GameStateHeader(
                    current_state=new_state,  # type: ignore
                    previous_state=current_state,  # type: ignore
                ),
                payload=payload,
            )

        except Exception as e:  # noqa: BLE001
            log.error(f"Error dispatching to {target_domain}: {e}")
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY, error="internal_error"), payload={}
            )
