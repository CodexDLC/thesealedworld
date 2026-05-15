from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.backend.features.scenario.dto.context import ScenarioContextDTO
    from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult
    from src.shared.schemas.scenario import ScenarioReturnContextDTO


@dataclass(frozen=True, slots=True)
class ScenarioInitialHandlerContext:
    sys_actor: str
    prev_state: str | None
    prev_loc: str | None


class ScenarioHandlerIntegration(Protocol):
    async def get_initial_handler_context(self, char_id: int) -> ScenarioInitialHandlerContext:
        pass

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        pass


class BaseScenarioHandler(ABC):
    def __init__(self, integration: ScenarioHandlerIntegration) -> None:
        self.integration = integration

    @abstractmethod
    async def on_initialize(
        self,
        char_id: int,
        quest_master: dict,
        *,
        return_context: ScenarioReturnContextDTO | None = None,
    ) -> ScenarioContextDTO:
        pass

    @abstractmethod
    async def on_finalize(
        self,
        char_id: int,
        context: ScenarioContextDTO,
        quest_master: dict,
    ) -> ScenarioFinalizeResult:
        pass
