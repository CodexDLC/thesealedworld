from typing import Any

from aiogram.utils.keyboard import InlineKeyboardBuilder
from codex_bot.base.view_dto import ViewResultDTO


class CustomErrorUI:
    """
    Template for overriding system error views.
    Registered in BotContainer.
    """

    def render_error(self, data: dict[str, Any]) -> ViewResultDTO:
        # Example: customize rendering for specific error types
        error_msg = str(data.get("message", "An unexpected error occurred."))

        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Try Again", callback_data="refresh")

        return ViewResultDTO(text=f"🚨 <b>System Notification</b>\n\n{error_msg}", kb=builder.as_markup())
