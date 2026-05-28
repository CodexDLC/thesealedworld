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
        refresh = getattr(self.repository, "refresh_clan_gear_scores", None)
        if refresh is None:
            for clan in clans:
                self.gear_score_service.refresh_stale_monster_scores(clan.members)
                self.gear_score_service.apply_clan_summary(clan)
            return clans

        refreshed_clans: list[GeneratedClan] = []
        for clan in clans:
            if not self._needs_gear_score_refresh(clan):
                refreshed_clans.append(clan)
                continue
            refreshed_members = await refresh(clan.id, gear_score_service=self.gear_score_service, persist=True)
            clan.members = list(refreshed_members)
            for member in clan.members:
                member.clan = clan
            self.gear_score_service.apply_clan_summary(clan)
            refreshed_clans.append(clan)
        return refreshed_clans

    def _needs_gear_score_refresh(self, clan: GeneratedClan) -> bool:
        raw_summary = (clan.raw_tags or {}).get("gear_score_summary")
        if not isinstance(raw_summary, dict) or raw_summary.get("version") != self.gear_score_service.VERSION:
            return True
        return any(self.gear_score_service.needs_recalculation(member) for member in clan.members)

    def _clan_payload(self, clan: GeneratedClan, *, role: str | None, include_members: bool) -> dict[str, Any]:
        members = [member for member in clan.members if role is None or member.role == role]
        summary = self._summary(clan, members, role=role)
        return {
            "clan_id": str(clan.id),
            "family_id": clan.family_id,
            "tier": clan.tier,
            "zone_id": clan.zone_id,
            "context_hash": clan.context_hash,
            "unique_hash": clan.unique_hash,
            "raw_tags": dict(clan.raw_tags or {}),
            "flavor_content": dict(clan.flavor_content or {}),
            "name_ru": clan.name_ru,
            "description": clan.description,
            "metadata_": dict(clan.metadata_ or {}),
            "context": dict(clan.context or {}),
            "source_context": dict(clan.source_context or {}),
            "lifecycle_status": clan.lifecycle_status,
            "archived_at": clan.archived_at,
            "expires_at": clan.expires_at,
            "schema_version": clan.schema_version,
            "created_at": clan.created_at,
            "updated_at": clan.updated_at,
            "visual": _visual((clan.flavor_content or {}).get("visual")),
            "gear_score_summary": summary,
            "members": [self._member_payload(member) for member in self._sort_members(members)]
            if include_members
            else [],
        }

    def _summary(self, clan: GeneratedClan, members: list[GeneratedMonster], *, role: str | None) -> dict[str, Any]:
        raw_summary = (clan.raw_tags or {}).get("gear_score_summary")
        if isinstance(raw_summary, dict) and role is None:
            return dict(raw_summary)
        return self.gear_score_service.build_clan_summary(members)

    @staticmethod
    def _member_payload(member: GeneratedMonster) -> dict[str, Any]:
        balance = _balance(member)
        return {
            "monster_id": str(member.id),
            "variant_key": member.variant_key,
            "role": member.role,
            "member_tier": member.member_tier,
            "name_ru": member.name_ru,
            "description": member.description or "",
            "text_content": dict(member.text_content or {}),
            "scaled_attributes": dict(member.scaled_attributes or {}),
            "scaled_skills": dict(member.scaled_skills or {}),
            "items": dict(member.items or {}),
            "vitals": dict(member.vitals or {}),
            "ai_profile": dict(member.ai_profile or {}),
            "generation_meta": dict(member.generation_meta or {}),
            "combat_actor_snapshot": dict(member.combat_actor_snapshot or {}),
            "metadata_": dict(member.metadata_ or {}),
            "context": dict(member.context or {}),
            "source_context": dict(member.source_context or {}),
            "lifecycle_status": member.lifecycle_status,
            "archived_at": member.archived_at,
            "expires_at": member.expires_at,
            "schema_version": member.schema_version,
            "created_at": member.created_at,
            "updated_at": member.updated_at,
            "threat_rating": member.threat_rating,
            "gear_score": _optional_int(balance.get("gear_score")),
            "base_cost": _optional_int(balance.get("base_cost")),
            "effective_cost": _optional_float(balance.get("effective_cost")),
            "visual": _visual((member.generation_meta or {}).get("visual")),
            "equipment_summary": _equipment_summary(member.items),
        }

    @staticmethod
    def _sort_members(members: list[GeneratedMonster]) -> list[GeneratedMonster]:
        return sorted(
            members,
            key=lambda member: (
                _optional_int(_balance(member).get("gear_score")) is None,
                _optional_int(_balance(member).get("gear_score")) or 0,
                member.role,
                member.variant_key,
            ),
        )


def _balance(member: GeneratedMonster) -> dict[str, Any]:
    generation_meta = member.generation_meta if isinstance(member.generation_meta, dict) else {}
    balance = generation_meta.get("balance")
    return dict(balance) if isinstance(balance, dict) else {}


def _visual(value: Any) -> dict[str, Any]:
    visual = dict(value) if isinstance(value, dict) else {}
    return {
        "status": str(visual.get("status") or ""),
        "source": str(visual.get("source") or ""),
        "image_url": str(visual.get("image_url") or ""),
        "generated_image_url": str(visual.get("generated_image_url") or ""),
        "fallback_image_url": str(visual.get("fallback_image_url") or ""),
        "storage_key": str(visual.get("storage_key") or ""),
        "storage_backend": str(visual.get("storage_backend") or ""),
        "asset_hash": str(visual.get("asset_hash") or ""),
        "content_type": str(visual.get("content_type") or ""),
        "size_bytes": _optional_int(visual.get("size_bytes")),
        "pending_task_id": str(visual.get("pending_task_id")) if visual.get("pending_task_id") else None,
    }


def _equipment_summary(items: dict[str, Any]) -> dict[str, list[str]]:
    if not isinstance(items, dict):
        return {"equipment": [], "weapons": [], "armor": [], "affixes": []}
    layout = dict(items.get("layout") or {})
    equipment_layout = dict(layout.get("equipment") or {})
    by_id = dict(items.get("by_id") or {})
    equipment: list[str] = []
    weapons: list[str] = []
    armor: list[str] = []
    affixes: list[str] = []

    for slot, item_id in sorted(equipment_layout.items()):
        item = dict(by_id.get(item_id) or {})
        label = str(item.get("name_ru") or item.get("name") or item.get("base_id") or item_id)
        row = f"{slot}: {label}"
        equipment.append(row)
        kind = str(item.get("kind") or item.get("item_kind") or "")
        if kind in {"weapon", "main_hand", "off_hand"} or slot in {"main_hand", "off_hand"}:
            weapons.append(row)
        if kind in {"armor", "body"} or slot == "body":
            armor.append(row)
        for affix in item.get("affixes") or item.get("bonus_ids") or []:
            affixes.append(str(affix))

    return {
        "equipment": equipment,
        "weapons": weapons,
        "armor": armor,
        "affixes": sorted(set(affixes)),
    }


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["GeneratedMonsterViewService"]
