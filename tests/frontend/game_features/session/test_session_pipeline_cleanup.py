from __future__ import annotations

from pathlib import Path

from src.frontend.game_features.game_menu.services.menu_service import GameMenuService
from src.shared.enums import CoreDomain

ROOT = Path(__file__).resolve().parents[4]


def test_removed_session_compatibility_names_do_not_return_to_live_code():
    forbidden = (
        "Character" + "SessionService",
        "get_character" + "_session_service",
        "State" + "ScreenService",
        "GameLobbyService" + ".enter_character",
    )
    live_files = [*ROOT.joinpath("src").rglob("*.py")]

    matches: list[str] = []
    for path in live_files:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                matches.append(f"{path.relative_to(ROOT)}: {token}")

    assert matches == []


def test_removed_tavern_feature_paths_do_not_return_to_live_code():
    forbidden = (
        "CoreDomain.TAVERN",
        "features.tavern",
        "game_features.tavern",
        "schemas.tavern",
        "BackendTavern",
        "game/domains/tavern",
        "/game/tavern",
        "/tavern/v1",
    )
    live_files = [*ROOT.joinpath("src").rglob("*.py"), *ROOT.joinpath("src/frontend/templates").rglob("*.html")]

    matches: list[str] = []
    for path in live_files:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                matches.append(f"{path.relative_to(ROOT)}: {token}")

    assert matches == []


def test_session_template_keeps_alpine_root_above_sidebars_and_inner_oob_targets():
    base_game = ROOT.joinpath("src/frontend/templates/game/base_game.html").read_text(encoding="utf-8")
    session = ROOT.joinpath("src/frontend/templates/game/session_content_inner.html").read_text(encoding="utf-8")
    scenario_viewport = ROOT.joinpath(
        "src/frontend/templates/game/domains/scenario/viewport/main.html"
    ).read_text(encoding="utf-8")

    assert base_game.index('id="app-viewport"') < base_game.index("{% block content %}")
    assert session.index('id="game-left"') < session.index('id="game-right"')
    assert 'id="game-left-content"' in session
    assert 'id="game-right-content"' in session
    assert 'id="game-right-context-content"' in session
    assert session.index('id="game-right-context-content"') < session.index("rightPanelView === 'inventory'")
    assert 'id="game-left-content" hx-swap-oob="true"' in scenario_viewport
    assert 'include "game/components/status/main.html"' in scenario_viewport
    assert "game/domains/scenario/left_sidebar/main.html" not in session
    assert "game/domains/exploration/left_sidebar/main.html" not in session
    assert "game/domains/rift/left_sidebar/main.html" not in session
    assert "game/domains/combat/left_sidebar/main.html" in session
    assert 'id="game-right-context-content" hx-swap-oob="innerHTML"' in scenario_viewport
    assert 'id="game-right-content" hx-swap-oob' not in scenario_viewport
    assert "domain == 'SCENARIO' and session_ui" not in session
    assert "session_ui and session_ui.left_open" not in scenario_viewport
    assert "session_ui and session_ui.right_open" not in scenario_viewport
    assert 'id="game-left" class="col-left" :class="{ \'panel-open\': leftOpen }" hx-swap-oob' not in scenario_viewport
    assert 'id="game-right" class="col-right" :class="{ \'panel-open\': rightOpen }" hx-swap-oob' not in scenario_viewport


def test_domain_viewports_do_not_replace_right_panel_shell():
    viewport_templates = [
        ROOT.joinpath("src/frontend/templates/game/domains/arena/viewport/main.html"),
        ROOT.joinpath("src/frontend/templates/game/domains/exploration/viewport/main.html"),
        ROOT.joinpath("src/frontend/templates/game/domains/scenario/viewport/main.html"),
    ]

    offenders: list[str] = []
    for path in viewport_templates:
        text = path.read_text(encoding="utf-8")
        if 'id="game-right-content" hx-swap-oob' in text:
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_legacy_scenario_menu_fallback_keeps_panel_controls():
    nav = GameMenuService().build_menu(CoreDomain.SCENARIO)

    assert nav.l2 is None
    assert nav.l1 is None
    assert nav.center is None
    assert nav.r1 is None
    assert nav.r2 is None


def test_legacy_game_menu_fallback_keeps_global_domains_in_center_only():
    global_labels = {"SCENARIO", "EXPLORE", "COMBAT", "ARENA"}
    menu = GameMenuService()

    for domain in [CoreDomain.EXPLORATION, CoreDomain.COMBAT]:
        nav = menu.build_menu(domain)

        assert nav.center is not None
        assert nav.center.label in global_labels
        for item in [nav.l2, nav.l1, nav.r1, nav.r2]:
            if item is not None:
                assert item.label not in global_labels


def test_combat_menu_uses_tactical_drawers():
    nav = GameMenuService().build_menu(CoreDomain.COMBAT)

    assert nav.center is not None
    assert nav.center.label == "COMBAT"
    assert nav.l2 is not None
    assert nav.l2.label == "STATUS"
    assert nav.l2.panel == "left"
    assert nav.l2.panel_view == "status"
    assert nav.l1 is not None
    assert nav.l1.label == "PARTY"
    assert nav.l1.panel == "left"
    assert nav.l1.panel_view == "allies"
    assert nav.r1 is not None
    assert nav.r1.label == "FOES"
    assert nav.r1.panel == "right"
    assert nav.r1.panel_view == "enemies"
    assert nav.r2 is not None
    assert nav.r2.label == "LOG"
    assert nav.r2.panel == "right"
    assert nav.r2.panel_view == "log"


def test_legacy_exploration_menu_fallback_does_not_link_to_other_main_states():
    nav = GameMenuService().build_menu(CoreDomain.EXPLORATION)

    assert nav.center is not None
    assert nav.center.label == "EXPLORE"
    assert nav.l2 is not None
    assert nav.l2.panel == "left"
    assert nav.l1 is not None
    assert nav.l1.label == "QUESTS"
    assert nav.l1.panel is None
    assert nav.l1.panel_view is None
    assert nav.l1.modal == "quests"
    assert nav.r1 is not None
    assert nav.r1.label == "INVENTORY"
    assert nav.r1.panel == "right"
    assert nav.r1.panel_view == "inventory"
    assert nav.r2 is not None
    assert nav.r2.label == "VIEW"
    assert nav.r2.panel == "right"


def test_scenario_step_route_does_not_force_panel_open_state():
    route = ROOT.joinpath("src/frontend/game_features/scenario/routes/pages.py").read_text(encoding="utf-8")

    assert "session:panel-state" not in route
    assert "HX-Trigger" not in route
