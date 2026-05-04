from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO, StateTransitionDTO
from src.shared.schemas.arena import ArenaActionDTO, ArenaUIPayloadDTO

ArenaResponse = CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO | dict[str, Any]]


class BackendArenaApi(BaseApiClient):
    async def view(self, access_token: str, *, char_id: int) -> ArenaResponse:
        return await self._request(
            "GET",
            "/arena/view",
            response_model=ArenaResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"char_id": char_id},
        )

    async def action(
        self,
        access_token: str,
        *,
        char_id: int,
        action: str,
        mode: str | None = None,
        value: dict[str, Any] | None = None,
    ) -> ArenaResponse:
        dto = ArenaActionDTO(action=action, mode=mode, value=value)
        return await self._request(
            "POST",
            f"/arena/{char_id}/action",
            response_model=ArenaResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )
