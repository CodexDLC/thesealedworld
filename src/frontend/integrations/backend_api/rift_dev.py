from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient


class BackendRiftDevApi(BaseApiClient):
    async def start_starter_rift(
        self,
        *,
        seed: str | None = None,
        void_cells: int | None = None,
        assembly_preset_key: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"debug": True}
        if seed:
            payload["seed"] = seed
        if void_cells is not None:
            payload["void_cells"] = void_cells
        if assembly_preset_key:
            payload["assembly_preset_key"] = assembly_preset_key
        raw = await self._request("POST", "/api/dev/rift/starter-rift/start", json=payload)
        return raw or {}

    async def screen(self, rift_instance_id: str) -> dict[str, Any]:
        raw = await self._request("GET", f"/api/dev/rift/{rift_instance_id}/screen")
        return raw or {}

    async def move(self, rift_instance_id: str, *, target_node_id: str) -> dict[str, Any]:
        raw = await self._request(
            "POST",
            f"/api/dev/rift/{rift_instance_id}/move",
            json={"target_node_id": target_node_id},
        )
        return raw or {}

    async def travel_start(self, rift_instance_id: str, *, target_node_id: str) -> dict[str, Any]:
        raw = await self._request(
            "POST",
            f"/api/dev/rift/{rift_instance_id}/travel/start",
            json={"target_node_id": target_node_id},
        )
        return raw or {}

    async def travel_tick(
        self,
        rift_instance_id: str,
        *,
        travel_id: str,
        force_event: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"travel_id": travel_id}
        if force_event:
            payload["force_event"] = force_event
        raw = await self._request(
            "POST",
            f"/api/dev/rift/{rift_instance_id}/travel/tick",
            json=payload,
        )
        return raw or {}

    async def action(
        self,
        rift_instance_id: str,
        *,
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
            f"/api/dev/rift/{rift_instance_id}/action",
            json=request_payload,
        )
        return raw or {}

    async def rebuild(
        self,
        rift_instance_id: str,
        *,
        seed: str | None = None,
        void_cells: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if seed:
            payload["seed"] = seed
        if void_cells is not None:
            payload["void_cells"] = void_cells
        raw = await self._request(
            "POST",
            f"/api/dev/rift/{rift_instance_id}/rebuild",
            json=payload,
        )
        return raw or {}
