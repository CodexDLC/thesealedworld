from __future__ import annotations

import logging
from time import perf_counter
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult
from src.backend.features.scenario.exceptions import (
    InvalidScenarioAction,
    ScenarioConditionFailed,
    ScenarioNodeNotFound,
    ScenarioSessionNotFound,
)
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from uuid import UUID

    from src.backend.features.scenario.dto.context import ScenarioContextDTO
    from src.backend.features.scenario.engine import ScenarioDirector, ScenarioEvaluator, ScenarioFormatter
    from src.backend.features.scenario.integrations.system_integrator import ScenarioSystemIntegrator
    from src.shared.schemas import ScenarioPayloadDTO

log = logging.getLogger(__name__)


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)


def _finalize_target_state(result: ScenarioFinalizeResult) -> CoreDomain:
    target_state = getattr(result, "target_state", CoreDomain.EXPLORATION)
    if isinstance(target_state, CoreDomain):
        return target_state
    if isinstance(target_state, str):
        return CoreDomain(target_state)
    return CoreDomain.EXPLORATION


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

    async def ensure_character_owner(self, *, user_id: UUID, char_id: int) -> None:
        await self.integrator.ensure_character_owner(user_id=user_id, char_id=char_id)

    async def initialize(self, char_id: int, quest_key: str, source: str = "onboarding") -> ScenarioPayloadDTO:
        master = await self.integrator.get_quest_master(quest_key)
        if master is None:
            log.warning("Scenario initialize rejected: master_missing char_id=%s quest_key=%s", char_id, quest_key)
            raise ScenarioNodeNotFound(quest_key, "START")

        handler = self.integrator.build_handler(quest_key)
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
            if action_id == "finish":
                await self.integrator.recover_missing_finish_to_exploration(char_id)
                await self.integrator.sync_active_character_to_db(char_id)
                await self.integrator.publish_event(
                    "scenario.recovered_missing_session",
                    {
                        "char_id": char_id,
                        "action_id": action_id,
                        "target_state": CoreDomain.EXPLORATION.value,
                    },
                )
                log.warning("Scenario finish recovered: session_not_found char_id=%s", char_id)
                return ScenarioFinalizeResult(
                    target_state=CoreDomain.EXPLORATION,
                    transition_reason="scenario_session_missing_recovered",
                    metadata={"recovered": True, "missing_session": True},
                )
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
        finalize_started_at = perf_counter()
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

        handler = self.integrator.build_handler(context.quest_key)
        step_started_at = perf_counter()
        result = await handler.on_finalize(char_id, context, master)
        logger.info(
            "ScenarioFinalizeTiming | step=handler_finalize char_id={} quest_key={} ms={}",
            char_id,
            context.quest_key,
            _elapsed_ms(step_started_at),
        )

        reward_items = result.rewards.items or []
        reward_skills = result.rewards.skills or []
        reward_skill_initial_xp = result.rewards.skill_initial_xp
        attribute_bonuses = result.rewards.attribute_bonuses or {}

        step_started_at = perf_counter()
        item_ids = await self.integrator.grant_inventory_rewards(char_id, reward_items, quest_key=context.quest_key)
        logger.info(
            "ScenarioFinalizeTiming | step=grant_inventory_rewards char_id={} quest_key={} reward_count={} ms={}",
            char_id,
            context.quest_key,
            len(reward_items),
            _elapsed_ms(step_started_at),
        )
        step_started_at = perf_counter()
        await self.integrator.unlock_skills(char_id, reward_skills, initial_xp=reward_skill_initial_xp)
        logger.info(
            "ScenarioFinalizeTiming | step=unlock_skills char_id={} quest_key={} skill_count={} ms={}",
            char_id,
            context.quest_key,
            len(reward_skills),
            _elapsed_ms(step_started_at),
        )
        step_started_at = perf_counter()
        await self.integrator.apply_attribute_bonuses(char_id, attribute_bonuses)
        logger.info(
            "ScenarioFinalizeTiming | step=apply_attribute_bonuses char_id={} quest_key={} bonus_count={} ms={}",
            char_id,
            context.quest_key,
            len(attribute_bonuses),
            _elapsed_ms(step_started_at),
        )
        target_state = _finalize_target_state(result)
        if target_state == CoreDomain.COMBAT:
            step_started_at = perf_counter()
            await self.integrator.prepare_combat_return_context(char_id, location_id=result.location_id)
            logger.info(
                "ScenarioFinalizeTiming | step=prepare_combat_return_context char_id={} quest_key={} ms={}",
                char_id,
                context.quest_key,
                _elapsed_ms(step_started_at),
            )
            step_started_at = perf_counter()
            await self.integrator.finalize_session(
                char_id,
                CoreDomain.EXPLORATION,
                prev_state=CoreDomain.EXPLORATION,
            )
            logger.info(
                "ScenarioFinalizeTiming | step=finalize_session_to_exploration char_id={} quest_key={} ms={}",
                char_id,
                context.quest_key,
                _elapsed_ms(step_started_at),
            )
            step_started_at = perf_counter()
            await self.integrator.sync_active_character_to_db(char_id)
            logger.info(
                "ScenarioFinalizeTiming | step=sync_exploration_snapshot_before_combat char_id={} quest_key={} ms={}",
                char_id,
                context.quest_key,
                _elapsed_ms(step_started_at),
            )
            step_started_at = perf_counter()
            combat_ready = await self.integrator.request_combat_start(
                char_id,
                context.quest_key,
                battle_type=str(result.metadata.get("battle_type") or "shadow"),
                location_id=result.location_id,
            )
            logger.info(
                "ScenarioFinalizeTiming | step=request_combat_start char_id={} quest_key={} combat_id={} ms={}",
                char_id,
                context.quest_key,
                combat_ready.get("combat_id"),
                _elapsed_ms(step_started_at),
            )
            result.combat_id = str(combat_ready.get("combat_id") or result.combat_id or "")
            result.metadata = {**result.metadata, "combat_ready": combat_ready}
            step_started_at = perf_counter()
            await self.integrator.enter_prepared_combat(char_id, result.combat_id)
            logger.info(
                "ScenarioFinalizeTiming | step=enter_prepared_combat char_id={} quest_key={} combat_id={} ms={}",
                char_id,
                context.quest_key,
                result.combat_id,
                _elapsed_ms(step_started_at),
            )
        else:
            step_started_at = perf_counter()
            await self.integrator.finalize_session(char_id, target_state)
            logger.info(
                "ScenarioFinalizeTiming | step=finalize_session char_id={} quest_key={} target_state={} ms={}",
                char_id,
                context.quest_key,
                target_state.value,
                _elapsed_ms(step_started_at),
            )
        step_started_at = perf_counter()
        await self.integrator.sync_active_character_to_db(char_id)
        logger.info(
            "ScenarioFinalizeTiming | step=sync_active_character_to_db char_id={} quest_key={} ms={}",
            char_id,
            context.quest_key,
            _elapsed_ms(step_started_at),
        )

        step_started_at = perf_counter()
        await self.integrator.publish_event(
            "scenario.finalized",
            {
                "char_id": char_id,
                "quest_key": context.quest_key,
                "target_state": target_state.value,
                "rewards": result.rewards.model_dump_json(),
                "reward_item_ids": item_ids,
                "combat_id": result.combat_id,
                "location_id": result.location_id,
            },
        )
        logger.info(
            "ScenarioFinalizeTiming | step=publish_finalized_event char_id={} quest_key={} ms={}",
            char_id,
            context.quest_key,
            _elapsed_ms(step_started_at),
        )
        logger.info(
            "ScenarioFinalizeTiming | step=total char_id={} quest_key={} target_state={} ms={}",
            char_id,
            context.quest_key,
            target_state.value,
            _elapsed_ms(finalize_started_at),
        )
        logger.info(f"Scenario finalized: char_id={char_id} quest={context.quest_key}")
        return result

    async def cleanup(self, char_id: int) -> None:
        await self.integrator.cleanup_session(char_id)

    async def _current_or_raise(self, context: ScenarioContextDTO) -> dict[str, Any]:
        node = await self.integrator.get_node(context.quest_key, context.current_node_key)
        if node is None:
            raise ScenarioNodeNotFound(context.quest_key, context.current_node_key)
        return node
