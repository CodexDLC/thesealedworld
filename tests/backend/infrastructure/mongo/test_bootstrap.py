from __future__ import annotations

from pathlib import Path

import pytest

from src.backend.infrastructure.mongo.bootstrap import ensure_all_mongo_indexes


@pytest.mark.unit
async def test_ensure_all_mongo_indexes_calls_every_registered_repository() -> None:
    calls: list[str] = []

    class Repository:
        def __init__(self, name: str) -> None:
            self.name = name

        async def ensure_indexes(self) -> None:
            calls.append(self.name)

    repositories = [
        Repository("combat"),
        Repository("chat"),
        Repository("rift_catalog"),
        Repository("rift_snapshots"),
        Repository("generation_ai"),
        Repository("monster_profiles"),
    ]

    await ensure_all_mongo_indexes(repositories=repositories)

    assert calls == [
        "combat",
        "chat",
        "rift_catalog",
        "rift_snapshots",
        "generation_ai",
        "monster_profiles",
    ]


def test_backend_alembic_reset_keeps_single_metadata_baseline() -> None:
    versions_dir = Path("src/backend/alembic/versions")
    revisions = sorted(path.name for path in versions_dir.glob("*.py") if not path.name.startswith("__"))

    assert revisions == ["0001_game_schema_baseline.py"]
