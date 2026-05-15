from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO

if TYPE_CHECKING:
    from src.backend.core.ai import AIService
    from src.backend.features.generation_ai.asset_storage import GeneratedAssetStorage
    from src.backend.features.generation_ai.models import AIGenerationTask


class CodexAIExecutor:
    def __init__(self, ai: AIService, *, asset_storage: GeneratedAssetStorage | None = None) -> None:
        self.ai = ai
        self.asset_storage = asset_storage

    async def generate(self, task: AIGenerationTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        if request.get("kind") == "image":
            return await self._generate_image(task, request)
        if request.get("kind") == "text":
            return await self._generate_text(task, request)

        raise RuntimeError(f"Unsupported AI generation request kind for task_type={task.task_type}: {request.get('kind')!r}")

    async def _generate_text(self, task: AIGenerationTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        kwargs = dict(request.get("kwargs") or {})
        raw_text = await self.ai.generate_text(request["prompt"], **kwargs)
        if raw_text is None:
            raise RuntimeError(f"AI text provider returned no response for task_type={task.task_type}")
        return AIGenerationTaskResultDTO(
            output_payload={
                "raw_text": str(raw_text),
            }
        )

    async def _generate_image(self, task: AIGenerationTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        if self.asset_storage is None:
            raise RuntimeError("AI image generation requires configured asset storage")
        generate_image_bytes = getattr(self.ai, "generate_image_bytes", None)
        if generate_image_bytes is None:
            raise RuntimeError("AI image generation provider is not configured")

        content, content_type = await generate_image_bytes(
            prompt=str(request["prompt"]),
            model=request.get("model"),
            response_mime_type=request.get("content_type") or "image/webp",
        )
        if not isinstance(content, bytes) or not content:
            raise RuntimeError(f"AI image provider returned no binary content for task_type={task.task_type}")

        ref = await self.asset_storage.put_bytes(
            storage_key=str(request["storage_key"]),
            content=content,
            content_type=str(content_type or request.get("content_type") or "image/webp"),
            metadata={
                "task_type": task.task_type,
                "entity_type": task.entity_type,
                "entity_id": task.entity_id,
                "model": request.get("model"),
            },
        )
        return ref.to_task_result(
            output_payload={
                "prompt": request["prompt"],
                "model": request.get("model"),
            }
        )
