from __future__ import annotations

from hashlib import sha256

import pytest

from src.backend.features.generation_ai.asset_storage import (
    LocalGeneratedAssetStorage,
    build_asset_public_url,
    normalize_asset_storage_key,
    storage_key_with_content_type_extension,
)


@pytest.mark.asyncio
async def test_local_asset_storage_writes_content_and_returns_contract(tmp_path) -> None:
    storage = LocalGeneratedAssetStorage(root=tmp_path, public_base_url="/static/generated-assets")
    content = b"generated image bytes"

    ref = await storage.put_bytes(
        storage_key="monsters/families/rat_pack/default.png",
        content=content,
        content_type="image/png",
        metadata={"family_id": "rat_pack"},
    )

    assert (tmp_path / "monsters/families/rat_pack/default.png").read_bytes() == content
    assert ref.storage_backend == "local"
    assert ref.storage_key == "monsters/families/rat_pack/default.png"
    assert ref.public_url == "/static/generated-assets/monsters/families/rat_pack/default.png"
    assert ref.asset_hash == sha256(content).hexdigest()
    assert ref.content_type == "image/png"
    assert ref.size_bytes == len(content)
    assert ref.metadata == {"family_id": "rat_pack"}

    task_result = ref.to_task_result(output_payload={"kind": "family_fallback"}, metadata={"variant": "default"})
    assert task_result.storage_key == ref.storage_key
    assert task_result.generated_url == ref.public_url
    assert task_result.asset_hash == ref.asset_hash
    assert task_result.storage_backend == "local"
    assert task_result.content_type == "image/png"
    assert task_result.size_bytes == len(content)
    assert task_result.output_payload == {"kind": "family_fallback"}
    assert task_result.metadata == {"family_id": "rat_pack", "variant": "default"}


def test_asset_storage_key_normalization_rejects_unsafe_paths() -> None:
    assert normalize_asset_storage_key(" monsters//families/rat.png ") == "monsters/families/rat.png"

    for key in ("", "/absolute/path.png", "../escape.png", "safe/../escape.png", "safe/.."):
        with pytest.raises(ValueError):
            normalize_asset_storage_key(key)


def test_asset_public_url_encodes_path_segments() -> None:
    assert (
        build_asset_public_url("/static/generated-assets/", "monsters/rat king/default image.png")
        == "/static/generated-assets/monsters/rat%20king/default%20image.png"
    )


def test_storage_key_extension_tracks_actual_image_content_type() -> None:
    assert storage_key_with_content_type_extension("monsters/generated/clans/hash.webp", "image/png") == (
        "monsters/generated/clans/hash.png"
    )
    assert storage_key_with_content_type_extension("monsters/generated/clans/hash.webp", "image/jpeg") == (
        "monsters/generated/clans/hash.jpg"
    )
    assert storage_key_with_content_type_extension("monsters/generated/clans/hash.webp", "image/webp") == (
        "monsters/generated/clans/hash.webp"
    )
