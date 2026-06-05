from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import BaseModel

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
from src.backend.features.generation_ai.handlers import AIGenerationTaskHandler
from src.backend.features.generation_ai.identity import build_generation_task_identity_key
from src.backend.features.generation_ai.models import AIGenerationTask
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
    output_payload: dict[str, Any] = field(default_factory=dict)
    metadata_: dict[str, Any] = field(default_factory=dict)
    mongo_document_id: str | None = None
    mongo_status: str = "legacy"
    mongo_schema_version: int | None = None
    last_error_type: str | None = None
    last_error_message: str | None = None

    def bump_revision(self) -> int:
        return 1


class FakeRepository:
    def __init__(self) -> None:
        self.by_identity: dict[str, FakeTask] = {}
        self.by_id: dict[str, FakeTask] = {}
        self.done: list[str] = []
        self.cooldown: list[str] = []
        self.failed: list[str] = []
        self.payload_documents: dict[str, dict[str, Any]] = {}

    async def find_by_identity_key(self, identity_key: str) -> FakeTask | None:
        return self.by_identity.get(identity_key)

    async def prepare_existing_for_enqueue(self, task: FakeTask, *, max_attempts: int) -> FakeTask:
        if task.status in {"failed", "cancelled"}:
            task.status = "pending"
            task.attempts = 0
            task.max_attempts = max(task.max_attempts, max_attempts)
            task.error = {}
            task.last_error_type = None
            task.last_error_message = None
            self.payload_documents[task.id]["error"] = {}
        elif task.status in {"pending", "cooldown"} and task.max_attempts < max_attempts:
            task.max_attempts = max_attempts
        return task

    async def create(self, spec: AIGenerationTaskSpecDTO, *, batch_id: str, identity_key: str) -> FakeTask:
        task_id = f"task-{len(self.by_id) + 1}"
        task = FakeTask(
            id=task_id,
            task_type=spec.task_type,
            entity_type=spec.entity_type,
            entity_id=spec.entity_id,
            output_kind=spec.output_kind,
            input_payload=spec.input_payload,
            prompt_payload=spec.prompt_payload,
            max_attempts=spec.max_attempts,
            metadata_=spec.metadata,
            mongo_document_id=f"mongo-{task_id}",
            mongo_status="stored",
            mongo_schema_version=1,
        )
        self.by_identity[identity_key] = task
        self.by_id[task.id] = task
        self.payload_documents[task.id] = {
            "_id": task.mongo_document_id,
            "input_payload": dict(spec.input_payload),
            "prompt_payload": dict(spec.prompt_payload),
            "output_payload": {},
            "metadata": dict(spec.metadata),
            "error": {},
        }
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
        task.output_payload = dict(result.output_payload)
        self.payload_documents[task.id]["output_payload"] = dict(result.output_payload)
        self.payload_documents[task.id]["metadata"] = {**task.metadata_, **result.metadata}
        self.payload_documents[task.id]["error"] = {}
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
        task.last_error_type = str(task.error.get("type") or "") or None
        task.last_error_message = str(task.error.get("message") or "") or None
        self.payload_documents[task.id]["error"] = dict(task.error)
        self.cooldown.append(task_id)
        return task

    async def mark_failed(self, task_id: str, error: dict[str, object]) -> FakeTask | None:
        task = self.by_id.get(task_id)
        if task is None:
            return None
        task.status = "failed"
        task.error = dict(error)
        task.last_error_type = str(task.error.get("type") or "") or None
        task.last_error_message = str(task.error.get("message") or "") or None
        self.payload_documents[task.id]["error"] = dict(task.error)
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


class _SimpleJsonSchema(BaseModel):
    value: str


class FakeSchemaJsonHandler(AIGenerationTaskHandler):
    task_type = "item.schema_json"

    async def build_request(self, task: FakeTask) -> dict[str, Any]:
        return {"kind": "json", "prompt": "Return JSON", "schema": _SimpleJsonSchema}

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


class LLMProviderError(RuntimeError):
    pass


class SchemaFailingExecutor:
    async def generate(self, task: FakeTask, request: dict[str, Any]) -> AIGenerationTaskResultDTO:
        raise LLMProviderError(
            "Gemini JSON generation failed schema validation: 1 validation error for DemoDTO"
        )


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


def _schema_json_spec() -> AIGenerationTaskSpecDTO:
    return AIGenerationTaskSpecDTO(
        task_type="item.schema_json",
        entity_type="item",
        entity_id="item-1",
        output_kind="json",
        input_payload={"item_id": "item-1"},
    )


def test_identity_key_is_stable_for_equivalent_specs() -> None:
    assert build_generation_task_identity_key(_spec()) == build_generation_task_identity_key(_spec())


def test_ai_generation_task_sql_model_has_no_heavy_payload_columns() -> None:
    assert {
        "prompt_payload",
        "input_payload",
        "output_payload",
        "metadata",
        "error",
    }.isdisjoint(AIGenerationTask.__table__.columns.keys())


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
async def test_enqueue_many_stores_heavy_payloads_in_task_document() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeHandler())
    repository = FakeRepository()
    service = GenerationAIService(repository=repository, registry=registry)

    result = await service.enqueue_many([_spec()])
    task = repository.by_id[result.task_ids[0]]
    document = repository.payload_documents[task.id]

    assert task.mongo_document_id == f"mongo-{task.id}"
    assert task.mongo_status == "stored"
    assert document["input_payload"] == {"item_id": "item-1"}
    assert document["prompt_payload"] == {}
    assert document["metadata"] == {}


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
async def test_enqueue_many_requeues_failed_existing_task_with_new_attempt_budget() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeHandler())
    repository = FakeRepository()
    arq = FakeArq()
    service = GenerationAIService(repository=repository, registry=registry, arq=arq)
    spec = _spec()
    first = await service.enqueue_many([spec])
    task = repository.by_id[first.task_ids[0]]
    task.status = "failed"
    task.attempts = 3
    task.max_attempts = 3
    task.error = {"type": "JSONDecodeError", "message": "empty response"}
    task.last_error_type = "JSONDecodeError"
    task.last_error_message = "empty response"
    retry_spec = spec.model_copy(update={"max_attempts": 5})

    second = await service.enqueue_many([retry_spec])

    assert second.created == 0
    assert second.reused == 1
    assert second.task_ids == first.task_ids
    assert task.status == "pending"
    assert task.attempts == 0
    assert task.max_attempts == 5
    assert task.error == {}
    assert task.last_error_type is None
    assert arq.jobs[-1] == (GENERATION_AI_ARQ_TASK, task.id)


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
    assert repository.payload_documents[task.id]["output_payload"]["task_id"] == task.id


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
    assert "schema" in task.last_error_message
    assert "schema" in repository.payload_documents[task.id]["error"]["message"]


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
async def test_process_task_extends_retry_budget_for_json_schema_provider_errors() -> None:
    registry = AIGenerationTaskRegistry()
    registry.register(FakeSchemaJsonHandler())
    repository = FakeRepository()
    service = GenerationAIService(
        repository=repository,
        registry=registry,
        executor=SchemaFailingExecutor(),
    )
    task = await repository.create(_schema_json_spec(), batch_id="batch-1", identity_key="identity-1")
    task.attempts = 2

    result = await service.process_task(task.id)

    assert result is None
    assert task.status == "cooldown"
    assert repository.cooldown == [task.id]
    assert task.attempts == 3
    assert task.error["type"] == "LLMProviderError"


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
