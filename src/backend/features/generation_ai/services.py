from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from loguru import logger

from src.backend.features.generation_ai.dto import (
    AIGenerationEnqueueResultDTO,
    AIGenerationTaskResultDTO,
    AIGenerationTaskSpecDTO,
)
from src.backend.features.generation_ai.identity import build_generation_task_identity_key

if TYPE_CHECKING:
    from src.backend.features.generation_ai.handlers import AIGenerationExecutor
    from src.backend.features.generation_ai.registry import AIGenerationTaskRegistry
    from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository

GENERATION_AI_ARQ_TASK = "generation_ai_process_task"


class GenerationAIService:
    def __init__(
        self,
        *,
        repository: AIGenerationTaskRepository,
        registry: AIGenerationTaskRegistry,
        executor: AIGenerationExecutor | None = None,
        arq: Any | None = None,
    ) -> None:
        self.repository = repository
        self.registry = registry
        self.executor = executor
        self.arq = arq

    async def enqueue_many(
        self,
        specs: list[AIGenerationTaskSpecDTO] | tuple[AIGenerationTaskSpecDTO, ...],
    ) -> AIGenerationEnqueueResultDTO:
        batch_id = str(uuid4())
        task_ids: list[str] = []
        schedulable_task_ids: list[str] = []
        created = 0
        reused = 0

        for spec in specs:
            self._validate_spec(spec)
            identity_key = build_generation_task_identity_key(spec)
            task = await self.repository.find_by_identity_key(identity_key)
            if task is None:
                task = await self.repository.create(spec, batch_id=batch_id, identity_key=identity_key)
                created += 1
            else:
                reused += 1
            task_ids.append(task.id)
            if task.status in {"pending", "cooldown"}:
                schedulable_task_ids.append(task.id)

        scheduled = await self._schedule_tasks(schedulable_task_ids)
        logger.info(
            "GenerationAI | enqueue batch={} created={} reused={} scheduled={}",
            batch_id,
            created,
            reused,
            scheduled,
        )
        return AIGenerationEnqueueResultDTO(
            batch_id=batch_id,
            task_ids=task_ids,
            created=created,
            reused=reused,
            scheduled=scheduled,
        )

    async def process_task(self, task_id: str) -> AIGenerationTaskResultDTO | None:
        task = await self.repository.claim_by_id(task_id)
        if task is None:
            existing = await self.repository.get(task_id)
            if existing is None:
                logger.warning("GenerationAI | task missing task_id={}", task_id)
            else:
                logger.info("GenerationAI | task skipped task_id={} status={}", task_id, existing.status)
            return None
        return await self._execute_claimed_task(task)

    async def _execute_claimed_task(self, task: Any) -> AIGenerationTaskResultDTO | None:
        try:
            handler = self.registry.resolve(task.task_type)
            if self.executor is None:
                raise RuntimeError("AI generation executor is not configured")

            request = await handler.build_request(task)
            result = await self.executor.generate(task, request)
            if not isinstance(result, AIGenerationTaskResultDTO):
                result = AIGenerationTaskResultDTO.model_validate(result)
            followup_specs = await handler.apply_result(task, result)
            await self.repository.mark_done(task.id, result)
            await self._enqueue_followups(followup_specs)
            logger.info("GenerationAI | task done task_id={} task_type={}", task.id, task.task_type)
            return result
        except Exception as exc:
            await self._mark_retry_or_failed(task.id, exc)
            return None

    async def claim_and_process_next(self) -> str | None:
        task = await self.repository.claim_next()
        if task is None:
            return None
        await self._execute_claimed_task(task)
        return task.id

    def _validate_spec(self, spec: AIGenerationTaskSpecDTO) -> None:
        if not self.registry.has(spec.task_type):
            raise ValueError(f"AI generation task type is not registered: {spec.task_type}")

    async def _schedule_tasks(self, task_ids: list[str]) -> int:
        scheduled = 0
        for task_id in task_ids:
            if await self._schedule_task(task_id):
                scheduled += 1
        return scheduled

    async def _enqueue_followups(
        self,
        specs: list[AIGenerationTaskSpecDTO] | tuple[AIGenerationTaskSpecDTO, ...] | None,
    ) -> AIGenerationEnqueueResultDTO | None:
        if not specs:
            return None
        return await self.enqueue_many(specs)

    async def _mark_retry_or_failed(self, task_id: str, exc: Exception) -> None:
        task = await self.repository.get(task_id)
        if task is None:
            return
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if int(task.attempts or 0) >= int(task.max_attempts or 1):
            await self.repository.mark_failed(task.id, error)
            logger.warning("GenerationAI | task failed task_id={} error={}", task.id, error)
            return

        not_before = datetime.now(UTC) + timedelta(seconds=30)
        await self.repository.mark_cooldown(
            task.id,
            not_before=not_before,
            error=error,
        )
        await self._schedule_task(task.id, not_before=not_before)
        logger.warning("GenerationAI | task cooldown task_id={} error={}", task.id, error)

    async def _schedule_task(self, task_id: str, *, not_before: datetime | None = None) -> bool:
        if self.arq is None:
            return False
        kwargs: dict[str, Any] = {}
        if not_before is not None:
            kwargs["_defer_until"] = not_before
        await self.arq.enqueue_job(GENERATION_AI_ARQ_TASK, task_id, **kwargs)
        return True
