from fastapi import Request

from src.frontend.game_features.session.token_state import require_game_access_token
from src.frontend.integrations.backend_api.tavern import BackendTavernApi, TavernResponse


class TavernActionService:
    def __init__(self, *, api: BackendTavernApi) -> None:
        self.api = api

    async def action(
        self,
        request: Request,
        *,
        char_id: int,
        action: str,
        screen: str | None = None,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
    ) -> TavernResponse:
        return await self.api.action(
            require_game_access_token(request),
            char_id=char_id,
            action=action,
            screen=screen,
            tavern_id=tavern_id,
            service_id=service_id,
            location_id=location_id,
        )
