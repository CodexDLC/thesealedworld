from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.monsters.dto.generated_view import MonsterImageRegenerationResponseDTO
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.visuals import build_clan_visual, build_member_visual
from src.backend.features.monsters.tasks_ai import (
    build_monster_clan_image_task_spec_from_orm,
    build_monster_member_image_task_spec_from_orm,
)
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


class MonsterVisualRegenerationService:
    def __init__(self, *, session: Any, arq: Any | None = None) -> None:
        self.session = session
        self.arq = arq

    async def request_clan_image(self, clan_id: str) -> MonsterImageRegenerationResponseDTO:
        clan = await self.session.scalar(
            select(GeneratedClanORM)
            .where(GeneratedClanORM.id == UUID(str(clan_id)))
            .options(selectinload(GeneratedClanORM.members))
        )
        if clan is None:
            raise ValueError(f"Generated clan not found: {clan_id}")

        previous_visual = dict((clan.flavor_content or {}).get("visual") or {})
        next_visual = build_clan_visual(
            clan.family_id,
            clan_name=clan.name_ru or clan.family_id,
            description=clan.description or "",
            context_tags=list((clan.raw_tags or {}).get("tags") or []),
            member_roster=_member_roster(clan),
        )
        flavor_content = dict(clan.flavor_content or {})
        flavor_content["visual"] = _pending_visual(next_visual, previous_visual)
        clan.flavor_content = flavor_content
        flag_modified(clan, "flavor_content")

        spec = build_monster_clan_image_task_spec_from_orm(clan)
        task_id, service = await self._enqueue_single(spec)
        flavor_content["visual"]["pending_task_id"] = task_id
        clan.flavor_content = flavor_content
        flag_modified(clan, "flavor_content")
        await self.session.commit()
        await service.schedule_pending_task_ids()
        return MonsterImageRegenerationResponseDTO(
            task_id=task_id,
            entity_type="monster_clan",
            entity_id=str(clan.id),
            status="pending",
            storage_key=str(spec.input_payload["visual"]["storage_key"]),
            image_url=str(flavor_content["visual"].get("image_url") or ""),
        )

    async def request_member_image(self, member_id: str) -> MonsterImageRegenerationResponseDTO:
        member = await self.session.scalar(
            select(GeneratedMonsterORM)
            .where(GeneratedMonsterORM.id == UUID(str(member_id)))
            .options(selectinload(GeneratedMonsterORM.clan))
        )
        if member is None:
            raise ValueError(f"Generated monster member not found: {member_id}")
        if member.clan is None:
            raise ValueError(f"Generated monster member has no clan: {member_id}")

        previous_visual = dict((member.generation_meta or {}).get("visual") or {})
        next_visual = build_member_visual(
            member.clan.family_id,
            variant_key=member.variant_key,
            role=member.role,
            member_name=member.name_ru or member.variant_key,
            appearance=_member_appearance(member),
        )
        generation_meta = dict(member.generation_meta or {})
        generation_meta["visual"] = _pending_visual(next_visual, previous_visual)
        member.generation_meta = generation_meta
        flag_modified(member, "generation_meta")

        spec = build_monster_member_image_task_spec_from_orm(member, clan=member.clan)
        task_id, service = await self._enqueue_single(spec)
        generation_meta["visual"]["pending_task_id"] = task_id
        member.generation_meta = generation_meta
        flag_modified(member, "generation_meta")
        await self.session.commit()
        await service.schedule_pending_task_ids()
        return MonsterImageRegenerationResponseDTO(
            task_id=task_id,
            entity_type="monster_member",
            entity_id=str(member.id),
            status="pending",
            storage_key=str(spec.input_payload["visual"]["storage_key"]),
            image_url=str(generation_meta["visual"].get("image_url") or ""),
        )

    async def _enqueue_single(self, spec: Any) -> tuple[str, GenerationAIService]:
        service = GenerationAIService(
            repository=AIGenerationTaskRepository(self.session),
            registry=build_generation_ai_registry(session=self.session),
            arq=self.arq,
            auto_schedule=False,
        )
        result = await service.enqueue_many([spec])
        return result.task_ids[0], service


def _pending_visual(next_visual: dict[str, Any], previous_visual: dict[str, Any]) -> dict[str, Any]:
    current_image_url = (
        previous_visual.get("image_url")
        or previous_visual.get("generated_image_url")
        or previous_visual.get("fallback_image_url")
        or next_visual.get("image_url")
        or ""
    )
    return {
        **next_visual,
        "status": "pending",
        "previous_image_url": current_image_url,
        "image_url": current_image_url,
        "previous_storage_key": previous_visual.get("storage_key") or "",
        "previous_asset_hash": previous_visual.get("asset_hash") or "",
    }


def _member_roster(clan: GeneratedClanORM) -> list[dict[str, str]]:
    family = get_family_config(clan.family_id)
    rows: list[dict[str, str]] = []
    for member in clan.members:
        variant = family.variants.get(member.variant_key) if family is not None else None
        rows.append(
            {
                "variant_key": member.variant_key,
                "role": member.role,
                "name": member.name_ru or member.variant_key,
                "appearance": _member_appearance(member) or (variant.narrative_hint if variant is not None else ""),
            }
        )
    return rows


def _member_appearance(member: GeneratedMonsterORM) -> str:
    text_content: dict[str, Any] = dict(member.text_content or {})
    return str(
        text_content.get("appearance_ru") or text_content.get("appearance") or member.description or member.variant_key
    )
