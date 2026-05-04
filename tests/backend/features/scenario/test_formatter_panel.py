from src.backend.features.scenario.engine.formatter import ScenarioFormatter


def test_scenario_right_panel_hides_symbiote_element_weights():
    context = {
        "quest_key": "awakening_rift",
        "step_counter": 3,
        "w_strength": 7,
        "w_agility": 0,
        "t_fire": 9,
        "loot_queue": ["warhammer"],
        "skills_queue": ["melee_combat"],
    }
    panel = ScenarioFormatter.build_right_panel(
        {"node_key": "node_1", "system_messages": ["SYNC"]},
        context,
        {"display_name": "Quest"},
    )

    dumped = panel.model_dump(mode="json")
    assert "w_strength" not in str(dumped)
    assert "t_fire" not in str(dumped)
    assert "Strength" in str(dumped)
    assert "catalog_key" in str(dumped)
    assert "warhammer" in str(dumped)
    assert "melee_combat" in str(dumped)


def test_scenario_ui_merges_master_and_node_panel_config():
    ui = ScenarioFormatter.resolve_ui(
        {"ui": {"left_panel": {"status": "normal"}}},
        {
            "ui": {
                "left_panel": {"mode": "character_status", "status": "error", "distortion": "glitch"},
                "right_panel": {"mode": "scenario_trace"},
            }
        },
    )

    assert ui["left_panel"] == {
        "mode": "character_status",
        "status": "normal",
        "distortion": "glitch",
    }
    assert ui["right_panel"] == {"mode": "scenario_trace"}


def test_scenario_visible_profile_sorts_by_weight_descending():
    panel = ScenarioFormatter.build_right_panel(
        {"node_key": "node_1"},
        {
            "quest_key": "awakening_rift",
            "step_counter": 3,
            "w_agility": 10,
            "w_projection": 1,
            "w_endurance": 10,
            "w_intellect": 5,
            "w_prediction": 7,
            "w_mental": 7,
            "w_perception": 9,
            "w_strength": 11,
            "w_memory": 5,
        },
        {"display_name": "Quest"},
    )

    profile = next(widget for widget in panel.widgets if widget.title == "CHOICE PROFILE")
    assert [item["label"] for item in profile.items] == [
        "Strength",
        "Agility",
        "Endurance",
        "Perception",
        "Prediction",
        "Mentality",
        "Intellect",
        "Memory",
        "Projection",
    ]
    assert all(item["display_value"].endswith("%") for item in profile.items)
    assert all(item["catalog"] == "attributes" for item in profile.items)


def test_scenario_pending_rewards_use_catalog_metadata():
    panel = ScenarioFormatter.build_right_panel(
        {"node_key": "node_1"},
        {
            "quest_key": "awakening_rift",
            "step_counter": 3,
            "loot_queue": ["battle_axe"],
            "skills_queue": ["skill_one_handed"],
        },
        {"display_name": "Quest"},
    )

    gear = next(widget for widget in panel.widgets if widget.title == "PENDING GEAR")
    skills = next(widget for widget in panel.widgets if widget.title == "PENDING SKILLS")

    assert gear.items == [{"label": "battle_axe", "catalog": "items", "catalog_key": "battle_axe"}]
    assert skills.items == [{"label": "skill_one_handed", "catalog": "skills", "catalog_key": "skill_one_handed"}]
