# backend/domains/user_features/scenario/engine/director.py
import random
from typing import TYPE_CHECKING, Any

from loguru import logger as log

if TYPE_CHECKING:
    from src.backend.domains.user_features.scenario.engine.evaluator import ScenarioEvaluator
    from src.backend.domains.user_features.scenario.service.session_service import ScenarioSessionService


class ScenarioDirector:
    """
    Главный мозг логики переходов.
    Исполняет шаг (execute_step), включая математику, ветвление и
    рекурсивный проход через Logic Gates.
    """

    def __init__(self, evaluator: "ScenarioEvaluator", manager: "ScenarioSessionService"):
        self.evaluator = evaluator
        self.manager = manager

    async def execute_step(
        self, quest_key: str, current_node_key: str, action_id: str, context: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Исполняет логику шага.
        """
        # 1. Загружаем текущую ноду
        node_data = await self.manager.get_node(quest_key, current_node_key)
        if not node_data:
            raise ValueError(f"Node {current_node_key} not found")

        # 2. Получаем данные действия
        action_data = node_data.get("actions_logic", {}).get(action_id, {})

        # 3. Применяем математику самого действия (верхний уровень)
        if "math" in action_data:
            context = self.evaluator.apply_math(action_data.get("math", {}), context)

        # 4. Резолвим ветвление (оно может содержать свою математику)
        next_destination, branch_math = self.resolve_branching(
            action_data.get("branching", []), context, action_data.get("to_node")
        )

        # Применяем математику ветки (если была)
        if branch_math:
            context = self.evaluator.apply_math(branch_math, context)

        # 5. Рекурсивно идем по цепочке
        return await self._resolve_target(quest_key, next_destination, context)

    async def _resolve_target(
        self, quest_key: str, target_key: str, context: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Рекурсивный резолвер.
        """
        # А) Обработка пула
        if target_key.startswith("pool:"):
            pool_tag = target_key.split(":")[1]
            candidates = await self.manager.get_nodes_by_pool(quest_key, pool_tag)
            target_key_from_pool = self.select_node_from_pool(candidates, context)
            if not target_key_from_pool:
                raise ValueError(f"No valid nodes found in pool: {pool_tag}")
            target_key = target_key_from_pool

        # Б) Загружаем ноду
        node_data = await self.manager.get_node(quest_key, target_key)
        if not node_data:
            raise ValueError(f"Target node {target_key} not found")

        # В) Проверяем на Logic Gate (auto)
        actions_logic = node_data.get("actions_logic", {})

        if "auto" in actions_logic:
            auto_data = actions_logic["auto"]

            # 1. Математика самого гейта
            if "math" in auto_data:
                context = self.evaluator.apply_math(auto_data.get("math", {}), context)

            # 2. Резолвим ветвление внутри гейта
            next_step, branch_math = self.resolve_branching(
                auto_data.get("branching", []), context, auto_data.get("to_node")
            )

            # 3. Применяем математику выбранной ветки
            if branch_math:
                context = self.evaluator.apply_math(branch_math, context)

            log.debug(f"Director | logic_gate node={target_key} -> next={next_step}")

            # 4. Рекурсия
            return await self._resolve_target(quest_key, next_step, context)

        # Г) Финальная нода
        return context, node_data

    def resolve_branching(
        self, branching_logic: list[dict[str, Any]], context: dict[str, Any], default_node: str | None = None
    ) -> tuple[str, dict[str, Any] | None]:
        """
        Определяет куда идти.
        Возвращает: (next_node_key, math_instructions_from_branch)
        """
        if not branching_logic:
            return (str(default_node) if default_node else "error_node"), None

        for branch in branching_logic:
            condition = branch.get("condition")
            target = branch.get("to_node")
            branch_math = branch.get("math")  # Математика внутри конкретной ветки

            # Ветка по умолчанию
            if condition == "default" or not condition:
                return str(target) if target else "error_node", branch_math

            # Проверка условия
            if self.evaluator.check_condition(condition, context):
                return str(target) if target else "error_node", branch_math

        return (str(default_node) if default_node else "error_node"), None

    def select_node_from_pool(self, candidate_nodes: list[dict[str, Any]], context: dict[str, Any]) -> str | None:
        """Выбор из пула."""
        visited_nodes = context.get("visited_nodes", [])
        valid_nodes = []

        for node in candidate_nodes:
            # Пропускаем уже посещенные ноды
            if node.get("node_key") in visited_nodes:
                continue

            reqs = node.get("selection_requirements")
            if not reqs or self.evaluator.check_condition(reqs, context):
                valid_nodes.append(node)

        if not valid_nodes:
            log.warning(f"Director | action=smart_selection status=no_candidates context_keys={list(context.keys())}")
            return None

        # Выбираем случайную ноду из валидных
        selected_node = random.choice(valid_nodes)
        return str(selected_node.get("node_key"))

    def get_available_actions(self, actions_logic: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
        """Фильтр кнопок."""
        available = []
        for act_id, data in actions_logic.items():
            if act_id == "auto":
                continue

            cond = data.get("condition")
            if not cond or self.evaluator.check_condition(cond, context):
                available.append(
                    {
                        "action_id": act_id,
                        "label": data.get("label", "Далее"),
                        "payload": data,
                    }
                )
        return available
