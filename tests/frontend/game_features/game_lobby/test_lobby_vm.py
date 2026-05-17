from pathlib import Path

from src.frontend.game_features.game_lobby.view_models.lobby import DEFAULT_CHARACTER_AVATAR_URL, build_lobby_page_vm
from src.frontend.integrations.backend_api.game_lobby import GameLobbyPayload, GameLobbyResponse, LobbySlotPayload
from src.shared.enums import CoreDomain
from src.shared.schemas import GameStateHeader

ROOT = Path(__file__).resolve().parents[4]


def _payload(*, slots: list[LobbySlotPayload]) -> GameLobbyPayload:
    return GameLobbyPayload(
        title="Порог",
        description="Выбери персонажа.",
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


def test_lobby_vm_preserves_backend_title_and_description():
    response = GameLobbyResponse(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=_payload(slots=[]),
        payload_type="lobby_start",
    )

    lobby = build_lobby_page_vm(response)

    assert lobby.title == "Порог"
    assert lobby.description == "Выбери персонажа."


def test_lobby_carousel_keeps_all_backend_slots():
    response = GameLobbyResponse(
        header=GameStateHeader(current_state=CoreDomain.LOBBY),
        payload=_payload(
            slots=[
                LobbySlotPayload(index=1, is_empty=False, character_id="8", name="CodeX", status="LOBBY"),
                LobbySlotPayload(index=2, is_empty=True, status="VACANT"),
                LobbySlotPayload(index=3, is_empty=True, status="VACANT"),
                LobbySlotPayload(index=4, is_empty=True, status="VACANT"),
            ]
        ),
        payload_type="lobby_start",
    )

    lobby = build_lobby_page_vm(response)

    assert [slot.index for slot in lobby.slots] == [1, 2, 3, 4]
    assert lobby.slots[1].is_empty is True
    assert lobby.slots[2].is_empty is True
    assert lobby.slots[3].is_empty is True


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


def test_create_button_opens_creation_when_slots_are_available():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/lobby_panel.html").read_text(
        encoding="utf-8"
    )

    assert '@click="mode = \'create\'"' in template
    assert ':disabled="selectedSlot !== null && !selectedEmpty"' not in template


def test_creation_form_uses_mvp_name_limits():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/creation_form.html").read_text(
        encoding="utf-8"
    )

    assert 'minlength="3"' in template
    assert 'maxlength="16"' in template
    assert 'pattern="[A-Za-zА-Яа-яЁё0-9_]{3,16}"' in template
    assert 'x-model.trim="creationName"' in template
    assert "checkCreationNameAvailability()" in template
    assert 'maxlength="32"' not in template


def test_empty_lobby_starts_with_intro_before_creation_form():
    panel_template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/lobby_panel.html").read_text(
        encoding="utf-8"
    )
    empty_template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/empty_state.html").read_text(
        encoding="utf-8"
    )

    assert "lobbyPanelState" in panel_template
    assert 'else "intro"' in panel_template
    assert "x-show=\"mode === 'intro'\"" in panel_template
    assert "lobby-intro" in empty_template
    assert '@click="mode = \'create\'"' in empty_template


def test_empty_lobby_intro_uses_readable_text_formatting():
    creation_template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/creation_form.html").read_text(
        encoding="utf-8"
    )
    empty_template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/empty_state.html").read_text(
        encoding="utf-8"
    )
    css = ROOT.joinpath("src/frontend/static/css/site/pages/game_lobby.css").read_text(encoding="utf-8")

    assert "lobby-primary-action" in empty_template
    assert "lobby-primary-action" in creation_template
    assert ".lobby-primary-action {" in css
    assert "letter-spacing: 0.04em;" in css
    assert "text-transform: none;" in css
    assert "text-align: left;" in css


def test_lobby_panel_state_lives_in_site_js_source():
    panel_template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/lobby_panel.html").read_text(
        encoding="utf-8"
    )
    source = ROOT.joinpath("src/frontend/static/js/site/lobby.js").read_text(encoding="utf-8")
    compiler_config = ROOT.joinpath("src/frontend/static/css/compiler_config.json").read_text(encoding="utf-8")

    assert "$refs.modalInput" not in panel_template
    assert "window.lobbyPanelState" in source
    assert "checkCreationNameAvailability" in source
    assert "/api/game-lobby/name-availability" in source
    assert "submitCreation" in source
    assert "site/lobby.js" in compiler_config


def test_lobby_panel_initializes_selected_character_from_server_rendered_slot():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/lobby_panel.html").read_text(
        encoding="utf-8"
    )
    source = ROOT.joinpath("src/frontend/static/js/site/lobby.js").read_text(encoding="utf-8")

    assert "initial_selection" in template
    assert '"selectedCharacterId": initial.slot.character_id if initial.slot else ""' in template
    assert "x-data='lobbyPanelState(" in template
    assert 'x-data="lobbyPanelState(' not in template
    assert 'name="character_id" value="{{ initial.slot.character_id if initial.slot else \'\' }}" :value="selectedCharacterId"' in template
    assert "initialSelection" in source
    assert "selectedCharacterId: selection.selectedCharacterId ?? \"\"" in source


def test_site_js_loads_before_alpine_for_lobby_x_data():
    base_template = ROOT.joinpath("src/frontend/templates/site/base_site.html").read_text(encoding="utf-8")

    assert base_template.index("/static/js/site.js") < base_template.index("/static/js/vendor/alpine.js")


def test_auth_pages_render_as_landing_overlay_modals():
    auth_routes = ROOT.joinpath("src/frontend/features/auth/routes/pages.py").read_text(encoding="utf-8")
    landing_template = ROOT.joinpath("src/frontend/templates/site/index.html").read_text(encoding="utf-8")
    auth_modal = ROOT.joinpath("src/frontend/templates/site/auth/modal.html").read_text(encoding="utf-8")
    site_bundle = ROOT.joinpath("src/frontend/static/css/site_bundle.css").read_text(encoding="utf-8")
    auth_css = ROOT.joinpath("src/frontend/static/css/site/pages/auth.css").read_text(encoding="utf-8")

    assert '"site/index.html"' in auth_routes
    assert '"auth_overlay_open": True' in auth_routes
    assert "{% include \"site/auth/modal.html\" %}" in landing_template
    assert 'class="auth-modal"' in auth_modal
    assert 'role="dialog"' in auth_modal
    assert '@import url("site/pages/auth.css");' in site_bundle
    assert ".auth-modal-backdrop" in auth_css


def test_landing_auth_actions_open_client_modal_without_navigation():
    base_template = ROOT.joinpath("src/frontend/templates/site/base_site.html").read_text(encoding="utf-8")
    header_template = ROOT.joinpath("src/frontend/templates/site/includes/header.html").read_text(encoding="utf-8")
    landing_template = ROOT.joinpath("src/frontend/templates/site/index.html").read_text(encoding="utf-8")
    modal_template = ROOT.joinpath("src/frontend/templates/site/includes/login_modal.html").read_text(encoding="utf-8")

    assert "authModal: null" in base_template
    assert "@click=\"authModal = 'login'\"" in header_template
    assert "href=\"/login\" class=\"btn-node site-login-link\"" not in header_template
    assert "@click=\"authModal = 'register'\"" in landing_template
    assert "@click=\"authModal = 'login'\"" in landing_template
    assert "href=\"/login\"><span>Войти</span>" not in landing_template
    assert "x-show=\"authModal\"" in modal_template
    assert "action=\"/login\"" in modal_template
    assert "action=\"/register\"" in modal_template


def test_site_account_menu_is_attached_control_with_icons():
    header_template = ROOT.joinpath("src/frontend/templates/site/includes/header.html").read_text(encoding="utf-8")
    header_css = ROOT.joinpath("src/frontend/static/css/site/shell/header.css").read_text(encoding="utf-8")

    assert 'class="site-account-btn"' in header_template
    assert 'class="btn-node site-account-btn"' not in header_template
    assert "/static/images/ui/game-menu-icons/person.svg" in header_template
    assert "/static/images/ui/service-icons/portal.svg" in header_template
    assert ".site-account {\n  position: relative;\n  width:" in header_css
    assert "top: calc(100% - 1px);" in header_css
    assert "width: 100%;" in header_css


def test_lobby_slots_are_hidden_while_creation_form_is_open():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/lobby_panel.html").read_text(
        encoding="utf-8"
    )

    assert 'class="lobby-slots lobby-slots--carousel" aria-label="Слоты персонажей" x-show="!creating"' in template
    assert 'aria-label="Слоты персонажей" x-show="!creating" x-cloak' not in template


def test_lobby_slots_render_as_single_horizontal_carousel():
    template = ROOT.joinpath("src/frontend/templates/site/game_lobby/fragments/lobby_panel.html").read_text(
        encoding="utf-8"
    )

    assert 'class="lobby-carousel-track"' in template
    assert "{% for slot in lobby.slots %}" in template
    assert "lobby.slots[:2]" not in template
    assert "lobby.slots[2:]" not in template


def test_lobby_modal_uses_responsive_breakpoints_and_centered_actions():
    css = ROOT.joinpath("src/frontend/static/css/site/pages/game_lobby.css").read_text(encoding="utf-8")

    assert "width: fit-content;" in css
    assert "calc((var(--lobby-card-size) * 2) + var(--lobby-grid-gap) + (var(--lobby-panel-padding) * 2))" in css
    assert ".page-game-lobby,\n    .has-lobby-modal" in css
    assert ".lobby-slot-actions {\n        width: 100%;" in css
    assert ".lobby-slot-actions {\n        display: grid;" in css
    assert "width: min(100%, 280px);" in css


def test_lobby_route_opens_as_landing_overlay_modal():
    route_template = ROOT.joinpath("src/frontend/game_features/game_lobby/routes/pages.py").read_text(encoding="utf-8")
    landing_template = ROOT.joinpath("src/frontend/templates/site/index.html").read_text(encoding="utf-8")
    modal_template = ROOT.joinpath("src/frontend/templates/site/game_lobby/modal.html").read_text(encoding="utf-8")

    assert '"site/index.html"' in route_template
    assert '"lobby_overlay_open": True' in route_template
    assert "{% include \"site/game_lobby/modal.html\" %}" in landing_template
    assert 'class="lobby-modal"' in modal_template
    assert 'role="dialog"' in modal_template


def test_landing_rift_links_to_lobby_with_tooltip():
    landing_template = ROOT.joinpath("src/frontend/templates/site/index.html").read_text(encoding="utf-8")
    landing_css = ROOT.joinpath("src/frontend/static/css/site/pages/the_sealed_world_landing.css").read_text(
        encoding="utf-8"
    )

    assert 'class="tsw-hero-bg" aria-hidden="true"' in landing_template
    assert '<a class="tsw-hero-rift" href="/game-lobby" aria-label="Заглянуть в мир">' in landing_template
    assert '<button type="button" class="tsw-hero-rift" @click="authModal = \'login\'"' in landing_template
    assert 'class="tsw-rift-tooltip"' in landing_template
    assert ".tsw-rift-tooltip" in landing_css
    assert ".tsw-hero-rift:hover .tsw-rift-tooltip" in landing_css
    assert "z-index: 6;" in landing_css
    assert "aspect-ratio: 1 / 1;" in landing_css
    assert "object-fit: contain;" in landing_css
    assert "display: grid;" in landing_css
    assert "pointer-events: none;" in landing_css


def test_landing_mobile_header_and_hero_contracts_are_explicit():
    header_css = ROOT.joinpath("src/frontend/static/css/site/shell/header.css").read_text(encoding="utf-8")
    landing_css = ROOT.joinpath("src/frontend/static/css/site/pages/the_sealed_world_landing.css").read_text(
        encoding="utf-8"
    )

    assert "@media (max-width: 720px)" in header_css
    assert ".site-account-label,\n  .site-account-caret" in header_css
    assert "width: auto;" in header_css
    assert "grid-template-columns: 1fr;" in header_css
    assert "@media (max-width: 720px) and (orientation: portrait)" in landing_css
    assert "@media (max-width: 900px) and (orientation: landscape)" in landing_css
    assert "width: min(76vw, 340px);" in landing_css
    assert "width: 132vw" not in landing_css


def test_site_buttons_do_not_use_cut_corners():
    buttons_css = ROOT.joinpath("src/frontend/static/css/site/components/buttons.css").read_text(encoding="utf-8")

    btn_node_block = buttons_css.split(".btn-node {", maxsplit=1)[1].split(".btn-node::before", maxsplit=1)[0]
    assert "clip-path" not in btn_node_block
    assert "border-radius: 2px;" in btn_node_block


def test_site_css_does_not_use_legacy_app_or_game_component_entrypoints():
    site_bundle = ROOT.joinpath("src/frontend/static/css/site_bundle.css").read_text(encoding="utf-8")
    site_base = ROOT.joinpath("src/frontend/templates/site/base_site.html").read_text(encoding="utf-8")
    cabinet_base = ROOT.joinpath("src/frontend/templates/site/base_cabinet.html").read_text(encoding="utf-8")

    assert not ROOT.joinpath("src/frontend/static/css/app.css").exists()
    assert not ROOT.joinpath("src/frontend/static/css/base.css").exists()
    assert not ROOT.joinpath("src/frontend/static/css/pages/game.css").exists()
    assert not ROOT.joinpath("src/frontend/static/css/pages/design_system.css").exists()
    assert not ROOT.joinpath("src/frontend/templates/shared/styles.html").exists()

    assert "/static/css/site.css" in site_base
    assert "/static/css/cabinet.css" in cabinet_base
    assert "/static/css/app.css" not in site_base
    assert "/static/css/app.css" not in cabinet_base
    assert "site/components/buttons.css" in site_bundle
    assert "components/game/" not in site_bundle


def test_guest_game_lobby_opens_auth_overlay_without_login_redirect():
    route_template = ROOT.joinpath("src/frontend/game_features/game_lobby/routes/pages.py").read_text(encoding="utf-8")

    assert "get_current_user(request)" in route_template
    assert "auth_overlay_open" in route_template
    assert "require_current_user(request)" not in route_template.split("@router.get(\"/game-lobby\"")[1].split(
        "@router.get(\"/api/game-lobby/status\""
    )[0]
