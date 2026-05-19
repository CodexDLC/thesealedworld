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
    assert nav["l1"]["label"] == "QUESTS"
    assert nav["l1"]["panel"] is None
    assert nav["l1"]["panel_view"] is None
    assert nav["l1"]["modal"] == "quests"
    assert nav["l1"]["url"] == "#"
    assert nav["r1"]["label"] == "INVENTORY"
    assert nav["r1"]["panel"] == "right"
    assert nav["r1"]["panel_view"] == "inventory"
    assert nav["r1"]["window"] is None
    assert nav["r2"]["label"] == "VIEW"
    assert nav["r2"]["panel"] == "right"
    assert nav["r2"]["panel_view"] == "context"


def test_global_domains_are_only_rendered_in_center_slot():
    global_labels = {"SCENARIO", "EXPLORE", "COMBAT", "ARENA", "SERVICE"}

    for state in [CoreDomain.EXPLORATION, CoreDomain.COMBAT, CoreDomain.ARENA, CoreDomain.CITY_SERVICES]:
        nav = build_game_nav(state=state, char_id=7)

        assert nav["center"]["label"] in global_labels
        for slot in ["l2", "l1", "r1", "r2"]:
            assert nav[slot]["label"] not in global_labels


def test_inventory_is_far_right_for_runtime_domains():
    for state in [CoreDomain.EXPLORATION, CoreDomain.ARENA, CoreDomain.CITY_SERVICES]:
        nav = build_game_nav(state=state, char_id=7)

        assert nav["l1"]["label"] in {"QUESTS", "BUILDS"}
        if state in {CoreDomain.EXPLORATION, CoreDomain.ARENA}:
            assert nav["l1"]["modal"] == "quests"
            assert nav["l1"]["panel"] is None
        else:
            assert nav["l1"]["panel"] == "left"
        assert nav["r1"]["label"] == "INVENTORY"
        assert nav["r1"]["panel"] == "right"
        assert nav["r1"]["panel_view"] == "inventory"
        assert nav["r1"]["window"] is None
        assert nav["r2"]["label"] == "VIEW"
        assert nav["r2"]["panel"] == "right"


def test_arena_nav_uses_quests_inventory_and_rank_view():
    nav = build_game_nav(state=CoreDomain.ARENA, char_id=7)

    assert nav["center"]["label"] == "ARENA"
    assert nav["l1"]["label"] == "QUESTS"
    assert nav["l1"]["modal"] == "quests"
    assert nav["r1"]["label"] == "INVENTORY"
    assert nav["r1"]["panel_view"] == "inventory"
    assert nav["r2"]["label"] == "VIEW"
    assert nav["r2"]["panel_view"] == "context"


def test_combat_nav_keeps_standard_shell_slots_for_rosters():
    nav = build_game_nav(state=CoreDomain.COMBAT, char_id=7)

    assert nav["center"]["label"] == "COMBAT"
    assert nav["center"]["is_active"] is True
    assert nav["l2"]["label"] == "STATUS"
    assert nav["l2"]["panel"] == "left"
    assert nav["l2"]["panel_view"] == "status"
    assert nav["l1"]["is_disabled"] is True
    assert nav["r1"]["is_disabled"] is True
    assert nav["r2"]["label"] == "VIEW"
    assert nav["r2"]["panel"] == "right"
    assert nav["r2"]["panel_view"] == "context"
