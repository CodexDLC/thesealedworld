from __future__ import annotations

from typing import Any

from loguru import logger

from src.backend.core.ai import AIService
from src.backend.core.database import get_manual_session_context
from src.backend.features.generation_ai.asset_storage import build_generated_asset_storage
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.integrations import CodexAIExecutor
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService


async def generation_ai_process_task(ctx: dict[str, Any], task_id: str) -> dict[str, Any]:
    async with get_manual_session_context() as session:
        ai = ctx.get("ai")
        if ai is None:
            ai = AIService()
            ctx["ai"] = ai
        arq = ctx.get("generation_ai_arq")
        service = GenerationAIService(
            repository=AIGenerationTaskRepository(session),
            registry=build_generation_ai_registry(session=session),
            executor=CodexAIExecutor(ai, asset_storage=build_generated_asset_storage()),
            arq=arq,
            auto_schedule=False,
        )
        await service.process_task(task_id)
        await session.commit()
        await service.schedule_pending_task_ids()

    logger.info("GenerationAI | worker processed task_id={}", task_id)
    return {"status": "ok", "task_id": task_id}


GENERATION_AI_TASKS = (generation_ai_process_task,)
