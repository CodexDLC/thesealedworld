from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO, EnterCharacterRequestDTO, ScenarioPayloadDTO

GameSessionEnterResponse = CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]


class BackendGameSessionApi(BaseApiClient):
    async def enter(self, access_token: str, dto: EnterCharacterRequestDTO) -> GameSessionEnterResponse:
        return await self._request(
            "POST",
            "/game-session/enter",
            response_model=GameSessionEnterResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )
