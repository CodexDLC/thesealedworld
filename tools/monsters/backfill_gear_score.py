from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from src.backend.core.database import get_session_context
from src.backend.features.monsters.repositories.monster_generation_repository import _to_generated_clan
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.infrastructure.monsters import GeneratedClanORM


async def _run(args: argparse.Namespace) -> None:
    service = MonsterGearScoreService()
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
        monster_count = 0
        for clan_row in clan_rows:
            clan = _to_generated_clan(clan_row)
            for member in clan.members:
                service.apply_monster_gear_score(member)
            service.apply_clan_summary(clan)
            monster_count += len(clan.members)

            if args.dry_run:
                continue

            members_by_id = {member.id: member for member in clan.members}
            for member_row in clan_row.members:
                member = members_by_id.get(member_row.id)
                if member is None:
                    continue
                _apply_member_backfill(member_row, member)
            clan_row.raw_tags = dict(clan.raw_tags)
            flag_modified(clan_row, "raw_tags")

        if args.dry_run:
            await session.rollback()

    print(
        "MonsterGearScoreBackfill | "
        f"clans={len(clan_rows)} monsters={monster_count} dry_run={bool(args.dry_run)} "
        f"limit={args.limit} offset={args.offset}"
    )


def _apply_member_backfill(member_row: object, member: object) -> None:
    member_row.generation_meta = dict(member.generation_meta)
    member_row.threat_rating = int(member.threat_rating)
    flag_modified(member_row, "generation_meta")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill generated monster gear score analytics.")
    parser.add_argument("--family-id", default=None)
    parser.add_argument("--clan-id", default=None)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
