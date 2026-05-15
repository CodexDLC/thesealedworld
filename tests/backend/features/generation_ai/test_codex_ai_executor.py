from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

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
async def test_generation_ai_image_uses_plain_prompt_and_actual_content_type() -> None:
    ai = SimpleNamespace(generate_image_bytes=AsyncMock(return_value=(b"png-bytes", "image/png")))
    storage = FakeAssetStorage()
    executor = CodexAIExecutor(ai, asset_storage=storage)
    task = SimpleNamespace(task_type="monster.clan_image", entity_type="monster_clan", entity_id="clan-1")

    result = await executor.generate(
        task,
        {
            "kind": "image",
            "prompt": "Create monster image",
            "model": "nano-banana-gemini-2.5-flash-preview-image",
            "content_type": "image/webp",
            "storage_key": "monsters/generated/clans/hash.webp",
        },
    )

    ai.generate_image_bytes.assert_awaited_once_with(
        prompt="Create monster image",
        model="nano-banana-gemini-2.5-flash-preview-image",
        response_mime_type="image/webp",
    )
    storage.put_bytes.assert_awaited_once()
    assert storage.put_bytes.await_args.kwargs["content"] == b"png-bytes"
    assert storage.put_bytes.await_args.kwargs["content_type"] == "image/png"
    assert result.storage_key == "monsters/generated/clans/hash.webp"
    assert result.content_type == "image/png"
