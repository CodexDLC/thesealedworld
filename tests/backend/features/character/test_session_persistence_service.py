from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.backend.features.character.integrations import CharacterSystemIntegrator
from src.backend.features.character.models import Character
from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
from src.backend.features.character.services import CharacterSessionPersistenceService


class FakeCharacterSessions:
    def __init__(self) -> None:
        self.cleared_dirty_ids: list[int] = []

    async def get_session(self, char_id):
        return {
            "schema_version": 1,
            "char_id": char_id,
            "user_id": uuid4(),
            "state": "exploration",
            "prev_state": "scenario",
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
            "symbiote": {"name": "SYSTEM"},
            "updated_at": datetime.now(UTC),
        }

    async def clear_dirty(self, char_id, *, generation=None):
        self.cleared_dirty_ids.append(char_id)


class FakeActiveExpeditionRepo:
    async def get_active_for_character(self, char_id, *, for_update=False):
        return object()


@pytest.mark.unit
async def test_service_delegates_active_session_sync_to_integrator() -> None:
    integrator = MagicMock()
    integrator.sync_active_session = AsyncMock(return_value={"char_id": 7, "state": "exploration"})
    service = CharacterSessionPersistenceService(system_integrator=integrator)

    result = await service.sync_active_session_to_db(7)

    assert result == {"char_id": 7, "state": "exploration"}
    integrator.sync_active_session.assert_awaited_once_with(7)


@pytest.mark.unit
async def test_system_integrator_persists_character_attributes_and_skills() -> None:
    character_repo = MagicMock()
    character_repo.sync_active_session_snapshot = AsyncMock(
        return_value={"state": "exploration", "location_id": "52_58"}
    )
    attributes_repo = MagicMock()
    attributes_repo.upsert_attributes = AsyncMock()
    skill_repo = MagicMock()
    skill_repo.upsert_progress_rows = AsyncMock()

    character_sessions = FakeCharacterSessions()
    integrator = CharacterSystemIntegrator(
        character_sessions=character_sessions,
        character_repo=character_repo,
        attributes_repo=attributes_repo,
        skill_repo=skill_repo,
    )

    result = await integrator.sync_active_session(7)

    assert result["state"] == "exploration"
    assert result["location_id"] == "52_58"
    assert result["skills"] == ["skill_swords"]
    character_repo.sync_active_session_snapshot.assert_awaited_once()
    attributes_repo.upsert_attributes.assert_awaited_once()
    skill_repo.upsert_progress_rows.assert_awaited_once()
    assert character_sessions.cleared_dirty_ids == [7]


@pytest.mark.unit
async def test_system_integrator_does_not_secure_dirty_state_during_active_expedition() -> None:
    character_repo = MagicMock()
    character_repo.sync_active_session_snapshot = AsyncMock()
    attributes_repo = MagicMock()
    attributes_repo.upsert_attributes = AsyncMock()
    skill_repo = MagicMock()
    skill_repo.upsert_progress_rows = AsyncMock()

    character_sessions = FakeCharacterSessions()
    integrator = CharacterSystemIntegrator(
        character_sessions=character_sessions,
        character_repo=character_repo,
        attributes_repo=attributes_repo,
        skill_repo=skill_repo,
        expedition_repo=FakeActiveExpeditionRepo(),
    )

    result = await integrator.sync_active_session(7)

    assert result["state"] == "exploration"
    assert result["location_id"] == "52_58"
    assert result["skills"] == []
    character_repo.sync_active_session_snapshot.assert_not_awaited()
    attributes_repo.upsert_attributes.assert_not_awaited()
    skill_repo.upsert_progress_rows.assert_not_awaited()
    assert character_sessions.cleared_dirty_ids == [7]


@pytest.mark.unit
async def test_character_repository_syncs_active_session_snapshot() -> None:
    character = Character(
        user_id=uuid4(),
        name="Ada",
        gender="female",
        game_stage="scenario",
        prev_game_stage="lobby",
        location_id="52_52",
    )
    character.character_id = 7
    session = MagicMock()
    session.flush = AsyncMock()
    repo = CharacterRepository(session)
    repo.get_by_id = AsyncMock(return_value=character)  # type: ignore[method-assign]
    document = CharacterSessionDocumentDTO.model_validate(await FakeCharacterSessions().get_session(7))

    result = await repo.sync_active_session_snapshot(7, document)

    assert result == {"state": "exploration", "location_id": "52_58"}
    assert character.game_stage == "exploration"
    assert character.prev_game_stage == "scenario"
    assert character.location_id == "52_58"
    assert character.prev_location_id == "52_52"
    assert character.active_sessions == {
        "scenario_id": None,
        "combat_id": None,
        "combat_finalization_id": None,
        "encounter_id": None,
        "arena_id": None,
        "inventory_id": None,
        "death_run_id": None,
        "death_corpse_id": None,
        "active_quest": None,
    }
    assert character.vitals_snapshot["hp"]["cur"] == 90
    session.flush.assert_awaited_once()
