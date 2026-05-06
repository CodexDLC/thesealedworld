from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.backend.features.scenario.dto.context import ScenarioContextDTO
    from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult


@dataclass(frozen=True, slots=True)
class ScenarioInitialHandlerContext:
    sys_actor: str
    prev_state: str | None
    prev_loc: str | None


class ScenarioHandlerIntegration(Protocol):
    async def get_initial_handler_context(self, char_id: int) -> ScenarioInitialHandlerContext:
        pass


class BaseScenarioHandler(ABC):
    def __init__(self, integration: ScenarioHandlerIntegration) -> None:
        self.integration = integration

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
