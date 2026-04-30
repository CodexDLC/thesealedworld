from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.handlers import get_handler
from src.backend.infrastructure.redis.character_session_manager import (
    StateTransitionError,
)
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService

    from src.backend.core.bus import GameEventProducer
    from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult
    from src.backend.features.scenario.engine import ScenarioDirector, ScenarioEvaluator, ScenarioFormatter
    from src.backend.features.scenario.services.content_service import ScenarioContentService
    from src.backend.infrastructure.db.scenario.repositories import ScenarioRepository
    from src.backend.infrastructure.redis.character_session_manager import CharacterSessionManager
    from src.backend.infrastructure.redis.scenario import ScenarioSessionManager
    from src.shared.schemas import ScenarioPayloadDTO

log = logging.getLogger(__name__)
BACKUP_INTERVAL = 5  # TODO: tune from runtime metrics after scenario traffic exists.


class ScenarioError(RuntimeError):
    pass


class ScenarioNotFoundError(ScenarioError):
    pass


class ScenarioSessionNotFoundError(ScenarioError):
    pass


class InvalidActionError(ScenarioError):
    pass


class ScenarioService:
    def __init__(
        self,
        *,
        content: ScenarioContentService,
        sessions: ScenarioSessionManager,
        character_sessions: CharacterSessionManager,
        repo: ScenarioRepository,
        evaluator: ScenarioEvaluator,
        director: ScenarioDirector,
        formatter: ScenarioFormatter,
        events: GameEventProducer,
        redis: RedisService,
    ) -> None:
        self.content = content
        self.sessions = sessions
        self.character_sessions = character_sessions
        self.repo = repo
        self.evaluator = evaluator
        self.director = director
        self.formatter = formatter
        self.events = events
        self.redis = redis

    async def initialize(self, char_id: int, quest_key: str, source: str = "onboarding") -> ScenarioPayloadDTO:
        master = await self.content.get_master(quest_key)
        if master is None:
            raise ScenarioNotFoundError(f"Scenario quest not found: {quest_key}")

        handler = get_handler(quest_key, character_sessions=self.character_sessions)
        context = await handler.on_initialize(char_id, master)
        await self.sessions.create(char_id, context)

        try:
            await self.character_sessions.transition_state(
                char_id, CoreDomain.SCENARIO, expected_state=CoreDomain.LOBBY
            )
        except StateTransitionError:
            log.warning("Scenario initialize state transition skipped: char_id=%s source=%s", char_id, source)
        await self.character_sessions.set_scenario_session(
            char_id,
            str(context.scenario_session_id),
            active_quest=quest_key,
        )
        await self.repo.upsert_state(
            char_id,
            quest_key,
            context.current_node_key,
            context.model_dump(mode="json"),
            context.scenario_session_id,
        )

        node = await self._current_or_raise(context)
        flat = context.flatten()
        if "auto" in self.director._get_node_actions(node):
            resolved = await self.director.execute_auto_chain(quest_key, node, flat, self.content)
            flat = resolved.context
            node = resolved.node
            context.apply_flat(flat)
            context.current_node_key = node["node_key"]
            await self._persist_context(char_id, context)

        payload = self.formatter.render_payload(node, context.flatten(), master)
        await self.events.publish(
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
        context = await self.sessions.get(char_id)
        if context is None:
            context = await self._repair_from_backup(char_id)
        if context is None:
            await self.events.publish(
                "scenario.failed", {"char_id": char_id, "quest_key": "", "error": "session_not_found"}
            )
            raise ScenarioSessionNotFoundError(f"Scenario session not found: char_id={char_id}")

        master = await self.content.get_master(context.quest_key)
        if master is None:
            raise ScenarioNotFoundError(f"Scenario quest not found: {context.quest_key}")
        node = await self._current_or_raise(context)
        flat = context.flatten()
        if "auto" in self.director._get_node_actions(node):
            resolved = await self.director.execute_auto_chain(context.quest_key, node, flat, self.content)
            flat = resolved.context
            node = resolved.node
            context.apply_flat(flat)
            context.current_node_key = node["node_key"]
            await self._persist_context(char_id, context)

        await self.events.publish(
            "scenario.resumed",
            {"char_id": char_id, "quest_key": context.quest_key, "node_key": context.current_node_key},
        )
        return self.formatter.render_payload(node, context.flatten(), master)

    async def step(self, char_id: int, action_id: str) -> ScenarioPayloadDTO | ScenarioFinalizeResult:
        context = await self.sessions.get(char_id)
        if context is None:
            context = await self._repair_from_backup(char_id)

        if context is None:
            raise ScenarioSessionNotFoundError(f"Scenario session not found: char_id={char_id}")

        current = await self._current_or_raise(context)
        # Use director's internal unification to handle both dict and list actions
        actions = self.director._get_node_actions(current)
        action = actions.get(action_id)

        if action is None:
            raise InvalidActionError(f"Invalid scenario action: {action_id}")
        flat = context.flatten()
        if action.get("condition") and not self.evaluator.check_condition(action["condition"], flat):
            raise InvalidActionError(f"Scenario action condition failed: {action_id}")

        if action.get("type") == "finish_quest":
            return await self.finalize(char_id)

        resolved = await self.director.resolve_next_node(context.quest_key, action, flat, self.content)
        prev_node = context.current_node_key
        context.apply_flat(resolved.context)
        context.current_node_key = resolved.node["node_key"]
        context.total_steps += 1
        if prev_node not in context.visited_nodes:
            context.visited_nodes.append(prev_node)
        await self._persist_context(char_id, context)

        if context.step_counter % BACKUP_INTERVAL == 0:
            await self.repo.upsert_state(
                char_id,
                context.quest_key,
                context.current_node_key,
                context.model_dump(mode="json"),
                context.scenario_session_id,
            )

        await self.events.publish(
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

        master = await self.content.get_master(context.quest_key) or {}
        return self.formatter.render_payload(resolved.node, context.flatten(), master)

    async def finalize(self, char_id: int) -> ScenarioFinalizeResult:
        context = await self.sessions.get(char_id)
        if context is None:
            raise ScenarioSessionNotFoundError(f"Scenario session not found: char_id={char_id}")
        master = await self.content.get_master(context.quest_key)
        if master is None:
            raise ScenarioNotFoundError(f"Scenario quest not found: {context.quest_key}")

        handler = get_handler(context.quest_key, character_sessions=self.character_sessions)
        result = await handler.on_finalize(char_id, context, master)

        await self._grant_inventory_rewards(char_id, result.rewards.items)
        await self._unlock_skills(char_id, result.rewards.skills)
        if result.rewards.attribute_bonuses:
            await self.character_sessions.apply_attribute_bonus(char_id, result.rewards.attribute_bonuses)

        await self._request_combat_start(char_id, context.quest_key)
        await self.character_sessions.transition_state(
            char_id, CoreDomain.EXPLORATION, expected_state=CoreDomain.SCENARIO
        )
        await self.character_sessions.clear_scenario_session(char_id)
        await self.sessions.delete(char_id)
        await self.repo.delete_state(char_id)

        await self.events.publish(
            "scenario.finalized",
            {
                "char_id": char_id,
                "quest_key": context.quest_key,
                "target_state": CoreDomain.EXPLORATION.value,
                "rewards": result.rewards.model_dump_json(),
            },
        )
        return result

    async def _grant_inventory_rewards(self, char_id: int, items: list[str]) -> None:
        # TODO(scenario-migration): call inventory service after inventory feature migrates.
        if items:
            log.info("TODO: inventory rewards skipped; char_id=%s items=%s", char_id, items)

    async def _unlock_skills(self, char_id: int, skills: list[str]) -> None:
        # TODO(scenario-migration): call skills service after skills feature migrates.
        if skills:
            log.info("TODO: skill unlocks skipped; char_id=%s skills=%s", char_id, skills)

    async def _request_combat_start(self, char_id: int, quest_key: str) -> None:
        # TODO(scenario-migration): call combat start after combat feature migrates.
        log.info("TODO: combat start skipped; char_id=%s source=scenario:%s", char_id, quest_key)

    async def _repair_from_backup(self, char_id: int) -> ScenarioContextDTO | None:
        state = await self.repo.get_active_state(char_id)
        if not state:
            return None
        context = ScenarioContextDTO.model_validate(state["context"])
        await self.sessions.create(char_id, context)
        await self.character_sessions.set_scenario_session(
            char_id,
            str(context.scenario_session_id),
            active_quest=context.quest_key,
        )
        return context

    async def _current_or_raise(self, context: ScenarioContextDTO) -> dict[str, Any]:
        node = await self.content.get_node(context.quest_key, context.current_node_key)
        if node is None:
            raise ScenarioNotFoundError(
                f"Scenario node not found: quest={context.quest_key} node={context.current_node_key}"
            )
        return node

    async def _persist_context(self, char_id: int, context: ScenarioContextDTO) -> None:
        await self.sessions.patch(
            char_id,
            {
                "$.current_node_key": context.current_node_key,
                "$.step_counter": context.step_counter,
                "$.total_steps": context.total_steps,
                "$.visited_nodes": context.visited_nodes,
                "$.weights": context.weights.model_dump(mode="json"),
                "$.queues": context.queues.model_dump(mode="json"),
                "$.flags": context.flags,
                "$.updated_at": context.updated_at.isoformat(),
            },
        )
