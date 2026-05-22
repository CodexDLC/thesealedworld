from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.backend.features.character.repositories.character import CharacterRepository


@pytest.mark.unit
async def test_character_repository_count_all() -> None:
    calls: list[object] = []

    class FakeSession:
        async def scalar(self, stmt):
            calls.append(stmt)
            return 14

    repo = CharacterRepository(FakeSession())

    result = await repo.count_all()

    assert result == 14
    assert len(calls) == 1


@pytest.mark.unit
async def test_game_lobby_integration_counts_all_characters() -> None:
    from src.backend.features.game_lobby.integrations import GameLobbyIntegration

    repo = SimpleNamespace(count_all=AsyncMock(return_value=6))
    integration = GameLobbyIntegration(character_repo=repo, character_sessions=SimpleNamespace())

    result = await integration.count_all_characters()

    assert result == 6
    repo.count_all.assert_awaited_once_with()
