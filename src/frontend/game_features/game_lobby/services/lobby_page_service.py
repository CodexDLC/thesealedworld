from fastapi import Request
from loguru import logger

from src.frontend.features.auth.dto.user import UserResponse
from src.frontend.game_features.session.token_state import require_game_access_token
from src.frontend.integrations.backend_api.game_lobby import (
    BackendGameLobbyApi,
    GameLobbyCharacterCreateRequest,
    GameLobbyCharacterDeleteRequest,
    GameLobbyCharacterReleaseRequest,
    GameLobbyCharacterSelectRequest,
    GameLobbyReleaseResponse,
    GameLobbyResponse,
    GameLobbySelectResponse,
    GameLobbyStartResponse,
    GameLobbyUserContext,
)
from src.shared.schemas import (
    CharacterStatusDTO,
    CreateCharacterRequestDTO,
    DeleteCharacterRequestDTO,
    EnterCharacterRequestDTO,
)


class GameLobbyPageService:
    def __init__(self, api: BackendGameLobbyApi) -> None:
        self.api = api

    async def get_view(self, user: UserResponse) -> GameLobbyResponse:
        response = await self.api.bootstrap(_user_context(user))
        logger.info("Lobby page view loaded")
        return response

    async def get_status(self, request: Request, char_id: int) -> CharacterStatusDTO:
        response = await self.api.get_status(require_game_access_token(request), char_id)
        logger.info("Lobby page status loaded: character_id={}", char_id)
        return response

    async def start(self, user: UserResponse, dto: CreateCharacterRequestDTO) -> GameLobbyStartResponse:
        response = await self.api.create(
            GameLobbyCharacterCreateRequest(
                user_id=user.id,
                email=user.email,
                character=dto,
            )
        )
        logger.info("Lobby page character start completed")
        return response

    async def select(self, user: UserResponse, dto: EnterCharacterRequestDTO) -> GameLobbySelectResponse:
        response = await self.api.select(
            GameLobbyCharacterSelectRequest(
                user_id=user.id,
                email=user.email,
                character_id=dto.character_id,
            )
        )
        logger.info("Lobby page character enter completed: character_id={}", dto.character_id)
        return response

    async def release(self, user: UserResponse, dto: EnterCharacterRequestDTO) -> GameLobbyReleaseResponse:
        response = await self.api.release(
            GameLobbyCharacterReleaseRequest(
                user_id=user.id,
                email=user.email,
                character=dto,
            )
        )
        logger.info("Lobby page character release completed: character_id={}", dto.character_id)
        return response

    async def delete(self, user: UserResponse, dto: DeleteCharacterRequestDTO) -> GameLobbyResponse:
        response = await self.api.delete_character(
            GameLobbyCharacterDeleteRequest(
                user_id=user.id,
                email=user.email,
                character=dto,
            )
        )
        logger.warning("Lobby page character deleted: character_id={}", dto.character_id)
        return response


def _user_context(user: UserResponse) -> GameLobbyUserContext:
    return GameLobbyUserContext(user_id=user.id, email=user.email)
