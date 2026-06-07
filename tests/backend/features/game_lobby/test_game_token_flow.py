from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.backend.core.exceptions import BusinessLogicException, SessionReplacedException
from src.backend.core.game_auth import (
    GameTokenRefreshRequestDTO,
    create_game_refresh_token,
    decode_game_access_token,
)
from src.backend.features.game_lobby.api.router import (
    bootstrap_lobby_for_site_user,
    check_lobby_character_name_for_site_user,
    create_lobby_character_for_site_user,
    delete_lobby_character_for_site_user,
    get_lobby_population_stats,
    refresh_game_token,
    release_lobby_character_for_site_user,
    select_lobby_character_for_site_user,
)
from src.backend.features.game_lobby.integrations import LobbyCharacterSummary
from src.backend.features.game_lobby.services.lobby_service import GameLobbyService
from src.shared.enums import CoreDomain
from src.shared.schemas import (
    CharacterNameAvailabilityDTO,
    CharacterNameAvailabilityRequestDTO,
    CoreResponseDTO,
    CreateCharacterRequestDTO,
    DeleteCharacterRequestDTO,
    EnterCharacterRequestDTO,
    GameLobbyCharacterCreateRequestDTO,
    GameLobbyCharacterDeleteRequestDTO,
    GameLobbyCharacterReleaseRequestDTO,
    GameLobbyCharacterSelectRequestDTO,
    GameLobbyPayloadDTO,
    GameLobbyPopulationStatsDTO,
    GameLobbyUserContextDTO,
    GameStateHeader,
    ScenarioPayloadDTO,
)


@pytest.mark.unit
async def test_service_bootstrap_filters_lobby_by_user_id() -> None:
    user_id = uuid4()
    integration = SimpleNamespace(
        list_user_characters=AsyncMock(
            return_value=[
                LobbyCharacterSummary(
                    character_id=7,
                    name="Hero",
                    avatar_url=None,
                    status="lobby",
                )
            ]
        )
    )
    service = GameLobbyService(integration)

    response = await bootstrap_lobby_for_site_user(
        GameLobbyUserContextDTO(user_id=user_id, email="hero@example.test"),
        object(),
        service,
    )

    integration.list_user_characters.assert_awaited_once_with(user_id)
    assert response.payload is not None
    assert response.payload.slots[0].character_id == "7"


@pytest.mark.unit
async def test_population_stats_for_site_user_uses_lobby_service() -> None:
    service = SimpleNamespace(
        get_population_stats=AsyncMock(return_value=GameLobbyPopulationStatsDTO(characters_total=11))
    )

    response = await get_lobby_population_stats(object(), service)

    service.get_population_stats.assert_awaited_once_with()
    assert response.characters_total == 11


def _request_with_session_lock() -> tuple[SimpleNamespace, AsyncMock]:
    """Fake FastAPI Request exposing ``app.state.game_session_lock.claim``."""
    claim = AsyncMock()
    state = SimpleNamespace(game_session_lock=SimpleNamespace(claim=claim))
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    return request, claim


@pytest.mark.unit
async def test_select_character_issues_game_access_token() -> None:
    user_id = uuid4()
    service = SimpleNamespace(
        enter_character=AsyncMock(
            return_value=CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY),
                payload={"character_id": 7, "state": "lobby"},
                payload_type="active_character_bootstrap",
            )
        )
    )
    request, claim = _request_with_session_lock()

    response = await select_lobby_character_for_site_user(
        request,
        GameLobbyCharacterSelectRequestDTO(user_id=user_id, character_id=7),
        object(),
        service,
    )

    service.enter_character.assert_awaited_once()
    assert response.payload is not None
    tokens = response.payload["game_tokens"]
    claims = decode_game_access_token(tokens["access_token"])
    assert claims.sub == user_id
    assert claims.character_id == 7
    # Session id must be a fresh uuid hex claim, not the legacy str(char_id).
    assert claims.session_id and claims.session_id != "7"
    claim.assert_awaited_once_with(7, claims.session_id)


@pytest.mark.unit
async def test_select_character_rejects_foreign_character() -> None:
    service = SimpleNamespace(enter_character=AsyncMock(side_effect=BusinessLogicException("Character is unavailable")))
    request, _ = _request_with_session_lock()

    with pytest.raises(BusinessLogicException, match="Character is unavailable"):
        await select_lobby_character_for_site_user(
            request,
            GameLobbyCharacterSelectRequestDTO(user_id=uuid4(), character_id=999),
            object(),
            service,
        )


@pytest.mark.unit
async def test_create_character_for_site_user_returns_scenario_and_game_tokens() -> None:
    user_id = uuid4()
    service = SimpleNamespace(
        create_and_enter=AsyncMock(
            return_value=ScenarioPayloadDTO(
                node_key="awakening",
                text="Ты просыпаешься у Порога.",
                extra_data={"char_id": 7},
            )
        )
    )
    request, claim = _request_with_session_lock()

    response = await create_lobby_character_for_site_user(
        request,
        GameLobbyCharacterCreateRequestDTO(
            user_id=user_id,
            email="hero@example.test",
            character=CreateCharacterRequestDTO(name="Ada", gender="female"),
        ),
        object(),
        service,
    )

    service.create_and_enter.assert_awaited_once()
    assert response.payload is not None
    assert response.payload.extra_data is not None
    tokens = response.payload.extra_data["game_tokens"]
    claims = decode_game_access_token(tokens["access_token"])
    assert claims.sub == user_id
    assert claims.character_id == 7
    assert claims.session_id and claims.session_id != "7"
    claim.assert_awaited_once_with(7, claims.session_id)


@pytest.mark.unit
async def test_name_availability_for_site_user_uses_creation_service() -> None:
    service = SimpleNamespace(
        check_name_availability=AsyncMock(
            return_value=CharacterNameAvailabilityDTO(available=False, code="name_taken")
        )
    )

    response = await check_lobby_character_name_for_site_user(
        CharacterNameAvailabilityRequestDTO(name="Ada"),
        object(),
        service,
    )

    assert response.available is False
    assert response.code == "name_taken"
    service.check_name_availability.assert_awaited_once_with("Ada")


@pytest.mark.unit
async def test_release_character_for_site_user_uses_internal_user_context() -> None:
    user_id = uuid4()
    service = SimpleNamespace(
        release_character=AsyncMock(
            return_value=CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.LOBBY),
                payload={"released": True},
                payload_type="active_character_release",
            )
        )
    )

    response = await release_lobby_character_for_site_user(
        GameLobbyCharacterReleaseRequestDTO(
            user_id=user_id,
            character=EnterCharacterRequestDTO(character_id=7),
        ),
        object(),
        service,
    )

    assert response.payload == {"released": True}
    service.release_character.assert_awaited_once()
    user, character_id = service.release_character.await_args.args
    assert user.id == user_id
    assert character_id == 7


def _request_with_lock_current(*, current_value: str | None) -> tuple[SimpleNamespace, AsyncMock]:
    """Fake Request exposing both ``current`` and ``claim`` on game_session_lock."""
    claim = AsyncMock()
    current = AsyncMock(return_value=current_value)
    state = SimpleNamespace(game_session_lock=SimpleNamespace(current=current, claim=claim))
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    return request, claim


@pytest.mark.unit
async def test_refresh_game_token_touches_lock_on_success() -> None:
    """Active players must keep their slot: each refresh re-claims the lock
    with the same session_id so its TTL rolls forward. Without this the lock
    silently expires while the refresh token is still valid, and the next
    refresh would see current=None and raise SessionReplacedException."""
    user_id = uuid4()
    refresh_token_value = create_game_refresh_token(
        user_id=user_id,
        character_id=7,
        session_id="sess-A",
    )
    request, claim = _request_with_lock_current(current_value="sess-A")

    pair = await refresh_game_token(
        request,
        GameTokenRefreshRequestDTO(refresh_token=refresh_token_value),
        object(),
    )

    new_claims = decode_game_access_token(pair.access_token)
    assert new_claims.session_id == "sess-A"
    claim.assert_awaited_once_with(7, "sess-A")


@pytest.mark.unit
async def test_refresh_game_token_rejects_stale_session_without_touching_lock() -> None:
    user_id = uuid4()
    refresh_token_value = create_game_refresh_token(
        user_id=user_id,
        character_id=7,
        session_id="sess-OLD",
    )
    request, claim = _request_with_lock_current(current_value="sess-NEW")

    with pytest.raises(SessionReplacedException):
        await refresh_game_token(
            request,
            GameTokenRefreshRequestDTO(refresh_token=refresh_token_value),
            object(),
        )

    claim.assert_not_awaited()


@pytest.mark.unit
async def test_delete_character_for_site_user_uses_confirmation_name() -> None:
    user_id = uuid4()
    service = SimpleNamespace(
        delete_character=AsyncMock(),
        get_start_payload=AsyncMock(return_value=GameLobbyPayloadDTO()),
    )

    response = await delete_lobby_character_for_site_user(
        GameLobbyCharacterDeleteRequestDTO(
            user_id=user_id,
            character=DeleteCharacterRequestDTO(character_id=7, confirm_name="Ada"),
        ),
        object(),
        service,
    )

    assert response.payload is not None
    service.delete_character.assert_awaited_once()
    user, character_id = service.delete_character.await_args.args
    assert user.id == user_id
    assert character_id == 7
    assert service.delete_character.await_args.kwargs == {"confirm_name": "Ada"}
