from __future__ import annotations

import asyncio
import mimetypes
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.staticfiles import StaticFiles

from src.frontend.config.settings import FrontendSettings, settings


@dataclass(frozen=True, slots=True)
class GeneratedAssetObject:
    content: bytes
    content_type: str


class S3ObjectClient(Protocol):
    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]: ...  # noqa: N803


class GeneratedAssetReader(Protocol):
    async def get_object(self, storage_key: str) -> GeneratedAssetObject | None: ...


class S3GeneratedAssetReader:
    def __init__(self, *, bucket: str, client: S3ObjectClient) -> None:
        self.bucket = bucket
        self.client = client

    async def get_object(self, storage_key: str) -> GeneratedAssetObject | None:
        safe_key = normalize_generated_asset_storage_key(storage_key)
        try:
            response = await asyncio.to_thread(self.client.get_object, Bucket=self.bucket, Key=safe_key)
        except Exception as exc:
            if _is_missing_s3_object(exc):
                return None
            raise

        body = response.get("Body")
        read = getattr(body, "read", None)
        if callable(read):
            content = await asyncio.to_thread(read)
        else:
            content = bytes(body or b"")
        content_type = str(response.get("ContentType") or "application/octet-stream")
        return GeneratedAssetObject(content=content, content_type=content_type)


class LocalGeneratedAssetReader:
    def __init__(self, *, root: Path) -> None:
        self.root = root

    async def get_object(self, storage_key: str) -> GeneratedAssetObject | None:
        safe_key = normalize_generated_asset_storage_key(storage_key)
        path = self.root.joinpath(*safe_key.split("/"))
        try:
            resolved = path.resolve(strict=True)
            root = self.root.resolve(strict=True)
        except FileNotFoundError:
            return None
        if root not in resolved.parents and resolved != root:
            raise ValueError(f"Unsafe generated asset key: {storage_key!r}")

        content = await asyncio.to_thread(resolved.read_bytes)
        content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        return GeneratedAssetObject(content=content, content_type=content_type)


def build_s3_generated_asset_reader(config: FrontendSettings = settings) -> S3GeneratedAssetReader:
    missing = [
        name
        for name, value in {
            "ASSET_S3_BUCKET": config.asset_s3_bucket,
            "ASSET_S3_REGION": config.asset_s3_region,
            "ASSET_S3_ENDPOINT_URL": config.asset_s3_endpoint_url,
            "ASSET_S3_ACCESS_KEY_ID": config.asset_s3_access_key_id,
            "ASSET_S3_SECRET_ACCESS_KEY": config.asset_s3_secret_access_key,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"S3 generated asset serving is missing required config: {', '.join(missing)}")

    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - covered by deployment smoke once dependency is installed
        raise RuntimeError("S3 generated asset serving requires the boto3 dependency") from exc

    return S3GeneratedAssetReader(
        bucket=str(config.asset_s3_bucket),
        client=boto3.client(
            "s3",
            region_name=config.asset_s3_region,
            endpoint_url=config.asset_s3_endpoint_url,
            aws_access_key_id=config.asset_s3_access_key_id,
            aws_secret_access_key=config.asset_s3_secret_access_key,
        ),
    )


def normalize_generated_asset_storage_key(storage_key: str) -> str:
    normalized = storage_key.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("Generated asset key must not be empty")
    if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized or normalized.endswith("/.."):
        raise ValueError(f"Unsafe generated asset key: {storage_key!r}")

    parts = [part for part in normalized.split("/") if part and part != "."]
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"Unsafe generated asset key: {storage_key!r}")
    return "/".join(parts)


def build_generated_asset_response(*, content: bytes, content_type: str) -> Response:
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


def configure_generated_asset_serving(
    app: FastAPI,
    *,
    config: FrontendSettings = settings,
    reader_provider: Callable[[], GeneratedAssetReader] | None = None,
) -> None:
    if config.asset_storage_backend == "local":
        generated_assets_dir = Path(config.generated_assets_dir)
        generated_assets_dir.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/static/generated-assets",
            StaticFiles(directory=str(generated_assets_dir)),
            name="generated_assets",
        )
        return

    if config.asset_storage_backend == "s3":
        cached_reader: GeneratedAssetReader | None = None
        local_reader = _build_optional_local_generated_asset_reader(config)

        def get_reader() -> GeneratedAssetReader:
            nonlocal cached_reader
            if reader_provider is not None:
                return reader_provider()
            if cached_reader is None:
                cached_reader = build_s3_generated_asset_reader(config)
            return cached_reader

        @app.get("/static/generated-assets/{storage_key:path}", include_in_schema=False)
        async def s3_generated_asset(storage_key: str) -> Response:
            reader = get_reader()
            try:
                asset = await reader.get_object(storage_key)
                if asset is None and local_reader is not None:
                    asset = await local_reader.get_object(storage_key)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated asset not found") from exc
            if asset is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated asset not found")
            return build_generated_asset_response(content=asset.content, content_type=asset.content_type)

        return

    raise RuntimeError(f"Unsupported generated asset storage backend: {config.asset_storage_backend!r}")


def _build_optional_local_generated_asset_reader(config: Any) -> LocalGeneratedAssetReader | None:
    generated_assets_dir = getattr(config, "generated_assets_dir", None)
    if generated_assets_dir is None:
        return None
    root = Path(generated_assets_dir)
    if not root.exists():
        return None
    return LocalGeneratedAssetReader(root=root)


def _is_missing_s3_object(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    error = response.get("Error", {}) if isinstance(response, dict) else {}
    error_code = str(error.get("Code", ""))
    return error_code in {"404", "NoSuchKey", "NotFound"} or exc.__class__.__name__ in {"NoSuchKey", "NotFound"}
