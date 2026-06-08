from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.frontend.integrations.generated_assets import (
    GeneratedAssetObject,
    LocalGeneratedAssetReader,
    S3GeneratedAssetReader,
    build_generated_asset_response,
    configure_generated_asset_serving,
    normalize_generated_asset_storage_key,
)


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, object]] = {}
        self.meta = SimpleNamespace(endpoint_url="https://assets.example")

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:  # noqa: N803
        obj = self.objects.get((Bucket, Key))
        if obj is None:
            exc = RuntimeError("missing")
            exc.response = {"Error": {"Code": "NoSuchKey"}}  # type: ignore[attr-defined]
            raise exc
        return obj

    def generate_presigned_url(self, ClientMethod: str, Params: dict[str, str], ExpiresIn: int) -> str:  # noqa: N803
        return f"https://assets.example/{Params['Key']}?ttl={ExpiresIn}&method={ClientMethod}"


class FakeGeneratedAssetReader:
    def __init__(self, objects: dict[str, GeneratedAssetObject]) -> None:
        self.objects = objects

    async def get_object(self, storage_key: str) -> GeneratedAssetObject | None:
        return self.objects.get(storage_key)


@pytest.mark.asyncio
async def test_s3_generated_asset_reader_returns_presigned_redirect_object() -> None:
    client = FakeS3Client()
    client.objects[("assets", "monsters/generated/rat.webp")] = {
        "ContentType": "image/webp",
    }
    reader = S3GeneratedAssetReader(bucket="assets", client=client)

    asset = await reader.get_object("monsters/generated/rat.webp")

    assert asset is not None
    assert asset.content == b""
    assert asset.content_type == "image/webp"
    assert asset.redirect_url == "https://assets.example/assets/monsters/generated/rat.webp"


@pytest.mark.asyncio
async def test_s3_generated_asset_reader_returns_none_for_missing_object() -> None:
    reader = S3GeneratedAssetReader(bucket="assets", client=FakeS3Client())

    assert await reader.get_object("missing.webp") is None


@pytest.mark.asyncio
async def test_local_generated_asset_reader_returns_mirrored_object(tmp_path) -> None:
    asset_path = tmp_path / "monsters" / "rat.webp"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"local-image")
    reader = LocalGeneratedAssetReader(root=tmp_path)

    asset = await reader.get_object("monsters/rat.webp")

    assert asset is not None
    assert asset.content == b"local-image"
    assert asset.content_type == "image/webp"


def test_generated_asset_key_normalization_rejects_unsafe_paths() -> None:
    assert normalize_generated_asset_storage_key(" monsters//rat.webp ") == "monsters/rat.webp"

    for key in ("", "/absolute.webp", "../secret", "monsters/../secret", "monsters\\..\\secret"):
        with pytest.raises(ValueError):
            normalize_generated_asset_storage_key(key)


def test_build_generated_asset_response_sets_cache_headers() -> None:
    response = build_generated_asset_response(content=b"asset", content_type="image/webp")

    assert response.body == b"asset"
    assert response.media_type == "image/webp"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_build_generated_asset_response_can_redirect_to_presigned_url() -> None:
    response = build_generated_asset_response(
        content_type="image/webp",
        redirect_url="https://assets.example/monsters/rat.webp?signature=1",
    )

    assert response.status_code == 301
    assert response.headers["location"] == "https://assets.example/monsters/rat.webp?signature=1"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_configure_generated_asset_serving_routes_s3_public_contract() -> None:
    app = FastAPI()
    reader = FakeGeneratedAssetReader(
        {
            "monsters/rat.webp": GeneratedAssetObject(
                content=b"rat-image",
                content_type="image/webp",
            )
        }
    )
    configure_generated_asset_serving(
        app,
        config=SimpleNamespace(asset_storage_backend="s3"),
        reader_provider=lambda: reader,
    )

    response = TestClient(app).get("/static/generated-assets/monsters/rat.webp")

    assert response.status_code == 200
    assert response.content == b"rat-image"
    assert response.headers["content-type"] == "image/webp"


def test_configure_generated_asset_serving_falls_back_to_local_mirror_for_missing_s3_asset(tmp_path) -> None:
    app = FastAPI()
    asset_path = tmp_path / "monsters" / "rat.webp"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"local-rat-image")
    configure_generated_asset_serving(
        app,
        config=SimpleNamespace(asset_storage_backend="s3", generated_assets_dir=tmp_path),
        reader_provider=lambda: FakeGeneratedAssetReader({}),
    )

    response = TestClient(app).get("/static/generated-assets/monsters/rat.webp")

    assert response.status_code == 200
    assert response.content == b"local-rat-image"
    assert response.headers["content-type"] == "image/webp"


def test_configure_generated_asset_serving_returns_404_for_missing_s3_asset() -> None:
    app = FastAPI()
    configure_generated_asset_serving(
        app,
        config=SimpleNamespace(asset_storage_backend="s3"),
        reader_provider=lambda: FakeGeneratedAssetReader({}),
    )

    response = TestClient(app).get("/static/generated-assets/missing.webp")

    assert response.status_code == 404
