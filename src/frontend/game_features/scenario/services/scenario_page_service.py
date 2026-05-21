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
            logger.bind(char_id=char_id, quest_key=quest_key, reason="empty_payload").warning(
                "ScenarioPageInitializeFailed"
            )
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario initialization failed")

        character_status = await self.character_status_api.get_panel(token, char_id=char_id)
        vm = build_scenario_page_vm(response, request.state.user, character_status=character_status)
        logger.bind(char_id=char_id, quest_key=quest_key).info("ScenarioPageInitialized")
        return vm

    async def resume(self, request: Request, *, char_id: int) -> ScenarioPageVM:
        token = require_game_access_token(request)
        response = await self.api.resume(token, char_id=char_id)
        if response.payload is None:
            logger.bind(char_id=char_id, reason="empty_payload").warning("ScenarioPageResumeFailed")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario resumption failed")

        character_status = await self.character_status_api.get_panel(token, char_id=char_id)
        vm = build_scenario_page_vm(response, request.state.user, character_status=character_status)
        logger.bind(char_id=char_id).info("ScenarioPageResumed")
        return vm

    async def step(self, request: Request, *, char_id: int, action_id: str) -> Any:
        token = require_game_access_token(request)
        try:
            response = await self.api.step(token, char_id=char_id, action_id=action_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == status.HTTP_400_BAD_REQUEST:
                logger.bind(char_id=char_id, action_id=action_id, body=exc.response.text).warning(
                    "ScenarioPageStepRejected"
                )
                return await self.api.resume(token, char_id=char_id)
            raise
        if response.payload is None:
            logger.bind(char_id=char_id, action_id=action_id, reason="empty_payload").warning("ScenarioPageStepFailed")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario step failed")

        if hasattr(response.payload, "node_key"):
            logger.bind(char_id=char_id, action_id=action_id).info("ScenarioPageStepCompleted")
            return response

        logger.bind(char_id=char_id, action_id=action_id, state=response.header.current_state).info(
            "ScenarioPageStateTransition"
        )
        return response
