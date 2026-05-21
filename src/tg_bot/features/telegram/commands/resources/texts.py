# текст хранит допустим текст кнопок и всего такого


"""
Texts for basic bot commands (Welcome, Help, etc.).
Used as fallbacks if i18n is not configured.
"""


def get_help_text() -> str:
    """Returns the help message."""
    return (
        "<b>🆘 Help Center</b>\n\n/start — Return to welcome screen\n/help — Show this message\n/menu — Open dashboard"
    )


WELCOME_USER = (
    "<b>👋 Hello, {name}!</b>\n\nWelcome to our bot. Ready to explore? Click the button below to start your journey."
)

WELCOME_ADMIN = "<b>👋 Hello, Administrator {name}!</b>\n\nYou have elevated privileges. Choose your workspace below:"
