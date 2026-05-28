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
            avatar_url="/static/images/avatars/silhouette_m.webp",
            created_at=datetime.now(UTC),
            location_id="52_52",
        )

        integration.count_user_characters = AsyncMock(return_value=1)
        integration.character_name_exists = AsyncMock(return_value=False)
        integration.create_character = AsyncMock(return_value=created_character)
        integration.materialize_starting_imprint = AsyncMock(
            return_value={"imprint_key": "starter_guard_01", "item_ids": ["item-1"]}
        )
        integration.create_active_session = AsyncMock()
        scenario_payload = MagicMock(spec=ScenarioPayloadDTO)
        integration.initialize_starting_scenario = AsyncMock(return_value=scenario_payload)
        integration.release_other_active_sessions = AsyncMock()
        integration.mark_character_entered_scenario = AsyncMock()

        result = await service.create_and_enter(user, dto)

        assert result == scenario_payload
        assert integration.create_character.called
        assert integration.create_character.await_args.kwargs["name"] == "NewHero"
        assert integration.create_character.await_args.kwargs["name_key"] == "newhero"
        integration.materialize_starting_imprint.assert_awaited_once_with(
            created_character,
            seed=f"{user_id}:123:newhero",
        )
        assert integration.create_active_session.called
        assert integration.initialize_starting_scenario.called
        assert integration.initialize_starting_scenario.await_args.kwargs["npc_key"] == "portal_pad_guide"
        integration.release_other_active_sessions.assert_awaited_once_with(user_id, 123)
        assert integration.mark_character_entered_scenario.called
        assert result.extra_data["starting_imprint"]["imprint_key"] == "starter_guard_01"

    async def test_ensure_slot_available_fails(self, service, integration):
        user = MagicMock(id=1)
        integration.count_user_characters = AsyncMock(return_value=4)

        with pytest.raises(BusinessLogicException) as exc:
            await service._ensure_slot_available(user)
        assert "Лимит персонажей достигнут" in str(exc.value)

    async def test_create_and_enter_rejects_taken_name(self, service, integration):
        user = MagicMock(id=1)
        integration.character_name_exists = AsyncMock(return_value=True)

        with pytest.raises(BusinessLogicException, match="Имя уже занято"):
            await service.create_and_enter(user, CreateCharacterRequestDTO(name="NewHero", gender="male"))

        integration.count_user_characters.assert_not_called()

    async def test_create_and_enter_rejects_reserved_name(self, service, integration):
        user = MagicMock(id=1)
        integration.character_name_exists = AsyncMock(return_value=False)

        with pytest.raises(BusinessLogicException, match="зарезервировано"):
            await service.create_and_enter(user, CreateCharacterRequestDTO(name="admin", gender="male"))

        integration.character_name_exists.assert_not_called()
        integration.count_user_characters.assert_not_called()

    async def test_name_availability_reports_taken_name(self, service, integration):
        integration.character_name_exists = AsyncMock(return_value=True)

        result = await service.check_name_availability("NewHero")

        assert result.available is False
        assert result.name == "NewHero"
        assert result.name_key == "newhero"
        assert result.code == "name_taken"

    async def test_name_availability_rejects_reserved_name(self, service, integration):
        integration.character_name_exists = AsyncMock(return_value=False)

        result = await service.check_name_availability("admin")

        assert result.available is False
        assert result.code == "reserved_name"
        integration.character_name_exists.assert_not_called()
