from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import quote

from src.backend.config.settings import BackendSettings, settings
from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO


@dataclass(frozen=True, slots=True)
class GeneratedAssetRef:
    storage_backend: Literal["local", "s3"]
    storage_key: str
    public_url: str
    asset_hash: str
    content_type: str
    size_bytes: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_task_result(
        self,
        *,
        output_payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AIGenerationTaskResultDTO:
        return AIGenerationTaskResultDTO(
            output_payload=dict(output_payload or {}),
            storage_key=self.storage_key,
            generated_url=self.public_url,
            asset_hash=self.asset_hash,
            storage_backend=self.storage_backend,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            metadata={**self.metadata, **dict(metadata or {})},
        )


class GeneratedAssetStorage(Protocol):
    async def put_bytes(
        self,
        *,
        storage_key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> GeneratedAssetRef:
        """Persist generated binary content and return its stable external reference."""


class LocalGeneratedAssetStorage:
    storage_backend: Literal["local"] = "local"

    def __init__(self, *, root: str | Path, public_base_url: str) -> None:
        self.root = Path(root).resolve()
        self.public_base_url = public_base_url.rstrip("/")

    async def put_bytes(
        self,
        *,
        storage_key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> GeneratedAssetRef:
        safe_key = normalize_asset_storage_key(storage_key)
        safe_key = storage_key_with_content_type_extension(safe_key, content_type)
        target = (self.root / safe_key).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"Asset storage key escapes root: {storage_key!r}")

        target.parent.mkdir(parents=True, exist_ok=True)
        temp_target = target.with_name(f".{target.name}.tmp")
        temp_target.write_bytes(content)
        temp_target.replace(target)

        digest = sha256(content).hexdigest()
        return GeneratedAssetRef(
            storage_backend=self.storage_backend,
            storage_key=safe_key,
            public_url=build_asset_public_url(self.public_base_url, safe_key),
            asset_hash=digest,
            content_type=content_type,
            size_bytes=len(content),
            metadata=dict(metadata or {}),
        )


class S3GeneratedAssetStorage:
    storage_backend: Literal["s3"] = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        public_base_url: str,
        client: Any,
    ) -> None:
        self.bucket = bucket
        self.public_base_url = public_base_url.rstrip("/")
        self.client = client

    async def put_bytes(
        self,
        *,
        storage_key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> GeneratedAssetRef:
        safe_key = normalize_asset_storage_key(storage_key)
        safe_key = storage_key_with_content_type_extension(safe_key, content_type)
        digest = sha256(content).hexdigest()
        object_metadata = {str(key): str(value) for key, value in dict(metadata or {}).items()}

        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=safe_key,
            Body=content,
            ContentType=content_type,
            Metadata=object_metadata,
        )
        return GeneratedAssetRef(
            storage_backend=self.storage_backend,
            storage_key=safe_key,
            public_url=build_asset_public_url(self.public_base_url, safe_key),
            asset_hash=digest,
            content_type=content_type,
            size_bytes=len(content),
            metadata=dict(metadata or {}),
        )

    async def exists(self, storage_key: str) -> bool:
        safe_key = normalize_asset_storage_key(storage_key)
        try:
            await asyncio.to_thread(self.client.head_object, Bucket=self.bucket, Key=safe_key)
        except Exception as exc:
            response = getattr(exc, "response", None)
            error = response.get("Error", {}) if isinstance(response, dict) else {}
            error_code = str(error.get("Code", ""))
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return False
            if exc.__class__.__name__ in {"NoSuchKey", "NotFound"}:
                return False
            raise
        return True


def build_generated_asset_storage(config: BackendSettings = settings) -> GeneratedAssetStorage:
    if config.asset_storage_backend == "local":
        return LocalGeneratedAssetStorage(
            root=config.asset_local_root,
            public_base_url=config.asset_public_base_url,
        )
    if config.asset_storage_backend == "s3":
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
            raise RuntimeError(f"S3 generated asset storage is missing required config: {', '.join(missing)}")
        return S3GeneratedAssetStorage(
            bucket=str(config.asset_s3_bucket),
            public_base_url=config.asset_public_base_url,
            client=build_s3_client(config),
        )
    raise RuntimeError(f"Unsupported generated asset storage backend: {config.asset_storage_backend!r}")


def build_s3_client(config: BackendSettings = settings) -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - covered by deployment smoke once dependency is installed
        raise RuntimeError("S3 generated asset storage requires the boto3 dependency") from exc

    return boto3.client(
        "s3",
        region_name=config.asset_s3_region,
        endpoint_url=config.asset_s3_endpoint_url,
        aws_access_key_id=config.asset_s3_access_key_id,
        aws_secret_access_key=config.asset_s3_secret_access_key,
    )


def normalize_asset_storage_key(storage_key: str) -> str:
    normalized = storage_key.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("Asset storage key must not be empty")
    if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized or normalized.endswith("/.."):
        raise ValueError(f"Unsafe asset storage key: {storage_key!r}")

    parts = [part for part in normalized.split("/") if part and part != "."]
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"Unsafe asset storage key: {storage_key!r}")
    return "/".join(parts)


def storage_key_with_content_type_extension(storage_key: str, content_type: str) -> str:
    extension = _extension_for_content_type(content_type)
    if extension is None:
        return storage_key
    path = Path(storage_key)
    return path.with_suffix(extension).as_posix()


def build_asset_public_url(public_base_url: str, storage_key: str) -> str:
    safe_key = normalize_asset_storage_key(storage_key)
    base = public_base_url.rstrip("/")
    encoded_key = "/".join(quote(part) for part in safe_key.split("/"))
    return f"{base}/{encoded_key}"


def _extension_for_content_type(content_type: str) -> str | None:
    normalized = content_type.split(";", 1)[0].strip().lower()
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(normalized)
