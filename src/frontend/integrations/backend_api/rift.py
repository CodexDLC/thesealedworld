from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient


class BackendRiftApi(BaseApiClient):
    async def view(self, token: str, *, char_id: int) -> dict[str, Any]:
        raw = await self._request(
            "GET",
            f"/api/game/rift/{char_id}/view",
            headers={"Authorization": f"Bearer {token}"},
        )
        return raw or {}

    async def travel_start(self, token: str, *, char_id: int, target_node_id: str) -> dict[str, Any]:
        raw = await self._request(
            "POST",
            f"/api/game/rift/{char_id}/travel/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"target_node_id": target_node_id},
        )
        return raw or {}

    async def travel_tick(
        self,
        token: str,
        *,
        char_id: int,
        travel_id: str,
        force_event: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"travel_id": travel_id}
        if force_event:
            payload["force_event"] = force_event
        raw = await self._request(
            "POST",
            f"/api/game/rift/{char_id}/travel/tick",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        return raw or {}

    async def action(
        self,
        token: str,
        *,
        char_id: int,
        action_type: str,
        action_id: str | None = None,
        target_node_id: str | None = None,
        direction: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_payload: dict[str, Any] = {"action_type": action_type}
        if action_id:
            request_payload["action_id"] = action_id
        if target_node_id:
            request_payload["target_node_id"] = target_node_id
        if direction:
            request_payload["direction"] = direction
        if payload:
            request_payload["payload"] = payload
        raw = await self._request(
            "POST",
            f"/api/game/rift/{char_id}/action",
            headers={"Authorization": f"Bearer {token}"},
            json=request_payload,
        )
        return raw or {}

    async def complete(self, token: str, *, char_id: int) -> dict[str, Any]:
        raw = await self._request(
            "POST",
            f"/api/game/rift/{char_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        return raw or {}

    async def leave(self, token: str, *, char_id: int) -> dict[str, Any]:
        raw = await self._request(
            "POST",
            f"/api/game/rift/{char_id}/leave",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        return raw or {}
