from pydantic import BaseModel, Field

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO


class LobbySlotPayload(BaseModel):
    index: int
    is_empty: bool = True
    character_id: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    status: str = "VACANT"


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


class BackendGameLobbyApi(BaseApiClient):
    async def get_view(self, access_token: str) -> GameLobbyResponse:
        return await self._request(
            "GET",
            "/game-lobby/view",
            response_model=GameLobbyResponse,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def start(self, access_token: str) -> GameLobbyResponse:
        return await self._request(
            "POST",
            "/game-lobby/start",
            response_model=GameLobbyResponse,
            headers={"Authorization": f"Bearer {access_token}"},
        )
