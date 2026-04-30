import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.features.scenario.engine.director import ScenarioDirector, ScenarioDirectorError, ResolvedNode

@pytest.mark.unit
class TestScenarioDirector:
    @pytest.fixture
    def evaluator(self):
        return MagicMock()

    @pytest.fixture
    def content(self):
        return MagicMock()

    @pytest.fixture
    def director(self, evaluator):
        return ScenarioDirector(evaluator)

    async def test_resolve_next_node_simple(self, director, evaluator, content):
        action = {"to_node": "n2", "math": {"a": 1}}
        context = {"a": 0}
        evaluator.apply_math.return_value = {"a": 1}
        content.get_node = AsyncMock(return_value={"node_key": "n2", "actions_logic": {}})

        result = await director.resolve_next_node("q1", action, context, content)
        assert result.node["node_key"] == "n2"
        assert result.context["a"] == 1

    async def test_resolve_next_node_branching(self, director, evaluator, content):
        action = {
            "branching": [
                {"condition": "a > 0", "to_node": "b1"},
                {"condition": "default", "to_node": "b2"}
            ]
        }
        evaluator.apply_math.side_effect = lambda m, c: c # No math
        evaluator.check_condition.side_effect = lambda cond, ctx: ctx["a"] > 0 if cond == "a > 0" else True

        content.get_node = AsyncMock(side_effect=lambda q, n: {"node_key": n, "actions_logic": {}})

        # Test branch 1
        res1 = await director.resolve_next_node("q1", action, {"a": 10}, content)
        assert res1.node["node_key"] == "b1"

        # Test branch 2
        res2 = await director.resolve_next_node("q1", action, {"a": 0}, content)
        assert res2.node["node_key"] == "b2"

    async def test_execute_auto_chain(self, director, evaluator, content):
        n1 = {"node_key": "n1", "actions_logic": {"auto": {"to_node": "n2"}}}
        n2 = {"node_key": "n2", "actions_logic": {}}
        content.get_node = AsyncMock(side_effect=lambda q, n: n2 if n == "n2" else None)
        evaluator.apply_math.side_effect = lambda m, c: c

        result = await director.execute_auto_chain("q1", n1, {}, content)
        assert result.node["node_key"] == "n2"

    async def test_execute_auto_chain_loop(self, director, evaluator, content):
        n1 = {"node_key": "n1", "actions_logic": {"auto": {"to_node": "n1"}}}
        content.get_node = AsyncMock(return_value=n1)
        evaluator.apply_math.side_effect = lambda m, c: c
        with pytest.raises(ScenarioDirectorError, match="auto chain exceeded 100 steps"):
            await director.execute_auto_chain("q1", n1, {}, content)

    async def test_resolve_target_no_target(self, director, content):
        with pytest.raises(ScenarioDirectorError, match="no target node"):
            await director._resolve_target("q1", None, {}, content)

    async def test_resolve_target_not_found(self, director, content):
        content.get_node = AsyncMock(return_value=None)
        with pytest.raises(ScenarioDirectorError, match="node not found"):
            await director._resolve_target("q1", "missing", {}, content)

    async def test_pick_from_pool(self, director, evaluator, content):
        nodes = [
            {"node_key": "p1", "selection_requirements": "gold > 10"},
            {"node_key": "p2", "selection_requirements": "gold > 100"},
            {"node_key": "visited"}
        ]
        content.get_nodes_by_pool = AsyncMock(return_value=nodes)
        evaluator.check_condition.side_effect = lambda r, c: c["gold"] > (10 if r == "gold > 10" else 100)

        context = {"gold": 50, "visited_nodes": ["visited"]}
        result = await director.pick_from_pool("q1", "tag", context, content)
        assert result["node_key"] == "p1"

    async def test_pick_from_pool_empty(self, director, content):
        content.get_nodes_by_pool = AsyncMock(return_value=[])
        with pytest.raises(ScenarioDirectorError, match="No scenario pool candidates"):
            await director.pick_from_pool("q1", "tag", {}, content)

    async def test_get_available_actions(self, director, evaluator):
        actions_logic = {
            "a1": {"label": "L1", "condition": "c1"},
            "a2": {"label": "L2"},
            "auto": {}
        }
        evaluator.check_condition.side_effect = lambda c, ctx: c == "c1" # Only c1 true
        result = director.get_available_actions({"actions_logic": actions_logic}, {})
        assert len(result) == 2
        assert result[0]["action_id"] == "a1"
        assert result[1]["action_id"] == "a2"

    async def test_resolve_target_auto(self, director, evaluator, content):
        n1 = {"node_key": "n1", "actions_logic": {"auto": {"to_node": "n2"}}}
        n2 = {"node_key": "n2", "actions_logic": {}}
        content.get_node = AsyncMock(side_effect=lambda q, n: n2 if n == "n2" else n1)
        evaluator.apply_math.side_effect = lambda m, c: c

        # Calling _resolve_target with n1 should trigger execute_auto_chain and return n2
        result = await director._resolve_target("q1", "n1", {}, content)
        assert result.node["node_key"] == "n2"

    async def test_resolve_target_pool(self, director, evaluator, content):
        content.get_nodes_by_pool = AsyncMock(return_value=[{"node_key": "p1"}])
        evaluator.check_condition.return_value = True
        result = await director._resolve_target("q1", "pool:tag", {}, content)
        assert result.node["node_key"] == "p1"
