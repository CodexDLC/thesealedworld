import logging
from typing import Any

from codex_ai.core import LLMDispatcher
from codex_ai.core.protocol import PromptResult
from codex_ai.providers import GeminiProvider

from src.backend.config.settings import settings

log = logging.getLogger(__name__)

GEMINI_PROVIDER_KWARGS = {
    "model",
    "temperature",
    "max_tokens",
    "top_p",
    "top_k",
    "candidate_count",
    "stop_sequences",
    "response_mime_type",
    "response_schema",
    "seed",
}


class FilteringGeminiProvider(GeminiProvider):
    """Gemini provider that does not pass prompt-builder payload kwargs into GenerateContentConfig."""

    def __init__(self, api_key: str, model: str, fallback_models: list[str] | None = None) -> None:
        super().__init__(api_key=api_key, model=model)
        self._fallback_models = fallback_models or []

    async def answer(self, prompt: Any, **kw: Any) -> str:
        provider_kw = {key: value for key, value in kw.items() if key in GEMINI_PROVIDER_KWARGS}
        normalized_prompt = self._normalize_prompt(prompt)
        try:
            return await super().answer(normalized_prompt, **provider_kw)
        except Exception as exc:
            if provider_kw.get("model"):
                raise
            if _is_rate_limit_error(exc):
                raise

            last_error = exc
            for fallback_model in self._fallback_models:
                try:
                    log.warning("Gemini primary model failed; trying fallback model=%s error=%s", fallback_model, exc)
                    return await super().answer(normalized_prompt, **{**provider_kw, "model": fallback_model})
                except Exception as fallback_exc:
                    last_error = fallback_exc

            raise last_error from exc

    @staticmethod
    def _normalize_prompt(prompt: Any) -> Any:
        if not isinstance(prompt, PromptResult):
            return prompt

        system_parts = [prompt.system] if prompt.system else []
        messages = []
        for message in prompt.messages:
            if message.role == "system":
                system_parts.append(message.content)
            else:
                messages.append(message)

        if len(messages) == len(prompt.messages) and not system_parts:
            return prompt

        return PromptResult(
            messages=messages,
            system="\n\n".join(system_parts),
            model=prompt.model,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "RATE_LIMIT" in text


class AIService:
    """Centralized service for AI operations across the application."""

    def __init__(self) -> None:
        self.dispatcher: LLMDispatcher | None = None

        if settings.gemini_api_key:
            log.info("Initializing AIService with GeminiProvider")
            provider = FilteringGeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                fallback_models=settings.gemini_fallback_models,
            )
            self.dispatcher = LLMDispatcher(provider=provider)
        else:
            log.warning("Gemini API key not found. AIService will be disabled.")

    def include_router(self, router: Any) -> None:
        """Registers a prompt router (e.g., for world, monsters, items)."""
        if self.dispatcher:
            # We assume routers can be safely re-included or the library handles it
            self.dispatcher.include_router(router)

    async def process(self, prompt_name: str, **kwargs: Any) -> Any:
        """Sends a request to the configured LLM provider."""
        if not self.dispatcher:
            log.debug("AI generation skipped for '%s': dispatcher not initialized", prompt_name)
            return None

        return await self.dispatcher.process(prompt_name, **kwargs)
