from typing import Any

from fastapi import Request

from src.frontend.integrations.backend_api.arena import ArenaResponse, BackendArenaApi
from src.frontend.site_features.auth.token_state import require_access_token


class ArenaActionService:
    def __init__(self, *, api: BackendArenaApi) -> None:
        self.api = api

    async def action(
        self,
        request: Request,
        *,
        char_id: int,
        action: str,
        mode: str | None = None,
        value: dict[str, Any] | None = None,
    ) -> ArenaResponse:
        return await self.api.action(
            require_access_token(request),
            char_id=char_id,
            action=action,
            mode=mode,
            value=value,
        )
