from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
    from src.backend.features.generation_ai.models import AIGenerationTask


AI_GENERATION_TASK_DOCUMENTS_COLLECTION = "ai_generation_task_documents"
AI_GENERATION_TASK_DOCUMENT_KIND = "ai_generation_task_payload"
AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION = 1


def _now() -> datetime:
    return datetime.now(UTC)


def _coerce_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


class AIGenerationTaskDocumentRepository:
    """Mongo repository for heavy AI generation task payload documents."""

    def __init__(self, database: Any | None = None) -> None:
        self._database = database
        self._collection: Any | None = None

    @property
    def collection(self) -> Any:
        if self._collection is None:
            database = self._database
            if database is None:
                from src.backend.infrastructure.mongo import get_mongo_provider

                database = get_mongo_provider().database()
            self._collection = database[AI_GENERATION_TASK_DOCUMENTS_COLLECTION]
        return self._collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("document_kind", 1), ("task_id", 1)],
            unique=True,
            name="uq_ai_generation_task_documents_task",
        )
        await self.collection.create_index([("identity_key", 1)], name="ix_ai_generation_task_documents_identity")
        await self.collection.create_index(
            [("task_type", 1), ("entity_id", 1)],
            name="ix_ai_generation_task_documents_task_entity",
        )
        await self.collection.create_index([("created_at", 1)], name="ix_ai_generation_task_documents_created")

    async def write_initial(
        self,
        *,
        task: AIGenerationTask,
        spec: AIGenerationTaskSpecDTO,
        identity_key: str,
        document_id: str | None = None,
    ) -> str:
        now = _now()
        doc_id = str(document_id or uuid4())
        filter_query = {"document_kind": AI_GENERATION_TASK_DOCUMENT_KIND, "task_id": str(task.id)}
        document = {
            "document_kind": AI_GENERATION_TASK_DOCUMENT_KIND,
            "schema_version": AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION,
            "task_id": str(task.id),
            "identity_key": identity_key,
            "task_type": task.task_type,
            "entity_type": task.entity_type,
            "entity_id": task.entity_id,
            "output_kind": task.output_kind,
            "prompt_payload": _coerce_dict(spec.prompt_payload),
            "input_payload": _coerce_dict(spec.input_payload),
            "output_payload": {},
            "metadata": _coerce_dict(spec.metadata),
            "error": {},
            "updated_at": now,
        }
        await self.ensure_indexes()
        await self.collection.update_one(
            filter_query,
            {
                "$set": document,
                "$setOnInsert": {"_id": doc_id, "created_at": now},
            },
            upsert=True,
        )
        stored = await self.collection.find_one(filter_query, {"_id": 1})
        return str(stored["_id"]) if isinstance(stored, dict) and stored.get("_id") is not None else doc_id

    async def fetch_by_task_id(self, task_id: str) -> dict[str, Any] | None:
        document = await self.collection.find_one(
            {"document_kind": AI_GENERATION_TASK_DOCUMENT_KIND, "task_id": str(task_id)}
        )
        return dict(document) if isinstance(document, dict) else None

    async def record_result(
        self,
        *,
        task: AIGenerationTask,
        result: AIGenerationTaskResultDTO,
        metadata: dict[str, Any],
    ) -> str:
        now = _now()
        doc_id = str(task.mongo_document_id or uuid4())
        filter_query = {"document_kind": AI_GENERATION_TASK_DOCUMENT_KIND, "task_id": str(task.id)}
        await self.ensure_indexes()
        await self.collection.update_one(
            filter_query,
            {
                "$set": {
                    "document_kind": AI_GENERATION_TASK_DOCUMENT_KIND,
                    "schema_version": AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION,
                    "task_id": str(task.id),
                    "identity_key": task.identity_key,
                    "task_type": task.task_type,
                    "entity_type": task.entity_type,
                    "entity_id": task.entity_id,
                    "output_kind": task.output_kind,
                    "output_payload": _coerce_dict(result.output_payload),
                    "metadata": _coerce_dict(metadata),
                    "error": {},
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "_id": doc_id,
                    "created_at": now,
                    "prompt_payload": _coerce_dict(getattr(task, "prompt_payload", {})),
                    "input_payload": _coerce_dict(getattr(task, "input_payload", {})),
                },
            },
            upsert=True,
        )
        stored = await self.collection.find_one(filter_query, {"_id": 1})
        return str(stored["_id"]) if isinstance(stored, dict) and stored.get("_id") is not None else doc_id

    async def record_error(self, *, task: AIGenerationTask, error: dict[str, Any]) -> str:
        now = _now()
        doc_id = str(task.mongo_document_id or uuid4())
        filter_query = {"document_kind": AI_GENERATION_TASK_DOCUMENT_KIND, "task_id": str(task.id)}
        await self.ensure_indexes()
        await self.collection.update_one(
            filter_query,
            {
                "$set": {
                    "document_kind": AI_GENERATION_TASK_DOCUMENT_KIND,
                    "schema_version": AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION,
                    "task_id": str(task.id),
                    "identity_key": task.identity_key,
                    "task_type": task.task_type,
                    "entity_type": task.entity_type,
                    "entity_id": task.entity_id,
                    "output_kind": task.output_kind,
                    "error": _coerce_dict(error),
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "_id": doc_id,
                    "created_at": now,
                    "prompt_payload": _coerce_dict(getattr(task, "prompt_payload", {})),
                    "input_payload": _coerce_dict(getattr(task, "input_payload", {})),
                    "output_payload": _coerce_dict(getattr(task, "output_payload", {})),
                    "metadata": _coerce_dict(getattr(task, "metadata_", {})),
                },
            },
            upsert=True,
        )
        stored = await self.collection.find_one(filter_query, {"_id": 1})
        return str(stored["_id"]) if isinstance(stored, dict) and stored.get("_id") is not None else doc_id
