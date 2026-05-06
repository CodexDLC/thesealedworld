from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import src.backend.features.game_session.integrations.session_integrator as session_integrator
from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.game_session.integrations import GameSessionCharacter, GameSessionIntegrator
from src.backend.features.game_session.services.session_service import GameSessionService
from src.backend.features.scenario.exceptions import ScenarioSessionNotFound
from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
from src.shared.enums import CoreDomain
from src.shared.schemas import ScenarioPayloadDTO


class FakeGameSessionIntegrator:
    character = GameSessionCharacter(
        character_id=7,
        name="Ada",
        game_stage="scenario",
        prev_game_stage="lobby",
    )

    def __init__(self, *, character=None, payload=None):
        self.character = self.character if character is None else character
        self.payload = scenario_payload() if payload is None else payload
        self.get_owned_character = AsyncMock(return_value=self.character)
        self.get_active_session = AsyncMock(return_value=None)
        self.resume_or_initialize_scenario = AsyncMock(return_value=self.payload)


class MissingCharacterIntegrator(FakeGameSessionIntegrator):
    def __init__(self):
        super().__init__(character=None)
        self.get_owned_character = AsyncMock(return_value=None)


class FakeCharacterRepository:
    character = SimpleNamespace()

    def __init__(self, db_session):
        self.db_session = db_session

    async def get_by_id_and_user_id(self, character_id, user_id):
        return self.character

    async def get_by_id(self, character_id):
        return self.character

    async def set_character_state(self, character_id, game_stage, *, prev_game_stage=None):
        self.character.game_stage = game_stage
        self.character.prev_game_stage = prev_game_stage
        return True

    async def commit(self):
        await self.db_session.commit()


def reset_fake_repository_character() -> None:
    FakeCharacterRepository.character = SimpleNamespace(
        character_id=7,
        name="Ada",
        game_stage="lobby",
        prev_game_stage=None,
    )


def scenario_payload() -> ScenarioPayloadDTO:
    return ScenarioPayloadDTO(
        node_key="rift_entry_01",
        text="Wake up.",
        extra_data={"show_left_sidebar": True, "show_right_sidebar": True},
    )


@pytest.mark.asyncio
async def test_enter_character_resumes_existing_scenario():
    integrator = FakeGameSessionIntegrator()
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=uuid4()), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.header.previous_state == CoreDomain.LOBBY
    assert response.payload_type == "scenario_screen"
    integrator.resume_or_initialize_scenario.assert_awaited_once_with(
        7,
        quest_key="awakening_rift",
        source="session_enter",
        previous_state=CoreDomain.LOBBY,
    )


@pytest.mark.asyncio
async def test_enter_character_returns_integrator_scenario_payload():
    payload = scenario_payload()
    payload.extra_data = {"quest_key": "awakening_rift", "char_id": 7}
    integrator = FakeGameSessionIntegrator(payload=payload)
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=uuid4()), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.header.previous_state == CoreDomain.LOBBY
    assert response.payload.extra_data["quest_key"] == "awakening_rift"
    assert response.payload.extra_data["char_id"] == 7


@pytest.mark.asyncio
async def test_enter_character_allows_missing_previous_state_for_first_enter():
    character = GameSessionCharacter(
        character_id=7,
        name="Ada",
        game_stage="scenario",
        prev_game_stage=None,
    )
    service = GameSessionService(integrator=FakeGameSessionIntegrator(character=character))

    response = await service.enter_character(SimpleNamespace(id=uuid4()), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.header.previous_state is None


@pytest.mark.asyncio
async def test_enter_character_prefers_hot_active_session_state_over_persistent_stage():
    character = GameSessionCharacter(
        character_id=7,
        name="Ada",
        game_stage="exploration",
        prev_game_stage="scenario",
    )
    integrator = FakeGameSessionIntegrator(character=character)
    integrator.get_active_session = AsyncMock(
        return_value=CharacterSessionDocumentDTO.model_validate(
            {
                "char_id": 7,
                "user_id": uuid4(),
                "state": "arena",
                "prev_state": "exploration",
                "bio": {
                    "name": "Ada",
                    "gender": "female",
                    "created_at": "2026-05-05T00:00:00Z",
                },
                "location": {"current": "52_51", "prev": "52_52"},
                "updated_at": "2026-05-05T00:00:00Z",
            }
        )
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=integrator.get_active_session.return_value.user_id), 7)

    assert response.header.current_state == CoreDomain.ARENA
    assert response.header.previous_state == CoreDomain.EXPLORATION
    assert response.payload_type == "arena_session"
    assert response.payload["source"] == "hot_ac"
    integrator.resume_or_initialize_scenario.assert_not_awaited()


@pytest.mark.asyncio
async def test_enter_character_rejects_unowned_character():
    service = GameSessionService(integrator=MissingCharacterIntegrator())

    with pytest.raises(BusinessLogicException):
        await service.enter_character(SimpleNamespace(id=uuid4()), 7)


@pytest.mark.asyncio
async def test_integrator_returns_owned_character(monkeypatch):
    reset_fake_repository_character()
    monkeypatch.setattr(session_integrator, "CharacterRepository", FakeCharacterRepository)
    integrator = GameSessionIntegrator(db_session=SimpleNamespace(), scenario_service=SimpleNamespace())

    character = await integrator.get_owned_character(7, uuid4())

    assert character == GameSessionCharacter(
        character_id=7,
        name="Ada",
        game_stage="lobby",
        prev_game_stage=None,
    )


@pytest.mark.asyncio
async def test_integrator_resumes_existing_scenario(monkeypatch):
    reset_fake_repository_character()
    monkeypatch.setattr(session_integrator, "CharacterRepository", FakeCharacterRepository)
    scenario = SimpleNamespace(resume=AsyncMock(return_value=scenario_payload()), initialize=AsyncMock())
    integrator = GameSessionIntegrator(db_session=SimpleNamespace(commit=AsyncMock()), scenario_service=scenario)

    payload = await integrator.resume_or_initialize_scenario(
        7,
        quest_key="awakening_rift",
        source="session_enter",
    )

    assert payload.extra_data["char_id"] == 7
    assert payload.extra_data["quest_key"] == "awakening_rift"
    scenario.resume.assert_awaited_once_with(7)
    scenario.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_integrator_initializes_starting_scenario_when_missing(monkeypatch):
    reset_fake_repository_character()
    monkeypatch.setattr(session_integrator, "CharacterRepository", FakeCharacterRepository)
    db_session = SimpleNamespace(commit=AsyncMock())
    scenario = SimpleNamespace(
        resume=AsyncMock(side_effect=ScenarioSessionNotFound(7)),
        initialize=AsyncMock(return_value=scenario_payload()),
    )
    integrator = GameSessionIntegrator(db_session=db_session, scenario_service=scenario)

    payload = await integrator.resume_or_initialize_scenario(
        7,
        quest_key="awakening_rift",
        source="session_enter",
    )

    assert payload.extra_data["quest_key"] == "awakening_rift"
    assert FakeCharacterRepository.character.game_stage == CoreDomain.SCENARIO.value
    assert FakeCharacterRepository.character.prev_game_stage == CoreDomain.LOBBY.value
    scenario.initialize.assert_awaited_once_with(7, "awakening_rift", source="session_enter")
    db_session.commit.assert_awaited_once()
