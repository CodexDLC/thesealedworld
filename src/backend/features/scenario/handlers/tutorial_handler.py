from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from src.backend.features.scenario.dto.context import ELEMENT_KEYS, STAT_KEYS, ScenarioContextDTO
from src.backend.features.scenario.dto.finalize import (
    ScenarioFinalizeResult,
    ScenarioRewardsDTO,
)
from src.backend.features.scenario.handlers.base_handler import BaseScenarioHandler
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.infrastructure.actor_state import CharacterSessionManager

log = logging.getLogger(__name__)

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

TUTORIAL_EXIT_LOCATIONS = [
    "52_58",
    "52_46",
    "58_52",
    "46_52",
    "56_56",
    "48_56",
    "56_48",
    "48_48",
    "55_57",
    "57_55",
    "49_57",
    "47_55",
]


class TutorialScenarioHandler(BaseScenarioHandler):
    def __init__(self, character_sessions: CharacterSessionManager) -> None:
        self.character_sessions = character_sessions

    async def on_initialize(self, char_id: int, quest_master: dict) -> ScenarioContextDTO:
        symbiote = await self.character_sessions.get_section(char_id, "symbiote")
        sys_actor = "Symbiote"
        if isinstance(symbiote, dict):
            sys_actor = str(symbiote.get("name") or sys_actor)
        elif isinstance(symbiote, str) and symbiote:
            sys_actor = symbiote

        location = await self.character_sessions.get_section(char_id, "location")
        prev_loc = location.get("current") if isinstance(location, dict) else "52_52"

        state = await self.character_sessions.get_section(char_id, "state")
        return ScenarioContextDTO(
            quest_key=quest_master["quest_key"],
            current_node_key=quest_master["start_node_id"],
            sys_actor=sys_actor,
            prev_state=str(state) if state else None,
            prev_loc=prev_loc,
            flags={"is_two_handed": 0},
        )

    async def on_finalize(
        self,
        char_id: int,
        context: ScenarioContextDTO,
        quest_master: dict,
    ) -> ScenarioFinalizeResult:
        location_id = self._select_tutorial_exit_location()
        log.info("Tutorial scenario shadow combat handoff: char_id=%s location_id=%s", char_id, location_id)
        bonuses = self._calculate_attribute_bonuses(context)
        return ScenarioFinalizeResult(
            rewards=ScenarioRewardsDTO(
                items=list(context.queues.loot),
                skills=list(context.queues.skills),
                attribute_bonuses=bonuses,
            ),
            target_state=CoreDomain.COMBAT,
            transition_reason="scenario_shadow_combat",
            location_id=location_id,
            metadata={
                "battle_type": "shadow",
                "quest_key": quest_master["quest_key"],
            },
        )

    @staticmethod
    def _select_tutorial_exit_location() -> str:
        return random.choice(TUTORIAL_EXIT_LOCATIONS)  # nosec B311

    @staticmethod
    def _calculate_attribute_bonuses(context: ScenarioContextDTO) -> dict[str, int]:
        order_index = {name: index for index, name in enumerate(VISIBLE_PROFILE_ORDER)}
        weighted = [(name, context.weights.stats.get(name, 0)) for name in STAT_KEYS]
        weighted.sort(key=lambda item: (-item[1], order_index.get(item[0], len(order_index))))
        return {stat_name: ATTRIBUTE_RANK_BONUSES[index] for index, (stat_name, _) in enumerate(weighted)}

    @staticmethod
    def _element_tokens(context: ScenarioContextDTO) -> dict[str, int]:
        return {f"t_{name}": context.weights.elements.get(name, 0) for name in ELEMENT_KEYS}
