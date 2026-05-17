from __future__ import annotations

import argparse
import asyncio
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from src.backend.core.arq import GENERATION_AI_ARQ_QUEUE, ArqService
from src.backend.core.database import get_manual_session_context
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.identity import build_generation_task_identity_key
from src.backend.features.generation_ai.models import AIGenerationTask
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.visuals import build_clan_visual, build_member_visual
from src.backend.features.monsters.tasks_ai import (
    build_monster_clan_image_task_spec_from_orm,
    build_monster_member_image_task_spec_from_orm,
)
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild generated monster image visuals and enqueue image tasks.")
    parser.add_argument(
        "--scope",
        choices=("all", "clans", "members"),
        default="all",
        help="Which image visuals to rebuild.",
    )
    parser.add_argument("--family-id", help="Only rebuild one monster family, e.g. goblin_tribe.")
    parser.add_argument("--limit", type=int, help="Limit clans processed for a small test run.")
    parser.add_argument(
        "--no-schedule",
        action="store_true",
        help="Create pending tasks without pushing them to ARQ.",
    )
    parser.add_argument(
        "--replace-existing-tasks",
        action="store_true",
        help="Delete existing tasks with the same visual identity before enqueueing new tasks.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print counts without writing DB changes.")
    return parser.parse_args()


async def async_main(args: argparse.Namespace | None = None) -> None:
    options = args or parse_args()
    arq = None if options.no_schedule or options.dry_run else ArqService(queue_name=GENERATION_AI_ARQ_QUEUE)
    if arq is not None:
        await arq.init()

    try:
        async with get_manual_session_context() as session:
            stmt = (
                select(GeneratedClanORM)
                .options(selectinload(GeneratedClanORM.members))
                .order_by(GeneratedClanORM.created_at)
            )
            if options.family_id:
                stmt = stmt.where(GeneratedClanORM.family_id == options.family_id)
            if options.limit:
                stmt = stmt.limit(options.limit)

            clans = list((await session.scalars(stmt)).all())
            specs = []
            rebuilt_clans = 0
            rebuilt_members = 0

            for clan in clans:
                if options.scope in {"all", "clans"}:
                    _rebuild_clan_visual(clan)
                    specs.append(build_monster_clan_image_task_spec_from_orm(clan))
                    rebuilt_clans += 1

                if options.scope in {"all", "members"}:
                    for member in clan.members:
                        _rebuild_member_visual(member, clan)
                        specs.append(build_monster_member_image_task_spec_from_orm(member, clan=clan))
                        rebuilt_members += 1

            if options.dry_run:
                print(
                    f"dry-run clans={len(clans)} rebuilt_clans={rebuilt_clans} "
                    f"rebuilt_members={rebuilt_members} tasks={len(specs)}"
                )
                return

            service = GenerationAIService(
                repository=AIGenerationTaskRepository(session),
                registry=build_generation_ai_registry(session=session),
                arq=arq,
                auto_schedule=False,
            )
            if options.replace_existing_tasks and specs:
                identity_keys = [build_generation_task_identity_key(spec) for spec in specs]
                await session.execute(delete(AIGenerationTask).where(AIGenerationTask.identity_key.in_(identity_keys)))
                await session.flush()
            result = await service.enqueue_many(specs) if specs else None
            await session.commit()
            scheduled = 0 if options.no_schedule else await service.schedule_pending_task_ids()
            print(
                f"monster image regeneration queued clans={rebuilt_clans} members={rebuilt_members} "
                f"tasks={len(specs)} created={getattr(result, 'created', 0)} reused={getattr(result, 'reused', 0)} "
                f"scheduled={scheduled}"
            )
    finally:
        if arq is not None:
            await arq.close()


def _rebuild_clan_visual(clan: GeneratedClanORM) -> None:
    flavor_content = dict(clan.flavor_content or {})
    context_tags = list((clan.raw_tags or {}).get("tags") or [])
    flavor_content["visual"] = build_clan_visual(
        clan.family_id,
        clan_name=clan.name_ru or clan.family_id,
        description=clan.description or "",
        context_tags=context_tags,
        member_roster=_member_roster(clan),
    )
    clan.flavor_content = flavor_content
    flag_modified(clan, "flavor_content")


def _rebuild_member_visual(member: GeneratedMonsterORM, clan: GeneratedClanORM) -> None:
    generation_meta = dict(member.generation_meta or {})
    generation_meta["visual"] = build_member_visual(
        clan.family_id,
        variant_key=member.variant_key,
        role=member.role,
        member_name=member.name_ru or member.variant_key,
        appearance=_member_appearance(member),
    )
    member.generation_meta = generation_meta
    flag_modified(member, "generation_meta")


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


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
