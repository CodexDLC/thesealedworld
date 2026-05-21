# клавиатуры хранять функции создания клавиатур
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Accessing other features should be done with project prefix or relative imports
from tg_bot.features.telegram.bot_menu.resources.callbacks import DashboardCallback


def build_welcome_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Keyboards for the welcome screen.
    Redirects user to the Dashboard feature.
    """
    builder = InlineKeyboardBuilder()

    launch_text = "🚀 Launch App"
    admin_text = "🛠 Admin Panel"

    builder.button(text=launch_text, callback_data=DashboardCallback(action="select", target="bot_menu").pack())

    if is_admin:
        builder.button(
            text=admin_text,
            callback_data=DashboardCallback(action="select", target="dashboard_admin").pack(),
        )

    builder.adjust(1)
    return builder.as_markup()
