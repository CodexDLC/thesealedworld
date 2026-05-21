from __future__ import annotations

from loguru import logger as log

from src.backend.features.scenario.dto.context import ELEMENT_KEYS, STAT_KEYS, ScenarioContextDTO
from src.backend.features.scenario.dto.finalize import (
    ScenarioFinalizeResult,
    ScenarioRewardsDTO,
)
from src.backend.features.scenario.handlers.base_handler import BaseScenarioHandler
from src.shared.enums import CoreDomain

VISIBLE_PROFILE_ORDER = [
    "agility",
    "projection",
    "endurance",
    "intellect",
    "prediction",
    "mental",
    "perception",
    "strength",
    "memory",
]
ATTRIBUTE_RANK_BONUSES = [9, 8, 7, 6, 5, 4, 3, 2, 1]


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
        location_id = await self.integration.select_tutorial_pve_spawn_location()
        log.bind(char_id=char_id, location_id=location_id).info("TutorialScenarioPveCombatHandoff")
        bonuses = self._calculate_attribute_bonuses(context)
        return ScenarioFinalizeResult(
            rewards=ScenarioRewardsDTO(
                items=list(context.queues.loot),
                skills=list(context.queues.skills),
                skill_initial_xp=0.10,
                attribute_bonuses=bonuses,
            ),
            target_state=CoreDomain.COMBAT,
            transition_reason="scenario_pve_combat",
            location_id=location_id,
            metadata={
                "battle_type": "pve",
                "quest_key": quest_master["quest_key"],
            },
        )

    @staticmethod
    def _calculate_attribute_bonuses(context: ScenarioContextDTO) -> dict[str, int]:
        order_index = {name: index for index, name in enumerate(VISIBLE_PROFILE_ORDER)}
        weighted = [(name, context.weights.stats.get(name, 0)) for name in STAT_KEYS]
        weighted.sort(key=lambda item: (-item[1], order_index.get(item[0], len(order_index))))
        return {stat_name: ATTRIBUTE_RANK_BONUSES[index] for index, (stat_name, _) in enumerate(weighted)}

    @staticmethod
    def _element_tokens(context: ScenarioContextDTO) -> dict[str, int]:
        return {f"t_{name}": context.weights.elements.get(name, 0) for name in ELEMENT_KEYS}
