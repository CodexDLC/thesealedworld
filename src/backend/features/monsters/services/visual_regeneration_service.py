from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.monsters.dto.generated_view import (
    MonsterImageRegenerationBatchResponseDTO,
    MonsterImageRegenerationResponseDTO,
)
from src.backend.features.monsters.resources.visuals import build_member_visual
from src.backend.features.monsters.tasks_ai import (
    build_monster_member_image_task_spec_from_orm,
)
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


class MonsterVisualRegenerationService:
    def __init__(self, *, session: Any, arq: Any | None = None) -> None:
        self.session = session
        self.arq = arq

    async def request_clan_member_images(self, clan_id: str) -> MonsterImageRegenerationBatchResponseDTO:
        clan = await self._get_clan(clan_id)
        prepared = [self._prepare_member_image(member, clan=clan) for member in clan.members]
        task_ids, service = await self._enqueue_prepared(prepared)
        await self.session.commit()
        await service.schedule_pending_task_ids()
        return _batch_response(
            task_ids=task_ids,
            entity_type="monster_clan_members",
            entity_id=str(clan.id),
            prepared=prepared,
        )

    async def request_clan_member_images_for_clans(
        self, clan_ids: list[str]
    ) -> MonsterImageRegenerationBatchResponseDTO:
        clans = await self._get_clans(clan_ids)
        prepared = [self._prepare_member_image(member, clan=clan) for clan in clans for member in clan.members]
        task_ids, service = await self._enqueue_prepared(prepared)
        await self.session.commit()
        await service.schedule_pending_task_ids()
        return _batch_response(
            task_ids=task_ids,
            entity_type="monster_clan_members",
            entity_id=None,
            prepared=prepared,
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
        prepared = [self._prepare_member_image(member, clan=member.clan)]
        task_ids, service = await self._enqueue_prepared(prepared)
        await self.session.commit()
        await service.schedule_pending_task_ids()
        item = prepared[0]
        return MonsterImageRegenerationResponseDTO(
            task_id=task_ids[0],
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            status="pending",
            storage_key=item.storage_key,
            image_url=item.image_url,
        )

    async def _get_clan(self, clan_id: str) -> GeneratedClanORM:
        clan = await self.session.scalar(
            select(GeneratedClanORM)
            .where(GeneratedClanORM.id == UUID(str(clan_id)))
            .options(selectinload(GeneratedClanORM.members))
        )
        if clan is None:
            raise ValueError(f"Generated clan not found: {clan_id}")
        return clan

    async def _get_clans(self, clan_ids: list[str]) -> list[GeneratedClanORM]:
        if not clan_ids:
            raise ValueError("No generated clans selected")
        ids = [UUID(str(clan_id)) for clan_id in clan_ids]
        result = await self.session.scalars(
            select(GeneratedClanORM).where(GeneratedClanORM.id.in_(ids)).options(selectinload(GeneratedClanORM.members))
        )
        clans_by_id = {clan.id: clan for clan in result.all()}
        missing = [str(clan_id) for clan_id in ids if clan_id not in clans_by_id]
        if missing:
            raise ValueError(f"Generated clans not found: {', '.join(missing)}")
        clans = [clans_by_id[clan_id] for clan_id in ids]
        return clans

    def _prepare_member_image(
        self,
        member: GeneratedMonsterORM,
        *,
        clan: GeneratedClanORM,
    ) -> _PreparedVisualRegeneration:
        metadata = dict(member.metadata_ or {})
        previous_visual = dict(metadata.get("visual") or {})
        next_visual = build_member_visual(
            clan.family_id,
            variant_key=member.variant_id,
            role=member.role,
            member_name=member.title or member.variant_id,
            appearance=_member_appearance(member),
            visual_hint=_member_visual_hint(member, clan),
            context_tags=list((clan.context_identity or {}).get("tags") or []),
            clan_name=clan.title or clan.family_id,
        )
        metadata["visual"] = _pending_visual(next_visual, previous_visual)
        member.metadata_ = metadata

        spec = build_monster_member_image_task_spec_from_orm(member, clan=clan)
        return _PreparedVisualRegeneration(
            spec=spec,
            entity_type="monster_member",
            entity_id=str(member.id),
            storage_key=str(spec.input_payload["visual"]["storage_key"]),
            image_url=str(metadata["visual"].get("image_url") or ""),
            target=member,
            json_field="metadata_",
            payload=metadata,
        )

    async def _enqueue_prepared(
        self,
        prepared: list[_PreparedVisualRegeneration],
    ) -> tuple[list[str], GenerationAIService]:
        service = GenerationAIService(
            repository=AIGenerationTaskRepository(self.session),
            registry=build_generation_ai_registry(session=self.session),
            arq=self.arq,
            auto_schedule=False,
        )
        result = await service.enqueue_many([item.spec for item in prepared])
        for task_id, item in zip(result.task_ids, prepared, strict=True):
            item.payload["visual"]["pending_task_id"] = task_id
            setattr(item.target, item.json_field, item.payload)
        return result.task_ids, service


@dataclass(frozen=True)
class _PreparedVisualRegeneration:
    spec: Any
    entity_type: str
    entity_id: str
    storage_key: str
    image_url: str
    target: Any
    json_field: str
    payload: dict[str, Any]


def _batch_response(
    *,
    task_ids: list[str],
    entity_type: str,
    entity_id: str | None,
    prepared: list[_PreparedVisualRegeneration],
) -> MonsterImageRegenerationBatchResponseDTO:
    return MonsterImageRegenerationBatchResponseDTO(
        task_ids=task_ids,
        entity_type=entity_type,
        entity_id=entity_id,
        status="pending",
        requested=len(task_ids),
        storage_keys=[item.storage_key for item in prepared],
    )


def _pending_visual(next_visual: dict[str, Any], previous_visual: dict[str, Any]) -> dict[str, Any]:
    current_image_url = (
        previous_visual.get("image_url")
        or previous_visual.get("generated_image_url")
        or previous_visual.get("placeholder_image_url")
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


def _member_appearance(member: GeneratedMonsterORM) -> str:
    return str(member.short_description or member.variant_id)


def _member_visual_hint(member: GeneratedMonsterORM, clan: GeneratedClanORM) -> str:
    metadata = dict(clan.metadata_ or {})
    flavor_content = dict(metadata.get("flavor_content") or {})
    variants_flavor = flavor_content.get("variants_flavor")
    if not isinstance(variants_flavor, dict):
        return ""
    variant_flavor = variants_flavor.get(member.variant_id)
    if not isinstance(variant_flavor, dict):
        return ""
    visual_hint = variant_flavor.get("visual_hint")
    if isinstance(visual_hint, dict):
        return str(visual_hint.get("en") or visual_hint.get("ru") or "")
    return str(visual_hint or variant_flavor.get("visual_hint_en") or variant_flavor.get("visual_hint_ru") or "")
