from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from src.backend.infrastructure.generation_ai import AIGenerationTaskDocumentRepository
from src.backend.infrastructure.mongo.chat_buckets import ChatBucketRepository
from src.backend.infrastructure.mongo.client import get_mongo_provider
from src.backend.infrastructure.mongo.combat_documents import CombatDocumentRepository
from src.backend.infrastructure.monsters.actor_documents import GeneratedMonsterActorRepository
from src.backend.infrastructure.rift.repositories.catalog_documents import RiftCatalogDocumentRepository
from src.backend.infrastructure.rift.repositories.snapshots import RiftRuntimeSnapshotRepository


class MongoIndexRepository(Protocol):
    async def ensure_indexes(self) -> None:
        """Create required indexes for one Mongo-backed document family."""


async def ensure_all_mongo_indexes(
    repositories: Sequence[MongoIndexRepository] | None = None,
) -> None:
    """Create MongoDB indexes required by backend hybrid persistence.

    Mongo collections are intentionally not part of Alembic. This bootstrap
    step makes a clean local/test Mongo database operational before runtime
    traffic starts writing documents.
    """

    for repository in repositories or _default_repositories():
        await repository.ensure_indexes()


def _default_repositories() -> list[MongoIndexRepository]:
    database = get_mongo_provider().database()
    return [
        CombatDocumentRepository(database),
        ChatBucketRepository(database),
        RiftCatalogDocumentRepository(database),
        RiftRuntimeSnapshotRepository(database),
        AIGenerationTaskDocumentRepository(database),
        GeneratedMonsterActorRepository(database),
    ]
