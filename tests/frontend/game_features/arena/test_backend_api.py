from src.frontend.integrations.backend_api.arena import ArenaResponse, _normalize_arena_response
from src.shared.schemas.arena import ArenaScreenEnum, ArenaUIPayloadDTO


def test_arena_response_normalizes_dict_payload_to_ui_payload():
    response = ArenaResponse.model_validate(
        {
            "header": {"current_state": "arena"},
            "payload_type": "arena_screen",
            "payload": {
                "screen": "main_menu",
                "title": "Ангар Арены",
                "description": "Описание",
                "buttons": [],
            },
        }
    )

    normalized = _normalize_arena_response(response)

    assert isinstance(normalized.payload, ArenaUIPayloadDTO)
    assert normalized.payload.screen == ArenaScreenEnum.MAIN_MENU
