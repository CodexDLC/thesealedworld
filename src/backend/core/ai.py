import logging
from typing import Any

from codex_ai import GeminiProvider

from src.backend.config.settings import settings

log = logging.getLogger(__name__)


class AIService:
    """Centralized AI facade for text, JSON, and image generation."""

    def __init__(self) -> None:
        self.provider: GeminiProvider | None = None

        if settings.gemini_api_key:
            log.info("Initializing AIService with GeminiProvider")
            self.provider = GeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                image_model=settings.gemini_image_model,
            )
        else:
            log.warning("Gemini API key not found. AIService will be disabled.")

    async def generate_text(self, prompt: Any, **kwargs: Any) -> str | None:
        if self.provider is None:
            log.debug("AI text generation skipped: provider not initialized")
            return None
        prompt_text, prompt_kwargs = _normalize_prompt(prompt)
        return await self.provider.generate_text(prompt_text, **_merge_prompt_kwargs(prompt_kwargs, kwargs))

    async def generate_json(self, prompt: Any, *, schema: type[Any], **kwargs: Any) -> Any | None:
        if self.provider is None:
            log.debug("AI JSON generation skipped: provider not initialized")
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
