import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import src.backend.features.game_lobby.integrations.system_integrator as lobby_integrator
from src.backend.core.exceptions import BusinessLogicException
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
                    avatar_url="/static/images/avatars/silhouette_m.webp",
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
        assert payload.slots[0].avatar_url == "/static/images/avatars/silhouette_m.webp"
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
            return SimpleNamespace(character_id=character_id, name="Ada")

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

    await integration.delete_owned_character(user_id=uuid.uuid4(), character_id=42, confirm_name="Ada")

    assert operations == [
        "load_character",
        "cleanup_scenario:42",
        "delete_session:42",
        "transfer_items:42",
        "delete:42",
        "commit",
    ]


@pytest.mark.unit
async def test_delete_owned_character_rejects_wrong_confirmation_name():
    operations: list[str] = []

    class FakeCharacterRepository:
        async def get_by_id_and_user_id(self, character_id, user_id):
            operations.append("load_character")
            return SimpleNamespace(character_id=character_id, name="Ada")

    class FakeCharacterSessions:
        async def delete_session(self, character_id):
            operations.append(f"delete_session:{character_id}")

    integration = GameLobbyIntegration(
        character_repo=FakeCharacterRepository(),
        character_sessions=FakeCharacterSessions(),
    )

    with pytest.raises(BusinessLogicException, match="Имя подтверждения не совпадает"):
        await integration.delete_owned_character(user_id=uuid.uuid4(), character_id=42, confirm_name="Other")

    assert operations == ["load_character"]


@pytest.mark.unit
async def test_bootstrap_existing_active_character_reuses_runtime_session(monkeypatch):
    user_id = uuid.uuid4()
    operations: list[str] = []

    class FakeSessions:
        async def exists(self, character_id):
            operations.append(f"exists:{character_id}")
            return True

        async def get_session(self, character_id):
            operations.append(f"get:{character_id}")
            return {
                "char_id": character_id,
                "user_id": str(user_id),
                "state": "scenario",
                "prev_state": "lobby",
                "bio": {
                    "name": "Ada",
                    "gender": "female",
                    "created_at": "2026-05-05T00:00:00Z",
                },
                "sessions": {"scenario_id": "scenario-session-1"},
                "updated_at": "2026-05-05T00:00:00Z",
            }

    class FakeStateIntegrator:
        def __init__(self, **kwargs):
            pass

        async def bootstrap_active_session(self, user_id, character_id):
            operations.append(f"bootstrap:{character_id}")
            return SimpleNamespace(char_id=character_id, model_dump=lambda mode: {"char_id": character_id})

    monkeypatch.setattr(lobby_integrator, "CharacterStateIntegrator", FakeStateIntegrator)
    integration = GameLobbyIntegration(
        character_repo=SimpleNamespace(),
        skill_repo=SimpleNamespace(),
        character_sessions=FakeSessions(),
    )
    integration.release_active_character = AsyncMock(side_effect=lambda **kwargs: operations.append("release"))
    integration.cleanup_runtime = AsyncMock(side_effect=lambda character_id: operations.append(f"cleanup:{character_id}"))

    session_doc = await integration.bootstrap_active_character(user_id=user_id, character_id=7)

    assert session_doc.char_id == 7
    assert session_doc.sessions.scenario_id == "scenario-session-1"
    assert operations == ["exists:7", "get:7"]
    integration.release_active_character.assert_not_awaited()
    integration.cleanup_runtime.assert_not_awaited()
