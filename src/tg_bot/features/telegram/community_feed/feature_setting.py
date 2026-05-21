from typing import Any

from aiogram.fsm.state import State, StatesGroup


# 1. State Definition
class CommunityFeedStates(StatesGroup):
    main = State()


STATES = CommunityFeedStates

# 2. Garbage Collector Settings
GARBAGE_COLLECT = True

# 3. Menu Settings
MENU_CONFIG = {
    "key": "community_feed",
    "text": "CommunityFeed",
    "description": "Description of the CommunityFeed feature",
    "target_state": "community_feed",
    "priority": 50,
    "is_admin": False,
    "is_superuser": False,
}


# 4. Factory (DI)
def create_orchestrator(container: Any) -> Any:
    """
    Creates the orchestrator instance.
    """
    from .logic.orchestrator import CommunityFeedOrchestrator

    return CommunityFeedOrchestrator(container)
