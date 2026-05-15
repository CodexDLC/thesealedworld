from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO, ScenarioPayloadDTO, ScenarioReturnContextDTO, StateTransitionDTO

ScenarioResponse = CoreResponseDTO[ScenarioPayloadDTO | StateTransitionDTO | dict[str, Any]]


class BackendScenarioApi(BaseApiClient):
    async def initialize(
        self,
        access_token: str,
        *,
        char_id: int,
        quest_key: str,
        return_context: ScenarioReturnContextDTO | dict | None = None,
    ) -> ScenarioResponse:
        """Start a new scenario quest."""
        payload: dict[str, Any] = {"char_id": char_id, "quest_key": quest_key}
        if return_context is not None:
            payload["return_context"] = (
                return_context.model_dump(mode="json")
                if isinstance(return_context, ScenarioReturnContextDTO)
                else return_context
            )
        return await self._request(
            "POST",
            "/scenario/initialize",
            response_model=ScenarioResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
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
