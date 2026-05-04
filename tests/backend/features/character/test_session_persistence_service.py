from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.backend.features.character.services import CharacterSessionPersistenceService
from src.backend.infrastructure.actor_state.models import Character


class FakeCharacterSessions:
    async def get_session(self, char_id):
        return {
            "schema_version": 1,
            "char_id": char_id,
            "user_id": uuid4(),
            "state": "EXPLORATION",
            "prev_state": "SCENARIO",
            "bio": {
                "name": "Ada",
                "gender": "female",
                "avatar": "/avatar.png",
                "created_at": datetime.now(UTC),
            },
            "location": {"current": "52_58", "prev": "52_52"},
            "vitals": {
                "hp": {"cur": 90, "max": 100, "regen": 1},
                "energy": {"cur": 80, "max": 100, "regen": 1},
                "stamina": {"cur": 70, "max": 100, "regen": 1},
                "last_update": datetime.now(UTC).timestamp(),
            },
            "attributes": {
                "strength": 17,
                "agility": 16,
                "endurance": 15,
                "intellect": 14,
                "memory": 13,
                "mental": 12,
                "perception": 11,
                "projection": 10,
                "prediction": 9,
            },
            "sessions": {"scenario_id": None, "combat_id": None, "inventory_id": None},
            "active_quest": None,
            "metrics": {"gear_score": 0},
            "skills": {"skill_swords": {"xp": 0.25, "unlocked": True, "state": "PLUS"}},
            "symbiote": {"name": "Symbiote"},
            "updated_at": datetime.now(UTC),
        }


@pytest.mark.unit
async def test_sync_active_session_to_db_persists_character_attributes_and_skills() -> None:
    character = Character(
        user_id=uuid4(),
        name="Ada",
        gender="female",
        game_stage="scenario",
        prev_game_stage="lobby",
        location_id="52_52",
    )
    character.character_id = 7
    db_session = MagicMock()
    db_session.scalar = AsyncMock(return_value=character)
    db_session.execute = AsyncMock()
    db_session.flush = AsyncMock()

    service = CharacterSessionPersistenceService(
        db_session=db_session,
        character_sessions=FakeCharacterSessions(),
    )

    result = await service.sync_active_session_to_db(character.character_id)

    assert result["state"] == "EXPLORATION"
    assert character.game_stage == "EXPLORATION"
    assert character.prev_game_stage == "SCENARIO"
    assert character.location_id == "52_58"
    assert character.prev_location_id == "52_52"
    assert character.active_sessions == {"scenario_id": None, "combat_id": None, "inventory_id": None, "active_quest": None}
    assert character.vitals_snapshot["hp"]["cur"] == 90
    assert result["skills"] == ["skill_swords"]
    assert db_session.execute.await_count == 2
    db_session.flush.assert_awaited_once()
