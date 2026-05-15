import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.frontend.features.auth.dto.user import UserResponse
from src.frontend.game_features.game_lobby.services.lobby_page_service import GameLobbyPageService
from src.frontend.integrations.backend_api.game_lobby import (
    BackendGameLobbyApi,
    GameLobbyCharacterCreateRequest,
    GameLobbyCharacterDeleteRequest,
    GameLobbyCharacterReleaseRequest,
    GameLobbyCharacterSelectRequest,
)
from src.shared.enums import CoreDomain
from src.shared.schemas import (
    CoreResponseDTO,
    CreateCharacterRequestDTO,
    DeleteCharacterRequestDTO,
    EnterCharacterRequestDTO,
    GameStateHeader,
)


def _user() -> UserResponse:
    return UserResponse(
        id=uuid.uuid4(),
        email="player@example.test",
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(),
    )


@pytest.mark.unit
async def test_lobby_page_service_bootstraps_with_site_user_context() -> None:
    user = _user()
    api = SimpleNamespace(bootstrap=AsyncMock(return_value="response"))

    response = await GameLobbyPageService(api).get_view(user)

    assert response == "response"
    api.bootstrap.assert_awaited_once()
    context = api.bootstrap.await_args.args[0]
    assert context.user_id == user.id
    assert context.email == user.email


@pytest.mark.unit
async def test_lobby_page_service_selects_character_with_site_user_context() -> None:
    user = _user()
    api = SimpleNamespace(select=AsyncMock(return_value="response"))

    response = await GameLobbyPageService(api).select(user, EnterCharacterRequestDTO(character_id=7))

    assert response == "response"
    api.select.assert_awaited_once()
    dto = api.select.await_args.args[0]
    assert dto.user_id == user.id
    assert dto.email == user.email
    assert dto.character_id == 7


@pytest.mark.unit
async def test_lobby_page_service_creates_character_with_site_user_context() -> None:
    user = _user()
    api = SimpleNamespace(create=AsyncMock(return_value="response"))
    dto = CreateCharacterRequestDTO(name="Ada", gender="female")

    response = await GameLobbyPageService(api).start(user, dto)

    assert response == "response"
    api.create.assert_awaited_once()
    payload = api.create.await_args.args[0]
    assert payload.user_id == user.id
    assert payload.email == user.email
    assert payload.character == dto


@pytest.mark.unit
async def test_lobby_page_service_releases_character_with_site_user_context() -> None:
    user = _user()
    api = SimpleNamespace(release=AsyncMock(return_value="response"))

    response = await GameLobbyPageService(api).release(user, EnterCharacterRequestDTO(character_id=7))

    assert response == "response"
    api.release.assert_awaited_once()
    payload = api.release.await_args.args[0]
    assert payload.user_id == user.id
    assert payload.email == user.email
    assert payload.character.character_id == 7


@pytest.mark.unit
async def test_lobby_page_service_deletes_character_with_site_user_context() -> None:
    user = _user()
    api = SimpleNamespace(delete_character=AsyncMock(return_value="response"))
    dto = DeleteCharacterRequestDTO(character_id=7, confirm_name="Ada")

    response = await GameLobbyPageService(api).delete(user, dto)

    assert response == "response"
    api.delete_character.assert_awaited_once()
    payload = api.delete_character.await_args.args[0]
    assert payload.user_id == user.id
    assert payload.email == user.email
    assert payload.character == dto


@pytest.mark.unit
async def test_backend_game_lobby_api_select_uses_internal_endpoint() -> None:
    calls = []

    class _Api(BackendGameLobbyApi):
        async def _request(self, method, endpoint, response_model=None, **kwargs):
            calls.append((method, endpoint, response_model, kwargs))
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY),
                payload={"game_tokens": {"access_token": "game-access"}},
                payload_type="game_character_selected",
            )

    user_id = uuid.uuid4()
    api = _Api(client=SimpleNamespace(), base_url="http://backend")

    response = await api.select(GameLobbyCharacterSelectRequest(user_id=user_id, character_id=7))

    assert response.payload["game_tokens"]["access_token"] == "game-access"
    method, endpoint, _, kwargs = calls[0]
    assert method == "POST"
    assert endpoint == "/game-lobby/select"
    assert kwargs["json"]["user_id"] == str(user_id)
    assert kwargs["json"]["character_id"] == 7


@pytest.mark.unit
async def test_backend_game_lobby_api_create_uses_internal_endpoint() -> None:
    calls = []

    class _Api(BackendGameLobbyApi):
        async def _request(self, method, endpoint, response_model=None, **kwargs):
            calls.append((method, endpoint, response_model, kwargs))
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.SCENARIO),
                payload={},
                payload_type="scenario_screen",
            )

    user_id = uuid.uuid4()
    api = _Api(client=SimpleNamespace(), base_url="http://backend")

    await api.create(
        GameLobbyCharacterCreateRequest(
            user_id=user_id,
            character=CreateCharacterRequestDTO(name="Ada", gender="female"),
        )
    )

    method, endpoint, _, kwargs = calls[0]
    assert method == "POST"
    assert endpoint == "/game-lobby/create"
    assert "headers" not in kwargs
    assert kwargs["json"]["user_id"] == str(user_id)
    assert kwargs["json"]["character"]["name"] == "Ada"


@pytest.mark.unit
async def test_backend_game_lobby_api_release_uses_internal_endpoint() -> None:
    calls = []

    class _Api(BackendGameLobbyApi):
        async def _request(self, method, endpoint, response_model=None, **kwargs):
            calls.append((method, endpoint, response_model, kwargs))
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY),
                payload={"released": True},
                payload_type="active_character_release",
            )

    user_id = uuid.uuid4()
    api = _Api(client=SimpleNamespace(), base_url="http://backend")

    await api.release(
        GameLobbyCharacterReleaseRequest(
            user_id=user_id,
            character=EnterCharacterRequestDTO(character_id=7),
        )
    )

    method, endpoint, _, kwargs = calls[0]
    assert method == "POST"
    assert endpoint == "/game-lobby/release-selected"
    assert "headers" not in kwargs
    assert kwargs["json"]["user_id"] == str(user_id)
    assert kwargs["json"]["character"]["character_id"] == 7


@pytest.mark.unit
async def test_backend_game_lobby_api_delete_uses_internal_endpoint() -> None:
    calls = []

    class _Api(BackendGameLobbyApi):
        async def _request(self, method, endpoint, response_model=None, **kwargs):
            calls.append((method, endpoint, response_model, kwargs))
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY),
                payload={},
                payload_type="lobby_start",
            )

    user_id = uuid.uuid4()
    api = _Api(client=SimpleNamespace(), base_url="http://backend")

    await api.delete_character(
        GameLobbyCharacterDeleteRequest(
            user_id=user_id,
            character=DeleteCharacterRequestDTO(character_id=7, confirm_name="Ada"),
        )
    )

    method, endpoint, _, kwargs = calls[0]
    assert method == "POST"
    assert endpoint == "/game-lobby/delete-character"
    assert "headers" not in kwargs
    assert kwargs["json"]["user_id"] == str(user_id)
    assert kwargs["json"]["character"]["character_id"] == 7
    assert kwargs["json"]["character"]["confirm_name"] == "Ada"


@pytest.mark.unit
async def test_backend_game_lobby_api_refresh_token_uses_internal_endpoint() -> None:
    calls = []

    class _Api(BackendGameLobbyApi):
        async def _request(self, method, endpoint, response_model=None, **kwargs):
            calls.append((method, endpoint, response_model, kwargs))
            return response_model.model_validate(
                {
                    "access_token": "new-game-access",
                    "refresh_token": "new-game-refresh",
                    "expires_in": 900,
                    "refresh_expires_in": 43200,
                }
            )

    api = _Api(client=SimpleNamespace(), base_url="http://backend")

    tokens = await api.refresh_token("old-game-refresh")

    assert tokens.access_token == "new-game-access"
    method, endpoint, _, kwargs = calls[0]
    assert method == "POST"
    assert endpoint == "/game-lobby/refresh-token"
    assert kwargs["json"] == {"refresh_token": "old-game-refresh"}
