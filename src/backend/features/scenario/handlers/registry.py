from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.scenario.handlers.tutorial_handler import TutorialScenarioHandler

if TYPE_CHECKING:
    from src.backend.features.scenario.handlers.base_handler import BaseScenarioHandler
    from src.backend.infrastructure.redis.character_session_manager import CharacterSessionManager

_HANDLERS: dict[str, type[BaseScenarioHandler]] = {
    "awakening_rift": TutorialScenarioHandler,
}


def get_handler(quest_key: str, *, character_sessions: CharacterSessionManager) -> BaseScenarioHandler:
    handler_class = _HANDLERS.get(quest_key)
    if handler_class is None:
        raise KeyError(f"Scenario handler not found: {quest_key}")
    return handler_class(character_sessions)
