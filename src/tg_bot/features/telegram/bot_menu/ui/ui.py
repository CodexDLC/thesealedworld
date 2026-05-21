from typing import Any

from codex_bot.base import ViewResultDTO

from ..resources.keyboards import build_dashboard_keyboard
from ..resources.texts import get_dashboard_title


class BotMenuUI:
    """
    Renders the main dashboard UI.
    """

    def render_dashboard(self, buttons: dict[str, Any], mode: str = "bot_menu") -> ViewResultDTO:
        """
        Generates ViewResultDTO with title, feature descriptions, and keyboard.
        """
        title = get_dashboard_title(mode)

        # Sort for the text list
        sorted_buttons = sorted(buttons.values(), key=lambda x: x.get("priority", 100))

        description_lines = []
        for btn in sorted_buttons:
            icon = btn.get("icon", "")
            label = btn.get("text", "Feature")
            desc = btn.get("description", "")

            line = f"{icon} <b>{label}</b>"
            if desc:
                line += f" — {desc}"
            description_lines.append(line)

        full_text = title
        if description_lines:
            full_text += "\n\nAvailable Features:\n" + "\n".join(description_lines)

        return ViewResultDTO(text=full_text, kb=build_dashboard_keyboard(buttons, mode))
