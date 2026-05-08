import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.game_lobby.integrations import GameLobbyIntegration, LobbyCharacterSummary
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.shared.schemas import GameLobbyPayloadDTO


@pytest.mark.unit
class TestGameLobbyService:
    async def test_get_start_payload(self):
        user = MagicMock(id=1)
        integration = MagicMock()
        integration.list_user_characters = AsyncMock(
            return_value=[
                LobbyCharacterSummary(
                    character_id=10,
                    name="Hero",
                    avatar_url="/static/images/avatars/silhouette_m.png",
                    status="lobby",
                    presence_status="online",
                )
            ]
        )
        service = GameLobbyService(integration)

        payload = await service.get_start_payload(user)

        assert isinstance(payload, GameLobbyPayloadDTO)
        assert len(payload.slots) == 4
        assert payload.slots[0].is_empty is False
        assert payload.slots[0].name == "Hero"
        assert payload.slots[0].avatar_url == "/static/images/avatars/silhouette_m.png"
        assert payload.slots[0].presence_status == "online"
        assert payload.slots[1].is_empty is True
        assert payload.slots[1].presence_status == "offline"
        assert payload.can_start is True

    async def test_get_start_payload_full(self):
        user = MagicMock(id=1)
        chars = [
            LobbyCharacterSummary(
                character_id=i,
                name=f"Hero{i}",
                avatar_url=f"/avatar-{i}.png",
                status="lobby",
                presence_status="offline",
            )
            for i in range(4)
        ]
        integration = MagicMock()
        integration.list_user_characters = AsyncMock(return_value=chars)
        service = GameLobbyService(integration)

        payload = await service.get_start_payload(user)
        assert payload.can_start is False
        assert all(not slot.is_empty for slot in payload.slots)


@pytest.mark.unit
async def test_delete_owned_character_transfers_item_instances_to_system_before_delete():
    operations: list[str] = []

    class FakeCharacterRepository:
        async def get_by_id_and_user_id(self, character_id, user_id):
            operations.append("load_character")
            return SimpleNamespace(character_id=character_id)

        async def delete(self, character_id):
            operations.append(f"delete:{character_id}")

        async def commit(self):
            operations.append("commit")

    class FakeScenarioService:
        async def cleanup(self, character_id):
            operations.append(f"cleanup_scenario:{character_id}")

    class FakeCharacterSessions:
        async def delete_session(self, character_id):
            operations.append(f"delete_session:{character_id}")

    class FakeItemPersistence:
        async def transfer_deleted_character_items_to_system(self, character_id):
            operations.append(f"transfer_items:{character_id}")
            return 2

    integration = GameLobbyIntegration(
        character_repo=FakeCharacterRepository(),
        item_persistence=FakeItemPersistence(),
        character_sessions=FakeCharacterSessions(),
        scenario_service=FakeScenarioService(),
    )

    await integration.delete_owned_character(user_id=uuid.uuid4(), character_id=42)

    assert operations == [
        "load_character",
        "cleanup_scenario:42",
        "delete_session:42",
        "transfer_items:42",
        "delete:42",
        "commit",
    ]
