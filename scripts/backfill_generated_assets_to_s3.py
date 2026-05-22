from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.backend.config.settings import settings
from src.backend.features.generation_ai.asset_storage import (
    S3GeneratedAssetStorage,
    build_s3_client,
    normalize_asset_storage_key,
)


@dataclass(slots=True)
class BackfillReport:
    uploaded_count: int = 0
    skipped_count: int = 0
    failed_files: list[str] = field(default_factory=list)
    total_bytes: int = 0
    dry_run: bool = False


async def backfill_generated_assets(
    *,
    local_root: Path,
    storage: S3GeneratedAssetStorage,
    dry_run: bool = False,
    skip_existing: bool = True,
) -> BackfillReport:
    root = local_root.resolve()
    report = BackfillReport(dry_run=dry_run)
    for path in iter_generated_asset_files(root):
        storage_key = storage_key_for_file(root, path)
        size = path.stat().st_size
        report.total_bytes += size
        try:
            if skip_existing and not dry_run and await storage.exists(storage_key):
                report.skipped_count += 1
                continue
            if dry_run:
                report.skipped_count += 1
                continue
            await storage.put_bytes(
                storage_key=storage_key,
                content=path.read_bytes(),
                content_type=content_type_for_path(path),
                metadata={"backfill_source": "generated_assets"},
            )
            report.uploaded_count += 1
        except Exception:
            report.failed_files.append(str(path))
    return report


def iter_generated_asset_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def storage_key_for_file(root: Path, path: Path) -> str:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    return normalize_asset_storage_key(relative)


def content_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".webp": "image/webp",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
    }.get(suffix, "application/octet-stream")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill local generated assets into S3-compatible storage.")
    parser.add_argument("--local-root", default=settings.asset_local_root)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-skip-existing", action="store_true")
    return parser.parse_args()


async def async_main(args: argparse.Namespace | None = None) -> BackfillReport:
    options = args or parse_args()
    client: Any = _DryRunS3Client() if options.dry_run else build_s3_client(settings)
    storage = S3GeneratedAssetStorage(
        bucket=str(settings.asset_s3_bucket),
        public_base_url=settings.asset_public_base_url,
        client=client,
    )
    report = await backfill_generated_assets(
        local_root=Path(options.local_root),
        storage=storage,
        dry_run=bool(options.dry_run),
        skip_existing=not bool(options.no_skip_existing),
    )
    print(
        "generated asset backfill "
        f"dry_run={report.dry_run} uploaded={report.uploaded_count} skipped={report.skipped_count} "
        f"failed={len(report.failed_files)} bytes={report.total_bytes}"
    )
    for failed in report.failed_files:
        print(f"FAILED {failed}")
    return report


def main() -> None:
    asyncio.run(async_main())


class _DryRunS3Client:
    def put_object(self, **kwargs: Any) -> None:
        return None

    def head_object(self, **kwargs: Any) -> None:
        return None


if __name__ == "__main__":
    main()
