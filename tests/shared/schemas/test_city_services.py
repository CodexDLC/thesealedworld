from pydantic import ValidationError

from src.shared.enums import CoreDomain
from src.shared.schemas.city_services import (
    CityServiceActionDTO,
    CityServiceActionEnum,
    CityServiceScreenEnum,
    CityServiceUIPayloadDTO,
)


def test_core_domain_city_services_serializes_as_runtime_domain() -> None:
    assert CoreDomain.CITY_SERVICES.value == "city_services"


def test_city_service_payload_validates_sections_and_actions() -> None:
    payload = CityServiceUIPayloadDTO.model_validate(
        {
            "service_id": "svc_tavern_hub",
            "service_type": "tavern",
            "screen": "section",
            "section_id": "bar",
            "title": "Стойка кормчего",
            "description": "Ключи и слухи.",
            "sections": [{"id": "bar", "title": "Стойка кормчего"}],
            "buttons": [{"label": "Поговорить", "action": "start_dialogue", "section_id": "bar"}],
        }
    )

    assert payload.screen == CityServiceScreenEnum.SECTION
    assert payload.buttons[0].action == CityServiceActionEnum.START_DIALOGUE


def test_city_service_action_rejects_unknown_action() -> None:
    try:
        CityServiceActionDTO.model_validate({"action": "unknown", "service_id": "svc_tavern_hub"})
    except ValidationError as exc:
        assert "Input should be" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown city service action must fail validation")
