from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from codex_ai.core import PromptResult

from src.backend.core.ai import AIService


@pytest.mark.unit
async def test_ai_service_initializes_direct_gemini_provider(monkeypatch):
    monkeypatch.setattr("src.backend.core.ai.settings.gemini_api_key", "test-key")  # pragma: allowlist secret
    monkeypatch.setattr("src.backend.core.ai.settings.gemini_model", "gemini-2.5-flash")
    monkeypatch.setattr("src.backend.core.ai.settings.gemini_image_model", "gemini-3.1-flash-image-preview")

    with patch("src.backend.core.ai.GeminiProvider") as provider_cls:
        provider = MagicMock()
        provider_cls.return_value = provider

        service = AIService()

    provider_cls.assert_called_once_with(
        api_key="test-key",
        model="gemini-2.5-flash",
        image_model="gemini-3.1-flash-image-preview",
    )
    assert service.provider is provider


@pytest.mark.unit
async def test_ai_service_generate_text_delegates_to_provider(monkeypatch):
    monkeypatch.setattr("src.backend.core.ai.settings.gemini_api_key", "test-key")  # pragma: allowlist secret
    with patch("src.backend.core.ai.GeminiProvider") as provider_cls:
        provider = MagicMock()
        provider.generate_text = AsyncMock(return_value="text")
        provider_cls.return_value = provider
        service = AIService()

        result = await service.generate_text("prompt", temperature=0.2)

    assert result == "text"
    provider.generate_text.assert_awaited_once_with("prompt", temperature=0.2)


@pytest.mark.unit
async def test_ai_service_generate_text_flattens_prompt_result(monkeypatch):
    monkeypatch.setattr("src.backend.core.ai.settings.gemini_api_key", "test-key")  # pragma: allowlist secret
    with patch("src.backend.core.ai.GeminiProvider") as provider_cls:
        provider = MagicMock()
        provider.generate_text = AsyncMock(return_value="text")
        provider_cls.return_value = provider
        service = AIService()

        result = await service.generate_text(
            PromptResult(
                messages=[
                    {"role": "system", "content": "System rules"},
                    {"role": "user", "content": "Payload"},
                ],
                temperature=0.7,
                max_tokens=8000,
            )
        )

    assert result == "text"
    provider.generate_text.assert_awaited_once_with(
        "System:\nSystem rules\n\nUser:\nPayload",
        temperature=0.7,
        max_tokens=8000,
    )


@pytest.mark.unit
async def test_ai_service_generate_json_delegates_to_provider(monkeypatch):
    class DTO:
        pass

    monkeypatch.setattr("src.backend.core.ai.settings.gemini_api_key", "test-key")  # pragma: allowlist secret
    with patch("src.backend.core.ai.GeminiProvider") as provider_cls:
        provider = MagicMock()
        provider.generate_json = AsyncMock(return_value={"ok": True})
        provider_cls.return_value = provider
        service = AIService()

        result = await service.generate_json("prompt", schema=DTO)

    assert result == {"ok": True}
    provider.generate_json.assert_awaited_once_with("prompt", schema=DTO)


@pytest.mark.unit
async def test_ai_service_generate_json_flattens_prompt_result(monkeypatch):
    class DTO:
        pass

    monkeypatch.setattr("src.backend.core.ai.settings.gemini_api_key", "test-key")  # pragma: allowlist secret
    with patch("src.backend.core.ai.GeminiProvider") as provider_cls:
        provider = MagicMock()
        provider.generate_json = AsyncMock(return_value={"ok": True})
        provider_cls.return_value = provider
        service = AIService()

        result = await service.generate_json(
            PromptResult(
                messages=[
                    {"role": "system", "content": "Return JSON only"},
                    {"role": "user", "content": '{"id": "x"}'},
                ],
                temperature=0.3,
            ),
            schema=DTO,
            temperature=0.1,
        )

    assert result == {"ok": True}
    provider.generate_json.assert_awaited_once_with(
        'System:\nReturn JSON only\n\nUser:\n{"id": "x"}',
        schema=DTO,
        temperature=0.1,
    )


@pytest.mark.unit
async def test_ai_service_generate_image_bytes_delegates_to_provider(monkeypatch):
    monkeypatch.setattr("src.backend.core.ai.settings.gemini_api_key", "test-key")  # pragma: allowlist secret
    with patch("src.backend.core.ai.GeminiProvider") as provider_cls:
        provider = MagicMock()
        provider.generate_image_bytes = AsyncMock(return_value=(b"image", "image/webp"))
        provider_cls.return_value = provider
        service = AIService()

        result = await service.generate_image_bytes(
            "prompt",
            model="gemini-3.1-flash-image-preview",
            response_mime_type="image/webp",
        )

    assert result == (b"image", "image/webp")
    provider.generate_image_bytes.assert_awaited_once_with(
        "prompt",
        model="gemini-3.1-flash-image-preview",
        response_mime_type="image/webp",
    )
