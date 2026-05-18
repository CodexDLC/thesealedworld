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
        return GeneratedMonstersResponseDTO(
            items=[self._clan_payload(clan, role=role, include_members=include_members) for clan in clans],
            pagination={
                "limit": limit,
                "offset": offset,
                "total": total,
                "has_more": offset + limit < total,
            },
        )

    def _clan_payload(self, clan: GeneratedClan, *, role: str | None, include_members: bool) -> dict[str, Any]:
        members = [member for member in clan.members if role is None or member.role == role]
        summary = self._summary(clan, members, role=role)
        return {
            "clan_id": str(clan.id),
            "family_id": clan.family_id,
            "tier": clan.tier,
            "zone_id": clan.zone_id,
            "name_ru": clan.name_ru,
            "description": clan.description,
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
            "threat_rating": member.threat_rating,
            "gear_score": _optional_int(balance.get("gear_score")),
            "base_cost": _optional_int(balance.get("base_cost")),
            "effective_cost": _optional_float(balance.get("effective_cost")),
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
