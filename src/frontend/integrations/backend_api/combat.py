from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO
from src.shared.schemas.combat import CombatDashboardDTO, CombatLogDTO, CombatRegisterMoveRequestDTO

CombatViewResponse = CoreResponseDTO[CombatDashboardDTO | dict[str, Any]]


class BackendCombatApi(BaseApiClient):
    async def view(self, access_token: str, *, char_id: int) -> CombatViewResponse:
        return await self._request(
            "GET",
            f"/api/game/combat/{char_id}/view",
            response_model=CombatViewResponse,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def snapshot(self, access_token: str, *, char_id: int) -> CombatDashboardDTO:
        return await self._request(
            "GET",
            f"/api/game/combat/{char_id}/snapshot",
            response_model=CombatDashboardDTO,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def logs(self, access_token: str, *, char_id: int, page: int = 1, page_size: int = 20) -> CombatLogDTO:
        return await self._request(
            "GET",
            f"/api/game/combat/{char_id}/logs",
            response_model=CombatLogDTO,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"page": page, "page_size": page_size},
        )

    async def register_move(
        self,
        access_token: str,
        *,
        char_id: int,
        body: CombatRegisterMoveRequestDTO,
    ) -> CombatDashboardDTO:
        return await self._request(
            "POST",
            f"/api/game/combat/{char_id}/moves",
            response_model=CombatDashboardDTO,
            headers={"Authorization": f"Bearer {access_token}"},
            json=body.model_dump(mode="json"),
        )
