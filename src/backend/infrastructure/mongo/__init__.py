from __future__ import annotations

from src.backend.infrastructure.mongo.chat_buckets import ChatBucketRepository
from src.backend.infrastructure.mongo.client import MongoClientProvider, get_mongo_provider

__all__ = ["ChatBucketRepository", "CombatDocumentRepository", "MongoClientProvider", "get_mongo_provider"]


def __getattr__(name: str) -> object:
    if name == "CombatDocumentRepository":
        from src.backend.infrastructure.mongo.combat_documents import CombatDocumentRepository

        return CombatDocumentRepository
    raise AttributeError(name)
