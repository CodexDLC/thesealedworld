from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, cast

from fastapi import APIRouter, Depends, Request

from src.backend.core.database import get_db
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.dto import (
    AIGenerationOutputKind,
    AIGenerationTaskCreateResponseDTO,
    AIGenerationTaskStatus,
    AIGenerationTaskViewDTO,
    NewsCoverGenerationRequestDTO,
)
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.generation_ai.tasks_news import build_news_cover_image_task_spec

if TYPE_CHECKING:
    from src.backend.features.generation_ai.models import AIGenerationTask

router = APIRouter(prefix="/api/admin/generation-ai", tags=["generation-ai-admin"])


def get_generation_task_repository(db_session=Depends(get_db)) -> AIGenerationTaskRepository:
    return AIGenerationTaskRepository(db_session)


@router.post("/news-covers", response_model=AIGenerationTaskCreateResponseDTO)
async def request_news_cover_generation(
    payload: NewsCoverGenerationRequestDTO,
    request: Request,
    db_session=Depends(get_db),
) -> AIGenerationTaskCreateResponseDTO:
    spec = build_news_cover_image_task_spec(
        article_id=payload.article_id,
        slug=payload.slug,
        title=payload.title,
        preview=payload.preview,
        body_excerpt=payload.body_excerpt,
        prompt=payload.prompt,
        content_type=payload.content_type,
    )
    repository = AIGenerationTaskRepository(db_session)
    service = GenerationAIService(
        repository=repository,
        registry=build_generation_ai_registry(session=db_session),
        arq=getattr(request.app.state, "generation_ai_arq", None),
        auto_schedule=False,
    )
    result = await service.enqueue_many([spec])
    await db_session.commit()
    scheduled = await service.schedule_pending_task_ids()
    task_id = result.task_ids[0]
    task = await repository.get(task_id)
    return AIGenerationTaskCreateResponseDTO(
        task_id=task_id,
        status=cast("AIGenerationTaskStatus", task.status) if task is not None else "pending",
        created=result.created > 0,
        scheduled=scheduled,
        storage_key=spec.input_payload.get("storage_key"),
        generated_url=task.generated_url if task is not None else None,
    )


@router.get("/tasks/{task_id}", response_model=AIGenerationTaskViewDTO)
async def get_generation_task(
    task_id: str,
    repository: Annotated[AIGenerationTaskRepository, Depends(get_generation_task_repository)],
) -> AIGenerationTaskViewDTO:
    task = await repository.get(task_id)
    if task is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="AI generation task not found")
    return _task_view(task)


def _task_view(task: AIGenerationTask) -> AIGenerationTaskViewDTO:
    return AIGenerationTaskViewDTO(
        task_id=task.id,
        task_type=task.task_type,
        entity_type=task.entity_type,
        entity_id=task.entity_id,
        output_kind=cast("AIGenerationOutputKind", task.output_kind),
        status=cast("AIGenerationTaskStatus", task.status),
        storage_key=task.storage_key,
        generated_url=task.generated_url,
        asset_hash=task.asset_hash,
        metadata=dict(getattr(task, "metadata_", {}) or {}),
        error=dict(getattr(task, "error", {}) or {}),
    )
