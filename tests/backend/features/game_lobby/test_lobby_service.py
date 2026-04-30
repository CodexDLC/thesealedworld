import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.shared.schemas import GameLobbyPayloadDTO

@pytest.mark.unit
class TestGameLobbyService:
    async def test_get_start_payload(self):
        service = GameLobbyService()
        user = MagicMock(id=1)
        db_session = MagicMock()

        char = MagicMock()
        char.character_id = 10
        char.name = "Hero"
        char.game_stage = "lobby"
        mock_result = MagicMock()
        mock_result.all.return_value = [char]
        db_session.scalars = AsyncMock(return_value=mock_result)

        payload = await service.get_start_payload(user, db_session)

        assert isinstance(payload, GameLobbyPayloadDTO)
        assert len(payload.slots) == 4
        assert payload.slots[0].is_empty is False
        assert payload.slots[0].name == "Hero"
        assert payload.slots[1].is_empty is True
        assert payload.can_start is True

    async def test_get_start_payload_full(self):
        service = GameLobbyService()
        user = MagicMock(id=1)
        db_session = MagicMock()

        chars = []
        for i in range(4):
            c = MagicMock()
            c.character_id = i
            c.name = f"Hero{i}"
            c.game_stage = "lobby"
            chars.append(c)

        mock_result = MagicMock()
        mock_result.all.return_value = chars
        db_session.scalars = AsyncMock(return_value=mock_result)

        payload = await service.get_start_payload(user, db_session)
        assert payload.can_start is False
        assert all(not slot.is_empty for slot in payload.slots)
