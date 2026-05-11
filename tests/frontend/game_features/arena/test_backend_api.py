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


def test_arena_action_route_maps_lifecycle_actions_to_v2_arena_channel():
    from src.frontend.integrations.backend_api.arena import BackendArenaApi

    assert BackendArenaApi._action_route(char_id=7, action="menu_main", mode=None) == (
        "POST",
        "/arena/v2/7/action",
    )
    assert BackendArenaApi._action_route(char_id=7, action="leave", mode=None) == ("POST", "/arena/v2/7/action")


def test_arena_action_route_maps_mode_entries_to_v2_read_channels():
    from src.frontend.integrations.backend_api.arena import BackendArenaApi

    assert BackendArenaApi._action_route(char_id=7, action="menu_mode", mode="one_vs_one") == (
        "GET",
        "/arena/v2/7/duel/view",
    )
    assert BackendArenaApi._action_route(char_id=7, action="menu_mode", mode="group") == (
        "GET",
        "/arena/v2/7/group/lobby",
    )


def test_arena_action_route_maps_duel_actions_to_v2_duel_channel():
    from src.frontend.integrations.backend_api.arena import BackendArenaApi

    assert BackendArenaApi._action_route(char_id=7, action="join_queue", mode="one_vs_one") == (
        "POST",
        "/arena/v2/7/duel/action",
    )
    assert BackendArenaApi._action_route(char_id=7, action="check_combat_ready", mode="one_vs_one") == (
        "POST",
        "/arena/v2/7/duel/action",
    )
