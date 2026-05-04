from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.scenario.exceptions import (
    InvalidScenarioAction,
    ScenarioConditionFailed,
    ScenarioNodeNotFound,
    ScenarioSessionNotFound,
)
from src.backend.features.scenario.handlers import get_handler
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.features.scenario.dto.context import ScenarioContextDTO
    from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult
    from src.backend.features.scenario.engine import ScenarioDirector, ScenarioEvaluator, ScenarioFormatter
    from src.backend.features.scenario.integrations.system_integrator import ScenarioSystemIntegrator
    from src.shared.schemas import ScenarioPayloadDTO

log = logging.getLogger(__name__)


class ScenarioService:
    def __init__(
        self,
        *,
        integrator: ScenarioSystemIntegrator,
        evaluator: ScenarioEvaluator,
        director: ScenarioDirector,
        formatter: ScenarioFormatter,
    ) -> None:
        self.integrator = integrator
        self.evaluator = evaluator
        self.director = director
        self.formatter = formatter

    async def initialize(self, char_id: int, quest_key: str, source: str = "onboarding") -> ScenarioPayloadDTO:
        master = await self.integrator.get_quest_master(quest_key)
        if master is None:
            log.warning("Scenario initialize rejected: master_missing char_id=%s quest_key=%s", char_id, quest_key)
            raise ScenarioNodeNotFound(quest_key, "START")

        handler = get_handler(quest_key, character_sessions=self.integrator.character_sessions)
        context = await handler.on_initialize(char_id, master)

        await self.integrator.prepare_session(char_id, quest_key, context)

        node = await self._current_or_raise(context)
        flat = context.flatten()
        if "auto" in self.director._get_node_actions(node):
            resolved = await self.director.execute_auto_chain(quest_key, node, flat, self.integrator)
            flat = resolved.context
            node = resolved.node
            context.apply_flat(flat)
            context.current_node_key = node["node_key"]
            await self.integrator.update_progress(char_id, context, force_backup=True)

        payload = self.formatter.render_payload(node, context.flatten(), master)
        logger.info(f"Scenario initialized: char_id={char_id} quest={quest_key} node={payload.node_key}")
        logger.debug(f"Buttons sent: {[b.label for b in payload.buttons]}")
        await self.integrator.publish_event(
            "scenario.initialized",
            {
                "char_id": char_id,
                "quest_key": quest_key,
                "scenario_session_id": str(context.scenario_session_id),
                "current_node_key": context.current_node_key,
            },
        )
        return payload

    async def resume(self, char_id: int) -> ScenarioPayloadDTO:
        context = await self.integrator.load_session(char_id)
        if context is None:
            await self.integrator.publish_event(
                "scenario.failed", {"char_id": char_id, "quest_key": "", "error": "session_not_found"}
            )
            log.warning("Scenario resume rejected: session_not_found char_id=%s", char_id)
            raise ScenarioSessionNotFound(char_id)

        master = await self.integrator.get_quest_master(context.quest_key)
        if master is None:
            log.warning("Scenario resume rejected: master_missing char_id=%s quest_key=%s", char_id, context.quest_key)
            raise ScenarioNodeNotFound(context.quest_key, "MASTER")
        node = await self._current_or_raise(context)
        flat = context.flatten()
        if "auto" in self.director._get_node_actions(node):
            resolved = await self.director.execute_auto_chain(context.quest_key, node, flat, self.integrator)
            flat = resolved.context
            node = resolved.node
            context.apply_flat(flat)
            context.current_node_key = node["node_key"]
            await self.integrator.update_progress(char_id, context)

        await self.integrator.publish_event(
            "scenario.resumed",
            {"char_id": char_id, "quest_key": context.quest_key, "node_key": context.current_node_key},
        )
        payload = self.formatter.render_payload(node, context.flatten(), master)
        logger.info(f"Scenario resumed: char_id={char_id} node={payload.node_key}")
        logger.debug(f"Buttons sent: {[b.label for b in payload.buttons]}")
        return payload

    async def step(self, char_id: int, action_id: str) -> ScenarioPayloadDTO | ScenarioFinalizeResult:
        context = await self.integrator.load_session(char_id)
        if context is None:
            log.warning("Scenario step rejected: session_not_found char_id=%s action_id=%s", char_id, action_id)
            raise ScenarioSessionNotFound(char_id)

        current = await self._current_or_raise(context)
        actions = self.director._get_node_actions(current)
        action = actions.get(action_id)

        if action is None:
            log.warning("Scenario step rejected: invalid_action char_id=%s action_id=%s", char_id, action_id)
            raise InvalidScenarioAction(action_id)
        flat = context.flatten()
        if action.get("condition") and not self.evaluator.check_condition(action["condition"], flat):
            log.warning("Scenario step rejected: condition_failed char_id=%s action_id=%s", char_id, action_id)
            raise ScenarioConditionFailed(action_id)

        if action.get("type") == "finish_quest":
            return await self.finalize(char_id)

        resolved = await self.director.resolve_next_node(context.quest_key, action, flat, self.integrator)
        prev_node = context.current_node_key
        context.apply_flat(resolved.context)
        context.current_node_key = resolved.node["node_key"]
        context.total_steps += 1
        if prev_node not in context.visited_nodes:
            context.visited_nodes.append(prev_node)

        await self.integrator.update_progress(char_id, context)

        await self.integrator.publish_event(
            "scenario.step_completed",
            {
                "char_id": char_id,
                "quest_key": context.quest_key,
                "prev_node": prev_node,
                "next_node": context.current_node_key,
                "step_counter": context.step_counter,
            },
        )
        if resolved.node.get("is_terminal"):
            return await self.finalize(char_id)

        master = await self.integrator.get_quest_master(context.quest_key) or {}
        payload = self.formatter.render_payload(resolved.node, context.flatten(), master)
        logger.info(f"Scenario stepped: char_id={char_id} action={action_id} -> next_node={payload.node_key}")
        logger.debug(f"Buttons sent: {[b.label for b in payload.buttons]}")
        return payload

    async def finalize(self, char_id: int) -> ScenarioFinalizeResult:
        context = await self.integrator.load_session(char_id)
        if context is None:
            log.warning("Scenario finalize rejected: session_not_found char_id=%s", char_id)
            raise ScenarioSessionNotFound(char_id)
        master = await self.integrator.get_quest_master(context.quest_key)
        if master is None:
            log.warning(
                "Scenario finalize rejected: master_missing char_id=%s quest_key=%s", char_id, context.quest_key
            )
            raise ScenarioNodeNotFound(context.quest_key, "MASTER")

        handler = get_handler(context.quest_key, character_sessions=self.integrator.character_sessions)
        result = await handler.on_finalize(char_id, context, master)

        await self.integrator.grant_inventory_rewards(char_id, result.rewards.items)
        await self.integrator.unlock_skills(char_id, result.rewards.skills)
        await self.integrator.apply_attribute_bonuses(char_id, result.rewards.attribute_bonuses)
        await self.integrator.request_combat_start(char_id, context.quest_key)

        await self.integrator.finalize_session(char_id, CoreDomain.EXPLORATION)

        await self.integrator.publish_event(
            "scenario.finalized",
            {
                "char_id": char_id,
                "quest_key": context.quest_key,
                "target_state": CoreDomain.EXPLORATION.value,
                "rewards": result.rewards.model_dump_json(),
            },
        )
        logger.info(f"Scenario finalized: char_id={char_id} quest={context.quest_key}")
        return result

    async def _current_or_raise(self, context: ScenarioContextDTO) -> dict[str, Any]:
        node = await self.integrator.get_node(context.quest_key, context.current_node_key)
        if node is None:
            raise ScenarioNodeNotFound(context.quest_key, context.current_node_key)
        return node
