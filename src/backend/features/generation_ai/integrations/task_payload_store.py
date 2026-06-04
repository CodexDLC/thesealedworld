from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from src.backend.infrastructure.generation_ai import (
    AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION,
    AIGenerationTaskDocumentRepository,
)

if TYPE_CHECKING:
    from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
    from src.backend.features.generation_ai.models import AIGenerationTask


class AIGenerationTaskPayloadStore:
    """Feature-facing boundary for heavy AI generation task payload documents."""

    def __init__(self, repository: AIGenerationTaskDocumentRepository | None = None) -> None:
        self.repository = repository or AIGenerationTaskDocumentRepository()

    async def create_task_document(
        self,
        *,
        task: AIGenerationTask,
        spec: AIGenerationTaskSpecDTO,
        identity_key: str,
    ) -> str:
        return await self.repository.write_initial(task=task, spec=spec, identity_key=identity_key)

    async def fetch_task_document(self, task_id: str) -> dict[str, Any] | None:
        return await self.repository.fetch_by_task_id(task_id)

    async def record_result(
        self,
        *,
        task: AIGenerationTask,
        result: AIGenerationTaskResultDTO,
        metadata: dict[str, Any],
    ) -> str:
        return await self.repository.record_result(task=task, result=result, metadata=metadata)

    async def record_error(self, *, task: AIGenerationTask, error: dict[str, Any]) -> str:
        return await self.repository.record_error(task=task, error=error)

    @staticmethod
    def apply_document(task: AIGenerationTask, document: dict[str, Any]) -> AIGenerationTask:
        schema_version = int(document.get("schema_version") or 0)
        if schema_version != AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported AI generation task document schema_version={schema_version} for task_id={task.id}"
            )
        hydrated_task = cast("Any", task)
        hydrated_task.prompt_payload = _payload_dict(document.get("prompt_payload"))
        hydrated_task.input_payload = _payload_dict(document.get("input_payload"))
        hydrated_task.output_payload = _payload_dict(document.get("output_payload"))
        hydrated_task.metadata_ = _payload_dict(document.get("metadata"))
        hydrated_task.error = _payload_dict(document.get("error"))
        if document.get("_id") is not None:
            task.mongo_document_id = str(document["_id"])
        task.mongo_schema_version = schema_version
        return task


def _payload_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
