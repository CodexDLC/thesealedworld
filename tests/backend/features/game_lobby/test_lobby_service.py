from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.game_lobby.integrations import LobbyCharacterSummary
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
