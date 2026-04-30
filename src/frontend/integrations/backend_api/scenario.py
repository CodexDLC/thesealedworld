from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO, ScenarioPayloadDTO

ScenarioResponse = CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]


class BackendScenarioApi(BaseApiClient):
    async def initialize(self, access_token: str, *, char_id: int, quest_key: str) -> ScenarioResponse:
        """Start a new scenario quest."""
        return await self._request(
            "POST",
            "/scenario/initialize",
            response_model=ScenarioResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"char_id": char_id, "quest_key": quest_key},
        )

    async def resume(self, access_token: str, *, char_id: int) -> ScenarioResponse:
        """Resume an existing scenario session."""
        return await self._request(
            "GET",
            f"/scenario/resume/{char_id}",
            response_model=ScenarioResponse,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def step(self, access_token: str, *, char_id: int, action_id: str) -> ScenarioResponse:
        """Execute a choice in the current scenario node."""
        return await self._request(
            "POST",
            "/scenario/step",
            response_model=ScenarioResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"char_id": char_id, "action_id": action_id},
        )
