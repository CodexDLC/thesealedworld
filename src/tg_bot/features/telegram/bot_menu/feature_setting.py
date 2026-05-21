from typing import Any

from aiogram import Router

from .logic.orchestrator import BotMenuOrchestrator

# 1. States Definition (Menu usually doesn't have its own states)
STATES = None

# 2. Garbage Collector Settings
GARBAGE_COLLECT = False

# 3. Menu Configuration
# The Dashboard itself is not a feature in the menu list
MENU_CONFIG = None


# 4. Factory (DI)
def create_orchestrator(container: Any) -> BotMenuOrchestrator:
    """
    Creates the dashboard orchestrator instance.
    """
    return BotMenuOrchestrator()


def get_router() -> Router:
    """
    Returns the aiogram router for this feature.
    """
    from .handlers.handlers import router

    return router
