from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import or_, select

from src.backend.features.generation_ai.identity import build_generation_task_identity_key
from src.backend.features.generation_ai.models import AIGenerationTask

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO


class AIGenerationTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
            prompt_payload=spec.prompt_payload,
            input_payload=spec.input_payload,
            metadata_=spec.metadata,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def find_by_identity_key(self, identity_key: str) -> AIGenerationTask | None:
        stmt = select(AIGenerationTask).where(AIGenerationTask.identity_key == identity_key)
        return await self.session.scalar(stmt)

    async def get(self, task_id: str) -> AIGenerationTask | None:
        return await self.session.scalar(select(AIGenerationTask).where(AIGenerationTask.id == task_id))

    async def find_existing(self, spec: AIGenerationTaskSpecDTO) -> AIGenerationTask | None:
        return await self.find_by_identity_key(build_generation_task_identity_key(spec))

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
        task.error = {}
        task.bump_revision()
        await self.session.flush()
        return task

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
        task.error = {}
        task.bump_revision()
        await self.session.flush()
        return task

    async def mark_done(self, task_id: str, result: AIGenerationTaskResultDTO) -> AIGenerationTask | None:
        task = await self.get(task_id)
        if task is None:
            return None
        task.status = "done"
        task.output_payload = result.output_payload
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
        task.metadata_ = {**dict(task.metadata_ or {}), **asset_metadata, **result.metadata}
        task.completed_at = datetime.now(UTC)
        task.error = {}
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
        task.error = dict(error or {})
        task.bump_revision()
        await self.session.flush()
        return task

    async def mark_failed(self, task_id: str, error: dict[str, Any]) -> AIGenerationTask | None:
        task = await self.get(task_id)
        if task is None:
            return None
        task.status = "failed"
        task.error = dict(error)
        task.completed_at = datetime.now(UTC)
        task.bump_revision()
        await self.session.flush()
        return task
