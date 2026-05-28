from __future__ import annotations

import argparse
import asyncio
import uuid
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from src.backend.core.database import get_session_context
from src.backend.features.items.services.generation_service import ItemGenerationService
from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster, MonsterGenerationContext
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.runtime.generation_builder import MonsterClanGenerationBuilder, _MemberPlan
from src.backend.features.monsters.runtime.hashing import normalize_tags
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


class _NoopGenerationRepository:
    async def get_clan_by_unique_hash(self, unique_hash: str) -> None:
        del unique_hash
        return None

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        del context_hash
        return []

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]:
        del clan_id
        return []

    async def create_clan_with_members(self, clan: GeneratedClan, members: list[GeneratedMonster]) -> GeneratedClan:
        del clan, members
        raise RuntimeError("rebuild_generated_monsters must not create clans through the generator repository")

    async def update_clan_flavor(self, clan: GeneratedClan) -> GeneratedClan:
        return clan


async def _run(args: argparse.Namespace) -> None:
    builder = MonsterClanGenerationBuilder(
        repository=_NoopGenerationRepository(),
        item_generation=ItemGenerationService(),
    )
    gear_score_service = MonsterGearScoreService()
    async with get_session_context() as session:
        stmt = (
            select(GeneratedClanORM)
            .options(selectinload(GeneratedClanORM.members))
            .order_by(GeneratedClanORM.family_id, GeneratedClanORM.tier, GeneratedClanORM.id)
            .limit(int(args.limit))
            .offset(int(args.offset))
        )
        if args.family_id:
            stmt = stmt.where(GeneratedClanORM.family_id == args.family_id)
        if args.clan_id:
            stmt = stmt.where(GeneratedClanORM.id == uuid.UUID(str(args.clan_id)))

        result = await session.scalars(stmt)
        clan_rows = list(result.all())
        report = _RebuildReport()
        for clan_row in clan_rows:
            rebuilt = await rebuild_clan_from_resources(clan_row, builder=builder)
            report.clans += 1
            report.monsters += len(rebuilt.members)
            if args.dry_run:
                continue

            existing_variant_count = len({member.variant_key for member in clan_row.members})
            _apply_clan_rebuild(
                clan_row,
                rebuilt,
                gear_score_service=gear_score_service,
                create_missing=not args.no_create_missing,
                prune_obsolete=bool(args.prune_obsolete),
            )
            report.created += max(0, len(rebuilt.members) - existing_variant_count)

        if args.dry_run:
            await session.rollback()

    print(
        "MonsterGeneratedRebuild | "
        f"clans={report.clans} monsters={report.monsters} dry_run={bool(args.dry_run)} "
        f"created={report.created} limit={args.limit} offset={args.offset}"
    )


async def rebuild_clan_from_resources(
    clan_row: GeneratedClanORM,
    *,
    builder: MonsterClanGenerationBuilder,
) -> GeneratedClan:
    family = get_family_config(clan_row.family_id)
    if family is None:
        raise ValueError(f"Unknown monster family for generated clan {clan_row.id}: {clan_row.family_id}")

    context = _context_from_clan_row(clan_row)
    member_plans = builder._build_member_plans(family, context)
    member_plans = _plans_with_existing_member_ids(member_plans, clan_row.members)
    item_requests = builder._build_item_requests(family, member_plans, clan_row.unique_hash)
    runtime_items = await builder._generate_runtime_items(item_requests)
    flavor = _flavor_for_rebuild(clan_row)
    rebuilt = GeneratedClan(
        id=clan_row.id,
        family_id=clan_row.family_id,
        tier=clan_row.tier,
        zone_id=clan_row.zone_id,
        context_hash=clan_row.context_hash,
        unique_hash=clan_row.unique_hash,
        raw_tags=_raw_tags_for_rebuild(clan_row, context, member_plans),
        flavor_content=dict(clan_row.flavor_content or {}),
        name_ru=clan_row.name_ru or "",
        description=clan_row.description or "",
        metadata_=dict(clan_row.metadata_ or {}),
        context=dict(clan_row.context or {}),
        source_context=dict(clan_row.source_context or {}),
        lifecycle_status=str(clan_row.lifecycle_status or "active"),
        archived_at=clan_row.archived_at,
        expires_at=clan_row.expires_at,
        schema_version=int(clan_row.schema_version or 1),
        created_at=clan_row.created_at,
        updated_at=clan_row.updated_at,
    )
    rebuilt.members.extend(
        builder._build_member_row(
            clan_id=rebuilt.id,
            family=family,
            plan=plan,
            runtime_items=runtime_items,
            flavor=flavor,
            context=context,
            unique_hash=rebuilt.unique_hash,
        )
        for plan in member_plans
    )
    for member in rebuilt.members:
        member.clan = rebuilt
    return rebuilt


def _context_from_clan_row(clan_row: GeneratedClanORM) -> MonsterGenerationContext:
    raw_tags = dict(clan_row.raw_tags or {})
    biome_id = str(clan_row.biome_id or raw_tags.get("biome_id") or "wasteland")
    tags = raw_tags.get("tags")
    context_meta = raw_tags.get("context_meta")
    return MonsterGenerationContext(
        zone_id=str(clan_row.zone_id or ""),
        biome_id=biome_id,
        tier=int(clan_row.tier or 0),
        tags=[str(tag) for tag in tags] if isinstance(tags, list) else [],
        difficulty=str(raw_tags.get("difficulty") or "mid"),
        context_meta=dict(context_meta) if isinstance(context_meta, dict) else {},
    )


def _plans_with_existing_member_ids(
    member_plans: list[_MemberPlan],
    existing_members: list[GeneratedMonsterORM],
) -> list[_MemberPlan]:
    existing_by_variant = {member.variant_key: member for member in existing_members}
    stable_plans: list[_MemberPlan] = []
    for plan in member_plans:
        existing = existing_by_variant.get(plan.variant.id)
        if existing is None:
            stable_plans.append(plan)
            continue
        stable_plans.append(replace(plan, member_id=existing.id, owner_key=str(existing.id)))
    return stable_plans


def _flavor_for_rebuild(clan_row: GeneratedClanORM) -> dict[str, Any]:
    flavor = dict(clan_row.flavor_content or {})
    if isinstance(flavor.get("variants_flavor"), dict):
        return flavor
    return {}


def _raw_tags_for_rebuild(
    clan_row: GeneratedClanORM,
    context: MonsterGenerationContext,
    member_plans: list[_MemberPlan],
) -> dict[str, Any]:
    raw_tags = dict(clan_row.raw_tags or {})
    raw_tags.update(
        {
            "schema_version": 2,
            "tags": normalize_tags(context.tags),
            "biome_id": context.biome_id,
            "difficulty": context.difficulty,
            "variant_window": {"min_tier": 0, "max_tier": min(7, context.tier + 1)},
            "composition": [plan.variant.id for plan in member_plans],
            "context_meta": dict(context.context_meta),
        }
    )
    return raw_tags


def _apply_clan_rebuild(
    clan_row: GeneratedClanORM,
    rebuilt: GeneratedClan,
    *,
    gear_score_service: MonsterGearScoreService,
    create_missing: bool,
    prune_obsolete: bool,
) -> None:
    existing_by_variant = {member.variant_key: member for member in clan_row.members}
    rebuilt_by_variant = {member.variant_key: member for member in rebuilt.members}

    clan_row.raw_tags = dict(rebuilt.raw_tags)
    flag_modified(clan_row, "raw_tags")

    for variant_key, rebuilt_member in rebuilt_by_variant.items():
        existing = existing_by_variant.get(variant_key)
        if existing is None:
            if not create_missing:
                continue
            existing = _new_member_row(rebuilt_member)
            clan_row.members.append(existing)
        _apply_member_rebuild(existing, rebuilt_member)

    if prune_obsolete:
        clan_row.members[:] = [member for member in clan_row.members if member.variant_key in rebuilt_by_variant]

    clan = GeneratedClan(
        id=clan_row.id,
        family_id=clan_row.family_id,
        tier=clan_row.tier,
        zone_id=clan_row.zone_id,
        context_hash=clan_row.context_hash,
        unique_hash=clan_row.unique_hash,
        raw_tags=dict(clan_row.raw_tags or {}),
        flavor_content=dict(clan_row.flavor_content or {}),
        name_ru=clan_row.name_ru or "",
        description=clan_row.description or "",
        members=[_generated_member_from_row(member, clan_row) for member in clan_row.members],
    )
    gear_score_service.apply_clan_summary(clan)
    clan_row.raw_tags = dict(clan.raw_tags)
    flag_modified(clan_row, "raw_tags")


def _apply_member_rebuild(member_row: GeneratedMonsterORM, rebuilt: GeneratedMonster) -> None:
    existing_meta = dict(member_row.generation_meta or {})
    rebuilt_meta = dict(rebuilt.generation_meta or {})
    visual = existing_meta.get("visual")
    if isinstance(visual, dict):
        rebuilt_meta["visual"] = visual

    member_row.role = rebuilt.role
    member_row.member_tier = rebuilt.member_tier
    member_row.threat_rating = rebuilt.threat_rating
    if not member_row.name_ru:
        member_row.name_ru = rebuilt.name_ru
    if not member_row.description:
        member_row.description = rebuilt.description
    if not member_row.text_content:
        member_row.text_content = dict(rebuilt.text_content)
        flag_modified(member_row, "text_content")
    member_row.scaled_attributes = dict(rebuilt.scaled_attributes)
    member_row.scaled_skills = dict(rebuilt.scaled_skills)
    member_row.items = dict(rebuilt.items)
    member_row.vitals = dict(rebuilt.vitals)
    member_row.ai_profile = dict(rebuilt.ai_profile)
    member_row.generation_meta = rebuilt_meta
    member_row.combat_actor_snapshot = dict(rebuilt.combat_actor_snapshot or {})

    for field_name in (
        "scaled_attributes",
        "scaled_skills",
        "items",
        "vitals",
        "ai_profile",
        "generation_meta",
        "combat_actor_snapshot",
    ):
        flag_modified(member_row, field_name)


def _new_member_row(member: GeneratedMonster) -> GeneratedMonsterORM:
    return GeneratedMonsterORM(
        id=member.id,
        clan_id=member.clan_id,
        variant_key=member.variant_key,
        role=member.role,
        member_tier=member.member_tier,
        threat_rating=member.threat_rating,
        name_ru=member.name_ru,
        description=member.description,
        text_content=dict(member.text_content),
        scaled_attributes=dict(member.scaled_attributes),
        scaled_skills=dict(member.scaled_skills),
        items=dict(member.items),
        vitals=dict(member.vitals),
        ai_profile=dict(member.ai_profile),
        generation_meta=dict(member.generation_meta),
        combat_actor_snapshot=dict(member.combat_actor_snapshot or {}),
    )


def _generated_member_from_row(member: GeneratedMonsterORM, clan_row: GeneratedClanORM) -> GeneratedMonster:
    return GeneratedMonster(
        id=member.id,
        clan_id=member.clan_id,
        variant_key=member.variant_key,
        role=member.role,
        member_tier=int(member.member_tier or 0),
        threat_rating=int(member.threat_rating or 0),
        name_ru=member.name_ru,
        description=member.description or "",
        text_content=dict(member.text_content or {}),
        scaled_attributes=dict(member.scaled_attributes or {}),
        scaled_skills=dict(member.scaled_skills or {}),
        items=dict(member.items or {}),
        vitals=dict(member.vitals or {}),
        ai_profile=dict(member.ai_profile or {}),
        generation_meta=dict(member.generation_meta or {}),
        combat_actor_snapshot=dict(member.combat_actor_snapshot or {}),
        clan=GeneratedClan(
            id=clan_row.id,
            family_id=clan_row.family_id,
            tier=clan_row.tier,
            zone_id=clan_row.zone_id,
            context_hash=clan_row.context_hash,
            unique_hash=clan_row.unique_hash,
            raw_tags=dict(clan_row.raw_tags or {}),
            flavor_content=dict(clan_row.flavor_content or {}),
            name_ru=clan_row.name_ru or "",
            description=clan_row.description or "",
        ),
    )


@dataclass(slots=True)
class _RebuildReport:
    clans: int = 0
    monsters: int = 0
    created: int = 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild generated monster rows from current family resources without enqueueing image tasks."
    )
    parser.add_argument("--family-id", default=None)
    parser.add_argument("--clan-id", default=None)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-create-missing", action="store_true")
    parser.add_argument("--prune-obsolete", action="store_true")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
