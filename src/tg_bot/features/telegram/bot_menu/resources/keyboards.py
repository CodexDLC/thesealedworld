from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callbacks import DashboardCallback


def build_dashboard_keyboard(buttons: dict[str, Any], mode: str = "bot_menu") -> InlineKeyboardMarkup:
    """
    Assembles the dashboard keyboard based on discovered feature buttons.
    """
    builder = InlineKeyboardBuilder()

    # 1. Sort feature buttons by priority
    sorted_buttons = sorted(buttons.values(), key=lambda x: x.get("priority", 100))

    # 2. Add buttons
    for btn_data in sorted_buttons:
        icon = btn_data.get("icon", "")
        label = btn_data.get("text", "Feature")
        text = f"{icon} {label}".strip()
        key = str(btn_data.get("key"))

        callback = DashboardCallback(action="select", target=key).pack()
        builder.button(text=text, callback_data=callback)

    builder.adjust(2)

    # 3. Add system buttons
    if mode == "dashboard_admin":
        builder.row()

        back_text = "🔙 Back to User Menu"

        builder.button(
            text=back_text,
            callback_data=DashboardCallback(action="select", target="bot_menu").pack(),
        )

    return builder.as_markup()
