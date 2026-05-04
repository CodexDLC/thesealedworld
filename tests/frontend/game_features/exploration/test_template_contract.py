from pathlib import Path


def test_exploration_center_template_has_navigation_and_encounter_surfaces():
    template = Path("src/frontend/templates/game/domains/exploration/viewport/main.html").read_text()

    assert "payload_type == 'exploration_encounter'" in template
    assert "/game/exploration/move" in template
    assert "/game/exploration/interact" in template
    assert "exploration-control-panel" in template
    assert "exploration.navigation" in template
    assert "game/domains/exploration/right_sidebar/main.html" in template
    assert "hx-swap-oob=\"true\"" in template
    assert "AUTO ROUTES" in template
    assert "MOVE NORTH" in template
    assert "service_card(service)" in template
    assert "game/domains/exploration/components/services.html" in template
    assert "SERVICE_PENDING" not in template
    assert "exploration_button(exploration.grid.ne" not in template
    assert "exploration_button(exploration.grid.sw" not in template
    assert "exploration_button(exploration.grid.se" not in template
    assert "PEOPLE" not in template


def test_exploration_right_sidebar_has_navigation_and_encounter_contexts():
    template = Path("src/frontend/templates/game/domains/exploration/right_sidebar/main.html").read_text()

    assert "payload_type == 'exploration_navigation'" in template
    assert "payload_type == 'exploration_encounter'" in template
    assert "LOCAL_CONTEXT" in template
    assert "service_card(service, compact=true)" in template


def test_exploration_service_component_has_default_icon_mapping():
    template = Path("src/frontend/templates/game/domains/exploration/components/services.html").read_text()

    assert "service_icon_url" in template
    assert "service-icons/blacksmith.svg" in template
    assert "service-icons/default.svg" in template
    assert "service-card-action" in template
    assert "/game/exploration/use-service" in template
    assert '"service_id"' in template


def test_arena_main_template_has_service_lobby_contract():
    template = Path("src/frontend/templates/game/domains/arena/viewport/main.html").read_text()

    assert "arena.screen == 'main_menu'" in template
    assert "arena-header-art" in template
    assert "arena-mode-grid" in template
    assert "arena-mode-card--duel" in template
    assert "arena-mode-card--group" in template
    assert "arena-service-exit" in template
    assert "NO_DATA" in template
    assert "/game/arena/action" in template


def test_arena_css_is_a_dedicated_game_module():
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()
    source = Path("src/frontend/static/css/pages/game/arena.css").read_text()

    assert '@import url("pages/game/arena.css");' in bundle
    assert ".arena-lobby" in source
    assert ".arena-header-art" in source
    assert "arena-icons/sword-clash.svg" in source
    assert "arena-icons/knight-banner.svg" in source
    assert "arena-icons/tattered-banner.svg" in source
    assert "button-surface-02-blackened-metal.webp" in source


def test_status_main_prefers_panel_renderer_before_legacy_fragments():
    template = Path("src/frontend/templates/game/components/status/main.html").read_text()

    assert "game/components/panel/main.html" in template
    assert "game/components/status/fragments/" in template
    assert template.index("game/components/panel/main.html") < template.index("game/components/status/fragments/")


def test_character_status_panel_header_can_refresh_itself():
    template = Path("src/frontend/templates/game/components/panel/main.html").read_text()

    assert "panel-refresh-button" in template
    assert 'hx-get="/game/character-status/panel?char_id={{ char_id }}"' in template
    assert 'hx-target="#status-container"' in template


def test_avatar_widget_marks_missing_resource_data_explicitly():
    template = Path("src/frontend/templates/game/components/panel/widgets/avatar.html").read_text()

    assert "DATA_MISSING" in template


def test_game_shell_has_inventory_hud_window_placeholder():
    template = Path("src/frontend/templates/game/base_game.html").read_text()

    assert "x-data='gameShell" in template
    assert "hud-window inventory-window" in template
    assert "windows.inventory.open" in template
    assert "windows.inventory.dragging" in template
    assert "hud-window-drag-handle" in template
    assert "startHudWindowDrag('inventory'" in template
    assert "INVENTORY_LINK_PENDING" in template


def test_game_shell_drag_logic_lives_in_source_js():
    source = Path("src/frontend/static/js/core/game_shell.js").read_text()
    config = Path("src/frontend/static/css/compiler_config.json").read_text()

    assert "window.gameShell" in source
    assert "this.leftOpen && this.leftPanelView === nextView" in source
    assert "this.rightOpen && this.rightPanelView === nextView" in source
    assert "startHudWindowDrag" in source
    assert "moveHudWindow" in source
    assert "core/game_shell.js" in config


def test_game_header_nav_marks_open_panels_and_windows_active():
    template = Path("src/frontend/templates/game/domains/game_menu/header_nav.html").read_text()

    assert "leftOpen && leftPanelView" in template
    assert "rightOpen && rightPanelView" in template
    assert "windows.{{ item.window }}.open" in template


def test_game_runtime_loads_before_alpine_initializes():
    template = Path("src/frontend/templates/game/base_game.html").read_text()

    assert template.index('/static/js/game.js') < template.index('/static/js/vendor/alpine.js')


def test_game_header_has_system_exit_to_lobby():
    template = Path("src/frontend/templates/game/includes/header.html").read_text()

    assert 'class="game-exit-link"' in template
    assert 'href="/game-lobby"' in template
    assert 'data-session-cleanup="pending"' in template
