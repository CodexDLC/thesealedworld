from __future__ import annotations

from typing import Any

from loguru import logger

from src.backend.core.database.session import get_session_context
from src.backend.features.character.integrations import CharacterSystemIntegrator
from src.backend.features.character.services import CharacterSessionPersistenceService


async def sync_active_session_task(ctx: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    char_id = int(payload["char_id"])
    redis_managers = ctx["redis_managers"]
    repositories = ctx["repositories"]

    logger.info("CharacterTask | sync_active_session start char_id={}", char_id)
    async with get_session_context() as session:
        actor_state = repositories.actor_state(session)
        service = CharacterSessionPersistenceService(
            system_integrator=CharacterSystemIntegrator(
                character_sessions=redis_managers.character_sessions,
                character_repo=actor_state.characters,
                attributes_repo=actor_state.attributes,
                skill_repo=actor_state.skills,
            ),
        )
        result = await service.sync_active_session_to_db(char_id)

    logger.info("CharacterTask | sync_active_session complete char_id={}", char_id)
    return {"status": "ok", **result}
