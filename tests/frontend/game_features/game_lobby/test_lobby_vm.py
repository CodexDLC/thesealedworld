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
                    presence_status="online",
                )
            ]
        ),
        payload_type="lobby_start",
    )

    lobby = build_lobby_page_vm(response)

    assert lobby.slots[0].avatar_url == DEFAULT_CHARACTER_AVATAR_URL
    assert lobby.slots[0].presence_label == "В сети"
    assert lobby.slots[0].status == "Путешествие"


def test_empty_lobby_slot_keeps_avatar_empty_for_portal_template_art():
    response = GameLobbyResponse(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=_payload(slots=[LobbySlotPayload(index=2, is_empty=True, status="VACANT")]),
        payload_type="lobby_start",
    )

    lobby = build_lobby_page_vm(response)

    assert lobby.slots[0].is_empty is True
    assert lobby.slots[0].avatar_url is None
    assert lobby.slots[0].presence_label == "Свободен"


def test_lobby_with_existing_character_can_create_when_empty_slot_exists():
    response = GameLobbyResponse(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=_payload(
            slots=[
                LobbySlotPayload(
                    index=1,
                    is_empty=False,
                    character_id="8",
                    name="CodeX",
                    status="LOBBY",
                ),
                LobbySlotPayload(index=2, is_empty=True, status="VACANT"),
            ]
        ),
        payload_type="lobby_start",
    )

    lobby = build_lobby_page_vm(response)

    assert lobby.has_characters is True
    assert lobby.can_create is True


def test_lobby_template_uses_portal_art_for_empty_slots():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/character_slot.html").read_text(
        encoding="utf-8"
    )

    assert "/static/images/ui/lobby/threshold-portal.svg" in template
    assert "Выберите слот для новой истории" in template


def test_empty_slot_selects_without_opening_creation_form():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/character_slot.html").read_text(
        encoding="utf-8"
    )

    assert "selectedSlot = {{ slot.index }}" in template
    assert "selectedEmpty = {{ 'true' if slot.is_empty else 'false' }}" in template
    assert "startCreation" not in template


def test_create_button_opens_creation_after_empty_slot_selection():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/lobby_panel.html").read_text(
        encoding="utf-8"
    )

    assert '@click="creating = true"' in template
    assert ':disabled="selectedSlot !== null && !selectedEmpty"' in template


def test_lobby_slots_are_hidden_while_creation_form_is_open():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/lobby_panel.html").read_text(
        encoding="utf-8"
    )

    assert 'class="lobby-slots" aria-label="Character slots" x-show="!creating" x-cloak' in template
