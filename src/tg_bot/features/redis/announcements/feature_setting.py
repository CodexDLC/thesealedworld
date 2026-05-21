from typing import Any

from aiogram.fsm.state import StatesGroup


# 1. State Definition
class AnnouncementsStates(StatesGroup):
    pass


STATES = AnnouncementsStates

# 2. Garbage Collector Settings
GARBAGE_COLLECT = False

# 3. Menu Settings
MENU_CONFIG = None


# 4. Factory (DI)
def create_orchestrator(container: Any) -> Any:
    """
    Factory for creating the Announcements feature orchestrator (Redis).
    """
    # Use project-relative import for better discovery
    from .logic.orchestrator import AnnouncementsOrchestrator

    return AnnouncementsOrchestrator(container)


def get_redis_router() -> Any:
    """
    Returns the Redis router for this feature.
    """
    from .handlers import redis_router

    return redis_router
