from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_bot.base import BaseBotOrchestrator, UnifiedViewDTO, ViewResultDTO
from loguru import logger as log

from ..ui.ui import BotMenuUI

if TYPE_CHECKING:
    from codex_bot.director import Director


class BotMenuOrchestrator(BaseBotOrchestrator[Any]):
    """
    Universal Menu Orchestrator (Dashboard).
    Discovers all features and renders navigation buttons.
    """

    def __init__(self) -> None:
        super().__init__(expected_state=None)
        self.ui = BotMenuUI()

    async def render_content(self, director: Director | None = None, payload: Any = None) -> ViewResultDTO:
        """
        Required implementation of BaseBotOrchestrator.
        Generates the main status text for the Dashboard.
        """
        # We can extract useful info from the director or container
        session_id = director.session_key if director else "N/A"

        text = (
            "🤖 <b>Codex-Bot Dashboard</b>\n"  # nosec B608
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Session:</b> <code>{session_id}</code>\n"
            "⚙️ <b>Status:</b> System Operational\n\n"
            "Select a module from the menu below to continue:"
        )

        return ViewResultDTO(text=text)

    async def handle_entry(
        self,
        director: Director,
        payload: Any = None,
    ) -> UnifiedViewDTO:
        """Entry point for the dashboard."""
        mode = payload if isinstance(payload, str) else "bot_menu"
        return await self.render_dashboard(director, mode=mode)

    async def render_dashboard(self, director: Director, mode: str = "bot_menu") -> UnifiedViewDTO:
        """Collects buttons from all features and renders the UI."""
        is_admin_mode = mode == "dashboard_admin"

        # Use Any for container to access project-specific services like discovery_service
        container: Any = director.container

        # 1. Fetch available buttons from Discovery Service
        discovery = getattr(container, "discovery_service", None)
        if not discovery:
            log.error("BotMenuDiscoveryServiceMissing")
            available_features: dict[str, Any] = {}
        else:
            available_features = discovery.get_menu_buttons(is_admin=is_admin_mode)

        # 2. RBAC check for admin mode
        if is_admin_mode and hasattr(container, "is_admin") and not container.is_admin(director.session_key):
            log.bind(session_key=director.session_key).warning("BotMenuAdminAccessDenied")
            return await self.render_dashboard(director, mode="bot_menu")

        # 3. Render
        menu_view = self.ui.render_dashboard(available_features, mode=mode)

        return UnifiedViewDTO(
            menu=menu_view,
            content=await self.render_content(director=director, payload=None),
            chat_id=director.context_id,
            session_key=director.session_key,
        )

    async def handle_callback(self, director: Director, payload: Any) -> UnifiedViewDTO | None:
        """Handles menu navigation clicks."""
        action = getattr(payload, "action", None)
        target = getattr(payload, "target", None)

        if action == "select" and target:
            # Logic for switching scenes via Director
            return await director.set_scene(feature=target)
        return None
