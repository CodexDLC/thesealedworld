from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.game_session.services import session_service
from src.backend.features.game_session.services.session_service import GameSessionService
from src.backend.features.scenario.exceptions import ScenarioSessionNotFound
from src.shared.enums import CoreDomain
from src.shared.schemas import ScenarioPayloadDTO


class FakeCharacterRepository:
    character = SimpleNamespace(
        character_id=7,
        user_id=uuid4(),
        name="Ada",
        game_stage="scenario",
        prev_game_stage="lobby",
    )

    def __init__(self, db_session):
        self.db_session = db_session

    async def get_by_id_and_user_id(self, character_id, user_id):
        return self.character

    async def get_by_id(self, character_id):
        return self.character


class MissingCharacterRepository(FakeCharacterRepository):
    async def get_by_id_and_user_id(self, character_id, user_id):
        return None


def scenario_payload() -> ScenarioPayloadDTO:
    return ScenarioPayloadDTO(
        node_key="rift_entry_01",
        text="Wake up.",
        extra_data={"show_left_sidebar": True, "show_right_sidebar": True},
    )


@pytest.mark.asyncio
async def test_enter_character_resumes_existing_scenario(monkeypatch):
    monkeypatch.setattr(session_service, "CharacterRepository", FakeCharacterRepository)
    scenario = SimpleNamespace(resume=AsyncMock(return_value=scenario_payload()), initialize=AsyncMock())
    service = GameSessionService(db_session=SimpleNamespace(commit=AsyncMock()), scenario_service=scenario)

    response = await service.enter_character(SimpleNamespace(id=FakeCharacterRepository.character.user_id), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.header.previous_state == CoreDomain.LOBBY
    assert response.payload_type == "scenario_screen"
    assert response.payload.extra_data["char_id"] == 7
    scenario.resume.assert_awaited_once_with(7)
    scenario.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_enter_character_initializes_starting_scenario_when_missing(monkeypatch):
    monkeypatch.setattr(session_service, "CharacterRepository", FakeCharacterRepository)
    db_session = SimpleNamespace(commit=AsyncMock())
    scenario = SimpleNamespace(
        resume=AsyncMock(side_effect=ScenarioSessionNotFound(7)),
        initialize=AsyncMock(return_value=scenario_payload()),
    )
    service = GameSessionService(db_session=db_session, scenario_service=scenario)

    response = await service.enter_character(SimpleNamespace(id=FakeCharacterRepository.character.user_id), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.header.previous_state == CoreDomain.LOBBY
    assert response.payload.extra_data["quest_key"] == "awakening_rift"
    scenario.initialize.assert_awaited_once_with(7, "awakening_rift", source="session_enter")
    db_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_enter_character_allows_missing_previous_state_for_first_enter(monkeypatch):
    monkeypatch.setattr(session_service, "CharacterRepository", FakeCharacterRepository)
    monkeypatch.setattr(FakeCharacterRepository.character, "prev_game_stage", None)
    scenario = SimpleNamespace(resume=AsyncMock(return_value=scenario_payload()), initialize=AsyncMock())
    service = GameSessionService(db_session=SimpleNamespace(commit=AsyncMock()), scenario_service=scenario)

    response = await service.enter_character(SimpleNamespace(id=FakeCharacterRepository.character.user_id), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.header.previous_state is None


@pytest.mark.asyncio
async def test_enter_character_rejects_unowned_character(monkeypatch):
    monkeypatch.setattr(session_service, "CharacterRepository", MissingCharacterRepository)
    service = GameSessionService(db_session=SimpleNamespace(), scenario_service=SimpleNamespace())

    with pytest.raises(BusinessLogicException):
        await service.enter_character(SimpleNamespace(id=uuid4()), 7)
