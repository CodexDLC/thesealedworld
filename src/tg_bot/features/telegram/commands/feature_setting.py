from typing import Any, cast

from aiogram.fsm.state import State, StatesGroup

from .contracts.auth_contract import AuthDataProvider
from .logic.orchestrator import StartOrchestrator


# 1. States Definition
class CommandsStates(StatesGroup):
    main = State()


STATES = CommandsStates

# 2. Garbage Collector Settings
GARBAGE_COLLECT = False

# 3. Menu Configuration
MENU_CONFIG = None


# 4. Factory (DI)
def create_orchestrator(container: Any) -> StartOrchestrator:
    """
    Creates the orchestrator instance.
    """
    # In a real project, AuthDataProvider implementation should be in the container.
    # For now, we cast it to satisfy Mypy during template generation.
    auth_provider = getattr(container, "auth_provider", None)

    return StartOrchestrator(auth_provider=cast("AuthDataProvider", auth_provider), settings=container.settings)


def get_router() -> Any:
    """
    Returns the aiogram router for this feature.
    """
    # Standard naming: we use 'handlers' instead of 'router'
    from .handlers.handlers import router

    return router
