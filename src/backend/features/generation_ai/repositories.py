from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from loguru import logger
from sqlalchemy import or_, select

from src.backend.features.generation_ai.identity import build_generation_task_identity_key
from src.backend.features.generation_ai.integrations import AIGenerationTaskPayloadStore
from src.backend.features.generation_ai.models import AIGenerationTask
from src.backend.infrastructure.generation_ai import AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO


class AIGenerationTaskRepository:
    def __init__(
        self,
        session: AsyncSession,
        *,
        payload_store: AIGenerationTaskPayloadStore | None = None,
    ) -> None:
        self.session = session
        self.payload_store = payload_store or AIGenerationTaskPayloadStore()

    async def create(
        self,
        spec: AIGenerationTaskSpecDTO,
        *,
        batch_id: str,
        identity_key: str,
        status: str = "pending",
    ) -> AIGenerationTask:
        task = AIGenerationTask(
            id=str(uuid4()),
            batch_id=batch_id,
            identity_key=identity_key,
            task_type=spec.task_type,
            entity_type=spec.entity_type,
            entity_id=spec.entity_id,
            season_id=spec.season_id,
            output_kind=spec.output_kind,
            status=status,
            priority=spec.priority,
            attempts=0,
            max_attempts=spec.max_attempts,
            model=spec.model,
            asset_hash=spec.asset_hash,
            storage_prefix=spec.storage_prefix,
            mongo_status="legacy",
        )
        self.session.add(task)
        await self.session.flush()
        await self._store_initial_payload(task, spec=spec, identity_key=identity_key)
        await self.session.flush()
        return task

    async def find_by_identity_key(self, identity_key: str) -> AIGenerationTask | None:
        stmt = select(AIGenerationTask).where(AIGenerationTask.identity_key == identity_key)
        task = await self.session.scalar(stmt)
        return await self._hydrate_task(task)

    async def get(self, task_id: str) -> AIGenerationTask | None:
        task = await self.session.scalar(select(AIGenerationTask).where(AIGenerationTask.id == task_id))
        return await self._hydrate_task(task)

    async def find_existing(self, spec: AIGenerationTaskSpecDTO) -> AIGenerationTask | None:
        return await self.find_by_identity_key(build_generation_task_identity_key(spec))

    async def prepare_existing_for_enqueue(
        self,
        task: AIGenerationTask,
        *,
        max_attempts: int,
    ) -> AIGenerationTask:
        if task.status in {"failed", "cancelled"}:
            task.status = "pending"
            task.attempts = 0
            task.max_attempts = max(int(task.max_attempts or 1), int(max_attempts))
            task.storage_key = None
            task.generated_url = None
            task.not_before = None
            task.claimed_at = None
            task.completed_at = None
            task.last_error_type = None
            task.last_error_message = None
            cast("Any", task).error = {}
            await self._record_error_payload(task, {})
            task.bump_revision()
            await self.session.flush()
            return task

        if task.status in {"pending", "cooldown"} and int(task.max_attempts or 1) < int(max_attempts):
            task.max_attempts = int(max_attempts)
            task.bump_revision()
            await self.session.flush()
        return task

    async def claim_next(self, *, now: datetime | None = None) -> AIGenerationTask | None:
        moment = now or datetime.now(UTC)
        stmt = (
            select(AIGenerationTask)
            .where(
                AIGenerationTask.status.in_(("pending", "cooldown")),
                AIGenerationTask.attempts < AIGenerationTask.max_attempts,
                or_(AIGenerationTask.not_before.is_(None), AIGenerationTask.not_before <= moment),
            )
            .order_by(AIGenerationTask.priority.asc(), AIGenerationTask.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        task = await self.session.scalar(stmt)
        if task is None:
            return None
        task.status = "running"
        task.attempts = int(task.attempts or 0) + 1
        task.claimed_at = moment
        task.not_before = None
        cast("Any", task).error = {}
        task.bump_revision()
        await self.session.flush()
        hydrated = await self._hydrate_task(task)
        if hydrated is not None:
            cast("Any", hydrated).error = {}
        return hydrated

    async def claim_by_id(self, task_id: str, *, now: datetime | None = None) -> AIGenerationTask | None:
        moment = now or datetime.now(UTC)
        stmt = (
            select(AIGenerationTask)
            .where(
                AIGenerationTask.id == task_id,
                AIGenerationTask.status.in_(("pending", "cooldown")),
                AIGenerationTask.attempts < AIGenerationTask.max_attempts,
                or_(AIGenerationTask.not_before.is_(None), AIGenerationTask.not_before <= moment),
            )
            .with_for_update(skip_locked=True)
        )
        task = await self.session.scalar(stmt)
        if task is None:
            return None
        task.status = "running"
        task.attempts = int(task.attempts or 0) + 1
        task.claimed_at = moment
        task.not_before = None
        cast("Any", task).error = {}
        task.bump_revision()
        await self.session.flush()
        hydrated = await self._hydrate_task(task)
        if hydrated is not None:
            cast("Any", hydrated).error = {}
        return hydrated

    async def mark_done(self, task_id: str, result: AIGenerationTaskResultDTO) -> AIGenerationTask | None:
        task = await self.get(task_id)
        if task is None:
            return None
        task.status = "done"
        task.storage_key = result.storage_key
        task.generated_url = result.generated_url
        task.asset_hash = result.asset_hash or task.asset_hash
        asset_metadata = {
            key: value
            for key, value in {
                "storage_backend": result.storage_backend,
                "content_type": result.content_type,
                "size_bytes": result.size_bytes,
            }.items()
            if value is not None
        }
        metadata = {**dict(getattr(task, "metadata_", {}) or {}), **asset_metadata, **result.metadata}
        cast("Any", task).metadata_ = metadata
        task.completed_at = datetime.now(UTC)
        cast("Any", task).error = {}
        task.last_error_type = None
        task.last_error_message = None
        await self._record_result_payload(task, result, metadata=metadata)
        task.bump_revision()
        await self.session.flush()
        return task

    async def mark_cooldown(
        self,
        task_id: str,
        *,
        not_before: datetime,
        error: dict[str, Any] | None = None,
    ) -> AIGenerationTask | None:
        task = await self.get(task_id)
        if task is None:
            return None
        task.status = "cooldown"
        task.not_before = not_before
        task_error = dict(error or {})
        cast("Any", task).error = task_error
        self._set_short_error(task, task_error)
        await self._record_error_payload(task, task_error)
        task.bump_revision()
        await self.session.flush()
        return task

    async def mark_failed(self, task_id: str, error: dict[str, Any]) -> AIGenerationTask | None:
        task = await self.get(task_id)
        if task is None:
            return None
        task.status = "failed"
        task_error = dict(error)
        cast("Any", task).error = task_error
        task.completed_at = datetime.now(UTC)
        self._set_short_error(task, task_error)
        await self._record_error_payload(task, task_error)
        task.bump_revision()
        await self.session.flush()
        return task

    async def _store_initial_payload(
        self,
        task: AIGenerationTask,
        *,
        spec: AIGenerationTaskSpecDTO,
        identity_key: str,
    ) -> None:
        try:
            document_id = await self.payload_store.create_task_document(
                task=task,
                spec=spec,
                identity_key=identity_key,
            )
        except Exception as exc:  # pragma: no cover - integration failure is environment-specific
            task.mongo_status = "write_failed"
            self._set_short_error(
                task,
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            )
            logger.bind(task_id=task.id, task_type=task.task_type).warning("GenerationAiPayloadInitialWriteFailed")
            return
        task.mongo_document_id = document_id
        task.mongo_status = "stored"
        task.mongo_schema_version = AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION

    async def _hydrate_task(self, task: AIGenerationTask | None) -> AIGenerationTask | None:
        if task is None:
            return None
        try:
            document = await self.payload_store.fetch_task_document(task.id)
        except Exception as exc:  # pragma: no cover - integration failure is environment-specific
            logger.bind(task_id=task.id, error=str(exc)).warning("GenerationAiPayloadHydrateFailed")
            return task
        if document is None:
            return task
        return self.payload_store.apply_document(task, document)

    async def _record_result_payload(
        self,
        task: AIGenerationTask,
        result: AIGenerationTaskResultDTO,
        *,
        metadata: dict[str, Any],
    ) -> None:
        try:
            document_id = await self.payload_store.record_result(task=task, result=result, metadata=metadata)
        except Exception as exc:  # pragma: no cover - integration failure is environment-specific
            task.mongo_status = "write_failed"
            self._set_short_error(
                task,
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            )
            logger.bind(task_id=task.id, task_type=task.task_type).warning("GenerationAiPayloadResultWriteFailed")
            return
        task.mongo_document_id = document_id
        task.mongo_status = "stored"
        task.mongo_schema_version = AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION

    async def _record_error_payload(self, task: AIGenerationTask, error: dict[str, Any]) -> None:
        try:
            document_id = await self.payload_store.record_error(task=task, error=error)
        except Exception as exc:  # pragma: no cover - integration failure is environment-specific
            task.mongo_status = "write_failed"
            logger.bind(task_id=task.id, task_type=task.task_type, error=str(exc)).warning(
                "GenerationAiPayloadErrorWriteFailed"
            )
            return
        task.mongo_document_id = document_id
        task.mongo_status = "stored"
        task.mongo_schema_version = AI_GENERATION_TASK_DOCUMENT_SCHEMA_VERSION

    @staticmethod
    def _set_short_error(task: AIGenerationTask, error: dict[str, Any]) -> None:
        task.last_error_type = str(error.get("type") or "")[:120] or None
        task.last_error_message = str(error.get("message") or "")[:1000] or None
