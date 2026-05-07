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

    async def get_public_monsters(self) -> dict[str, dict[str, Any]]:
        response = await self._request("GET", "/game/catalog/public/monsters", response_model=None)
        if not response:
            return {}
        return {key: value for key, value in response.items() if isinstance(value, dict)}

    async def get_public_generated_monster_clans(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/game/catalog/public/generated-monster-clans", response_model=None)
        data = response.get("data") if response else None
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]
