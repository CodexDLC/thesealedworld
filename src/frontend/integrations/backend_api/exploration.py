from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO, StateTransitionDTO
from src.shared.schemas.exploration import EncounterDTO, ExplorationListDTO, WorldNavigationDTO

ExplorationPayload = WorldNavigationDTO | EncounterDTO | ExplorationListDTO | StateTransitionDTO | dict[str, Any]
ExplorationResponse = CoreResponseDTO[ExplorationPayload]


class BackendExplorationApi(BaseApiClient):
    async def look_around(self, access_token: str, *, char_id: int) -> ExplorationResponse:
        return await self._request(
            "GET",
            "/exploration/look_around",
            response_model=ExplorationResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"char_id": char_id},
        )

    async def move(
        self,
        access_token: str,
        *,
        char_id: int,
        direction: str | None = None,
        target_id: str | None = None,
    ) -> ExplorationResponse:
        return await self._request(
            "POST",
            "/exploration/move",
            response_model=ExplorationResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"char_id": char_id, "direction": direction or target_id, "target_id": target_id},
        )

    async def interact(
        self,
        access_token: str,
        *,
        char_id: int,
        action: str,
        target_id: str | None = None,
    ) -> ExplorationResponse:
        return await self._request(
            "POST",
            "/exploration/interact",
            response_model=ExplorationResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"char_id": char_id, "action": action, "target_id": target_id},
        )

    async def use_service(self, access_token: str, *, char_id: int, service_id: str) -> ExplorationResponse:
        return await self._request(
            "POST",
            "/exploration/use_service",
            response_model=ExplorationResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"char_id": char_id, "service_id": service_id},
        )
