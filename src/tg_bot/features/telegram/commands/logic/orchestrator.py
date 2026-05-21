from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_bot.base import BaseBotOrchestrator, UnifiedViewDTO, ViewResultDTO

from ..contracts.auth_contract import AuthDataProvider
from ..ui.commands_ui import CommandsUI

if TYPE_CHECKING:
    from codex_bot.director import Director


class StartOrchestrator(BaseBotOrchestrator[Any]):
    """
    Welcome Screen Orchestrator.
    Handles user registration and orchestrates the initial greeting.
    """

    def __init__(self, auth_provider: AuthDataProvider, settings: Any) -> None:
        super().__init__(expected_state=None)
        self.auth = auth_provider
        self.settings = settings
        self.ui = CommandsUI()

    async def render_content(
        self, director: "Director" | None = None, payload: Any = None
    ) -> ViewResultDTO | UnifiedViewDTO:
        """
        Delegates the welcome screen rendering to the UI layer.
        """
        user_name = "Guest"
        is_admin = False

        # 1. Extract context from payload (Telegram User object)
        if payload and hasattr(payload, "first_name"):
            user_name = payload.first_name

        # 2. Check admin privileges via container (centralized RBAC)
        if director and hasattr(director.container, "is_admin"):
            user_id = getattr(payload, "id", 0)
            is_admin = director.container.is_admin(user_id)

        # 3. Call UI layer for presentation
        return self.ui.render_welcome_screen(name=user_name, is_admin=is_admin)

    async def handle_entry(self, director: "Director", payload: Any = None) -> UnifiedViewDTO:
        """
        Entry point for /start command.
        Registers the user and renders the welcome screen.
        """
        if payload and hasattr(payload, "id"):
            # Registration logic (Stateless hand-off to data provider)
            user_data = {
                "telegram_id": payload.id,
                "first_name": getattr(payload, "first_name", ""),
                "username": getattr(payload, "username", ""),
                "last_name": getattr(payload, "last_name", ""),
                "language_code": getattr(payload, "language_code", "ru"),
            }
            await self.auth.upsert_user(user_data)

        # Presentation hand-off
        return await self.render(director=director, payload=payload)
