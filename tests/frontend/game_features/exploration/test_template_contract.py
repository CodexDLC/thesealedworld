from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.frontend.game_features.inventory.view_models.window import (
    InventoryRowVM,
    build_inventory_card_vm,
    build_inventory_window_vm,
    inventory_card_class,
    inventory_card_dimensions,
)
from src.shared.schemas.exploration import (
    ExplorationLocalMapDTO,
    ExplorationMapCellDTO,
    ExplorationMapEdgeDTO,
    NavigationGridDTO,
    WorldNavigationDTO,
)
from src.shared.schemas.inventory import InventoryWindowDTO


def test_exploration_center_template_has_navigation_and_encounter_surfaces():
    template = Path("src/frontend/templates/game/domains/exploration/viewport/main.html").read_text()

    assert "payload_type == 'exploration_encounter'" in template
    assert "/game/exploration/move" in template
    assert "/game/exploration/interact" in template
    assert "exploration-main-dock" in template
    assert "mobile-center-menu" in template
    assert "QUESTS" in template
    assert "BUILDS" not in template
    assert "game-screen-content exploration-screen-content" in template
    assert "mobile-scene parchment" in template
    assert "mobile-scene-services" in template
    assert "location_view.city_map" in template
    assert "city_map_layout = city_map and not active_encounter" in template
    assert "has-city-map-layout" in template
    assert "has-city-map-scene" in template
    assert "mobile-scene-copy mobile-scene-copy--map" in template
    assert "is-mobile-row-trim" in template
    assert "exploration-city-map" in template
    assert "exploration-city-map-tile" in template
    assert "exploration-city-map-marker" in template
    assert "map_cell.service_markers" in template
    assert "[map_cell.service_marker]" not in template
    assert "exploration-city-map-service-marker" in template
    assert "is-{{ service_marker_corner }}" in template
    assert "data-services" in template
    assert "NO SERVICES" in template
    assert "mobile-services" in template
    assert "game-action-panel game-action-panel--bottom exploration-action-panel" in template
    assert "mobile-action-grid exploration-navigation-grid" in template
    assert "game-action-button mobile-action" in template
    assert "location_view.navigation" in template
    assert "data-move-duration" in template
    assert "button.tooltip" in template
    assert "data-tippy-theme=\"game-hint\"" in template
    assert "mobile-move-cooldown" in template
    assert "mobile-move-cooldown exploration-movement-block" not in template
    assert "mobile-bottom-rule" in template
    assert template.index("mobile-bottom-rule") < template.index("mobile-move-cooldown")
    assert template.index("mobile-move-cooldown") < template.index("exploration-action-panel__body")
    assert template.index("mobile-services") < template.index("mobile-action-grid exploration-navigation-grid")
    assert "game/domains/exploration/right_sidebar/main.html" in template
    assert 'id="game-right-context-content" hx-swap-oob="innerHTML"' in template
    assert "game/components/status/main.html" in template
    assert "game/domains/exploration/left_sidebar/main.html" not in template
    assert 'id="game-left-content" hx-swap-oob="true"' in template
    assert "mobile-encounter-interrupt" in template
    assert "mobile-encounter-layout" in template
    assert "mobile-encounter-target-card" in template
    assert "mobile-encounter-target-switcher" in template
    assert "mobile-encounter-roster" in template
    assert "mobile-encounter-actions" in template
    assert 'encounter_surfaces(active_encounter, symbiote_name)' in template
    assert '<span class="symbiote-readout-name">SYMBIOTE:</span>' not in template
    assert "default_bypass_chance" in template
    assert "шанс обойти" in template
    assert "\"action\": \"bypass\"" in template
    assert "@click=\"selected =" in template
    assert "enemy.hp_percent" in template
    assert "hp.cur" not in template
    assert "POWER" not in template
    assert "<span>THREAT</span>" not in template
    assert "<span>ENERGY</span>" in template
    assert "<span>CONC</span>" in template
    assert "<span>DANGER</span>" in template
    assert "NORTH" in template
    assert "service_tile(service" in template
    assert "service_icon_url(service)" in template
    assert "game/domains/exploration/components/services.html" in template
    assert "SERVICE_PENDING" not in template
    assert "mobile-chat-drawer" not in template
    assert "PEOPLE" not in template
    assert "location_view.hud.threat if location_view.hud is defined" in template
    assert "data-risk-frame" in template
    assert "payload_type == 'exploration_encounter' and not" not in template
    assert "HOSTILES" not in template


def test_runtime_surfaces_do_not_use_legacy_world_glass_contract():
    checked_paths = [
        Path("src/frontend/templates/game/includes/world_theme_vars.html"),
        Path("src/frontend/static/css/game/shell/layout/base.css"),
        Path("src/frontend/static/css/game/shell/layout/columns.css"),
        Path("src/frontend/static/css/game/shell/responsive/mobile_drawers.css"),
        Path("src/frontend/static/css/game/components/panels.css"),
        Path("src/frontend/static/css/game/domains/exploration/scene.css"),
        Path("src/frontend/static/css/site/components/panels.css"),
        Path("src/frontend/static/css/admin/components/panels.css"),
    ]

    for path in checked_paths:
        assert "--world-glass" not in path.read_text(encoding="utf-8"), path


def test_game_panel_and_scenario_readability_avoids_micro_text():
    checked_paths = [
        Path("src/frontend/static/css/game/components/panel_dock.css"),
        Path("src/frontend/static/css/game/components/info_panel.css"),
        Path("src/frontend/static/css/game/components/status_widgets.css"),
        Path("src/frontend/static/css/game/domains/scenario/screen.css"),
        Path("src/frontend/static/css/game/domains/scenario/scene.css"),
        Path("src/frontend/static/css/game/domains/scenario/choices.css"),
        Path("src/frontend/static/css/game/domains/scenario/panels.css"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked_paths)
    tokens = Path("src/frontend/static/css/game/core/tokens.css").read_text(encoding="utf-8")

    assert "--game-panel-label-size" in tokens
    assert "--game-panel-value-size" in tokens
    for path in checked_paths:
        assert "font-size: 6px" not in path.read_text(encoding="utf-8"), path
    assert "letter-spacing: 0.18em" not in combined
    assert "font-size: var(--game-panel-label-size)" in combined


def test_exploration_right_sidebar_has_navigation_and_encounter_contexts():
    template = Path("src/frontend/templates/game/domains/exploration/right_sidebar/main.html").read_text()

    assert "payload_type == 'exploration_encounter'" in template
    assert "exploration-info-dock" in template
    assert "INFO" in template
    assert "CLOSE" in template
    assert "info-widget-section exploration-location-card" in template
    assert "exploration-encounter-info" in template
    assert "exploration-monster-card" in template
    assert "hud.threat if hud and hud.threat is defined else 0" in template
    assert "<span>Tier</span>" in template
    assert "exploration-minimap-card" in template
    assert "exploration-minimap-grid" in template
    assert "data-map-tooltip" in template
    assert "is-route-hint" in template
    assert "NO MAP DATA" in template


def test_exploration_right_sidebar_renders_runtime_local_radar():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/domains/exploration/right_sidebar/main.html")
    radar = ExplorationLocalMapDTO(
        char_id=7,
        current_loc_id="52_52",
        radius=1,
        size=3,
        rows=[
            [
                ExplorationMapCellDTO(
                    loc_id="52_52",
                    x=52,
                    y=52,
                    dx=0,
                    dy=0,
                    is_current=True,
                    is_known=True,
                    title="Площадь Исхода",
                    is_safe_zone=True,
                    threat_tier=0,
                    zone_id="D4_1_1",
                    terrain="ancient_pavement",
                    service_count=1,
                    service_labels=["В постоялый двор"],
                    players_count=2,
                    battles_count=1,
                    edges={
                        "north": ExplorationMapEdgeDTO(
                            direction="north",
                            state="open",
                            target_loc_id="52_51",
                            label="Северный проспект",
                        ),
                        "south": ExplorationMapEdgeDTO(direction="south", state="locked"),
                        "west": ExplorationMapEdgeDTO(direction="west", state="blocked"),
                        "east": ExplorationMapEdgeDTO(direction="east", state="open", target_loc_id="53_52"),
                    },
                    render_edges={
                        "south": ExplorationMapEdgeDTO(direction="south", state="locked"),
                        "west": ExplorationMapEdgeDTO(direction="west", state="blocked"),
                    },
                    tooltip={"title": "Площадь Исхода"},
                )
            ]
        ],
    )

    html = template.render(
        payload_type="exploration_navigation",
        exploration=WorldNavigationDTO(
            loc_id="52_52",
            title="Площадь Исхода",
            description="Центральная площадь.",
            grid=NavigationGridDTO(),
        ),
        exploration_local_map=radar,
    )

    assert "LOCAL RADAR" in html
    assert "RADAR DATA" in html
    assert 'data-map-cell="52_52"' in html
    assert "is-zone-safe" in html
    assert "is-tier-0" not in html
    assert "exploration-minimap-status-code is-safe" in html
    assert ">S<" in html.replace("\n", "").replace(" ", "")
    assert 'data-zone-id="D4_1_1"' in html
    assert 'data-terrain="ancient_pavement"' in html
    assert 'data-tippy-content="Площадь Исхода // X 52 / Y 52 // SAFE · T0 // Entrances: В постоялый двор // People 2 · Battles 1 · Corpses NO_DATA"' in html
    assert "exploration-minimap-marker is-players" in html
    assert "exploration-minimap-marker is-battles" in html
    assert "exploration-minimap-marker is-services" in html
    assert "Площадь Исхода" in html
    assert "exploration-minimap-wall--south is-locked" in html
    assert "exploration-minimap-wall--west" in html
    assert "NO MAP DATA" not in html


def test_exploration_uses_shared_base_css_contracts():
    panel_css = Path("src/frontend/static/css/game/components/panel_dock.css").read_text()
    action_css = Path("src/frontend/static/css/game/components/action_panel.css").read_text()
    exploration_dir = Path("src/frontend/static/css/game/domains/exploration")
    screen_css = exploration_dir.joinpath("screen.css").read_text()
    scene_css = exploration_dir.joinpath("scene.css").read_text()
    services_css = exploration_dir.joinpath("services.css").read_text()
    movement_css = exploration_dir.joinpath("movement.css").read_text()
    encounters_css = exploration_dir.joinpath("encounters.css").read_text()
    right_sidebar_css = exploration_dir.joinpath("right_sidebar.css").read_text()
    responsive_css = exploration_dir.joinpath("responsive.css").read_text()
    index_css = exploration_dir.joinpath("index.css").read_text()
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()

    assert ".dock-nav--five" in panel_css
    assert ".mobile-center-menu" in panel_css
    assert ".mobile-nav-icon" in panel_css
    assert ".side-panel-drawer--right" in panel_css
    assert ".game-screen-area" in screen_css
    assert ".game-screen-content" in screen_css
    assert ".exploration-main-dock" in screen_css
    assert "var(--game-column-gutter-top" in screen_css
    assert ".mobile-scene" in scene_css
    assert ".mobile-scene-art.has-city-map" in scene_css
    assert ".mobile-scene.parchment.has-city-map-scene" in scene_css
    assert ".mobile-scene-copy--map" in scene_css
    assert ".exploration-city-map" in scene_css
    assert "width: min(100cqw, calc(100cqh - var(--city-map-copy-reserve, 132px)))" in scene_css
    assert "height: min(100cqw, calc(100cqh - var(--city-map-copy-reserve, 132px)))" in scene_css
    assert "grid-template-columns: repeat(var(--city-map-columns, var(--city-map-size, 5)), minmax(0, 1fr))" in scene_css
    assert "grid-template-rows: repeat(var(--city-map-rows, var(--city-map-size, 5)), minmax(0, 1fr))" in scene_css
    assert "background-size: 100% 100%" in scene_css
    assert ".exploration-city-map-marker" in scene_css
    assert ".exploration-city-map-service-marker" in scene_css
    assert ".exploration-city-map-service-marker.is-top-left" in scene_css
    assert ".exploration-city-map-service-marker.is-top-right" in scene_css
    assert ".exploration-city-map-service-marker.is-bottom-left" in scene_css
    assert ".exploration-city-map-service-marker.is-bottom-right" in scene_css
    assert "right: auto" in scene_css
    assert "bottom: auto" in scene_css
    assert "top: auto" in scene_css
    assert "left: auto" in scene_css
    assert "aspect-ratio: 7 / 5" in scene_css
    assert "--city-map-rows: 5" in scene_css
    assert ".exploration-city-map-tile.is-mobile-row-trim" in scene_css
    assert ".mobile-services" in services_css
    assert ".service-card" in services_css
    assert ".mobile-action-grid" in movement_css
    assert ".mobile-action-icon" in movement_css
    assert ".mobile-move-cooldown" in movement_css
    assert ".mobile-move-cooldown.is-cooling" in movement_css
    assert ".mobile-encounter-interrupt" in encounters_css
    assert ".mobile-encounter-target-card" in encounters_css
    assert ".exploration-minimap-grid" in right_sidebar_css
    assert "aspect-ratio: 1 / 1" in right_sidebar_css
    assert "grid-template-columns: repeat(5, minmax(0, 1fr))" in right_sidebar_css
    assert ".exploration-minimap-cell:not([data-tippy-content])::after" in right_sidebar_css
    assert ".exploration-minimap-cell.is-route-hint" in right_sidebar_css
    assert ".exploration-minimap-cell.is-zone-safe::before" in right_sidebar_css
    assert ".exploration-minimap-cell.is-tier-1::before" in right_sidebar_css
    assert ".exploration-minimap-cell.is-tier-3::before" in right_sidebar_css
    assert ".exploration-minimap-status-code" in right_sidebar_css
    assert ".exploration-minimap-status-code.is-safe" in right_sidebar_css
    assert ".exploration-minimap-status-code.is-danger" in right_sidebar_css
    assert ".exploration-minimap-markers" in right_sidebar_css
    assert ".exploration-action-panel" in screen_css
    assert ".exploration-screen-content.has-city-map-layout" in screen_css
    assert "container-type: size" in screen_css
    assert "--city-map-copy-reserve" in screen_css
    assert "--game-action-padding" in screen_css
    assert "grid-template-rows: auto auto" in screen_css
    assert "grid-template-columns: minmax(220px, 0.4fr) minmax(0, 0.6fr)" in responsive_css
    assert "grid-template-rows: auto" in responsive_css
    assert ".exploration-main-dock .mobile-services" in screen_css
    assert "grid-column: 1" in responsive_css
    assert "grid-row: 1" in screen_css
    assert ".exploration-main-dock .mobile-move-cooldown" in screen_css
    assert ".exploration-main-dock .mobile-action-grid" in screen_css
    assert "grid-row: 2" in screen_css
    assert ".exploration-main-dock .exploration-navigation-grid" in screen_css
    assert ".exploration-main-dock .exploration-navigation-grid {\n    align-self: stretch;\n}" in screen_css
    assert not responsive_css.lstrip().startswith("align-self:")
    assert "margin-top: auto" in action_css
    assert ".exploration-main-dock.mobile-rift--encounter .mobile-screen.is-active" in responsive_css
    assert ".exploration-main-dock.mobile-rift--encounter .mobile-encounter-layout" in responsive_css
    assert ".exploration-main-dock.mobile-rift--encounter .exploration-action-panel" in responsive_css
    assert ".exploration-main-dock.mobile-rift--encounter .mobile-encounter-actions" in responsive_css
    assert ".exploration-main-dock.mobile-rift--encounter .mobile-encounter-target-switcher" in responsive_css
    assert "@media (max-width: 899px)" in responsive_css
    assert '@import url("game/components/action_panel.css");' in bundle
    assert '@import url("game/components/panel_dock.css");' in bundle
    assert '@import url("game/domains/exploration/index.css");' in bundle
    assert '@import url("screen.css");' in index_css
    assert '@import url("responsive.css");' in index_css
    assert 'game/domains/exploration/screen.css' not in bundle
    assert 'game/domains/exploration/responsive.css' not in bundle
    assert 'game/domains/exploration.css' not in bundle


def test_game_action_panel_bottom_behavior_is_explicit_shell_contract():
    action_css = Path("src/frontend/static/css/game/components/action_panel.css").read_text()
    scenario_css = Path("src/frontend/static/css/game/domains/scenario/choices.css").read_text()
    templates = "\n".join(
        Path(path).read_text()
        for path in (
            "src/frontend/templates/game/domains/exploration/viewport/main.html",
            "src/frontend/templates/game/domains/scenario/viewport/main.html",
            "src/frontend/templates/game/domains/scenario/viewport/finalized.html",
            "src/frontend/templates/game/domains/combat/viewport/main.html",
            "src/frontend/templates/game/domains/arena/viewport/main.html",
        )
    )

    bottom_contract = action_css.split(
        ".game-screen-area--vertical > .game-action-panel--bottom {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    scenario_block = scenario_css.split(".scenario-action-panel {", maxsplit=1)[1].split("}", maxsplit=1)[0]

    assert ".game-action-panel--bottom" in action_css
    assert "flex: 0 0 auto;" in bottom_contract
    assert "grid-row: -2 / -1;" in bottom_contract
    assert "align-self: stretch;" in bottom_contract
    assert "margin-top: auto;" in bottom_contract
    assert "z-index: var(--game-action-z" in bottom_contract
    assert "align-self:" not in scenario_block
    assert "margin-top:" not in scenario_block
    assert "game-action-panel game-action-panel--bottom exploration-action-panel" in templates
    assert "game-action-panel game-action-panel--bottom scenario-action-panel" in templates
    assert "game-action-panel game-action-panel--bottom combat-action-panel" in templates
    assert "game-action-panel game-action-panel--bottom arena-action-panel" in templates


def test_exploration_quests_nav_opens_central_unavailable_modal():
    nav = Path("src/frontend/templates/game/domains/game_menu/header_nav.html").read_text()
    shell_js = Path("src/frontend/static/js/core/game_shell.js").read_text()
    modal_css = Path("src/frontend/static/css/game/components/modal.css").read_text()
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()

    assert "item.modal" in nav
    assert "game-modal-open" in nav
    assert "openUnavailableModal" in shell_js
    assert "Система квестов будет доступна позже" in shell_js
    assert "if (detail.title) copy.title = detail.title" in shell_js
    assert "if (detail.body) copy.body = detail.body" in shell_js
    assert ".game-modal-backdrop" in modal_css
    assert ".game-unavailable-modal" in modal_css
    assert '@import url("game/components/modal.css");' in bundle


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

    assert "arena_screen == 'main_menu'" in template
    assert "arena-header-art" in template
    assert "arena-mode-grid" in template
    assert "arena-mode-card--duel" in template
    assert "arena-mode-card--group" in template
    assert "arena-mode-stage" in template
    assert "arena-queue-card" in template
    assert "arena-queue-card--primary" in template
    assert "queue_waiting_count" in template
    assert "arena-search-limit" in template
    assert "arena-repair-banner" in template
    assert "arena-group-tabs" in template
    assert "arena_group_browser" in template
    assert "/game/arena/group-action" in template
    assert "arena-live-battles" in template
    assert "arena-battle-row" in template
    assert "arena-matchmaking-panel" in template
    assert "arena-search-stage" in template
    assert "arena-service-exit" in template
    assert "status_seed.symbiote_name" in template
    assert "symbiote-readout-name" in template
    assert "NO_DATA" in template
    assert "/game/arena/action" in template


def test_arena_right_sidebar_has_view_contract():
    shell = Path("src/frontend/templates/game/session_content_inner.html").read_text()
    template = Path("src/frontend/templates/game/domains/arena/right_sidebar/main.html").read_text()

    assert "game/domains/arena/right_sidebar/main.html" in shell
    assert "panel-dock" in template
    assert "info-widget-section" in template
    assert "dock-nav-button--close" in template
    assert "ARENA VIEW" in template
    assert "Rank" in template
    assert "RATING" in template
    assert "MMR" in template
    assert "League" in template
    assert "Record" in template
    assert "Placement" in template
    assert "Season" in template
    assert "Hall" in template
    assert "GEAR SCORE" not in template
    assert "LIVE BATTLES" not in template
    assert "NO_DATA" in template


def test_arena_group_action_modal_contract():
    template = Path("src/frontend/templates/game/domains/arena/fragments/group_action_modal.html").read_text()
    route = Path("src/frontend/game_features/arena/routes/actions.py").read_text()

    assert "game-modal-root" in template
    assert "arena-modal-backdrop" in template
    assert "arena-dev-modal" in template
    assert "notice.get('formats'" in template
    assert "/game/arena/group-action" in route
    assert "service.group_action" in route


def test_arena_css_is_a_dedicated_game_module():
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()
    arena_dir = Path("src/frontend/static/css/game/domains/arena")
    index = arena_dir.joinpath("index.css").read_text()
    lobby = arena_dir.joinpath("lobby.css").read_text()
    modes = arena_dir.joinpath("modes.css").read_text()
    matchmaking = arena_dir.joinpath("matchmaking.css").read_text()
    groups = arena_dir.joinpath("groups.css").read_text()
    live_battles = arena_dir.joinpath("live_battles.css").read_text()
    group_browser = arena_dir.joinpath("group_browser.css").read_text()
    modals = arena_dir.joinpath("modals.css").read_text()
    right_sidebar = arena_dir.joinpath("right_sidebar.css").read_text()
    responsive = arena_dir.joinpath("responsive.css").read_text()
    source = "\n".join(
        path.read_text()
        for path in (
            arena_dir / "lobby.css",
            arena_dir / "modes.css",
            arena_dir / "groups.css",
            arena_dir / "matchmaking.css",
            arena_dir / "live_battles.css",
            arena_dir / "group_browser.css",
            arena_dir / "modals.css",
            arena_dir / "right_sidebar.css",
            arena_dir / "repair.css",
            arena_dir / "responsive.css",
        )
    )

    assert '@import url("game/domains/arena/index.css");' in bundle
    assert '@import url("lobby.css");' in index
    assert '@import url("responsive.css");' in index
    assert ".arena-lobby" in lobby
    assert "#arena-poll-region" in lobby
    assert ".arena-header-art" in lobby
    assert ".arena-mode-stage" in modes
    assert ".arena-queue-card" in matchmaking
    assert ".arena-queue-card--primary" in matchmaking
    assert ".arena-center-screens" in modes
    assert ".arena-search-limit" in matchmaking
    assert ".arena-repair-banner" in source
    assert ".arena-group-tabs" in group_browser
    assert ".arena-plan-card" in groups
    assert ".arena-modal-backdrop" in modals
    assert ".arena-live-battles" in live_battles
    assert ".arena-battle-row" in live_battles
    assert ".arena-search-stage" in matchmaking
    assert ".arena-countdown-value" in matchmaking
    assert ".arena-view-stat-grid" in right_sidebar
    assert "@media (max-width: 900px) and (orientation: landscape)" in responsive
    assert "arena-icons/sword-clash.svg" in source
    assert "arena-icons/knight-banner.svg" in source
    assert "arena-icons/tattered-banner.svg" in source
    assert "arena-main-hub.webp" in source
    assert "duel-hall.webp" in source
    assert "team-battle-hall.webp" in source
    assert "queue-scanner.webp" in source
    assert "combat-pending-gate.webp" in source
    assert "button-surface-02-blackened-metal.webp" in source


def test_game_domain_css_uses_manifest_entrypoints():
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()
    domains = ("status", "chat", "exploration", "selection", "field", "scenario", "arena", "combat", "loot")

    for domain in domains:
        domain_dir = Path(f"src/frontend/static/css/game/domains/{domain}")
        assert domain_dir.joinpath("index.css").exists()
        assert not Path(f"src/frontend/static/css/game/domains/{domain}.css").exists()
        assert f'@import url("game/domains/{domain}/index.css");' in bundle
        assert f'@import url("game/domains/{domain}.css");' not in bundle


def test_game_shell_layout_uses_manifest_entrypoint():
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()
    layout_dir = Path("src/frontend/static/css/game/shell/layout")
    index = layout_dir.joinpath("index.css").read_text()
    base = layout_dir.joinpath("base.css").read_text()
    header = layout_dir.joinpath("header.css").read_text()
    columns = layout_dir.joinpath("columns.css").read_text()
    legacy_screen = layout_dir.joinpath("legacy_screen.css").read_text()
    utilities = layout_dir.joinpath("utilities.css").read_text()

    assert '@import url("game/shell/layout/index.css");' in bundle
    assert '@import url("game/shell/layout.css");' not in bundle
    assert not Path("src/frontend/static/css/game/shell/layout.css").exists()
    assert '@import url("base.css");' in index
    assert '@import url("utilities.css");' in index
    assert ".game-container" in base
    assert "#app-viewport" in base
    assert ".game-header" in header
    assert ".game-system-menu" in header
    assert ".game-top-row" in columns
    assert ".col-center-inner" in columns
    assert "--game-column-gutter-top: 10px" in base
    assert "#game-left-content" in columns
    assert "#game-right-content" in columns
    assert "var(--game-column-gutter-top" in columns
    assert ".cs-content" in legacy_screen
    assert ".status-dot.pulse" in utilities


def test_game_shell_responsive_uses_manifest_entrypoint():
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()
    responsive_dir = Path("src/frontend/static/css/game/shell/responsive")
    index = responsive_dir.joinpath("index.css").read_text()
    tokens = responsive_dir.joinpath("tokens.css").read_text()
    columns_desktop = responsive_dir.joinpath("columns_desktop.css").read_text()
    combat_desktop = responsive_dir.joinpath("combat_desktop.css").read_text()
    tablet_drawers = responsive_dir.joinpath("tablet_drawers.css").read_text()
    mobile_drawers = responsive_dir.joinpath("mobile_drawers.css").read_text()
    mobile_header = responsive_dir.joinpath("mobile_header.css").read_text()
    system_menu = responsive_dir.joinpath("system_menu.css").read_text()
    narrow_phone = responsive_dir.joinpath("narrow_phone.css").read_text()

    assert '@import url("game/shell/responsive/index.css");' in bundle
    assert '@import url("game/shell/layout_responsive.css");' not in bundle
    assert not Path("src/frontend/static/css/game/shell/layout_responsive.css").exists()
    assert '@import url("tokens.css");' in index
    assert '@import url("narrow_phone.css");' in index
    assert "--game-drawer-width" in tokens
    assert "@media (min-width: 1280px)" in columns_desktop
    assert ".game-top-row.combat-layout" in combat_desktop
    assert "@media (min-width: 768px) and (max-width: 1279px)" in tablet_drawers
    assert "grid-template-columns: var(--side-panel-width) minmax(0, 1fr) 0 !important;" in tablet_drawers
    assert ".col-right {\n        position: fixed;" in tablet_drawers
    assert "@media (max-width: 767px)" in mobile_drawers
    assert ".col-left.panel-open" in mobile_drawers
    assert "--game-header-height: 40px;" in mobile_header
    assert "--game-header-height: 72px;" not in mobile_header
    assert "@media (min-width: 768px)" in system_menu
    assert ".game-system-menu-toggle" in system_menu
    assert "@media (max-width: 500px)" in narrow_phone


def test_status_main_uses_shared_compact_status_dock():
    template = Path("src/frontend/templates/game/components/status/main.html").read_text()
    compact = Path("src/frontend/templates/game/components/status/compact_panel.html").read_text()
    status_nav = Path("src/frontend/templates/game/components/status/nav.html").read_text()
    status_shell_css = Path("src/frontend/static/css/game/domains/status/shell.css").read_text()
    status_avatar_css = Path("src/frontend/static/css/game/domains/status/avatar.css").read_text()
    obsolete_left_sidebars = [
        Path("src/frontend/templates/game/domains/scenario/left_sidebar/main.html"),
        Path("src/frontend/templates/game/domains/exploration/left_sidebar/main.html"),
        Path("src/frontend/templates/game/domains/rift/left_sidebar/main.html"),
    ]

    assert "game/components/status/compact_panel.html" in template
    assert "game/components/panel/main.html" not in template
    assert "character_status.panel" not in template
    assert "game/components/status/fragments/" not in template
    assert "status_mode" not in template
    assert "distortion" not in template
    assert "status_panel_class" not in template
    assert "panel-dock" in compact
    assert "status-dock" in compact
    assert "scenario-status-dock" not in compact
    assert "status-widget-card" in compact
    assert "status-widget-section" in compact
    assert "status-widget-bar" in compact
    assert "dock-nav-button--close" in status_nav
    assert not any(path.exists() for path in obsolete_left_sidebars)
    assert ".sec {\n    font-size: 8px;\n    letter-spacing: .18em;" in status_shell_css
    assert not status_avatar_css.lstrip().startswith("letter-spacing:")


def test_build_panel_is_marked_as_draft():
    template = Path("src/frontend/templates/game/components/status/build_draft.html").read_text()

    assert "BUILD DRAFT" in template
    assert "NOT ACTIVE FUNCTIONALITY" in template
    assert 'include "game/components/status/nav.html"' in template


def test_avatar_widget_marks_missing_resource_data_explicitly():
    template = Path("src/frontend/templates/game/components/panel/widgets/avatar.html").read_text()

    assert "DATA_MISSING" in template


def test_avatar_widget_renders_gear_score_corner():
    template = Path("src/frontend/templates/game/components/panel/widgets/avatar.html").read_text()

    assert "gear_score" in template
    assert ">GS<" in template


def test_status_attribute_and_skill_widgets_are_collapsible():
    attribute_template = Path("src/frontend/templates/game/components/panel/widgets/attribute_grid.html").read_text()
    skill_template = Path("src/frontend/templates/game/components/panel/widgets/skill_groups.html").read_text()
    legacy_skill_template = Path("src/frontend/templates/game/components/status/fragments/skills.html").read_text()
    compact_status = Path("src/frontend/templates/game/components/status/compact_panel.html").read_text()

    for template in (attribute_template, skill_template):
        assert 'class="status-section status-section--collapsible"' in template
        assert 'class="sec status-section-toggle"' in template
        assert "status-section-toggle-icon" in template

    assert "NO_DATA_AVAILABLE" not in legacy_skill_template
    assert "status-widget-skill-groups" in compact_status
    assert "status-widget-skill-group" in compact_status
    assert "status-widget-skill-group-title" in compact_status
    assert "status-widget-skill-group-row" in compact_status
    assert "status-widget-metrics" in compact_status
    assert "status-widget-metric-card--primary" in compact_status
    assert ">GS<" in compact_status
    assert "loop.index <= 8" not in compact_status
    assert (
        "('COMBAT STYLE', ['skill_ranged_combat', 'skill_two_handed', "
        "'skill_shield_mastery', 'skill_dual_wield'])"
    ) in compact_status
    assert "('COMBAT SUPPORT', ['skill_parrying', 'skill_anatomy', 'skill_tactics'])" in compact_status
    assert "('TACTICS', ['skill_ranged_combat'" not in compact_status


def test_scenario_panels_hide_missing_transfer_data():
    right_template = Path("src/frontend/templates/game/domains/scenario/right_sidebar/main.html").read_text()
    viewport_template = Path("src/frontend/templates/game/domains/scenario/viewport/main.html").read_text()
    finalized_template = Path("src/frontend/templates/game/domains/scenario/viewport/finalized.html").read_text()

    for marker in ("NO_DATA", "NO_SKILLS", "DATA_MISSING", "FUTURE"):
        assert marker not in right_template

    for marker in ("<span>Quest</span>", "<span>Node</span>", "<span>Step</span>", "<span>Phase</span>"):
        if marker != "<span>Quest</span>":
            assert marker not in right_template

    assert "<span>Quest</span>" in right_template
    assert "<span>Place</span>" in right_template
    assert "<span>Focus</span>" in right_template
    assert "<span>quest_key</span>" not in right_template
    assert "<span>node_key</span>" not in right_template

    assert "TRACE" not in viewport_template
    assert "TRACE" not in finalized_template
    assert "техничес" not in viewport_template
    assert "техничес" not in right_template


def test_scenario_title_splits_coordinate_suffix():
    template = Path("src/frontend/templates/game/domains/scenario/viewport/main.html").read_text()
    right_template = Path("src/frontend/templates/game/domains/scenario/right_sidebar/main.html").read_text()
    css = Path("src/frontend/static/css/game/domains/scenario/scene.css").read_text()

    assert "split_bracket_coords" not in template
    assert "display_name_raw.rsplit" in template
    assert "display_name_coord_parts = display_name_coords.split(':')" in template
    assert "scene_coord_parts = scene_coords.split(':')" in right_template
    assert "<b>X</b>" in template
    assert "X {{ scene_coord_parts[0] }} / Y {{ scene_coord_parts[1] }}" in right_template
    assert "scenario-title-coords" in template
    assert ".scenario-title-coords" in css


def test_game_shell_uses_right_panel_inventory_instead_of_floating_hud():
    base_template = Path("src/frontend/templates/game/base_game.html").read_text()
    session_template = Path("src/frontend/templates/game/session_content_inner.html").read_text()
    inventory_panel = Path("src/frontend/templates/game/components/inventory/right_panel.html").read_text()

    assert "x-data='gameShell" in base_template
    assert "game-modal-root" in base_template
    assert "hud-window inventory-window" not in base_template
    assert "windows.inventory.open" not in base_template
    assert 'id="inventory-window-body"' not in base_template
    assert "hud_window_resize_handles.html" not in base_template
    assert "rightPanelView === 'inventory'" in session_template
    assert 'id="game-right-context-content"' in session_template
    assert "game/components/inventory/right_panel.html" in session_template
    assert 'id="right-inventory-panel-body"' in inventory_panel
    assert "game/components/inventory/window.html" in inventory_panel


def test_inventory_window_template_defines_frontend_contract():
    template = Path("src/frontend/templates/game/components/inventory/window.html").read_text()
    compact_status = Path("src/frontend/templates/game/components/status/compact_panel.html").read_text()
    status_nav = Path("src/frontend/templates/game/components/status/nav.html").read_text()

    assert "inventory_target_id" in template
    assert 'hx-target="#{{ inventory_target_id }}"' in template
    assert "inventory-window-body" not in template
    assert "inventory.contract_state" in template
    assert "inventory-loadout" in template
    assert "inventory-doll" in template
    assert "inventory-accessories" in template
    assert "inventory-belt-slots" in template
    assert "is-locked" in template
    assert "accessory_slot_label_map" in template
    assert "inventory-accessory-row-label" in template
    assert "row.row_id != 'rings'" in template
    assert "inventory-accessory-row--{{ row.row_id }}" in template
    assert "'ring_1': 'Кольцо 1'" in template
    assert "'ring_2': 'Кольцо 2'" in template
    assert "base_icon_map" in template
    assert "'scout_leggings': 'legs_light'" in template
    assert "'breeches': 'legs_medium'" in template
    assert "'greaves': 'legs_heavy'" in template
    assert "'legs_garment': 'legwear'" in template
    assert "'feetwear': 'feetwear'" in template
    assert "weapon_icon_base_map" in template
    assert "'greatsword': 'weapon_two_hand'" in template
    assert "'dagger': 'weapon_dagger'" in template
    assert "'battle_axe': 'weapon_axe'" in template
    assert "'spear': 'weapon_spear'" in template
    assert "'quarterstaff': 'weapon_staff'" in template
    assert "slot.slot_id == 'two_hand'" in template
    assert "inventory-equip-zone--two-shadow" in template
    assert "inventory-tabs" in template
    assert "aria-selected" in template
    assert "inventory-search" in template
    assert "inventory.visible_cards" in template
    assert "for row in inventory_cards" in template
    assert "inventory_cards[:inventory.rows_visible_count]" not in template
    assert "resource_cards" in template
    assert "data-inventory-cells" in template
    assert "inventory-container-status" in template
    assert "inventory-feedback" in template
    assert "inventory-tooltip-card" in template
    assert "inventory-equipped-icon" in template
    assert "inventory-grade-r" in template
    assert "inventory-gear/" in template
    assert "data-inventory-tooltip-trigger" in template
    assert "data-inventory-menu-trigger" in template
    assert "data-inventory-actions" in template
    assert "data-inventory-valid-slots" in template
    assert "inventory-tooltip-template" in template
    assert "activeInventoryTab === 'resources'" in template
    assert "activeInventoryTab === 'quest'" in template
    assert "hoverRow" not in template
    assert 'hx-post="/game/inventory/action"' in template
    assert 'x-model.debounce.150ms="searchQuery"' in template
    assert "inventory_notice" in template
    assert "row.card_class" in template
    assert "row.comparison" in template
    assert "row_valid_slots | tojson | forceescape" in template
    assert "INVENTORY_LINK_PENDING" not in template
    assert 'include "game/components/status/nav.html"' in compact_status
    assert 'hx-get="/game/character-status/panel?char_id={{ char_id }}"' in status_nav
    assert 'hx-trigger="character-status-refresh from:body"' in compact_status
    assert 'hx-target="this"' in compact_status
    assert 'hx-swap="outerHTML"' in compact_status
    assert ">SYNC</button>" in status_nav
    assert 'hx-target="#status-container"' in status_nav


def test_inventory_window_template_renders_contract_view_model():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/components/inventory/window.html")

    html = template.render(inventory_window=build_inventory_window_vm({"avatar_url": "/avatar.png", "name": "Ada"}))

    assert 'data-contract-state="FRONTEND_CONTRACT_PENDING"' in html
    assert 'src="/avatar.png"' in html
    assert 'data-slot-id="chest_armor"' in html
    assert 'data-slot-id="chest_garment"' not in html
    assert 'data-slot-id="belt_accessory"' in html
    assert "NO_RUNTIME_ITEMS" not in html
    assert 'data-inventory-cells="50"' in html
    assert "Leather Bracers" not in html


def test_inventory_window_template_renders_backend_contract_dto():
    env = Environment(loader=FileSystemLoader("src/frontend/templates"), autoescape=True)
    template = env.get_template("game/components/inventory/window.html")
    inventory = InventoryWindowDTO.model_validate(
        {
            "char_id": 7,
            "avatar_url": "/avatar.png",
            "avatar_name": "Ada",
            "stats": {"slots_total": 64, "slots_used": 8},
            "body_zones": [
                {
                    "zone_id": "chest",
                    "label": "Torso",
                    "position": "chest",
                    "primary_slot": {
                        "slot_id": "chest_armor",
                        "label": "Armor",
                        "layer": "armor",
                        "item": {
                            "item_id": "item-1",
                            "base_id": "leather_armor",
                            "item_type": "armor",
                            "placement": "equipped",
                            "name": "Leather Armor",
                        },
                    },
                }
            ],
            "weapon_slots": [
                {
                    "slot_id": "two_hand",
                    "label": "Two hand",
                    "layer": "equipment",
                    "item": {
                        "item_id": "item-3",
                        "base_id": "greatsword",
                        "item_type": "weapon",
                        "placement": "equipped",
                        "name": "Iron Greatsword",
                    },
                }
            ],
            "accessory_rows": [],
            "quick_slots": [{"slot_id": "belt_1", "slot_index": 1, "enabled": True}],
            "tabs": [{"tab_id": "items", "label": "Items", "icon": "I", "is_active": True}],
            "visible_rows": [
                {
                    "item_id": "item-2",
                    "icon": "B",
                    "name": "Bronze Sword",
                    "item_type": "weapon",
                    "filter_group": "items",
                    "quantity": 1,
                    "rarity": "shared",
                    "equip_target": "main_hand",
                    "valid_slots": ["main_hand", "off_hand"],
                    "details": {
                        "item_id": "item-2",
                        "name": "Bronze Sword",
                        "item_type": "weapon",
                        "rarity": "shared",
                        "details": [{"label": "Damage", "value": "+3", "tone": "positive"}],
                        "actions": [
                            {
                                "action": "equip",
                                "label": "Equip",
                                "slot_id": "main_hand",
                                "style": "primary",
                            }
                        ],
                    },
                }
            ],
        }
    )

    html = template.render(inventory_window=inventory)

    assert 'data-contract-state="SHARED_INVENTORY_CONTRACT_V1"' in html
    assert "x-data='{" in html
    assert '"activeInventoryTab": "items"' in html
    assert '"selectedSlot": null' in html
    assert '"inventoryNotice": ""' in html
    assert '"searchQuery": ""' in html
    assert 'inventoryNotice: "' not in html
    assert "Leather Armor" in html
    assert "Bronze Sword" in html
    assert "inventory-gear/weapon.svg" in html
    assert "inventory-equipped-icon" in html
    assert "inventory-grade-r0" in html
    assert 'hx-post="/game/inventory/action"' in html
    assert 'hx-target="#right-inventory-panel-body"' in html
    assert '"action": "unequip"' in html
    assert '"item_id": "item-1"' in html
    assert "Iron Greatsword" in html
    assert 'data-slot-id="two_hand-shadow"' in html
    assert '"item_id": "item-3"' in html
    assert '"slot_id": "two_hand"' in html
    assert '"action": "equip"' in html
    assert "x-bind:hx-vals" in html
    assert '["main_hand", "off_hand"].includes(selectedSlot)' in html
    assert '? selectedSlot : "main_hand"' in html
    assert "activeInventoryTab === 'items'" in html
    assert 'data-inventory-cells="64"' in html
    assert (
        "{ 'inventory-hidden': !((!selectedSlot || 'main_hand' === selectedSlot || "
        "[&#34;main_hand&#34;, &#34;off_hand&#34;].includes(selectedSlot))"
    ) in html

    locked_html = template.render(
        inventory_window=inventory.model_copy(
            update={
                "can_act": False,
                "forbidden_reason": "Вы не можете пользоваться инвентарём сейчас.",
            }
        )
    )
    assert "inventoryNotice = &#34;\\u0412\\u044b" in locked_html
    assert "inventoryNotice = \"Вы не можете пользоваться инвентарём сейчас.\"" not in locked_html
    assert "&#34;Bronze Sword&#34;.toLowerCase()" in locked_html
    assert '|| "Bronze Sword".toLowerCase()' not in locked_html


def test_inventory_card_mapper_builds_grid_card_from_type_and_numeric_size():
    assert inventory_card_dimensions("armor", 0, 0) == (2, 2)
    assert inventory_card_dimensions("quest", 12, 7) == (8, 4)
    assert inventory_card_class("armor", 2, 2) == (
        "inventory-card--armor inventory-card--square inventory-card--medium inventory-card--2x2"
    )

    card = build_inventory_card_vm(
        InventoryRowVM(
            row_id="item-1",
            icon="A",
            name="Leather Bracers",
            item_type="armor",
            weight="1.2",
            quantity="1",
            rarity="common",
            equip_target="arms_armor",
            grid_w=0,
            grid_h=0,
            comparison=["Heat resist +5"],
        )
    )

    assert card.grid_w == 2
    assert card.grid_h == 2
    assert card.style == "--item-w: 2; --item-h: 2;"
    assert card.card_class == "inventory-card--armor inventory-card--square inventory-card--medium inventory-card--2x2"
    assert card.details == ["Тип: armor", "Вес: 1.2", "Кол-во: 1", "Грейд: common", "Heat resist +5"]


def test_inventory_css_has_loadout_container_and_table_contract():
    source = Path("src/frontend/static/css/game/components/inventory.css").read_text()
    bundle = Path("src/frontend/static/css/game_bundle.css").read_text()
    legwear_icon = Path("src/frontend/static/images/ui/inventory-gear/legwear.svg")
    legs_light_icon = Path("src/frontend/static/images/ui/inventory-gear/legs_light.svg")
    legs_medium_icon = Path("src/frontend/static/images/ui/inventory-gear/legs_medium.svg")
    legs_heavy_icon = Path("src/frontend/static/images/ui/inventory-gear/legs_heavy.svg")
    weapon_spear_icon = Path("src/frontend/static/images/ui/inventory-gear/weapon_spear.svg")
    weapon_staff_icon = Path("src/frontend/static/images/ui/inventory-gear/weapon_staff.svg")
    weapon_two_hand_icon = Path("src/frontend/static/images/ui/inventory-gear/weapon_two_hand.svg")

    assert ".inventory-loadout" in source
    assert ".right-inventory-panel" in source
    assert ".right-inventory-panel-body" in source
    assert ".inventory-equip-zone--head" in source
    assert ".inventory-equip-zone--outer" in source
    assert ".inventory-equip-zone--main { grid-column: 3; grid-row: 2; }" in source
    assert ".inventory-equip-zone--off { grid-column: 1; grid-row: 2; }" in source
    assert ".inventory-equip-zone--two" in source
    assert ".inventory-equip-zone--two { grid-column: 3; grid-row: 2; }" in source
    assert ".inventory-equip-zone--two-shadow { grid-column: 1; grid-row: 2; }" in source
    assert ".inventory-equip-zone--two-shadow .inventory-slot-title" in source
    assert "display: none" in source
    assert "grid-column: 1 / 4; grid-row: 2" not in source
    assert ".inventory-accessory-row--split" in source
    assert ".inventory-belt-slots" in source
    assert ".inventory-table-body" in source
    assert "flex: 1 1 auto" in source
    assert "--inventory-cell: var(--inventory-grid-base-cell)" in source
    assert "grid-auto-rows: var(--inventory-cell)" in source
    assert "grid-column: 1 / -1" in source
    assert "grid-row: span var(--inventory-grid-rows)" in source
    assert ".inventory-container-status" in source
    assert ".inventory-feedback" in source
    assert "scrollbar-width: none" in source
    assert "--inventory-grid-viewport-height" in source
    assert "height: var(--inventory-grid-height)" in source
    assert "--inventory-grid-cols: 8" in source
    assert "grid-template-columns: repeat(4, minmax(28px, 34px))" in source
    assert ".inventory-tooltip-card" in source
    assert ".inventory-tooltip-affix" in source
    assert ".inventory-tooltip-section-title" in source
    assert ".inventory-floating-tooltip--touch" in source
    assert ".inventory-tooltip-action" in source
    assert ".inventory-context-menu" in source
    assert ".inventory-context-menu-action" in source
    assert ".inventory-accessory-row-label" in source
    assert ".inventory-accessory-row--rings .inventory-accessory-slot" in source
    assert ".inventory-accessory-row--split .inventory-accessory-slot-label" in source
    assert ".inventory-tooltip-meta" in source
    assert ".inventory-equipped-icon" in source
    assert ".inventory-grade-r7" in source
    assert "--inventory-item-icon-url" in source
    assert "--inventory-tooltip-icon-url" in source
    assert "-webkit-mask" in source
    assert ".inventory-card--square" in source
    assert ".inventory-card--wide" in source
    assert "fabric_leather_02_diff_1k.webp" in source
    assert legwear_icon.exists()
    assert legs_light_icon.exists()
    assert legs_medium_icon.exists()
    assert legs_heavy_icon.exists()
    assert weapon_spear_icon.exists()
    assert weapon_staff_icon.exists()
    assert weapon_two_hand_icon.exists()
    assert '@import url("game/components/cards.css");' in bundle


def test_game_shell_drag_logic_lives_in_source_js():
    source = Path("src/frontend/static/js/core/game_shell.js").read_text()
    config = Path("src/frontend/static/css/compiler_config.json").read_text()

    assert "window.gameShell" in source
    main_source = Path("src/frontend/static/js/core/main.js").read_text()
    assert "isTouchInventoryMode" in main_source
    assert "appendTouchInventoryActions" in main_source
    assert "event.stopImmediatePropagation()" in main_source
    assert "inventory-tooltip-action" in main_source
    assert "contextmenu" in main_source
    assert "inventory-context-menu-host" in main_source
    assert "data-inventory-menu-trigger" in main_source
    assert "setTimeout" in main_source
    assert "!detail.forceOpen && this.leftOpen && this.leftPanelView === nextView" in source
    assert "!detail.forceOpen && this.rightOpen && this.rightPanelView === nextView" in source
    assert "startHudWindowDrag" in source
    assert "startHudWindowResize" in source
    assert "resizeHudWindow" in source
    assert "moveHudWindow" in source
    assert "hudOpenStorageKey" in source
    assert "panelStateStorageKey" in source
    assert "explorationDesktopPanelsDefaultOpen" in source
    assert "clearDrawerPanelState" in source
    assert "if (isDrawerViewport())" in source
    assert "window.localStorage.removeItem(panelStateStorageKey())" in source
    assert 'domain !== "exploration"' in source
    assert 'window.matchMedia("(min-width: 1025px)")' in source
    assert 'window.matchMedia("(max-width: 1024px)")' in source
    assert '${domainScope}:${scope}:${viewportScope}:v1' in source
    assert "savePanelState(this)" in source
    assert "panelStateUserEdited" in source
    assert "applySessionPanelState" not in source
    assert "initialInventoryOpen" not in source
    assert "loadHudOpenState" not in source
    assert "savedInventoryOpen" not in source
    assert "inventoryWindow" not in source
    assert "saveHudOpenState(name, hudWindow.open)" in source
    assert "closeHudWindow(name)" in source
    assert "core/game_shell.js" in config


def test_status_runtime_does_not_accept_server_panel_state():
    source = Path("src/frontend/static/js/core/status.js").read_text()

    assert "session:panel-state" not in source
    assert "applySessionPanelState" not in source
    assert "left_open" not in source
    assert "right_open" not in source


def test_mobile_drawer_close_controls_live_in_panel_nav_only():
    template = Path("src/frontend/templates/game/session_content_inner.html").read_text()
    panel_templates = "\n".join(
        [
            Path("src/frontend/templates/game/components/status/nav.html").read_text(),
            Path("src/frontend/templates/game/components/status/compact_panel.html").read_text(),
            Path("src/frontend/templates/game/components/status/build_draft.html").read_text(),
            Path("src/frontend/templates/game/components/inventory/right_panel.html").read_text(),
        ]
    )
    responsive_dir = Path("src/frontend/static/css/game/shell/responsive")
    tablet_css = responsive_dir.joinpath("tablet_drawers.css").read_text()
    mobile_css = responsive_dir.joinpath("mobile_drawers.css").read_text()
    mobile_header_css = responsive_dir.joinpath("mobile_header.css").read_text()
    layout_css = "\n".join((tablet_css, mobile_css, mobile_header_css))
    panel_css = Path("src/frontend/static/css/game/components/panel_dock.css").read_text()

    assert "side-panel-close" not in template
    assert "$dispatch('panel-toggle', { side: 'left'" in panel_templates
    assert "$dispatch('panel-toggle', { side: 'right'" in panel_templates
    assert ".side-panel-close" not in layout_css
    assert ".dock-nav-button--close" in panel_css
    assert "@media (min-width: 768px)" in panel_css
    assert "display: none" in panel_css
    assert "@media (min-width: 768px) and (max-width: 1279px)" in layout_css
    assert "grid-template-columns: var(--side-panel-width) minmax(0, 1fr) 0 !important;" in layout_css
    assert ".col-left {\n        position: relative;" in layout_css
    assert ".col-right {\n        position: fixed;" in layout_css
    assert "@media (max-width: 767px)" in layout_css
    assert "--game-header-height: 40px;" in layout_css
    assert "--game-header-height: 72px;" not in layout_css
    assert "top: var(--game-header-height);" in layout_css
    assert "bottom: var(--game-footer-height);" in layout_css


def test_inventory_frontend_route_proxies_actions_to_backend():
    route = Path("src/frontend/game_features/inventory/routes/fragments.py").read_text()
    client = Path("src/frontend/integrations/backend_api/inventory.py").read_text()

    assert '@router.post("/game/inventory/action"' in route
    assert "InventoryActionRequestDTO.model_validate" in route
    assert "inventory_api.action" in route
    assert 'http_response.headers["HX-Trigger"] = "character-status-refresh"' in route
    assert "HTTP_409_CONFLICT" in route
    assert "async def action" in client
    assert '"/api/game/inventory/actions?{query}"' in client


def test_status_runtime_has_no_legacy_agent_polling():
    source = Path("src/frontend/static/js/core/status.js").read_text()

    assert "pollingEnabled" not in source
    assert "setInterval" not in source
    assert "agents[charId]" not in source
    assert "/api/game/character-status" not in source


def test_game_header_nav_marks_open_panels_and_inventory_panel_active():
    template = Path("src/frontend/templates/game/domains/game_menu/header_nav.html").read_text()

    assert "leftOpen && leftPanelView" in template
    assert "rightOpen && rightPanelView" in template
    assert "windows.{{ item.window }}.open" not in template
    assert "forceOpen: true" not in template
    assert 'hx-get="/game/inventory/window?char_id={{ char_id }}"' in template
    assert 'hx-target="#right-inventory-panel-body"' in template


def test_game_runtime_loads_before_alpine_initializes():
    template = Path("src/frontend/templates/game/base_game.html").read_text()

    assert '/static/css/game.css?v={{ static_version }}' in template
    assert '/static/js/game.js?v={{ static_version }}' in template
    assert template.index('/static/js/game.js') < template.index('/static/js/vendor/alpine.js')


def test_chat_template_uses_normalized_websocket_endpoint():
    template = Path("src/frontend/templates/shared/chat/main.html").read_text(encoding="utf-8")

    assert 'ws-connect="{{ chat_ws_endpoint }}?token={{ access_token }}&char_id={{ char_id }}' in template
    assert "{{ chat_ws_url }}/ws/chat" not in template


def test_game_header_has_system_exit_to_lobby():
    template = Path("src/frontend/templates/game/includes/header.html").read_text()

    assert "The Sealed World" in template
    assert "header_nav.html" not in template
    assert "center-nav" not in template
    assert "game-system-menu" in template
    assert "game-system-action" in template
    assert "game-system-action-glyph--cabinet" in template
    assert "game-system-action-glyph--restart" in template
    assert "game-system-action-glyph--settings" in template
    assert "<span>Restart</span>" in template
    assert "<span>Lobby</span>" not in template
    assert 'action="/game-lobby/release"' in template
    assert 'data-session-cleanup="pending"' in template
