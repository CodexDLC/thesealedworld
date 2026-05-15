from fastapi import Request

from src.frontend.game_features.session.token_state import require_game_access_token
from src.frontend.integrations.backend_api.exploration import BackendExplorationApi, ExplorationResponse


class ExplorationActionService:
    def __init__(self, *, api: BackendExplorationApi) -> None:
        self.api = api

    async def move(
        self,
        request: Request,
        *,
        char_id: int,
        direction: str | None,
        target_id: str | None,
    ) -> ExplorationResponse:
        return await self.api.move(
            require_game_access_token(request),
            char_id=char_id,
            direction=direction,
            target_id=target_id,
        )

    async def interact(
        self,
        request: Request,
        *,
        char_id: int,
        action: str,
        target_id: str | None,
    ) -> ExplorationResponse:
        return await self.api.interact(
            require_game_access_token(request),
            char_id=char_id,
            action=action,
            target_id=target_id,
        )

    async def use_service(self, request: Request, *, char_id: int, service_id: str) -> ExplorationResponse:
        return await self.api.use_service(
            require_game_access_token(request),
            char_id=char_id,
            service_id=service_id,
        )
