from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO
from src.backend.features.generation_ai.image_normalization import normalize_generated_image

if TYPE_CHECKING:
    from src.backend.core.ai import AIService
    from src.backend.features.generation_ai.asset_storage import GeneratedAssetStorage
    from src.backend.features.generation_ai.models import AIGenerationTask


class CodexAIExecutor:
    def __init__(self, ai: AIService, *, asset_storage: GeneratedAssetStorage | None = None) -> None:
        self.ai = ai
        self.asset_storage = asset_storage

    async def generate(self, task: AIGenerationTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        task_output_kind = getattr(task, "output_kind", None)
        if task_output_kind is not None and request.get("kind") != task_output_kind:
            raise RuntimeError(
                f"AI generation request kind mismatch for task_type={task.task_type}: "
                f"request={request.get('kind')!r} task_output_kind={task_output_kind!r}"
            )
        if request.get("kind") == "image":
            return await self._generate_image(task, request)
        if request.get("kind") == "json":
            return await self._generate_json(task, request)
        if request.get("kind") == "text":
            return await self._generate_text(task, request)

        raise RuntimeError(
            f"Unsupported AI generation request kind for task_type={task.task_type}: {request.get('kind')!r}"
        )

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

    async def _generate_json(self, task: AIGenerationTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        schema = request.get("schema")
        if schema is None:
            raise RuntimeError(f"AI JSON generation requires schema for task_type={task.task_type}")

        kwargs = dict(request.get("kwargs") or {})
        generated = await self.ai.generate_json(request["prompt"], schema=schema, **kwargs)
        if generated is None:
            raise RuntimeError(f"AI JSON provider returned no response for task_type={task.task_type}")
        if hasattr(generated, "model_dump"):
            payload = generated.model_dump(mode="json")
        elif isinstance(generated, dict):
            payload = generated
        else:
            payload = schema.model_validate(generated).model_dump(mode="json")
        return AIGenerationTaskResultDTO(output_payload=payload)

    async def _generate_image(self, task: AIGenerationTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        if self.asset_storage is None:
            raise RuntimeError("AI image generation requires configured asset storage")
        generate_image_bytes = getattr(self.ai, "generate_image_bytes", None)
        if generate_image_bytes is None:
            raise RuntimeError("AI image generation provider is not configured")

        prompt = _validate_image_prompt(task, request.get("prompt"))
        model = _validate_gemini_image_model(task, request.get("model"))
        storage_key = _validate_image_storage_key(task, request.get("storage_key"))
        requested_content_type = _validate_image_content_type(task, request.get("content_type"))
        target_size = _optional_target_size(task, request.get("target_size"))
        content, content_type = await generate_image_bytes(
            prompt=prompt,
            model=model,
            response_mime_type=requested_content_type,
        )
        if not isinstance(content, bytes) or not content:
            raise RuntimeError(f"AI image provider returned no binary content for task_type={task.task_type}")
        actual_content_type = _validate_image_content_type(task, content_type or requested_content_type)
        normalized = normalize_generated_image(
            content,
            actual_content_type,
            target_content_type=requested_content_type,
            target_size=target_size,
        )

        ref = await self.asset_storage.put_bytes(
            storage_key=storage_key,
            content=normalized.content,
            content_type=normalized.content_type,
            metadata={
                "task_type": task.task_type,
                "entity_type": task.entity_type,
                "entity_id": task.entity_id,
                "model": model,
                "requested_content_type": requested_content_type,
                "provider_content_type": actual_content_type,
                **normalized.metadata,
            },
        )
        return ref.to_task_result(
            output_payload={
                "prompt": prompt,
                "model": model,
            }
        )


def _validate_image_prompt(task: AIGenerationTask, prompt: Any) -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise RuntimeError(f"AI image generation requires plain non-empty string prompt for task_type={task.task_type}")
    return prompt


def _validate_gemini_image_model(task: AIGenerationTask, model: Any) -> str:
    if not isinstance(model, str) or not model.strip():
        raise RuntimeError(f"AI image generation requires model for task_type={task.task_type}")
    model_id = model.strip()
    lowered = model_id.lower()
    if lowered.startswith("imagen-"):
        raise RuntimeError(
            f"Imagen models are not supported by current image tasks for task_type={task.task_type}: {model_id}"
        )
    if "nano-banana" in lowered:
        raise RuntimeError(
            f"Unsupported Gemini image alias for task_type={task.task_type}; use real API id: {model_id}"
        )
    if not lowered.startswith("gemini-") or "image" not in lowered:
        raise RuntimeError(f"Unsupported Gemini image model id for task_type={task.task_type}: {model_id}")
    return model_id


def _validate_image_storage_key(task: AIGenerationTask, storage_key: Any) -> str:
    if not isinstance(storage_key, str) or not storage_key.strip():
        raise RuntimeError(f"AI image generation requires storage_key for task_type={task.task_type}")
    return storage_key


def _validate_image_content_type(task: AIGenerationTask, content_type: Any) -> str:
    if not isinstance(content_type, str) or not content_type.strip():
        raise RuntimeError(f"AI image generation requires content_type for task_type={task.task_type}")
    normalized = content_type.strip()
    if not normalized.split(";", 1)[0].lower().startswith("image/"):
        raise RuntimeError(f"AI image generation returned non-image content_type for task_type={task.task_type}")
    return normalized


def _optional_target_size(task: AIGenerationTask, target_size: Any) -> tuple[int, int] | None:
    if target_size is None:
        return None
    if not isinstance(target_size, dict):
        raise RuntimeError(f"AI image generation target_size must be an object for task_type={task.task_type}")
    try:
        width = int(target_size.get("width"))
        height = int(target_size.get("height"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"AI image generation target_size must contain integer width/height for {task.task_type}"
        ) from exc
    if width <= 0 or height <= 0:
        raise RuntimeError(f"AI image generation target_size must be positive for task_type={task.task_type}")
    return width, height
