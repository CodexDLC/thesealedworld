from pydantic import ValidationError

from src.shared.enums import CoreDomain
from src.shared.schemas.tavern import TavernActionDTO, TavernActionEnum, TavernScreenEnum, TavernUIPayloadDTO


def test_core_domain_tavern_serializes_as_runtime_domain() -> None:
    assert CoreDomain.TAVERN.value == "tavern"


def test_tavern_payload_validates_screen_and_actions() -> None:
    payload = TavernUIPayloadDTO.model_validate(
        {
            "tavern_id": "last_refuge",
            "service_id": "svc_tavern_hub",
            "screen": "bar",
            "title": "Барная стойка",
            "description": "Ключи и слухи.",
            "buttons": [{"label": "Поговорить", "action": "talk_bartender"}],
        }
    )

    assert payload.screen == TavernScreenEnum.BAR
    assert payload.buttons[0].action == TavernActionEnum.TALK_BARTENDER


def test_tavern_action_rejects_unknown_action() -> None:
    try:
        TavernActionDTO.model_validate({"action": "unknown"})
    except ValidationError as exc:
        assert "Input should be" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown tavern action must fail validation")
