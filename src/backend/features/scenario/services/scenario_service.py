from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Any
from uuid import uuid4

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
    from src.shared.schemas.scenario import ScenarioReturnContextDTO

log = logger


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)


def _finalize_target_state(result: ScenarioFinalizeResult) -> CoreDomain:
    target_state = getattr(result, "target_state", CoreDomain.EXPLORATION)
    if isinstance(target_state, CoreDomain):
        return target_state
    if isinstance(target_state, str):
        return CoreDomain(target_state)
    return CoreDomain.EXPLORATION


def _log_finalize_timing(
    step: str,
    *,
    char_id: int,
    quest_key: str,
    started_at: float,
    **extra: Any,
) -> None:
    logger.bind(step=step, char_id=char_id, quest_key=quest_key, duration_ms=_elapsed_ms(started_at), **extra).info(
        "ScenarioFinalizeTiming"
    )


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

    async def initialize(
        self,
        char_id: int,
        quest_key: str,
        source: str = "onboarding",
        *,
        return_context: ScenarioReturnContextDTO | None = None,
        npc_key: str | None = None,
    ) -> ScenarioPayloadDTO:
        _ = source
        master = await self.integrator.get_quest_master(quest_key)
        if master is None:
            log.bind(char_id=char_id, quest_key=quest_key, reason="master_missing").warning(
                "ScenarioInitializeRejected"
            )
            raise ScenarioNodeNotFound(quest_key, "START")

        handler = self.integrator.build_handler(master)
        resolved_npc_key = npc_key or (return_context.npc_key if return_context is not None else None)
        if not resolved_npc_key:
            master_npc_key = master.get("npc_key")
            resolved_npc_key = str(master_npc_key) if master_npc_key else None
        context = await handler.on_initialize(
            char_id,
            master,
            return_context=return_context,
            npc_key=resolved_npc_key,
        )
        if return_context is not None and context.return_context is None:
            context.return_context = return_context
        if context.npc_key:
            await self.integrator.attach_npc_context(char_id, context)

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
        logger.bind(char_id=char_id, quest_key=quest_key, node_key=payload.node_key).info("ScenarioInitialized")
        logger.bind(button_labels=[b.label for b in payload.buttons]).debug("ScenarioButtonsSent")
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
            log.bind(char_id=char_id, reason="session_not_found").warning("ScenarioResumeRejected")
            raise ScenarioSessionNotFound(char_id)

        master = await self.integrator.get_quest_master(context.quest_key)
        if master is None:
            log.bind(char_id=char_id, quest_key=context.quest_key, reason="master_missing").warning(
                "ScenarioResumeRejected"
            )
            raise ScenarioNodeNotFound(context.quest_key, "MASTER")
        if context.npc_key:
            await self.integrator.attach_npc_context(char_id, context)
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
        logger.bind(char_id=char_id, node_key=payload.node_key).info("ScenarioResumed")
        logger.bind(button_labels=[b.label for b in payload.buttons]).debug("ScenarioButtonsSent")
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
                log.bind(char_id=char_id, reason="session_not_found").warning("ScenarioFinishRecovered")
                return ScenarioFinalizeResult(
                    target_state=CoreDomain.EXPLORATION,
                    transition_reason="scenario_session_missing_recovered",
                    metadata={"recovered": True, "missing_session": True},
                )
            log.bind(char_id=char_id, action_id=action_id, reason="session_not_found").warning("ScenarioStepRejected")
            raise ScenarioSessionNotFound(char_id)

        current = await self._current_or_raise(context)
        actions = self.director._get_node_actions(current)
        action = actions.get(action_id)

        if action is None:
            log.bind(char_id=char_id, action_id=action_id, reason="invalid_action").warning("ScenarioStepRejected")
            raise InvalidScenarioAction(action_id)
        flat = context.flatten()
        if action.get("condition") and not self.evaluator.check_condition(action["condition"], flat):
            log.bind(char_id=char_id, action_id=action_id, reason="condition_failed").warning("ScenarioStepRejected")
            raise ScenarioConditionFailed(action_id)

        if action.get("type") == "enter_prepared_rift":
            if not await self.integrator.has_prepared_rift_entry(char_id):
                await self._prepare_rift_entry_for_node(char_id, context, current)
                master = await self.integrator.get_quest_master(context.quest_key) or {}
                return self.formatter.render_payload(current, context.flatten(), master)
            metadata = await self.integrator.activate_prepared_rift_entry(char_id, context)
            await self.integrator.sync_active_character_to_db(char_id)
            await self.integrator.publish_event(
                "scenario.finalized",
                {
                    "char_id": char_id,
                    "quest_key": context.quest_key,
                    "target_state": CoreDomain.RIFT.value,
                    "rift_session_id": metadata.get("rift_session_id"),
                    "rift_instance_id": metadata.get("rift_instance_id"),
                },
            )
            return ScenarioFinalizeResult(
                target_state=CoreDomain.RIFT,
                transition_reason="scenario_rift_entry",
                metadata={
                    "quest_key": context.quest_key,
                    **metadata,
                },
            )

        if action.get("type") == "finish_quest":
            return await self.finalize(char_id)
        if action.get("effects"):
            await self.integrator.apply_action_effects(
                char_id,
                context,
                effects=list(action.get("effects") or []),
                action_id=action_id,
            )
            if context.npc_key:
                await self.integrator.attach_npc_context(char_id, context)
            flat = context.flatten()

        resolved = await self.director.resolve_next_node(context.quest_key, action, flat, self.integrator)
        prev_node = context.current_node_key
        context.apply_flat(resolved.context)
        context.current_node_key = resolved.node["node_key"]
        context.total_steps += 1
        if prev_node not in context.visited_nodes:
            context.visited_nodes.append(prev_node)

        await self.integrator.update_progress(char_id, context)
        await self._prepare_rift_entry_for_node(char_id, context, resolved.node)

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
        logger.bind(char_id=char_id, action_id=action_id, next_node=payload.node_key).info("ScenarioStepped")
        logger.bind(button_labels=[b.label for b in payload.buttons]).debug("ScenarioButtonsSent")
        return payload

    async def finalize(self, char_id: int) -> ScenarioFinalizeResult:
        finalize_started_at = perf_counter()
        context = await self.integrator.load_session(char_id)
        if context is None:
            log.bind(char_id=char_id, reason="session_not_found").warning("ScenarioFinalizeRejected")
            raise ScenarioSessionNotFound(char_id)
        master = await self.integrator.get_quest_master(context.quest_key)
        if master is None:
            log.bind(char_id=char_id, quest_key=context.quest_key, reason="master_missing").warning(
                "ScenarioFinalizeRejected"
            )
            raise ScenarioNodeNotFound(context.quest_key, "MASTER")

        handler = self.integrator.build_handler(master)
        step_started_at = perf_counter()
        result = await handler.on_finalize(char_id, context, master)
        _log_finalize_timing(
            "handler_finalize", char_id=char_id, quest_key=context.quest_key, started_at=step_started_at
        )

        reward_items = result.rewards.items or []
        reward_skills = result.rewards.skills or []
        reward_skill_initial_xp = result.rewards.skill_initial_xp
        attribute_bonuses = result.rewards.attribute_bonuses or {}

        step_started_at = perf_counter()
        item_ids = await self.integrator.grant_inventory_rewards(char_id, reward_items, quest_key=context.quest_key)
        _log_finalize_timing(
            "grant_inventory_rewards",
            char_id=char_id,
            quest_key=context.quest_key,
            started_at=step_started_at,
            reward_count=len(reward_items),
        )
        step_started_at = perf_counter()
        await self.integrator.unlock_skills(char_id, reward_skills, initial_xp=reward_skill_initial_xp)
        _log_finalize_timing(
            "unlock_skills",
            char_id=char_id,
            quest_key=context.quest_key,
            started_at=step_started_at,
            skill_count=len(reward_skills),
        )
        step_started_at = perf_counter()
        await self.integrator.apply_attribute_bonuses(char_id, attribute_bonuses)
        _log_finalize_timing(
            "apply_attribute_bonuses",
            char_id=char_id,
            quest_key=context.quest_key,
            started_at=step_started_at,
            bonus_count=len(attribute_bonuses),
        )
        step_started_at = perf_counter()
        effect_metadata = await self.integrator.apply_finalize_effects(
            char_id,
            result.metadata,
            quest_key=context.quest_key,
        )
        result.metadata = {**result.metadata, **effect_metadata}
        _log_finalize_timing(
            "apply_finalize_effects",
            char_id=char_id,
            quest_key=context.quest_key,
            started_at=step_started_at,
            effect_count=len(effect_metadata.get("effects", {}))
            if isinstance(effect_metadata.get("effects"), dict)
            else 0,
        )
        target_state = _finalize_target_state(result)
        if target_state == CoreDomain.COMBAT:
            step_started_at = perf_counter()
            await self.integrator.sync_active_character_to_db(char_id)
            _log_finalize_timing(
                "sync_exploration_snapshot_before_combat",
                char_id=char_id,
                quest_key=context.quest_key,
                started_at=step_started_at,
            )
            step_started_at = perf_counter()
            combat_ready = await self.integrator.request_combat_start(
                char_id,
                context.quest_key,
                battle_type=str(result.metadata.get("battle_type") or ""),
                location_id=result.location_id,
            )
            _log_finalize_timing(
                "request_combat_start",
                char_id=char_id,
                quest_key=context.quest_key,
                started_at=step_started_at,
                combat_id=combat_ready.get("combat_id"),
            )
            result.combat_id = str(combat_ready.get("combat_id") or result.combat_id or "")
            result.metadata = {**result.metadata, "combat_ready": combat_ready}
            step_started_at = perf_counter()
            await self.integrator.prepare_combat_return_context(char_id, location_id=result.location_id)
            _log_finalize_timing(
                "prepare_combat_return_context",
                char_id=char_id,
                quest_key=context.quest_key,
                started_at=step_started_at,
            )
            step_started_at = perf_counter()
            await self.integrator.finalize_session(
                char_id,
                CoreDomain.EXPLORATION,
                prev_state=CoreDomain.EXPLORATION,
            )
            _log_finalize_timing(
                "finalize_session_to_exploration",
                char_id=char_id,
                quest_key=context.quest_key,
                started_at=step_started_at,
            )
            step_started_at = perf_counter()
            await self.integrator.enter_prepared_combat(char_id, result.combat_id)
            _log_finalize_timing(
                "enter_prepared_combat",
                char_id=char_id,
                quest_key=context.quest_key,
                started_at=step_started_at,
                combat_id=result.combat_id,
            )
        else:
            if target_state == CoreDomain.EXPLORATION and result.location_id:
                step_started_at = perf_counter()
                await self.integrator.prepare_exploration_return_context(char_id, location_id=result.location_id)
                _log_finalize_timing(
                    "prepare_exploration_return_context",
                    char_id=char_id,
                    quest_key=context.quest_key,
                    started_at=step_started_at,
                    location_id=result.location_id,
                )
            step_started_at = perf_counter()
            await self.integrator.finalize_session(char_id, target_state)
            _log_finalize_timing(
                "finalize_session",
                char_id=char_id,
                quest_key=context.quest_key,
                started_at=step_started_at,
                target_state=target_state.value,
            )
        step_started_at = perf_counter()
        await self.integrator.sync_active_character_to_db(char_id)
        _log_finalize_timing(
            "sync_active_character_to_db",
            char_id=char_id,
            quest_key=context.quest_key,
            started_at=step_started_at,
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
        _log_finalize_timing(
            "publish_finalized_event",
            char_id=char_id,
            quest_key=context.quest_key,
            started_at=step_started_at,
        )
        _log_finalize_timing(
            "total",
            char_id=char_id,
            quest_key=context.quest_key,
            started_at=finalize_started_at,
            target_state=target_state.value,
        )
        logger.bind(char_id=char_id, quest_key=context.quest_key).info("ScenarioFinalized")
        return result

    async def cleanup(self, char_id: int) -> None:
        await self.integrator.cleanup_session(char_id)

    async def _prepare_rift_entry_for_node(
        self,
        char_id: int,
        context: ScenarioContextDTO,
        node: dict[str, Any],
    ) -> None:
        metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        rift_entry = metadata.get("rift_entry") if isinstance(metadata.get("rift_entry"), dict) else {}
        if not bool(rift_entry.get("prepare_on_show")):
            return
        if await self.integrator.has_prepared_rift_entry(char_id):
            context.flags["rift_entry_status"] = "ready"
            return
        if not context.flags.get("rift_entry_request_id"):
            context.flags["rift_entry_request_id"] = uuid4().hex
        result = await self.integrator.publish_rift_entry_requested(char_id, context, node)
        context.flags["rift_entry_status"] = "requested"
        context.flags["rift_entry_request_id"] = str(result.get("request_id") or context.flags["rift_entry_request_id"])
        await self.integrator.update_progress(char_id, context, force_backup=True)

    async def _current_or_raise(self, context: ScenarioContextDTO) -> dict[str, Any]:
        node = await self.integrator.get_node(context.quest_key, context.current_node_key)
        if node is None:
            raise ScenarioNodeNotFound(context.quest_key, context.current_node_key)
        return node
