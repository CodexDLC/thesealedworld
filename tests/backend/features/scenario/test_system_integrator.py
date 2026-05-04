from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.character.events import CharacterEvents
from src.backend.features.scenario.integrations.system_integrator import ScenarioSystemIntegrator


@pytest.mark.unit
async def test_unlock_skills_updates_active_character_runtime() -> None:
    events = MagicMock()
    events.request = AsyncMock(return_value={"status": "ok", "skill_keys": ["skill_swords"]})
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content_manager=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=events,
        redis=MagicMock(),
    )

    await integrator.unlock_skills(7, ["skill_swords"])

    events.request.assert_awaited_once()
    event_type, payload = events.request.await_args.args[:2]
    assert event_type == CharacterEvents.SKILLS_UNLOCK_REQUESTED
    assert payload["char_id"] == 7
    assert payload["skill_keys"] == '["skill_swords"]'
