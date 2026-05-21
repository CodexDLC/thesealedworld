from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callbacks import AnnouncementsCallback


def build_task_control_kb(task_id: str) -> InlineKeyboardMarkup:
    """Control keyboard for background tasks."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Retry", callback_data=AnnouncementsCallback(action="retry", task_id=task_id).pack())
    builder.button(text="🗑 Dismiss", callback_data=AnnouncementsCallback(action="dismiss", task_id=task_id).pack())
    builder.adjust(2)
    return builder.as_markup()
