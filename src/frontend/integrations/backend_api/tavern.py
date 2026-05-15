from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO, StateTransitionDTO
from src.shared.schemas.tavern import TavernActionDTO, TavernActionEnum, TavernScreenEnum, TavernUIPayloadDTO

TavernResponse = CoreResponseDTO[TavernUIPayloadDTO | StateTransitionDTO | dict[str, Any]]


class BackendTavernApi(BaseApiClient):
    async def view(
        self,
        access_token: str,
        *,
        char_id: int,
        screen: str | None = None,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
    ) -> TavernResponse:
        params = {
            key: value
            for key, value in {
                "screen": screen,
                "tavern_id": tavern_id,
                "service_id": service_id,
                "location_id": location_id,
            }.items()
            if value
        }
        response = await self._request(
            "GET",
            f"/tavern/v1/{char_id}/view",
            response_model=TavernResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        return _normalize_tavern_response(response)

    async def action(
        self,
        access_token: str,
        *,
        char_id: int,
        action: str,
        screen: str | None = None,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
        value: dict[str, Any] | None = None,
    ) -> TavernResponse:
        dto = TavernActionDTO(
            action=TavernActionEnum(action),
            screen=TavernScreenEnum(screen) if screen else None,
            tavern_id=tavern_id,
            service_id=service_id,
            location_id=location_id,
            value=value,
        )
        response = await self._request(
            "POST",
            f"/tavern/v1/{char_id}/action",
            response_model=TavernResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )
        return _normalize_tavern_response(response)


def _normalize_tavern_response(response: TavernResponse) -> TavernResponse:
    if isinstance(response.payload, dict) and response.payload_type != "state_transition":
        return response.model_copy(update={"payload": TavernUIPayloadDTO.model_validate(response.payload)})
    return response
