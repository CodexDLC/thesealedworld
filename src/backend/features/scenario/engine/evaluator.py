from __future__ import annotations

import ast
import operator
import random
import re
from typing import Any


class ScenarioEvaluator:
    _compare_ops = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.In: lambda left, right: left in right,
        ast.NotIn: lambda left, right: left not in right,
    }
    _bin_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
    }
    _unary_ops = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}

    def __init__(self, seed: int | float | str | None = None) -> None:
        self._rng = random.Random(seed)
        self._dice_pattern = re.compile(r"(\d+)d(\d+)")

    def check_condition(self, expression: str | None, context: dict[str, Any]) -> bool:
        if not expression or expression.strip() in {"", "default"}:
            return True
        try:
            parsed = ast.parse(expression, mode="eval")
            return bool(self._eval_node(parsed.body, context))
        except Exception:
            return False

    def apply_math(self, updates: dict[str, Any] | None, context: dict[str, Any]) -> dict[str, Any]:
        new_context = dict(context)
        for var_name, instruction in (updates or {}).items():
            if isinstance(instruction, list):
                for item in instruction:
                    new_context[var_name] = self._apply_one(var_name, item, new_context)
            else:
                new_context[var_name] = self._apply_one(var_name, instruction, new_context)
        return new_context

    def roll_dice(self, spec: str) -> int:
        match = re.fullmatch(r"(\d+)d(\d+)", spec.strip())
        if not match:
            raise ValueError(f"Invalid dice spec: {spec}")
        count = min(int(match.group(1)), 100)
        sides = min(int(match.group(2)), 1000)
        return sum(self._rng.randint(1, sides) for _ in range(count))

    def _apply_one(self, var_name: str, instruction: Any, context: dict[str, Any]) -> Any:
        if not isinstance(instruction, str):
            return instruction

        target = list(context.get(var_name, [])) if isinstance(context.get(var_name), list) else []
        if instruction.startswith(("append:", "push:")):
            target.append(instruction.split(":", 1)[1])
            return target
        if instruction.startswith(("remove:", "pop:")):
            value = instruction.split(":", 1)[1]
            if value in target:
                target.remove(value)
            return target

        current = context.get(var_name, 0)
        processed = self._dice_pattern.sub(lambda match: str(self.roll_dice(match.group(0))), instruction.strip())
        if processed.startswith("+"):
            return current + self._eval_expr(processed[1:], context)
        if processed.startswith("-"):
            return current - self._eval_expr(processed[1:], context)
        if processed.startswith("="):
            return self._eval_expr(processed[1:], context)
        return self._eval_expr(processed, context)

    def _eval_expr(self, expression: str, context: dict[str, Any]) -> Any:
        try:
            return self._eval_node(ast.parse(expression, mode="eval").body, context)
        except Exception:
            return self._to_scalar(expression)

    def _eval_node(self, node: ast.AST, context: dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in {"True", "False", "None"}:
                return {"True": True, "False": False, "None": None}[node.id]
            return context.get(node.id, 0)
        if isinstance(node, ast.BoolOp):
            values = [self._eval_node(value, context) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._unary_ops:
            op_func = self._unary_ops[type(node.op)]
            return op_func(self._eval_node(node.operand, context))  # type: ignore
        if isinstance(node, ast.BinOp) and type(node.op) in self._bin_ops:
            return self._bin_ops[type(node.op)](
                self._eval_node(node.left, context),
                self._eval_node(node.right, context),
            )
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators, strict=True):
                op_func = self._compare_ops.get(type(op))  # type: ignore
                if op_func is None:
                    raise ValueError("Unsupported compare operator")
                right = self._eval_node(comparator, context)
                if not op_func(left, right):  # type: ignore
                    return False
                left = right
            return True
        if isinstance(node, ast.List):
            return [self._eval_node(item, context) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(item, context) for item in node.elts)
        raise ValueError(f"Unsupported expression node: {node.__class__.__name__}")

    @staticmethod
    def _to_scalar(value: str) -> int | float | str:
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
