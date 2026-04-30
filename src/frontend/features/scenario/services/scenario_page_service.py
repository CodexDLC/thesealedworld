from typing import Any

from fastapi import HTTPException, Request, status

from src.frontend.features.scenario.view_models.scenario import ScenarioPageVM, build_scenario_page_vm
from src.frontend.integrations.backend_api.scenario import BackendScenarioApi


class ScenarioPageService:
    access_cookie_name = "tbmmorpg_access_token"

    def __init__(self, api: BackendScenarioApi) -> None:
        self.api = api

    async def initialize(self, request: Request, *, char_id: int, quest_key: str) -> ScenarioPageVM:
        response = await self.api.initialize(self._require_access_token(request), char_id=char_id, quest_key=quest_key)
        if response.payload is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario initialization failed")

        return build_scenario_page_vm(response, request.state.user)

    async def resume(self, request: Request, *, char_id: int) -> ScenarioPageVM:
        response = await self.api.resume(self._require_access_token(request), char_id=char_id)
        if response.payload is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario resumption failed")

        return build_scenario_page_vm(response, request.state.user)

    async def step(
        self, request: Request, *, char_id: int, action_id: str
    ) -> tuple[str, ScenarioPageVM | dict[str, Any]]:
        response = await self.api.step(self._require_access_token(request), char_id=char_id, action_id=action_id)
        if response.payload is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario step failed")

        vm = build_scenario_page_vm(response, request.state.user)

        if hasattr(response.payload, "node_key"):
            return "game/domains/scenario/viewport/main.html", vm

        # Scenario finished
        return "game/domains/scenario/viewport/finalized.html", {
            "vm": vm,
            "result": response.payload,
            "next_domain": response.header.current_state,
        }

    def _require_access_token(self, request: Request) -> str:
        token = request.cookies.get(self.access_cookie_name)
        if not token:
            raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
        return token
