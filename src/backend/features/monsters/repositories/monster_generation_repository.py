from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM, Monster

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class MonsterGenerationRepository:
    """Persistence adapter for generated monster ownership."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClan | None:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.unique_hash == unique_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        clan = await self.session.scalar(stmt)
        return _to_generated_clan(clan) if clan is not None else None

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.context_hash == context_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        result = await self.session.scalars(stmt)
        return [_to_generated_clan(clan) for clan in result.all()]

    async def get_clans_by_zone(self, zone_id: str) -> list[GeneratedClan]:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.zone_id == zone_id)
            .options(selectinload(GeneratedClanORM.members))
        )
        result = await self.session.scalars(stmt)
        return [_to_generated_clan(clan) for clan in result.all()]

    async def list_generated_clans(self, limit: int = 100) -> list[GeneratedClan]:
        stmt = (
            select(GeneratedClanORM)
            .options(selectinload(GeneratedClanORM.members))
            .order_by(GeneratedClanORM.zone_id, GeneratedClanORM.tier, GeneratedClanORM.family_id)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return [_to_generated_clan(clan) for clan in result.all()]

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]:
        stmt = (
            select(Monster)
            .where(Monster.clan_id == uuid.UUID(str(clan_id)))
            .options(selectinload(Monster.clan))
            .order_by(Monster.threat_rating, Monster.role)
        )
        result = await self.session.scalars(stmt)
        return [_to_generated_monster(monster) for monster in result.all()]

    async def create_clan_with_members(
        self,
        clan: GeneratedClan,
        members: Sequence[GeneratedMonster],
    ) -> GeneratedClan:
        log.debug(
            "MonsterGenerationRepository | action=create_clan_with_members clan_id={} members={}",
            clan.id,
            len(members),
        )
        clan_orm = _to_clan_orm(clan)
        member_orms = [_to_monster_orm(member) for member in members]
        clan_orm.members.extend(member_orms)
        self.session.add(clan_orm)
        self.session.add_all(member_orms)
        await self.session.flush()
        return _to_generated_clan(clan_orm)

    async def update_clan_flavor(self, clan: GeneratedClan) -> GeneratedClan:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.id == clan.id)
            .options(selectinload(GeneratedClanORM.members))
        )
        clan_orm = await self.session.scalar(stmt)
        if clan_orm is None:
            raise ValueError(f"Generated clan not found: {clan.id}")

        clan_orm.flavor_content = dict(clan.flavor_content)
        clan_orm.name_ru = clan.name_ru
        clan_orm.description = clan.description

        members_by_id = {member.id: member for member in clan.members}
        for member_orm in clan_orm.members:
            member = members_by_id.get(member_orm.id)
            if member is None:
                continue
            member_orm.name_ru = member.name_ru
            member_orm.description = member.description

        await self.session.flush()
        return _to_generated_clan(clan_orm)

    async def get_monsters_by_role_and_threat(
        self,
        role: str,
        min_threat: int,
        max_threat: int,
        limit: int = 5,
    ) -> list[GeneratedMonster]:
        stmt = (
            select(Monster)
            .where(Monster.role == role, Monster.threat_rating >= min_threat, Monster.threat_rating <= max_threat)
            .options(selectinload(Monster.clan))
            .order_by(Monster.threat_rating)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return [_to_generated_monster(monster) for monster in result.all()]


def _to_generated_clan(clan: GeneratedClanORM) -> GeneratedClan:
    generated = GeneratedClan(
        id=clan.id,
        family_id=clan.family_id,
        tier=clan.tier,
        zone_id=clan.zone_id,
        context_hash=clan.context_hash,
        unique_hash=clan.unique_hash,
        raw_tags=dict(clan.raw_tags or {}),
        flavor_content=dict(clan.flavor_content or {}),
        name_ru=clan.name_ru or "",
        description=clan.description or "",
    )
    generated.members.extend(_to_generated_monster(member, generated) for member in clan.members)
    return generated


def _to_generated_monster(monster: GeneratedMonsterORM, clan: GeneratedClan | None = None) -> GeneratedMonster:
    generated_clan = clan
    if generated_clan is None:
        monster_clan = getattr(monster, "clan", None)
        if monster_clan is not None:
            generated_clan = _to_generated_clan_without_members(monster_clan)
    return GeneratedMonster(
        id=monster.id,
        clan_id=monster.clan_id,
        variant_key=monster.variant_key,
        role=monster.role,
        member_tier=int(getattr(monster, "member_tier", 0) or 0),
        threat_rating=monster.threat_rating,
        name_ru=monster.name_ru,
        description=monster.description or "",
        text_content=dict(getattr(monster, "text_content", None) or {}),
        scaled_attributes=dict(monster.scaled_attributes or {}),
        scaled_skills=dict(monster.scaled_skills or {}),
        items=dict(monster.items or {}),
        vitals=dict(monster.vitals or {}),
        ai_profile=dict(monster.ai_profile or {}),
        generation_meta=dict(monster.generation_meta or {}),
        clan=generated_clan,
    )


def _to_generated_clan_without_members(clan: GeneratedClanORM) -> GeneratedClan:
    return GeneratedClan(
        id=clan.id,
        family_id=clan.family_id,
        tier=clan.tier,
        zone_id=clan.zone_id,
        context_hash=clan.context_hash,
        unique_hash=clan.unique_hash,
        raw_tags=dict(clan.raw_tags or {}),
        flavor_content=dict(clan.flavor_content or {}),
        name_ru=clan.name_ru or "",
        description=clan.description or "",
    )


def _to_clan_orm(clan: GeneratedClan) -> GeneratedClanORM:
    return GeneratedClanORM(
        id=clan.id,
        family_id=clan.family_id,
        tier=clan.tier,
        zone_id=clan.zone_id,
        context_hash=clan.context_hash,
        unique_hash=clan.unique_hash,
        raw_tags=dict(clan.raw_tags),
        flavor_content=dict(clan.flavor_content),
        name_ru=clan.name_ru,
        description=clan.description,
    )


def _to_monster_orm(monster: GeneratedMonster) -> GeneratedMonsterORM:
    return GeneratedMonsterORM(
        id=monster.id,
        clan_id=monster.clan_id,
        variant_key=monster.variant_key,
        role=monster.role,
        member_tier=monster.member_tier,
        threat_rating=monster.threat_rating,
        name_ru=monster.name_ru,
        description=monster.description,
        text_content=dict(monster.text_content),
        scaled_attributes=dict(monster.scaled_attributes),
        scaled_skills=dict(monster.scaled_skills),
        items=dict(monster.items),
        vitals=dict(monster.vitals),
        ai_profile=dict(monster.ai_profile),
        generation_meta=dict(monster.generation_meta),
    )


def _copy_json_collection(value: dict[str, Any] | list[Any] | None) -> dict[str, Any] | list[Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return {}
