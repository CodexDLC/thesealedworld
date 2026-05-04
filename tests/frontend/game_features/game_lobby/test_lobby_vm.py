from pathlib import Path

from src.frontend.game_features.game_lobby.view_models.lobby import DEFAULT_CHARACTER_AVATAR_URL, build_lobby_page_vm
from src.frontend.integrations.backend_api.game_lobby import GameLobbyPayload, GameLobbyResponse, LobbySlotPayload
from src.shared.enums import CoreDomain
from src.shared.schemas import GameStateHeader

ROOT = Path(__file__).resolve().parents[4]


def _payload(*, slots: list[LobbySlotPayload]) -> GameLobbyPayload:
    return GameLobbyPayload(
        title="The Threshold",
        description="Choose a vessel.",
        primary_action_label="Начать приключение",
        primary_action="start_adventure",
        slots=slots,
    )


def test_occupied_lobby_slot_uses_default_avatar_when_backend_has_none():
    response = GameLobbyResponse(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=_payload(
            slots=[
                LobbySlotPayload(
                    index=1,
                    is_empty=False,
                    character_id="8",
                    name="CodeX",
                    avatar_url=None,
                    status="EXPLORATION",
                )
            ]
        ),
        payload_type="lobby_start",
    )

    lobby = build_lobby_page_vm(response)

    assert lobby.slots[0].avatar_url == DEFAULT_CHARACTER_AVATAR_URL


def test_empty_lobby_slot_keeps_avatar_empty_for_portal_template_art():
    response = GameLobbyResponse(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=_payload(slots=[LobbySlotPayload(index=2, is_empty=True, status="VACANT")]),
        payload_type="lobby_start",
    )

    lobby = build_lobby_page_vm(response)

    assert lobby.slots[0].is_empty is True
    assert lobby.slots[0].avatar_url is None


def test_lobby_template_uses_portal_art_for_empty_slots():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/character_slot.html").read_text(
        encoding="utf-8"
    )

    assert "/static/images/ui/lobby/threshold-portal.svg" in template
