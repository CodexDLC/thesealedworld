"""
Internal Package Launcher for tg_bot.
This module is responsible for initializing the core components and starting the app.
"""

from typing import Any, cast

from codex_bot.engine.runner import run_bot_app

from .core.config import BotSettings
from .core.container import BotContainer
from .core.factory import build_bot
from .core.logging import setup_logging


def run() -> None:
    """
    Launches the bot application.
    Used by the tg-bot image entrypoint via ``python -m tg_bot.launcher``.
    """
    # Instantiate settings
    settings = BotSettings()

    # Use cast or Any to satisfy the runner's protocol strictly without changing the library core
    run_bot_app(
        settings=cast("Any", settings),
        container_class=cast("Any", BotContainer),
        bot_factory=cast("Any", build_bot),
        setup_logging_func=cast("Any", setup_logging),
    )


if __name__ == "__main__":
    run()
