from src.frontend.core.api import BaseApiClient


class CombatSessionsApi(BaseApiClient):
    async def list_active(self) -> list[dict]:
        raw = await self._request("GET", "/api/internal/combat/sessions")
        if isinstance(raw, dict):
            return raw.get("data", [])  # type: ignore[return-value]
        return []

    async def get_session(self, session_id: str) -> dict | None:
        try:
            raw = await self._request("GET", f"/api/internal/combat/sessions/{session_id}")
            return raw if isinstance(raw, dict) else None
        except Exception:
            return None
