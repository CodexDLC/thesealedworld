from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult, ScenarioRewardsDTO
from src.backend.features.scenario.handlers.base_handler import BaseScenarioHandler
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.shared.schemas.scenario import ScenarioReturnContextDTO


class DialogueScenarioHandler(BaseScenarioHandler):
    """Generic handler for data-driven repeatable NPC dialogues."""

    async def on_initialize(
        self,
        char_id: int,
        quest_master: dict[str, Any],
        *,
        return_context: ScenarioReturnContextDTO | None = None,
        npc_key: str | None = None,
    ) -> ScenarioContextDTO:
        initial = await self.integration.get_initial_handler_context(char_id)
        resolved_npc_key = npc_key or str(quest_master.get("npc_key") or "") or None
        if return_context is not None:
            initial_prev_state = str(return_context.source_state)
            initial_prev_loc = return_context.location_id or initial.prev_loc
        else:
            initial_prev_state = initial.prev_state
            initial_prev_loc = initial.prev_loc

        start_node_id = str(quest_master["start_node_id"])
        if return_context is not None and isinstance(return_context.metadata, dict):
            override = return_context.metadata.get("initial_node_key") or return_context.metadata.get("start_node_id")
            if override:
                start_node_id = str(override)

        return ScenarioContextDTO(
            quest_key=str(quest_master["quest_key"]),
            current_node_key=start_node_id,
            sys_actor=initial.sys_actor,
            npc_key=resolved_npc_key,
            prev_state=initial_prev_state,
            prev_loc=initial_prev_loc,
            return_context=return_context,
        )

    async def on_finalize(
        self,
        char_id: int,
        context: ScenarioContextDTO,
        quest_master: dict[str, Any],
    ) -> ScenarioFinalizeResult:
        _ = char_id, quest_master
        node = await self.integration.get_node(context.quest_key, context.current_node_key)
        metadata = node.get("metadata", {}) if isinstance(node, dict) else {}
        finalize = metadata.get("finalize", {}) if isinstance(metadata, dict) else {}
        if not isinstance(finalize, dict):
            finalize = {}

        return_context = context.return_context
        raw_target = finalize.get("target_state")
        if raw_target is None and return_context is not None:
            raw_target = return_context.return_state
        target_state = _core_domain(raw_target, default=CoreDomain.EXPLORATION)

        response_metadata = finalize.get("response_metadata") or {}
        if not isinstance(response_metadata, dict):
            response_metadata = {}
        result_metadata: dict[str, Any] = dict(response_metadata)

        next_screen = finalize.get("next_screen")
        if next_screen is None and return_context is not None:
            next_screen = return_context.return_screen
        if next_screen:
            result_metadata["next_screen"] = str(next_screen)

        effects = finalize.get("effects") or []
        if effects:
            result_metadata["_effects"] = effects

        if return_context is not None:
            result_metadata["return_context"] = return_context.model_dump(mode="json")

        return ScenarioFinalizeResult(
            rewards=ScenarioRewardsDTO(),
            target_state=target_state,
            transition_reason=str(finalize.get("transition_reason") or "dialogue_finalized"),
            location_id=str(finalize.get("location_id") or return_context.location_id)
            if return_context is not None and (finalize.get("location_id") or return_context.location_id)
            else None,
            metadata=result_metadata,
        )


def _core_domain(value: Any, *, default: CoreDomain) -> CoreDomain:
    if isinstance(value, CoreDomain):
        return value
    if value is None:
        return default
    return CoreDomain(str(value))
