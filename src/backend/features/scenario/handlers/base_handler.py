from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.features.scenario.dto.context import ScenarioContextDTO
    from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult


class BaseScenarioHandler(ABC):
    @abstractmethod
    async def on_initialize(self, char_id: int, quest_master: dict) -> ScenarioContextDTO:
        pass

    @abstractmethod
    async def on_finalize(
        self,
        char_id: int,
        context: ScenarioContextDTO,
        quest_master: dict,
    ) -> ScenarioFinalizeResult:
        pass
