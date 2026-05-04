from typing import Annotated

from fastapi import Depends, Request

from src.backend.features.character.services.status_service import CharacterStatusService
from src.backend.infrastructure.actor_state.managers.session import CharacterSessionManager


def get_character_sessions(request: Request) -> CharacterSessionManager:
    return request.app.state.character_sessions


def get_character_status_service(
    character_sessions: Annotated[CharacterSessionManager, Depends(get_character_sessions)],
) -> CharacterStatusService:
    return CharacterStatusService(character_sessions=character_sessions)
