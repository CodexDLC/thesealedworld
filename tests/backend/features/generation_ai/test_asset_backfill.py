from __future__ import annotations

from dataclasses import dataclass

import pytest
from scripts.backfill_generated_assets_to_s3 import (
    backfill_generated_assets,
    content_type_for_path,
    storage_key_for_file,
)


@dataclass
class StoredObject:
    key: str
    content: bytes
    content_type: str


class FakeStorage:
    def __init__(self, existing: set[str] | None = None) -> None:
        self.existing = set(existing or set())
        self.uploaded: list[StoredObject] = []

    async def exists(self, storage_key: str) -> bool:
        return storage_key in self.existing

    async def put_bytes(self, *, storage_key: str, content: bytes, content_type: str, metadata=None):
        self.uploaded.append(StoredObject(storage_key, content, content_type))
        self.existing.add(storage_key)


@pytest.mark.unit
def test_backfill_storage_key_preserves_relative_path(tmp_path) -> None:
    root = tmp_path / "generated"
    path = root / "monsters" / "clan.webp"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"image")

    assert storage_key_for_file(root, path) == "monsters/clan.webp"
    assert content_type_for_path(path) == "image/webp"


@pytest.mark.unit
async def test_backfill_dry_run_does_not_upload_or_require_existing_checks(tmp_path) -> None:
    root = tmp_path / "generated"
    (root / "news").mkdir(parents=True)
    (root / "news" / "cover.png").write_bytes(b"image")
    storage = FakeStorage()

    report = await backfill_generated_assets(local_root=root, storage=storage, dry_run=True)

    assert report.dry_run is True
    assert report.uploaded_count == 0
    assert report.skipped_count == 1
    assert report.total_bytes == len(b"image")
    assert storage.uploaded == []


@pytest.mark.unit
async def test_backfill_uploads_new_files_and_skips_existing(tmp_path) -> None:
    root = tmp_path / "generated"
    (root / "monsters").mkdir(parents=True)
    (root / "monsters" / "new.webp").write_bytes(b"new")
    (root / "monsters" / "old.webp").write_bytes(b"old")
    storage = FakeStorage(existing={"monsters/old.webp"})

    report = await backfill_generated_assets(local_root=root, storage=storage, skip_existing=True)

    assert report.uploaded_count == 1
    assert report.skipped_count == 1
    assert storage.uploaded == [StoredObject("monsters/new.webp", b"new", "image/webp")]
