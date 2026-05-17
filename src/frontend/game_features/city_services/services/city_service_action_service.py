from fastapi import Request

from src.frontend.game_features.session.token_state import require_game_access_token
from src.frontend.integrations.backend_api.city_services import BackendCityServicesApi, CityServiceResponse


class CityServiceActionService:
    def __init__(self, *, api: BackendCityServicesApi) -> None:
        self.api = api

    async def action(
        self,
        request: Request,
        *,
        char_id: int,
        action: str,
        service_id: str,
        screen: str | None = None,
        section_id: str | None = None,
        location_id: str | None = None,
    ) -> CityServiceResponse:
        return await self.api.action(
            require_game_access_token(request),
            char_id=char_id,
            action=action,
            service_id=service_id,
            screen=screen,
            section_id=section_id,
            location_id=location_id,
        )
