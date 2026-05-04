from unittest.mock import MagicMock

import pytest

from src.backend.features.scenario.engine.formatter import ScenarioFormatter
from src.shared.schemas import ScenarioPayloadDTO


@pytest.mark.unit
class TestScenarioFormatter:
    @pytest.fixture
    def director(self):
        return MagicMock()

    @pytest.fixture
    def formatter(self, director):
        return ScenarioFormatter(director)

    def test_format_text_basic(self, formatter):
        context = {"name": "Hero", "stats": {"hp": 50}}
        assert formatter.format_text("Hello [#name]!", context) == "Hello Hero!"
        assert formatter.format_text("HP: [#stats.hp]", context) == "HP: 50"

    def test_format_text_nested_list(self, formatter):
        context = {"items": ["sword", "shield"]}
        assert formatter.format_text("First item: [#items.0]", context) == "First item: sword"
        assert formatter.format_text("Missing item: [#items.5]", context) == "Missing item: Unknown:items.5"

    def test_format_text_invalid_access(self, formatter):
        context = {"name": "Hero"}
        # Accessing .part on a string should return Unknown
        assert formatter.format_text("[#name.part]", context) == "Unknown:name.part"

    def test_format_text_unknown(self, formatter):
        context = {}
        assert formatter.format_text("Unknown: [#missing]", context) == "Unknown: Unknown:missing"
        assert formatter.format_text("Unknown nested: [#a.b]", context) == "Unknown nested: Unknown:a.b"

    def test_build_status_bar(self, formatter):
        master = {"status_bar_fields": [{"label": "Gold", "key": "gold"}, {"label": "XP", "key": "xp"}]}
        context = {"gold": 100}
        result = formatter.build_status_bar(master, context)
        assert result == ["Gold 100", "XP ??"]

    def test_render_payload(self, formatter, director):
        node = {
            "node_key": "n1",
            "node_type": "dialog",
            "phase": "arrival",
            "speaker": "overseer",
            "text_content": "Welcome [#name]",
            "actions_logic": {"a1": {"label": "Go [#target]"}},
        }
        context = {"name": "Hero", "target": "North"}
        master = {"status_bar_fields": []}

        director.get_available_actions.return_value = [
            {"action_id": "a1", "label": "Go [#target]", "payload": {"icon": "move"}}
        ]

        payload = formatter.render_payload(node, context, master)
        assert isinstance(payload, ScenarioPayloadDTO)
        assert payload.node_key == "n1"
        assert payload.node_type == "dialog"
        assert payload.phase == "arrival"
        assert payload.speaker == "overseer"
        assert payload.text == "Welcome Hero"
        assert len(payload.buttons) == 1
        assert payload.buttons[0].label == "Go North"
        assert payload.buttons[0].action_id == "a1"

    def test_resolve_action_icon_infers_semantic_icon_from_math(self, formatter):
        assert formatter.resolve_action_icon({"icon": "default", "math": {"w_strength": "+3"}}) == "strength"
        assert formatter.resolve_action_icon({"math": {"w_agility": "+3"}}) == "move"
        assert formatter.resolve_action_icon({"math": {"w_intellect": "+3"}}) == "inspect"
        assert formatter.resolve_action_icon({"math": {"w_memory": "+3"}}) == "brain"
        assert formatter.resolve_action_icon({"math": {"w_endurance": "+3"}}) == "guard"
        assert formatter.resolve_action_icon({"icon": "risk", "math": {"w_strength": "+3"}}) == "risk"

    def test_resolve_sidebar_visibility_prefers_explicit_values_and_falls_back(self, formatter):
        assert formatter.resolve_sidebar_visibility({"show_left_sidebar": False}, {}, "show_left_sidebar", True) is False
        assert formatter.resolve_sidebar_visibility({"show_left_sidebar": None}, {}, "show_left_sidebar", {"mode": "x"}) is True
        assert formatter.resolve_sidebar_visibility({}, {"show_left_sidebar": None}, "show_left_sidebar", []) is False

    def test_format_text_stats_tag(self, formatter):
        # Pattern supports stats: prefix
        context = {"hp": 10}
        assert formatter.format_text("HP: [#stats:hp]", context) == "HP: 10"

    def test_format_text_empty(self, formatter):
        assert formatter.format_text("", {}) == ""
        assert formatter.format_text(None, {}) == ""
