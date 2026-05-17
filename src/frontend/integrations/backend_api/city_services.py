from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO, StateTransitionDTO
from src.shared.schemas.city_services import (
    CityServiceActionDTO,
    CityServiceActionEnum,
    CityServiceScreenEnum,
    CityServiceUIPayloadDTO,
)

CityServiceResponse = CoreResponseDTO[CityServiceUIPayloadDTO | StateTransitionDTO | dict[str, Any]]


class BackendCityServicesApi(BaseApiClient):
    async def view(
        self,
        access_token: str,
        *,
        char_id: int,
        service_id: str | None = None,
        screen: str | None = None,
        section_id: str | None = None,
        location_id: str | None = None,
        tavern_id: str | None = None,
    ) -> CityServiceResponse:
        params = {
            key: value
            for key, value in {
                "service_id": service_id,
                "screen": screen,
                "section_id": section_id,
                "location_id": location_id,
                "tavern_id": tavern_id,
            }.items()
            if value
        }
        response = await self._request(
            "GET",
            f"/city-services/v1/{char_id}/view",
            response_model=CityServiceResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        return _normalize_city_service_response(response)

    async def action(
        self,
        access_token: str,
        *,
        char_id: int,
        action: str,
        service_id: str,
        screen: str | None = None,
        section_id: str | None = None,
        location_id: str | None = None,
        value: dict[str, Any] | None = None,
    ) -> CityServiceResponse:
        dto = CityServiceActionDTO(
            action=CityServiceActionEnum(action),
            service_id=service_id,
            screen=CityServiceScreenEnum(screen) if screen else None,
            section_id=section_id,
            location_id=location_id,
            value=value,
        )
        response = await self._request(
            "POST",
            f"/city-services/v1/{char_id}/action",
            response_model=CityServiceResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )
        return _normalize_city_service_response(response)


def _normalize_city_service_response(response: CityServiceResponse) -> CityServiceResponse:
    if isinstance(response.payload, dict) and response.payload_type != "state_transition":
        return response.model_copy(update={"payload": CityServiceUIPayloadDTO.model_validate(response.payload)})
    return response
