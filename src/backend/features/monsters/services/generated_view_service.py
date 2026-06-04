from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.monsters.dto.generated_view import GeneratedMonstersResponseDTO
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
    from src.backend.features.monsters.repositories import MonsterGenerationRepository


class GeneratedMonsterViewService:
    def __init__(self, repository: MonsterGenerationRepository) -> None:
        self.repository = repository
        self.gear_score_service = MonsterGearScoreService()

    async def list_generated(
        self,
        *,
        family_id: str | None = None,
        clan_id: str | None = None,
        role: str | None = None,
        include_members: bool = True,
        limit: int = 25,
        offset: int = 0,
    ) -> GeneratedMonstersResponseDTO:
        total = await self.repository.count_generated_clans(family_id=family_id, clan_id=clan_id)
        clans = await self.repository.list_generated_clans_page(
            family_id=family_id,
            clan_id=clan_id,
            limit=limit,
            offset=offset,
        )
        clans = await self._refresh_stale_clans(clans)
        return GeneratedMonstersResponseDTO(
            items=[self._clan_payload(clan, role=role, include_members=include_members) for clan in clans],
            pagination={
                "limit": limit,
                "offset": offset,
                "total": total,
                "has_more": offset + limit < total,
            },
        )

    async def _refresh_stale_clans(self, clans: list[GeneratedClan]) -> list[GeneratedClan]:
        return clans

    def _needs_gear_score_refresh(self, clan: GeneratedClan) -> bool:
        del clan
        return False

    def _clan_payload(self, clan: GeneratedClan, *, role: str | None, include_members: bool) -> dict[str, Any]:
        members = [member for member in clan.members if role is None or member.role == role]
        summary = self._summary(clan, members, role=role)
        return {
            "clan_id": str(clan.id),
            "family_id": clan.family_id,
            "zone_id": clan.zone_id,
            "context_hash": clan.context_hash,
            "identity_hash": clan.identity_hash,
            "context_identity": dict(clan.context_identity or {}),
            "selected_traits": list(clan.selected_traits or []),
            "title": clan.title,
            "description": clan.description,
            "encounter_texts": dict(clan.encounter_texts or {}),
            "generation_version": clan.generation_version,
            "resource_version": clan.resource_version,
            "metadata_": dict(clan.metadata_ or {}),
            "context": dict(clan.context or {}),
            "source_context": dict(clan.source_context or {}),
            "lifecycle_status": clan.lifecycle_status,
            "archived_at": clan.archived_at,
            "expires_at": clan.expires_at,
            "schema_version": clan.schema_version,
            "created_at": clan.created_at,
            "updated_at": clan.updated_at,
            "visual": _visual((clan.metadata_ or {}).get("visual")),
            "gear_score_summary": summary,
            "members": [self._member_payload(member) for member in self._sort_members(members)]
            if include_members
            else [],
        }

    def _summary(self, clan: GeneratedClan, members: list[GeneratedMonster], *, role: str | None) -> dict[str, Any]:
        del clan, role
        return self.gear_score_service.build_clan_summary(members)

    @staticmethod
    def _member_payload(member: GeneratedMonster) -> dict[str, Any]:
        return {
            "member_id": str(member.id),
            "clan_id": str(member.clan_id),
            "variant_id": member.variant_id,
            "member_hash": member.member_hash,
            "role": member.role,
            "title": member.title,
            "short_description": member.short_description or "",
            "min_tier": member.min_tier,
            "max_tier": member.max_tier,
            "mongo_actor_key": member.mongo_actor_key,
            "metadata_": dict(member.metadata_ or {}),
            "context": dict(member.context or {}),
            "source_context": dict(member.source_context or {}),
            "lifecycle_status": member.lifecycle_status,
            "archived_at": member.archived_at,
            "expires_at": member.expires_at,
            "schema_version": member.schema_version,
            "created_at": member.created_at,
            "updated_at": member.updated_at,
            "visual": _visual((member.metadata_ or {}).get("visual")),
        }

    @staticmethod
    def _sort_members(members: list[GeneratedMonster]) -> list[GeneratedMonster]:
        return sorted(
            members,
            key=lambda member: (
                _optional_int(_balance(member).get("gear_score")) is None,
                _optional_int(_balance(member).get("gear_score")) or 0,
                member.role,
                member.variant_id,
            ),
        )


def _balance(member: GeneratedMonster) -> dict[str, Any]:
    gear_score = member.active_snapshot.get("gear_score")
    return {"gear_score": gear_score} if gear_score is not None else {}


def _visual(value: Any) -> dict[str, Any]:
    visual = dict(value) if isinstance(value, dict) else {}
    return {
        "status": str(visual.get("status") or ""),
        "source": str(visual.get("source") or ""),
        "image_url": str(visual.get("image_url") or ""),
        "generated_image_url": str(visual.get("generated_image_url") or ""),
        "placeholder_image_url": str(visual.get("placeholder_image_url") or ""),
        "storage_key": str(visual.get("storage_key") or ""),
        "storage_backend": str(visual.get("storage_backend") or ""),
        "asset_hash": str(visual.get("asset_hash") or ""),
        "content_type": str(visual.get("content_type") or ""),
        "size_bytes": _optional_int(visual.get("size_bytes")),
        "pending_task_id": str(visual.get("pending_task_id")) if visual.get("pending_task_id") else None,
    }


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = ["GeneratedMonsterViewService"]
