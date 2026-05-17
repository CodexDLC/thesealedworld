from src.frontend.core.api import BaseApiClient


class ExplorationSessionsApi(BaseApiClient):
    async def list_active(self) -> list[dict]:
        raw = await self._request("GET", "/api/internal/exploration/sessions")
        if isinstance(raw, dict):
            return raw.get("data", [])  # type: ignore[return-value]
        if isinstance(raw, list):
            return raw
        return []
