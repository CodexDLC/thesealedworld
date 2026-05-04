from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.shared.schemas import CreateCharacterRequestDTO, ScenarioPayloadDTO


@pytest.mark.unit
class TestCharacterCreationService:
    @pytest.fixture
    def db_session(self):
        return MagicMock()

    @pytest.fixture
    def character_sessions(self):
        return MagicMock()

    @pytest.fixture
    def scenario_service(self):
        return MagicMock()

    @pytest.fixture
    def service(self, db_session, character_sessions, scenario_service):
        return CharacterCreationService(db_session, character_sessions, scenario_service)

    async def test_create_and_enter_success(self, service, db_session, character_sessions, scenario_service):
        import uuid
        user_id = uuid.uuid4()
        user = MagicMock(id=user_id)
        dto = CreateCharacterRequestDTO(name="NewHero", gender="male")

        # Mock slot available
        db_session.scalar = AsyncMock(return_value=1)

        # Mock database actions
        db_session.flush = AsyncMock()
        db_session.commit = AsyncMock()
        db_session.execute = AsyncMock()

        # Mock char_id assignment (happens during add/flush usually but we can manually set it on character)
        def side_effect_add(char):
            char.character_id = 123

        db_session.add.side_effect = side_effect_add

        # Mock session creation
        character_sessions.create_session = AsyncMock()

        # Mock scenario service
        scenario_payload = MagicMock(spec=ScenarioPayloadDTO)
        scenario_service.initialize = AsyncMock(return_value=scenario_payload)
        scenario_service.finalize = AsyncMock()

        result = await service.create_and_enter(user, dto)

        assert result == scenario_payload
        assert db_session.add.called
        assert character_sessions.create_session.called
        assert scenario_service.initialize.called

    async def test_ensure_slot_available_fails(self, service, db_session):
        user = MagicMock(id=1)
        db_session.scalar = AsyncMock(return_value=4)

        with pytest.raises(BusinessLogicException) as exc:
            await service._ensure_slot_available(user)
        assert "slot limit reached" in str(exc.value)
