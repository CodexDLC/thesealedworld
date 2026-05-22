import json
from typing import Any

from codex_ai import GeminiProvider
from google import genai
from loguru import logger as log
from pydantic import BaseModel, Field

from src.backend.config.settings import settings


class ImageTextValidationDTO(BaseModel):
    visible_text: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    detected_text: str = ""


class AIService:
    """Centralized AI facade for text, JSON, and image generation."""

    def __init__(self) -> None:
        self.provider: GeminiProvider | None = None
        self._image_text_validation_client: Any | None = None

        if settings.gemini_api_key:
            log.info("AiServiceInitializing")
            self.provider = GeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                image_model=settings.gemini_image_model,
            )
            self._image_text_validation_client = genai.Client(api_key=settings.gemini_api_key)
        else:
            log.warning("AiServiceGeminiApiKeyMissing")

    async def generate_text(self, prompt: Any, **kwargs: Any) -> str | None:
        if self.provider is None:
            log.debug("AiTextGenerationSkipped")
            return None
        prompt_text, prompt_kwargs = _normalize_prompt(prompt)
        return await self.provider.generate_text(prompt_text, **_merge_prompt_kwargs(prompt_kwargs, kwargs))

    async def generate_json(self, prompt: Any, *, schema: type[Any], **kwargs: Any) -> Any | None:
        if self.provider is None:
            log.debug("AiJsonGenerationSkipped")
            return None
        prompt_text, prompt_kwargs = _normalize_prompt(prompt)
        return await self.provider.generate_json(
            prompt_text, schema=schema, **_merge_prompt_kwargs(prompt_kwargs, kwargs)
        )

    async def generate_image_bytes(
        self,
        prompt: str,
        *,
        model: str | None = None,
        response_mime_type: str = "image/webp",
        **kwargs: Any,
    ) -> tuple[bytes, str]:
        if self.provider is None:
            raise RuntimeError("AI image generation provider is not initialized")
        return await self.provider.generate_image_bytes(
            prompt,
            model=model,
            response_mime_type=response_mime_type,
            **kwargs,
        )

    async def validate_generated_image_no_text(
        self,
        *,
        image_bytes: bytes,
        content_type: str,
        model: str | None = None,
    ) -> ImageTextValidationDTO:
        if self.provider is None:
            raise RuntimeError("AI image text validation provider is not initialized")
        client = self._image_text_validation_client
        if client is None:
            raise RuntimeError("AI image text validation requires Gemini client access")

        from google.genai import types as genai_types

        prompt = (
            "Inspect the attached image for any visible text. Return JSON only. "
            "Set visible_text=true if the image contains letters, words, numbers, captions, signs, labels, logos, "
            "watermarks, signatures, readable or pseudo-readable glyphs/runes. "
            "Set visible_text=false only when there is no visible text-like mark."
        )
        response = await client.aio.models.generate_content(
            model=model or settings.gemini_model,
            contents=[
                genai_types.Part.from_text(text=prompt),
                genai_types.Part.from_bytes(data=image_bytes, mime_type=content_type),
            ],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ImageTextValidationDTO,
                temperature=0,
                max_output_tokens=256,
            ),
        )
        text = response.text or ""
        if not text.strip():
            raise RuntimeError("AI image text validation returned an empty response")
        return ImageTextValidationDTO.model_validate(json.loads(text))


def _normalize_prompt(prompt: Any) -> tuple[str, dict[str, Any]]:
    messages = getattr(prompt, "messages", None)
    if not isinstance(messages, list):
        return str(prompt), {}

    parts: list[str] = []
    prompt_system = getattr(prompt, "system", "")
    if prompt_system:
        parts.append(f"System:\n{prompt_system}")

    for message in messages:
        role = _message_value(message, "role") or "user"
        content = _message_value(message, "content")
        if not content:
            continue
        parts.append(f"{str(role).title()}:\n{content}")

    prompt_kwargs: dict[str, Any] = {}
    for key in ("model", "temperature", "max_tokens"):
        value = getattr(prompt, key, None)
        if value is not None:
            prompt_kwargs[key] = value

    return "\n\n".join(parts), prompt_kwargs


def _message_value(message: Any, key: str) -> Any:
    if isinstance(message, dict):
        return message.get(key)
    return getattr(message, key, None)


def _merge_prompt_kwargs(prompt_kwargs: dict[str, Any], call_kwargs: dict[str, Any]) -> dict[str, Any]:
    merged = dict(prompt_kwargs)
    merged.update(call_kwargs)
    return merged
