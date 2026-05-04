from fastapi import Request

from src.frontend.integrations.backend_api.exploration import BackendExplorationApi, ExplorationResponse
from src.frontend.site_features.auth.token_state import require_access_token


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
            require_access_token(request),
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
            require_access_token(request),
            char_id=char_id,
            action=action,
            target_id=target_id,
        )

    async def use_service(self, request: Request, *, char_id: int, service_id: str) -> ExplorationResponse:
        return await self.api.use_service(
            require_access_token(request),
            char_id=char_id,
            service_id=service_id,
        )
