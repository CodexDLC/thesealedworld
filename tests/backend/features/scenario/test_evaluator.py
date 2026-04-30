import pytest
from src.backend.features.scenario.engine.evaluator import ScenarioEvaluator

@pytest.mark.unit
class TestScenarioEvaluator:
    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator(seed=42)

    def test_check_condition_simple(self, evaluator):
        assert evaluator.check_condition("True", {}) is True
        assert evaluator.check_condition("False", {}) is False
        assert evaluator.check_condition("", {}) is True
        assert evaluator.check_condition(None, {}) is True
        assert evaluator.check_condition("default", {}) is True

    def test_check_condition_vars(self, evaluator):
        context = {"gold": 100, "name": "Hero"}
        assert evaluator.check_condition("gold > 50", context) is True
        assert evaluator.check_condition("gold < 50", context) is False
        assert evaluator.check_condition("name == 'Hero'", context) is True

    def test_check_condition_complex(self, evaluator):
        context = {"gold": 100, "hp": 50}
        assert evaluator.check_condition("gold > 50 and hp >= 50", context) is True
        assert evaluator.check_condition("gold > 200 or hp < 100", context) is True

    def test_check_condition_invalid(self, evaluator):
        assert evaluator.check_condition("syntax error !!!", {}) is False

    def test_apply_math_basic(self, evaluator):
        context = {"gold": 10, "hp": 20}
        updates = {"gold": "+5", "hp": "-10", "xp": "=100", "level": "5"}
        result = evaluator.apply_math(updates, context)
        assert result["gold"] == 15
        assert result["hp"] == 10
        assert result["xp"] == 100
        assert result["level"] == 5

    def test_apply_math_dice(self, evaluator):
        # With seed 42, 1d6 is 6? (Let's check)
        context = {"hp": 10}
        updates = {"hp": "+1d6"}
        result = evaluator.apply_math(updates, context)
        # We don't need exact value if we trust RNG, but let's check it's changed
        assert result["hp"] > 10

    def test_apply_math_list(self, evaluator):
        context = {"items": ["sword"]}
        updates = {"items": "append:shield"}
        result = evaluator.apply_math(updates, context)
        assert result["items"] == ["sword", "shield"]

        updates = {"items": "remove:sword"}
        result2 = evaluator.apply_math(updates, result)
        assert result2["items"] == ["shield"]

    def test_apply_math_list_multi(self, evaluator):
        context = {"items": []}
        updates = {"items": ["append:a", "append:b"]}
        result = evaluator.apply_math(updates, context)
        assert result["items"] == ["a", "b"]

    def test_roll_dice(self, evaluator):
        val = evaluator.roll_dice("2d6")
        assert 2 <= val <= 12
        with pytest.raises(ValueError):
            evaluator.roll_dice("invalid")

    def test_eval_node_binops(self, evaluator):
        assert evaluator.check_condition("1 + 2 == 3", {}) is True
        assert evaluator.check_condition("10 - 2 == 8", {}) is True
        assert evaluator.check_condition("2 * 3 == 6", {}) is True
        assert evaluator.check_condition("10 / 2 == 5", {}) is True
        assert evaluator.check_condition("10 // 3 == 3", {}) is True
        assert evaluator.check_condition("10 % 3 == 1", {}) is True

    def test_eval_node_unary(self, evaluator):
        assert evaluator.check_condition("-1 == -1", {}) is True
        assert evaluator.check_condition("not False", {}) is True

    def test_eval_node_compare(self, evaluator):
        assert evaluator.check_condition("1 != 2", {}) is True
        assert evaluator.check_condition("5 <= 5", {}) is True
        assert evaluator.check_condition("1 in [1, 2]", {}) is True
        assert evaluator.check_condition("3 not in [1, 2]", {}) is True

    def test_eval_node_list_tuple(self, evaluator):
        assert evaluator.check_condition("[1, 2] == [1, 2]", {}) is True
        assert evaluator.check_condition("(1, 2) == (1, 2)", {}) is True

    def test_eval_node_unsupported(self, evaluator):
        import ast
        node = ast.parse("lambda x: x", mode="eval").body
        with pytest.raises(ValueError, match="Unsupported expression node"):
             evaluator._eval_node(node, {})

    def test_apply_one_scalar_instruction(self, evaluator):
        assert evaluator._apply_one("foo", 123, {}) == 123

    def test_eval_expr_fallback(self, evaluator):
        # Syntax error in ast.parse triggers fallback
        assert evaluator._eval_expr("123", {}) == 123
        assert evaluator._eval_expr("!!!", {}) == "!!!"
        # 'some_string' parses as ast.Name, returns context.get(..., 0)
        assert evaluator._eval_expr("some_string", {}) == 0

    def test_compare_unsupported(self, evaluator):
        # Mocking a compare op that is not in the map
        import ast
        node = ast.Compare(left=ast.Constant(value=1), ops=[ast.Is()], comparators=[ast.Constant(value=1)])
        with pytest.raises(ValueError, match="Unsupported compare operator"):
            evaluator._eval_node(node, {})
