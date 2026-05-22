from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from src.backend.features.generation_ai.image_prompt_contract import NO_TEXT_IMAGE_CONTRACT
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


def _ai_with_image_result(
    image_result: tuple[bytes, str],
    *,
    visible_text: bool = False,
):
    return SimpleNamespace(
        generate_image_bytes=AsyncMock(return_value=image_result),
        validate_generated_image_no_text=AsyncMock(
            return_value=SimpleNamespace(
                visible_text=visible_text,
                confidence=0.99 if visible_text else 0.01,
                reason="visible labels" if visible_text else "no visible text",
                detected_text="label" if visible_text else "",
            )
        ),
    )


@pytest.mark.asyncio
async def test_generation_ai_image_uses_plain_prompt_and_normalizes_to_requested_webp() -> None:
    ai = _ai_with_image_result((_tiny_png(), "image/png"))
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

    provider_prompt = ai.generate_image_bytes.await_args.kwargs["prompt"]
    assert provider_prompt.startswith("Create monster image")
    assert NO_TEXT_IMAGE_CONTRACT in provider_prompt
    ai.generate_image_bytes.assert_awaited_once_with(
        prompt=provider_prompt,
        model="gemini-2.5-flash-image",
        response_mime_type="image/webp",
    )
    storage.put_bytes.assert_awaited_once()
    ai.validate_generated_image_no_text.assert_awaited_once()
    assert storage.put_bytes.await_args.kwargs["content"].startswith(b"RIFF")
    assert storage.put_bytes.await_args.kwargs["content_type"] == "image/webp"
    assert storage.put_bytes.await_args.kwargs["metadata"]["provider_content_type"] == "image/png"
    assert storage.put_bytes.await_args.kwargs["metadata"]["image_normalized"] is True
    assert result.storage_key == "monsters/generated/clans/hash.webp"
    assert result.content_type == "image/webp"
    assert result.output_payload["prompt"] == provider_prompt


@pytest.mark.asyncio
async def test_generation_ai_image_does_not_duplicate_no_text_contract() -> None:
    ai = _ai_with_image_result((_tiny_png(), "image/png"))
    executor = CodexAIExecutor(ai, asset_storage=FakeAssetStorage())
    task = SimpleNamespace(
        task_type="monster.clan_image",
        entity_type="monster_clan",
        entity_id="clan-1",
        output_kind="image",
    )

    await executor.generate(
        task,
        {
            "kind": "image",
            "prompt": f"Create monster image\n\n{NO_TEXT_IMAGE_CONTRACT}",
            "model": "gemini-2.5-flash-image",
            "content_type": "image/webp",
            "storage_key": "monsters/generated/clans/hash.webp",
        },
    )

    provider_prompt = ai.generate_image_bytes.await_args.kwargs["prompt"]
    assert provider_prompt.count(NO_TEXT_IMAGE_CONTRACT) == 1


@pytest.mark.asyncio
async def test_generation_ai_image_rejects_visible_text_before_upload() -> None:
    ai = _ai_with_image_result((_tiny_png(), "image/png"), visible_text=True)
    storage = FakeAssetStorage()
    executor = CodexAIExecutor(ai, asset_storage=storage)
    task = SimpleNamespace(
        task_type="monster.clan_image",
        entity_type="monster_clan",
        entity_id="clan-1",
        output_kind="image",
    )

    with pytest.raises(RuntimeError, match="visible text"):
        await executor.generate(
            task,
            {
                "kind": "image",
                "prompt": "Create monster image",
                "model": "gemini-2.5-flash-image",
                "content_type": "image/webp",
                "storage_key": "monsters/generated/clans/hash.webp",
            },
        )

    ai.validate_generated_image_no_text.assert_awaited_once()
    storage.put_bytes.assert_not_awaited()


@pytest.mark.asyncio
async def test_generation_ai_image_can_force_target_size() -> None:
    ai = _ai_with_image_result((_wide_png(), "image/png"))
    storage = FakeAssetStorage()
    executor = CodexAIExecutor(ai, asset_storage=storage)
    task = SimpleNamespace(
        task_type="world.location_image",
        entity_type="world_location",
        entity_id="52_52",
        output_kind="image",
    )

    await executor.generate(
        task,
        {
            "kind": "image",
            "prompt": "Create location background",
            "model": "gemini-2.5-flash-image",
            "content_type": "image/webp",
            "storage_key": "world/locations/d4/52_52_hash.webp",
            "target_size": {"width": 1536, "height": 864},
        },
    )

    metadata = storage.put_bytes.await_args.kwargs["metadata"]
    assert metadata["width"] == 1536
    assert metadata["height"] == 864
    assert metadata["target_width"] == 1536
    assert metadata["target_height"] == 864
    assert metadata["source_width"] == 400
    assert metadata["source_height"] == 400


@pytest.mark.asyncio
async def test_generation_ai_image_forwards_provider_kwargs() -> None:
    ai = _ai_with_image_result((_tiny_png(), "image/png"))
    storage = FakeAssetStorage()
    executor = CodexAIExecutor(ai, asset_storage=storage)
    task = SimpleNamespace(
        task_type="world.region_map_image",
        entity_type="world_region",
        entity_id="D4",
        output_kind="image",
    )

    await executor.generate(
        task,
        {
            "kind": "image",
            "prompt": "Create square region map",
            "model": "gemini-3-pro-image-preview",
            "content_type": "image/png",
            "storage_key": "world/maps/d4/master.png",
            "kwargs": {
                "image_config": {
                    "aspect_ratio": "1:1",
                    "image_size": "4K",
                }
            },
        },
    )

    provider_prompt = ai.generate_image_bytes.await_args.kwargs["prompt"]
    assert provider_prompt.startswith("Create square region map")
    assert NO_TEXT_IMAGE_CONTRACT in provider_prompt
    ai.generate_image_bytes.assert_awaited_once_with(
        prompt=provider_prompt,
        model="gemini-3-pro-image-preview",
        response_mime_type="image/png",
        image_config={
            "aspect_ratio": "1:1",
            "image_size": "4K",
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "nano-banana-gemini-2.5-flash-preview-image",
        "imagen-3.0-generate-002",
    ],
)
async def test_generation_ai_image_rejects_unsupported_image_models(model: str) -> None:
    ai = _ai_with_image_result((b"png-bytes", "image/png"))
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


def _wide_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (400, 400), color=(20, 90, 120)).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_generation_ai_image_rejects_message_bundle_prompt() -> None:
    ai = _ai_with_image_result((b"png-bytes", "image/png"))
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
