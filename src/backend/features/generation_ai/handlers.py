from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
    from src.backend.features.generation_ai.models import AIGenerationTask


class AIGenerationExecutor(Protocol):
    async def generate(self, task: AIGenerationTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        """Run the provider call for a prepared generation request."""


class AIGenerationTaskHandler(Protocol):
    task_type: str

    async def build_request(self, task: AIGenerationTask) -> dict[str, Any]:
        """Build provider-facing request payload from the stored task row."""

    async def apply_result(
        self,
        task: AIGenerationTask,
        result: AIGenerationTaskResultDTO,
    ) -> list[AIGenerationTaskSpecDTO] | tuple[AIGenerationTaskSpecDTO, ...] | None:
        """Persist generated output and optionally enqueue the next domain generation steps."""
