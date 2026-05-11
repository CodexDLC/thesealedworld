from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO
from src.shared.schemas.inventory import InventoryActionRequestDTO, InventoryWindowDTO

InventoryViewResponse = CoreResponseDTO[InventoryWindowDTO | dict[str, Any]]


class BackendInventoryApi(BaseApiClient):
    async def view(self, access_token: str, *, char_id: int) -> InventoryViewResponse:
        return await self._request(
            "GET",
            f"/api/game/inventory/{char_id}/view",
            response_model=InventoryViewResponse,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def action(self, access_token: str, dto: InventoryActionRequestDTO) -> InventoryViewResponse:
        return await self._request(
            "POST",
            "/api/game/inventory/actions",
            response_model=InventoryViewResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )
