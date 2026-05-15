from typing import Any

import httpx
from fastapi import HTTPException, Request, status
from loguru import logger

from src.frontend.game_features.scenario.view_models.scenario import ScenarioPageVM, build_scenario_page_vm
from src.frontend.game_features.session.token_state import require_game_access_token
from src.frontend.integrations.backend_api.character_status import BackendCharacterStatusApi
from src.frontend.integrations.backend_api.scenario import BackendScenarioApi


class ScenarioPageService:
    def __init__(self, api: BackendScenarioApi, character_status_api: BackendCharacterStatusApi) -> None:
        self.api = api
        self.character_status_api = character_status_api

    async def initialize(self, request: Request, *, char_id: int, quest_key: str) -> ScenarioPageVM:
        token = require_game_access_token(request)
        response = await self.api.initialize(token, char_id=char_id, quest_key=quest_key)
        if response.payload is None:
            logger.warning("Scenario page initialize failed: empty_payload char_id={} quest_key={}", char_id, quest_key)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario initialization failed")

        character_status = await self.character_status_api.get_panel(token, char_id=char_id)
        vm = build_scenario_page_vm(response, request.state.user, character_status=character_status)
        logger.info("Scenario page initialized: char_id={} quest_key={}", char_id, quest_key)
        return vm

    async def resume(self, request: Request, *, char_id: int) -> ScenarioPageVM:
        token = require_game_access_token(request)
        response = await self.api.resume(token, char_id=char_id)
        if response.payload is None:
            logger.warning("Scenario page resume failed: empty_payload char_id={}", char_id)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario resumption failed")

        character_status = await self.character_status_api.get_panel(token, char_id=char_id)
        vm = build_scenario_page_vm(response, request.state.user, character_status=character_status)
        logger.info("Scenario page resumed: char_id={}", char_id)
        return vm

    async def step(self, request: Request, *, char_id: int, action_id: str) -> Any:
        token = require_game_access_token(request)
        try:
            response = await self.api.step(token, char_id=char_id, action_id=action_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == status.HTTP_400_BAD_REQUEST:
                logger.warning(
                    "Scenario page step rejected; resyncing current screen: char_id={} action_id={} body={}",
                    char_id,
                    action_id,
                    exc.response.text,
                )
                return await self.api.resume(token, char_id=char_id)
            raise
        if response.payload is None:
            logger.warning("Scenario page step failed: empty_payload char_id={} action_id={}", char_id, action_id)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario step failed")

        if hasattr(response.payload, "node_key"):
            logger.info("Scenario page step completed: char_id={} action_id={}", char_id, action_id)
            return response

        logger.info(
            "Scenario page state transition: char_id={} action_id={} state={}",
            char_id,
            action_id,
            response.header.current_state,
        )
        return response
