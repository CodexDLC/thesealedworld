from codex_bot.base import ViewResultDTO

from ..resources.keyboards import build_welcome_keyboard
from ..resources.texts import WELCOME_ADMIN, WELCOME_USER


class CommandsUI:
    """
    Renders UI elements for system commands.
    """

    def render_welcome_screen(self, name: str, is_admin: bool = False) -> ViewResultDTO:
        """
        Renders the initial greeting message using templates from resources.
        """
        raw_text = WELCOME_ADMIN if is_admin else WELCOME_USER
        text = raw_text.format(name=name)

        keyboard = build_welcome_keyboard(is_admin=is_admin)

        return ViewResultDTO(text=text, kb=keyboard)
