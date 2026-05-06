from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.game_lobby.integrations import CreatedLobbyCharacter
from src.backend.features.game_lobby.services.character_creation_service import CharacterCreationService
from src.shared.schemas import CreateCharacterRequestDTO, ScenarioPayloadDTO


@pytest.mark.unit
class TestCharacterCreationService:
    @pytest.fixture
    def integration(self):
        return MagicMock()

    @pytest.fixture
    def service(self, integration):
        return CharacterCreationService(integration)

    async def test_create_and_enter_success(self, service, integration):
        user_id = uuid4()
        user = MagicMock(id=user_id)
        dto = CreateCharacterRequestDTO(name="NewHero", gender="male")
        created_character = CreatedLobbyCharacter(
            character_id=123,
            user_id=user_id,
            name="NewHero",
            gender="male",
            avatar_url="/static/images/avatars/silhouette_m.png",
            created_at=datetime.now(UTC),
            location_id="52_52",
        )

        integration.count_user_characters = AsyncMock(return_value=1)
        integration.create_character = AsyncMock(return_value=created_character)
        integration.create_active_session = AsyncMock()
        scenario_payload = MagicMock(spec=ScenarioPayloadDTO)
        integration.initialize_starting_scenario = AsyncMock(return_value=scenario_payload)
        integration.mark_character_entered_scenario = AsyncMock()

        result = await service.create_and_enter(user, dto)

        assert result == scenario_payload
        assert integration.create_character.called
        assert integration.create_active_session.called
        assert integration.initialize_starting_scenario.called
        assert integration.mark_character_entered_scenario.called

    async def test_ensure_slot_available_fails(self, service, integration):
        user = MagicMock(id=1)
        integration.count_user_characters = AsyncMock(return_value=4)

        with pytest.raises(BusinessLogicException) as exc:
            await service._ensure_slot_available(user)
        assert "slot limit reached" in str(exc.value)
