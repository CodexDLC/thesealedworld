from __future__ import annotations

from loguru import logger as log

from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult
from src.backend.features.scenario.handlers.base_handler import BaseScenarioHandler
from src.shared.enums import CoreDomain


class TutorialScenarioHandler(BaseScenarioHandler):
    async def on_initialize(
        self,
        char_id: int,
        quest_master: dict,
        *,
        npc_key: str | None = None,
        **_: object,
    ) -> ScenarioContextDTO:
        initial = await self.integration.get_initial_handler_context(char_id)
        context = ScenarioContextDTO(
            quest_key=quest_master["quest_key"],
            current_node_key=quest_master["start_node_id"],
            sys_actor=initial.sys_actor,
            npc_key=npc_key or str(quest_master.get("npc_key") or "") or None,
            prev_state=initial.prev_state,
            prev_loc=initial.prev_loc,
            flags={"is_two_handed": 0},
        )
        if context.npc_key:
            await self.integration.apply_initialize_effects(
                char_id,
                context,
                effects=[
                    {"type": "npc.set_flag", "npc_key": context.npc_key, "flag": "met", "value": True},
                    {"type": "npc.bump_counter", "npc_key": context.npc_key, "counter": "meetings", "amount": 1},
                ],
            )
        return context

    async def on_finalize(
        self,
        char_id: int,
        context: ScenarioContextDTO,
        quest_master: dict,
    ) -> ScenarioFinalizeResult:
        _ = context
        location_id = await self.integration.select_tutorial_outskirts_spawn_location()
        log.bind(char_id=char_id, location_id=location_id).info("TutorialScenarioOutskirtsHandoff")
        return ScenarioFinalizeResult(
            target_state=CoreDomain.EXPLORATION,
            transition_reason="scenario_outskirts_handoff",
            location_id=location_id,
            metadata={
                "quest_key": quest_master["quest_key"],
            },
        )
