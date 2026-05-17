from typing import Any

from pydantic import BaseModel, Field

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import (
    CharacterNameAvailabilityDTO,
    CharacterNameAvailabilityRequestDTO,
    CharacterStatusDTO,
    CoreResponseDTO,
    GameLobbyCharacterCreateRequestDTO,
    GameLobbyCharacterDeleteRequestDTO,
    GameLobbyCharacterReleaseRequestDTO,
    GameLobbyCharacterSelectRequestDTO,
    GameLobbyUserContextDTO,
    ScenarioPayloadDTO,
)


class LobbySlotPayload(BaseModel):
    index: int
    is_empty: bool = True
    character_id: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    status: str = "VACANT"
    presence_status: str = "offline"


class GameLobbyPayload(BaseModel):
    title: str
    description: str
    primary_action_label: str
    primary_action: str
    message: str | None = None
    max_slots: int = 4
    can_start: bool = True
    slots: list[LobbySlotPayload] = Field(default_factory=list)


class GameTokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None
    refresh_expires_in: int | None = None


GameLobbyResponse = CoreResponseDTO[GameLobbyPayload]
GameLobbyStartResponse = CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]
GameLobbyReleaseResponse = CoreResponseDTO[dict[str, Any]]
GameLobbySelectResponse = CoreResponseDTO[dict[str, Any]]

GameLobbyUserContext = GameLobbyUserContextDTO
GameLobbyCharacterSelectRequest = GameLobbyCharacterSelectRequestDTO
GameLobbyCharacterCreateRequest = GameLobbyCharacterCreateRequestDTO
GameLobbyCharacterReleaseRequest = GameLobbyCharacterReleaseRequestDTO
GameLobbyCharacterDeleteRequest = GameLobbyCharacterDeleteRequestDTO


class BackendGameLobbyApi(BaseApiClient):
    async def bootstrap(self, user: GameLobbyUserContext) -> GameLobbyResponse:
        return await self._request(
            "POST",
            "/game-lobby/bootstrap",
            response_model=GameLobbyResponse,
            json=user.model_dump(mode="json"),
        )

    async def select(self, dto: GameLobbyCharacterSelectRequest) -> GameLobbySelectResponse:
        return await self._request(
            "POST",
            "/game-lobby/select",
            response_model=GameLobbySelectResponse,
            json=dto.model_dump(mode="json"),
        )

    async def create(self, dto: GameLobbyCharacterCreateRequest) -> GameLobbyStartResponse:
        return await self._request(
            "POST",
            "/game-lobby/create",
            response_model=GameLobbyStartResponse,
            json=dto.model_dump(mode="json"),
        )

    async def check_name_availability(self, dto: CharacterNameAvailabilityRequestDTO) -> CharacterNameAvailabilityDTO:
        return await self._request(
            "POST",
            "/game-lobby/name-availability",
            response_model=CharacterNameAvailabilityDTO,
            json=dto.model_dump(mode="json"),
        )

    async def release(self, dto: GameLobbyCharacterReleaseRequest) -> GameLobbyReleaseResponse:
        return await self._request(
            "POST",
            "/game-lobby/release-selected",
            response_model=GameLobbyReleaseResponse,
            json=dto.model_dump(mode="json"),
        )

    async def delete_character(self, dto: GameLobbyCharacterDeleteRequest) -> GameLobbyResponse:
        return await self._request(
            "POST",
            "/game-lobby/delete-character",
            response_model=GameLobbyResponse,
            json=dto.model_dump(mode="json"),
        )

    async def refresh_token(self, refresh_token: str) -> GameTokenPair:
        return await self._request(
            "POST",
            "/game-lobby/refresh-token",
            response_model=GameTokenPair,
            json={"refresh_token": refresh_token},
        )

    async def get_status(self, access_token: str, char_id: int) -> CharacterStatusDTO:
        return await self._request(
            "GET",
            "/game-lobby/status",
            response_model=CharacterStatusDTO,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"char_id": char_id},
        )
