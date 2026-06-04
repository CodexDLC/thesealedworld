from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.monsters.dto.generated_view import MonsterAIRegenerationResponseDTO
from src.backend.features.monsters.tasks_ai import build_monster_clan_flavor_task_spec
from src.backend.infrastructure.monsters import GeneratedClanORM


class MonsterContentRegenerationService:
    def __init__(self, *, session: Any, arq: Any | None = None) -> None:
        self.session = session
        self.arq = arq

    async def request_clan_flavor(self, clan_id: str) -> MonsterAIRegenerationResponseDTO:
        clan = await self.session.scalar(
            select(GeneratedClanORM)
            .where(GeneratedClanORM.id == UUID(str(clan_id)))
            .options(selectinload(GeneratedClanORM.members))
        )
        if clan is None:
            raise ValueError(f"Generated clan not found: {clan_id}")

        service = GenerationAIService(
            repository=AIGenerationTaskRepository(self.session),
            registry=build_generation_ai_registry(session=self.session),
            arq=self.arq,
            auto_schedule=False,
        )
        spec = build_monster_clan_flavor_task_spec(clan)
        spec.prompt_payload["regeneration_request_id"] = str(uuid4())
        result = await service.enqueue_many([spec])
        await self.session.commit()
        await service.schedule_pending_task_ids()
        return MonsterAIRegenerationResponseDTO(
            task_id=result.task_ids[0],
            entity_type="monster_clan",
            entity_id=str(clan.id),
            status="pending",
        )


__all__ = ["MonsterContentRegenerationService"]
