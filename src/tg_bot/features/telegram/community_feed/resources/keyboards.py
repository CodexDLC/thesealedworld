from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callbacks import CommunityFeedCallback
from .texts import CommunityFeedTexts


def build_main_kb() -> InlineKeyboardMarkup:
    """Main screen keyboard for the CommunityFeed feature."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=CommunityFeedTexts.BUTTON_ACTION,
        callback_data=CommunityFeedCallback(action="action", id=0).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()
