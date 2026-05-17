from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
from src.backend.features.generation_ai.handlers import AIGenerationTaskHandler
from src.backend.features.generation_ai.identity import build_generation_task_identity_key
from src.backend.features.generation_ai.registry import AIGenerationTaskRegistry
from src.backend.features.generation_ai.services import GENERATION_AI_ARQ_TASK, GenerationAIService


@dataclass
class FakeTask:
    id: str
    task_type: str
    entity_type: str = "item"
    entity_id: str = "item-1"
    output_kind: str = "text"
    status: str = "pending"
    attempts: int = 0
    max_attempts: int = 3
    input_payload: dict[str, Any] = field(default_factory=dict)
    prompt_payload: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] = field(default_factory=dict)

    def bump_revision(self) -> int:
        return 1


class FakeRepository:
    def __init__(self) -> None:
        self.by_identity: dict[str, FakeTask] = {}
        self.by_id: dict[str, FakeTask] = {}
        self.done: list[str] = []
        self.cooldown: list[str] = []
        self.failed: list[str] = []

    async def find_by_identity_key(self, identity_key: str) -> FakeTask | None:
        return self.by_identity.get(identity_key)

    async def create(self, spec: AIGenerationTaskSpecDTO, *, batch_id: str, identity_key: str) -> FakeTask:
        task = FakeTask(
            id=f"task-{len(self.by_id) + 1}",
            task_type=spec.task_type,
            entity_type=spec.entity_type,
            entity_id=spec.entity_id,
            output_kind=spec.output_kind,
            input_payload=spec.input_payload,
            prompt_payload=spec.prompt_payload,
            max_attempts=spec.max_attempts,
        )
        self.by_identity[identity_key] = task
        self.by_id[task.id] = task
        return task

    async def get(self, task_id: str) -> FakeTask | None:
        return self.by_id.get(task_id)

    async def claim_by_id(self, task_id: str) -> FakeTask | None:
        task = self.by_id.get(task_id)
        if task is None or task.status not in {"pending", "cooldown"}:
            return None
        task.status = "running"
        task.attempts += 1
        return task

    async def mark_done(self, task_id: str, result: AIGenerationTaskResultDTO) -> FakeTask | None:
        task = self.by_id.get(task_id)
        if task is None:
            return None
        task.status = "done"
        self.done.append(task_id)
        return task

    async def mark_cooldown(
        self,
        task_id: str,
        *,
        not_before: Any,
        error: dict[str, object] | None = None,
    ) -> FakeTask | None:
        task = self.by_id.get(task_id)
        if task is None:
            return None
        task.status = "cooldown"
        task.error = dict(error or {})
        self.cooldown.append(task_id)
        return task

    async def mark_failed(self, task_id: str, error: dict[str, object]) -> FakeTask | None:
        task = self.by_id.get(task_id)
        if task is None:
            return None
        task.status = "failed"
        task.error = dict(error)
        self.failed.append(task_id)
        return task


class FakeArq:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []

    async def enqueue_job(self, name: str, task_id: str, **kwargs: Any) -> None:
        if kwargs:
            self.jobs.append((name, task_id, kwargs))
        else:
            self.jobs.append((name, task_id))


class FakeHandler(AIGenerationTaskHandler):
    task_type = "item.description"

    def __init__(self) -> None:
        self.applied: list[str] = []

    async def build_request(self, task: FakeTask) -> dict[str, Any]:
        return {"kind": "text", "prompt": task.input_payload}

    async def apply_result(self, task: FakeTask, result: AIGenerationTaskResultDTO) -> None:
        self.applied.append(task.id)


class FakeImageHandler(AIGenerationTaskHandler):
    task_type = "item.image"

    async def build_request(self, task: FakeTask) -> dict[str, Any]:
        return {"kind": "image", "input": task.input_payload}

    async def apply_result(self, task: FakeTask, result: AIGenerationTaskResultDTO) -> None:
        return None


class FakeJsonWithoutSchemaHandler(AIGenerationTaskHandler):
    task_type = "item.bad_json"

    async def build_request(self, task: FakeTask) -> dict[str, Any]:
        return {"kind": "json", "prompt": "Return JSON"}

    async def apply_result(self, task: FakeTask, result: AIGenerationTaskResultDTO) -> None:
        return None


class FakeMismatchedKindHandler(AIGenerationTaskHandler):
    task_type = "item.mismatched_kind"

    async def build_request(self, task: FakeTask) -> dict[str, Any]:
        return {"kind": "text", "prompt": "Return text"}

    async def apply_result(self, task: FakeTask, result: AIGenerationTaskResultDTO) -> None:
        return None


class FakeBadImageModelHandler(AIGenerationTaskHandler):
    task_type = "item.bad_image_model"

    async def build_request(self, task: FakeTask) -> dict[str, Any]:
        return {
            "kind": "image",
            "prompt": "Create item image",
            "model": "imagen-3.0-generate-002",
            "content_type": "image/webp",
            "storage_key": "items/generated/item.webp",
        }

    async def apply_result(self, task: FakeTask, result: AIGenerationTaskResultDTO) -> None:
        return None


class FakeChainedHandler(FakeHandler):
    async def apply_result(
        self,
        task: FakeTask,
        result: AIGenerationTaskResultDTO,
    ) -> list[AIGenerationTaskSpecDTO]:
        self.applied.append(task.id)
        return [
            AIGenerationTaskSpecDTO(
                task_type="item.image",
                entity_type="item",
                entity_id=task.input_payload["item_id"],
                output_kind="image",
                input_payload={
                    "item_id": task.input_payload["item_id"],
                    "description": result.output_payload,
                },
            )
        ]


class FakeExecutor:
    async def generate(self, task: FakeTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        return AIGenerationTaskResultDTO(output_payload={"request": request, "task_id": task.id})


class FailingExecutor:
    async def generate(self, task: FakeTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        raise RuntimeError("provider down")


def _spec(entity_id: str = "item-1") -> AIGenerationTaskSpecDTO:
    return AIGenerationTaskSpecDTO(
        task_type="item.description",
        entity_type="item",
        entity_id=entity_id,
        output_kind="text",
        input_payload={"item_id": entity_id},
    )


def _bad_json_spec() -> AIGenerationTaskSpecDTO:
    return AIGenerationTaskSpecDTO(
        task_type="item.bad_json",
        entity_type="item",
        entity_id="item-1",
        output_kind="json",
        input_payload={"item_id": "item-1"},
    )


def _mismatched_kind_spec() -> AIGenerationTaskSpecDTO:
    return AIGenerationTaskSpecDTO(
        task_type="item.mismatched_kind",
        entity_type="item",
        entity_id="item-1",
        output_kind="json",
        input_payload={"item_id": "item-1"},
    )


def _bad_image_model_spec() -> AIGenerationTaskSpecDTO:
    return AIGenerationTaskSpecDTO(
        task_type="item.bad_image_model",
        entity_type="item",
        entity_id="item-1",
        output_kind="image",
        input_payload={"item_id": "item-1"},
    )


def test_identity_key_is_stable_for_equivalent_specs() -> None:
    assert build_generation_task_identity_key(_spec()) == build_generation_task_identity_key(_spec())


def test_registry_rejects_duplicate_task_type() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeHandler())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeHandler())


@pytest.mark.asyncio
async def test_enqueue_many_creates_or_reuses_tasks_and_schedules_arq() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeHandler())
    repository = FakeRepository()
    arq = FakeArq()
    service = GenerationAIService(repository=repository, registry=registry, arq=arq)

    first = await service.enqueue_many([_spec()])
    second = await service.enqueue_many([_spec()])

    assert first.created == 1
    assert first.reused == 0
    assert second.created == 0
    assert second.reused == 1
    assert first.task_ids == second.task_ids
    assert arq.jobs == [
        (GENERATION_AI_ARQ_TASK, first.task_ids[0]),
        (GENERATION_AI_ARQ_TASK, first.task_ids[0]),
    ]


@pytest.mark.asyncio
async def test_enqueue_many_can_defer_arq_schedule_until_manual_commit_boundary() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeHandler())
    repository = FakeRepository()
    arq = FakeArq()
    service = GenerationAIService(repository=repository, registry=registry, arq=arq, auto_schedule=False)

    result = await service.enqueue_many([_spec()])

    assert result.created == 1
    assert result.scheduled == 0
    assert arq.jobs == []

    scheduled = await service.schedule_pending_task_ids()

    assert scheduled == 1
    assert arq.jobs == [(GENERATION_AI_ARQ_TASK, result.task_ids[0])]


@pytest.mark.asyncio
async def test_process_task_routes_through_registered_handler_and_marks_done() -> None:
    handler = FakeHandler()
    registry = AIGenerationTaskRegistry()
    registry.register(handler)
    repository = FakeRepository()
    service = GenerationAIService(
        repository=repository,
        registry=registry,
        executor=FakeExecutor(),
    )
    task = await repository.create(_spec(), batch_id="batch-1", identity_key="identity-1")

    result = await service.process_task(task.id)

    assert result is not None
    assert repository.done == [task.id]
    assert handler.applied == [task.id]
    assert task.status == "done"


@pytest.mark.asyncio
async def test_process_task_rejects_json_request_without_schema() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeJsonWithoutSchemaHandler())
    repository = FakeRepository()
    service = GenerationAIService(
        repository=repository,
        registry=registry,
        executor=FakeExecutor(),
    )
    task = await repository.create(_bad_json_spec(), batch_id="batch-1", identity_key="identity-1")

    result = await service.process_task(task.id)

    assert result is None
    assert task.status == "cooldown"
    assert repository.cooldown == [task.id]
    assert "schema" in task.error["message"]


@pytest.mark.asyncio
async def test_process_task_rejects_output_kind_mismatch() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeMismatchedKindHandler())
    repository = FakeRepository()
    service = GenerationAIService(
        repository=repository,
        registry=registry,
        executor=FakeExecutor(),
    )
    task = await repository.create(_mismatched_kind_spec(), batch_id="batch-1", identity_key="identity-1")

    result = await service.process_task(task.id)

    assert result is None
    assert task.status == "cooldown"
    assert repository.cooldown == [task.id]
    assert "kind mismatch" in task.error["message"]


@pytest.mark.asyncio
async def test_process_task_rejects_unsupported_image_model_before_executor() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeBadImageModelHandler())
    repository = FakeRepository()
    service = GenerationAIService(
        repository=repository,
        registry=registry,
        executor=FakeExecutor(),
    )
    task = await repository.create(_bad_image_model_spec(), batch_id="batch-1", identity_key="identity-1")

    result = await service.process_task(task.id)

    assert result is None
    assert task.status == "cooldown"
    assert repository.cooldown == [task.id]
    assert "Unsupported image model" in task.error["message"]


@pytest.mark.asyncio
async def test_process_task_enqueues_followup_specs_returned_by_handler() -> None:
    handler = FakeChainedHandler()
    registry = AIGenerationTaskRegistry()
    registry.register(handler)
    registry.register(FakeImageHandler())
    repository = FakeRepository()
    arq = FakeArq()
    service = GenerationAIService(
        repository=repository,
        registry=registry,
        executor=FakeExecutor(),
        arq=arq,
    )
    task = await repository.create(_spec(), batch_id="batch-1", identity_key="identity-1")

    result = await service.process_task(task.id)

    assert result is not None
    assert repository.done == [task.id]
    assert handler.applied == [task.id]
    assert len(repository.by_id) == 2
    followup = repository.by_id["task-2"]
    assert followup.task_type == "item.image"
    assert followup.input_payload["item_id"] == "item-1"
    assert followup.status == "pending"
    assert arq.jobs == [(GENERATION_AI_ARQ_TASK, followup.id)]


@pytest.mark.asyncio
async def test_process_task_can_defer_cooldown_reschedule_until_manual_commit_boundary() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeHandler())
    repository = FakeRepository()
    arq = FakeArq()
    service = GenerationAIService(
        repository=repository,
        registry=registry,
        executor=FailingExecutor(),
        arq=arq,
        auto_schedule=False,
    )
    task = await repository.create(_spec(), batch_id="batch-1", identity_key="identity-1")

    result = await service.process_task(task.id)

    assert result is None
    assert task.status == "cooldown"
    assert repository.cooldown == [task.id]
    assert arq.jobs == []

    scheduled = await service.schedule_pending_task_ids()

    assert scheduled == 1
    assert arq.jobs[0][0:2] == (GENERATION_AI_ARQ_TASK, task.id)
    assert "_defer_until" in arq.jobs[0][2]
