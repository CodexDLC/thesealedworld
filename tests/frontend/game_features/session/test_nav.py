from src.frontend.game_features.session.view_models.nav import build_game_nav
from src.shared.enums import CoreDomain


def test_build_game_nav_leaves_scenario_header_navigation_empty():
    nav = build_game_nav(state=CoreDomain.SCENARIO, char_id=7)

    assert nav == {"l2": None, "l1": None, "center": None, "r1": None, "r2": None}


def test_build_game_nav_exploration_does_not_offer_scenario_transition():
    nav = build_game_nav(state=CoreDomain.EXPLORATION, char_id=7)

    assert nav["center"]["label"] == "EXPLORE"
    assert nav["center"]["is_active"] is True
    assert nav["center"]["icon"] == "map"
    assert nav["l2"]["panel"] == "left"
    assert nav["l1"]["label"] == "BUILDS"
    assert nav["l1"]["panel"] == "left"
    assert nav["l1"]["panel_view"] == "builds"
    assert nav["l1"]["url"] == "#"
    assert nav["r1"]["label"] == "INVENTORY"
    assert nav["r1"]["window"] == "inventory"
    assert nav["r2"]["label"] == "VIEW"
    assert nav["r2"]["panel"] == "right"
    assert nav["r2"]["panel_view"] == "context"


def test_global_domains_are_only_rendered_in_center_slot():
    global_labels = {"SCENARIO", "EXPLORE", "COMBAT", "ARENA", "TAVERN"}

    for state in [CoreDomain.EXPLORATION, CoreDomain.COMBAT, CoreDomain.ARENA, CoreDomain.TAVERN]:
        nav = build_game_nav(state=state, char_id=7)

        assert nav["center"]["label"] in global_labels
        for slot in ["l2", "l1", "r1", "r2"]:
            assert nav[slot]["label"] not in global_labels


def test_inventory_is_far_right_for_runtime_domains():
    for state in [CoreDomain.EXPLORATION, CoreDomain.ARENA, CoreDomain.TAVERN]:
        nav = build_game_nav(state=state, char_id=7)

        assert nav["l1"]["label"] == "BUILDS"
        assert nav["l1"]["panel"] == "left"
        assert nav["r1"]["label"] == "INVENTORY"
        assert nav["r1"]["window"] == "inventory"
        assert nav["r2"]["label"] == "VIEW"
        assert nav["r2"]["panel"] == "right"


def test_combat_nav_keeps_shell_slots_but_disables_side_actions():
    nav = build_game_nav(state=CoreDomain.COMBAT, char_id=7)

    assert nav["center"]["label"] == "COMBAT"
    assert nav["center"]["is_active"] is True
    for slot in ["l2", "l1", "r1", "r2"]:
        assert nav[slot]["is_disabled"] is True
        assert nav[slot]["panel"] is None
        assert nav[slot]["window"] is None
