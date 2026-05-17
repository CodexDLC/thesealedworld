from src.frontend.core.api import BaseApiClient


class ScenarioSessionsApi(BaseApiClient):
    async def list_active(self) -> list[dict]:
        raw = await self._request("GET", "/api/internal/scenario/sessions")
        if isinstance(raw, dict):
            return raw.get("data", [])  # type: ignore[return-value]
        if isinstance(raw, list):
            return raw
        return []
