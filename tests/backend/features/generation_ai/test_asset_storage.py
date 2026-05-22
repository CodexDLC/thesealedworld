from __future__ import annotations

from hashlib import sha256

import pytest

from src.backend.features.generation_ai.asset_storage import (
    LocalGeneratedAssetStorage,
    S3GeneratedAssetStorage,
    build_asset_public_url,
    build_generated_asset_storage,
    normalize_asset_storage_key,
    storage_key_with_content_type_extension,
)


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict] = {}
        self.head_failures: dict[tuple[str, str], Exception] = {}

    def put_object(self, **kwargs):
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs

    def head_object(self, **kwargs):
        key = (kwargs["Bucket"], kwargs["Key"])
        if key in self.head_failures:
            raise self.head_failures[key]
        return self.objects[key]


class FakeNotFoundError(Exception):
    response = {"Error": {"Code": "404"}}


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


@pytest.mark.asyncio
async def test_s3_asset_storage_puts_object_and_returns_public_contract() -> None:
    client = FakeS3Client()
    storage = S3GeneratedAssetStorage(
        bucket="generated-assets",
        public_base_url="/static/generated-assets",
        client=client,
    )
    content = b"image"

    ref = await storage.put_bytes(
        storage_key="news/covers/launch/raw-name.png",
        content=content,
        content_type="image/webp",
        metadata={"article": "launch"},
    )

    uploaded = client.objects[("generated-assets", "news/covers/launch/raw-name.webp")]
    assert uploaded["Body"] == content
    assert uploaded["ContentType"] == "image/webp"
    assert uploaded["Metadata"] == {"article": "launch"}
    assert ref.storage_backend == "s3"
    assert ref.storage_key == "news/covers/launch/raw-name.webp"
    assert ref.public_url == "/static/generated-assets/news/covers/launch/raw-name.webp"
    assert ref.asset_hash == sha256(content).hexdigest()


@pytest.mark.asyncio
async def test_s3_asset_storage_exists_uses_head_object() -> None:
    client = FakeS3Client()
    storage = S3GeneratedAssetStorage(bucket="bucket", public_base_url="/assets", client=client)
    await storage.put_bytes(
        storage_key="monsters/generated/clans/a.webp",
        content=b"image",
        content_type="image/webp",
    )
    client.head_failures[("bucket", "missing.webp")] = FakeNotFoundError()

    assert await storage.exists("monsters/generated/clans/a.webp") is True
    assert await storage.exists("missing.webp") is False


def test_s3_storage_config_fails_fast_when_required_values_are_missing() -> None:
    class Config:
        asset_storage_backend = "s3"
        asset_public_base_url = "/static/generated-assets"
        asset_s3_bucket = "bucket"
        asset_s3_region = None
        asset_s3_endpoint_url = "https://nbg1.your-objectstorage.com"
        asset_s3_access_key_id = "key"
        asset_s3_secret_access_key = "secret"  # pragma: allowlist secret

    with pytest.raises(RuntimeError, match="ASSET_S3_REGION"):
        build_generated_asset_storage(Config())  # type: ignore[arg-type]
