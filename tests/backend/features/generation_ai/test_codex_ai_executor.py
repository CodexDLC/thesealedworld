from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from src.backend.features.generation_ai.integrations.codex_ai_executor import CodexAIExecutor


class FakeAssetRef:
    def __init__(self, *, storage_key: str, content_type: str) -> None:
        self.storage_key = storage_key
        self.content_type = content_type

    def to_task_result(self, *, output_payload=None, metadata=None):
        return SimpleNamespace(
            output_payload=dict(output_payload or {}),
            storage_key=self.storage_key,
            generated_url=f"/assets/{self.storage_key}",
            content_type=self.content_type,
            metadata=dict(metadata or {}),
        )


class FakeAssetStorage:
    def __init__(self) -> None:
        self.put_bytes = AsyncMock(side_effect=self._put_bytes)

    async def _put_bytes(self, *, storage_key, content, content_type, metadata=None):
        return FakeAssetRef(storage_key=storage_key, content_type=content_type)


@pytest.mark.asyncio
async def test_generation_ai_image_uses_plain_prompt_and_normalizes_to_requested_webp() -> None:
    ai = SimpleNamespace(generate_image_bytes=AsyncMock(return_value=(_tiny_png(), "image/png")))
    storage = FakeAssetStorage()
    executor = CodexAIExecutor(ai, asset_storage=storage)
    task = SimpleNamespace(
        task_type="monster.clan_image",
        entity_type="monster_clan",
        entity_id="clan-1",
        output_kind="image",
    )

    result = await executor.generate(
        task,
        {
            "kind": "image",
            "prompt": "Create monster image",
            "model": "gemini-2.5-flash-image",
            "content_type": "image/webp",
            "storage_key": "monsters/generated/clans/hash.webp",
        },
    )

    ai.generate_image_bytes.assert_awaited_once_with(
        prompt="Create monster image",
        model="gemini-2.5-flash-image",
        response_mime_type="image/webp",
    )
    storage.put_bytes.assert_awaited_once()
    assert storage.put_bytes.await_args.kwargs["content"].startswith(b"RIFF")
    assert storage.put_bytes.await_args.kwargs["content_type"] == "image/webp"
    assert storage.put_bytes.await_args.kwargs["metadata"]["provider_content_type"] == "image/png"
    assert storage.put_bytes.await_args.kwargs["metadata"]["image_normalized"] is True
    assert result.storage_key == "monsters/generated/clans/hash.webp"
    assert result.content_type == "image/webp"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "nano-banana-gemini-2.5-flash-preview-image",
        "imagen-3.0-generate-002",
    ],
)
async def test_generation_ai_image_rejects_unsupported_image_models(model: str) -> None:
    ai = SimpleNamespace(generate_image_bytes=AsyncMock(return_value=(b"png-bytes", "image/png")))
    executor = CodexAIExecutor(ai, asset_storage=FakeAssetStorage())
    task = SimpleNamespace(
        task_type="monster.clan_image",
        entity_type="monster_clan",
        entity_id="clan-1",
        output_kind="image",
    )

    with pytest.raises(RuntimeError):
        await executor.generate(
            task,
            {
                "kind": "image",
                "prompt": "Create monster image",
                "model": model,
                "content_type": "image/webp",
                "storage_key": "monsters/generated/clans/hash.webp",
            },
        )

    ai.generate_image_bytes.assert_not_awaited()


def _tiny_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), color=(120, 20, 10)).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_generation_ai_image_rejects_message_bundle_prompt() -> None:
    ai = SimpleNamespace(generate_image_bytes=AsyncMock(return_value=(b"png-bytes", "image/png")))
    executor = CodexAIExecutor(ai, asset_storage=FakeAssetStorage())
    task = SimpleNamespace(
        task_type="monster.clan_image",
        entity_type="monster_clan",
        entity_id="clan-1",
        output_kind="image",
    )

    with pytest.raises(RuntimeError, match="plain non-empty string prompt"):
        await executor.generate(
            task,
            {
                "kind": "image",
                "prompt": {"messages": [{"role": "system", "content": "bad"}]},
                "model": "gemini-2.5-flash-image",
                "content_type": "image/webp",
                "storage_key": "monsters/generated/clans/hash.webp",
            },
        )

    ai.generate_image_bytes.assert_not_awaited()
