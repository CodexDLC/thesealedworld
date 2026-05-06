from typing import Any

from pydantic import BaseModel, Field

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import (
    CharacterStatusDTO,
    CoreResponseDTO,
    CreateCharacterRequestDTO,
    DeleteCharacterRequestDTO,
    EnterCharacterRequestDTO,
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


GameLobbyResponse = CoreResponseDTO[GameLobbyPayload]
GameLobbyStartResponse = CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]
GameLobbyEnterResponse = CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]


class BackendGameLobbyApi(BaseApiClient):
    async def get_status(self, access_token: str, char_id: int) -> CharacterStatusDTO:
        return await self._request(
            "GET",
            "/game-lobby/status",
            response_model=CharacterStatusDTO,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"char_id": char_id},
        )

    async def get_view(self, access_token: str) -> GameLobbyResponse:
        return await self._request(
            "GET",
            "/game-lobby/view",
            response_model=GameLobbyResponse,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def start(self, access_token: str, dto: CreateCharacterRequestDTO) -> GameLobbyStartResponse:
        return await self._request(
            "POST",
            "/game-lobby/start",
            response_model=GameLobbyStartResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )

    async def enter(self, access_token: str, dto: EnterCharacterRequestDTO) -> GameLobbyEnterResponse:
        return await self._request(
            "POST",
            "/game-lobby/enter",
            response_model=GameLobbyEnterResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )

    async def delete(self, access_token: str, dto: DeleteCharacterRequestDTO) -> GameLobbyResponse:
        return await self._request(
            "POST",
            "/game-lobby/delete",
            response_model=GameLobbyResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )
