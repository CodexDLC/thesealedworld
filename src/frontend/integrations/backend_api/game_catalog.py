from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient


class BackendGameCatalogApi(BaseApiClient):
    async def get_bootstrap(self, access_token: str) -> dict[str, Any]:
        response = await self._request(
            "GET",
            "/game/catalog/bootstrap",
            response_model=None,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return response or {}
