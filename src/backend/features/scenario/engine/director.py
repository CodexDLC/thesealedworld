from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.scenario.engine.evaluator import ScenarioEvaluator
    from src.backend.features.scenario.services.content_service import ScenarioContentService


class ScenarioDirectorError(RuntimeError):
    pass


@dataclass
class ResolvedNode:
    context: dict[str, Any]
    node: dict[str, Any]


class ScenarioDirector:
    def __init__(self, evaluator: ScenarioEvaluator) -> None:
        self.evaluator = evaluator

    async def resolve_next_node(
        self,
        quest_key: str,
        action: dict[str, Any],
        context: dict[str, Any],
        content: ScenarioContentService,
    ) -> ResolvedNode:
        next_context = self.evaluator.apply_math(action.get("math", {}), context)
        target, branch_math = self._resolve_branching(action.get("branching", []), next_context, action.get("to_node"))
        next_context = self.evaluator.apply_math(branch_math or {}, next_context)
        return await self._resolve_target(quest_key, target, next_context, content)

    def _get_node_actions(self, node: dict[str, Any]) -> dict[str, Any]:
        """Unifies actions from 'actions' (list) and 'actions_logic' (dict)"""
        logic = node.get("actions_logic", {}).copy()
        for action in node.get("actions", []):
            aid = action.get("action_id")
            if aid:
                logic[aid] = action
        return logic

    async def execute_auto_chain(
        self,
        quest_key: str,
        node: dict[str, Any],
        context: dict[str, Any],
        content: ScenarioContentService,
    ) -> ResolvedNode:
        current = node
        next_context = context
        guard = 0
        actions = self._get_node_actions(current)
        while "auto" in actions:
            guard += 1
            if guard > 100:
                raise ScenarioDirectorError("Scenario auto chain exceeded 100 steps")
            auto_action = actions["auto"]
            next_context = self.evaluator.apply_math(auto_action.get("math", {}), next_context)
            target, branch_math = self._resolve_branching(
                auto_action.get("branching", []),
                next_context,
                auto_action.get("to_node"),
            )
            next_context = self.evaluator.apply_math(branch_math or {}, next_context)
            resolved = await self._resolve_target(quest_key, target, next_context, content, run_auto=False)
            current = resolved.node
            next_context = resolved.context
            actions = self._get_node_actions(current)
        return ResolvedNode(context=next_context, node=current)

    async def _resolve_target(
        self,
        quest_key: str,
        target: str | None,
        context: dict[str, Any],
        content: ScenarioContentService,
        *,
        run_auto: bool = True,
    ) -> ResolvedNode:
        if not target:
            raise ScenarioDirectorError("Scenario action has no target node")
        node: dict[str, Any] | None
        if target.startswith("pool:"):
            node = await self.pick_from_pool(quest_key, target.split(":", 1)[1], context, content)
        else:
            node = await content.get_node(quest_key, target)
        if node is None:
            raise ScenarioDirectorError(f"Scenario node not found: quest={quest_key} node={target}")

        actions = self._get_node_actions(node)
        if run_auto and "auto" in actions:
            return await self.execute_auto_chain(quest_key, node, context, content)
        return ResolvedNode(context=context, node=node)

    async def pick_from_pool(
        self,
        quest_key: str,
        pool_tag: str,
        context: dict[str, Any],
        content: ScenarioContentService,
    ) -> dict[str, Any]:
        visited = set(context.get("visited_nodes", []))
        candidates = []
        for node in await content.get_nodes_by_pool(quest_key, pool_tag):
            if node["node_key"] in visited:
                continue
            requirement = node.get("selection_requirements")
            if not requirement or self.evaluator.check_condition(requirement, context):
                candidates.append(node)
        if not candidates:
            raise ScenarioDirectorError(f"No scenario pool candidates: quest={quest_key} pool={pool_tag}")
        return random.choice(candidates)

    def get_available_actions(self, node: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
        actions_logic = self._get_node_actions(node)
        available = []
        for action_id, action in actions_logic.items():
            if action_id == "auto":
                continue
            condition = action.get("condition")
            if not condition or self.evaluator.check_condition(condition, context):
                available.append({"action_id": action_id, "label": action.get("label", "Далее"), "payload": action})
        return available

    def _resolve_branching(
        self,
        branching: list[dict[str, Any]],
        context: dict[str, Any],
        default_node: str | None = None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        for branch in branching:
            condition = branch.get("condition")
            if condition == "default" or self.evaluator.check_condition(condition, context):
                return branch.get("to_node") or default_node, branch.get("math")
        return default_node, None
