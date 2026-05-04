from unittest.mock import AsyncMock

import pytest
from codex_ai.core.exceptions import LLMProviderError
from codex_ai.core.protocol import PromptResult

from src.backend.core.ai import FilteringGeminiProvider


@pytest.mark.unit
async def test_filtering_gemini_provider_drops_prompt_builder_payload_kwargs(mocker):
    provider = FilteringGeminiProvider(api_key="test-key", model="gemini-2.5-flash")
    answer = mocker.patch.object(FilteringGeminiProvider.__mro__[1], "answer", new=AsyncMock(return_value="{}"))

    prompt = object()
    result = await provider.answer(prompt, payload_items=[{"id": "45_45"}], max_tokens=16000, temperature=0.7)

    assert result == "{}"
    answer.assert_awaited_once_with(prompt, max_tokens=16000, temperature=0.7)


@pytest.mark.unit
async def test_filtering_gemini_provider_moves_system_messages_to_system_instruction():
    prompt = PromptResult(
        messages=[
            {"role": "system", "content": "System rules"},
            {"role": "user", "content": "User payload"},
        ]
    )

    normalized = FilteringGeminiProvider._normalize_prompt(prompt)

    assert isinstance(normalized, PromptResult)
    assert normalized.system == "System rules"
    assert len(normalized.messages) == 1
    assert normalized.messages[0].role == "user"
    assert normalized.messages[0].content == "User payload"


@pytest.mark.unit
async def test_filtering_gemini_provider_tries_fallback_model(mocker):
    provider = FilteringGeminiProvider(
        api_key="test-key",
        model="gemini-2.5-flash",
        fallback_models=["gemini-2.5-pro"],
    )
    answer = mocker.patch.object(
        FilteringGeminiProvider.__mro__[1],
        "answer",
        new=AsyncMock(side_effect=[LLMProviderError("503 unavailable"), "{}"]),
    )

    prompt = object()
    result = await provider.answer(prompt, max_tokens=16000)

    assert result == "{}"
    assert answer.await_count == 2
    assert answer.await_args_list[0].kwargs == {"max_tokens": 16000}
    assert answer.await_args_list[1].kwargs == {"max_tokens": 16000, "model": "gemini-2.5-pro"}
