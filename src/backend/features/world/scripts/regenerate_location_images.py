from __future__ import annotations

import argparse
import asyncio
from typing import Any

from sqlalchemy import delete, select, tuple_

from src.backend.core.arq import GENERATION_AI_ARQ_QUEUE, ArqService
from src.backend.core.database import get_manual_session_context
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.identity import build_generation_task_identity_key
from src.backend.features.generation_ai.models import AIGenerationTask
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.world.location_images import build_world_location_image_task_spec
from src.backend.features.world.resources.static.start_village import STATIC_LOCATIONS
from src.backend.infrastructure.world.models import WorldGrid

D4_TEST_LOCATION_IDS = ("52_52", "53_52", "52_53", "52_50", "50_50")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enqueue generated background images for D4 world locations.")
    parser.add_argument(
        "--scope",
        choices=("test", "all"),
        default="test",
        help="Use the approved 5-node D4 test batch or all 25 static D4 hub locations.",
    )
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
    parser.add_argument("--dry-run", action="store_true", help="Print tasks without writing DB changes.")
    return parser.parse_args()


async def async_main(args: argparse.Namespace | None = None) -> None:
    options = args or parse_args()
    arq = None if options.no_schedule or options.dry_run else ArqService(queue_name=GENERATION_AI_ARQ_QUEUE)
    if arq is not None:
        await arq.init()

    try:
        loc_ids = D4_TEST_LOCATION_IDS if options.scope == "test" else tuple(_static_loc_ids())
        async with get_manual_session_context() as session:
            nodes = await _load_nodes(session, loc_ids)
            specs = [_build_spec_from_node(node) for node in nodes]
            missing = sorted(set(loc_ids) - {f"{node.x}_{node.y}" for node in nodes})

            if options.dry_run:
                print(f"dry-run scope={options.scope} nodes={len(nodes)} missing={missing} tasks={len(specs)}")
                for spec in specs:
                    print(f"{spec.entity_id} -> {spec.input_payload['storage_key']}")
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
                f"world location image generation queued scope={options.scope} nodes={len(nodes)} missing={missing} "
                f"tasks={len(specs)} created={getattr(result, 'created', 0)} reused={getattr(result, 'reused', 0)} "
                f"scheduled={scheduled}"
            )
    finally:
        if arq is not None:
            await arq.close()


async def _load_nodes(session: Any, loc_ids: tuple[str, ...]) -> list[WorldGrid]:
    coords = [_parse_loc_id(loc_id) for loc_id in loc_ids]
    stmt = select(WorldGrid).where(tuple_(WorldGrid.x, WorldGrid.y).in_(coords)).order_by(WorldGrid.y, WorldGrid.x)
    return list((await session.scalars(stmt)).all())


def _build_spec_from_node(node: WorldGrid):
    loc_id = f"{node.x}_{node.y}"
    content = dict(node.content or {})
    return build_world_location_image_task_spec(
        loc_id=loc_id,
        title=str(content.get("title") or loc_id),
        description=str(content.get("description") or ""),
        biome_id=str(node.biome_id or ""),
        terrain_type=str(node.terrain_type or ""),
        environment_tags=[str(tag) for tag in content.get("environment_tags") or []],
        visual_overrides=dict(node.visual_overrides or {}),
        region_id="D4",
    )


def _parse_loc_id(loc_id: str) -> tuple[int, int]:
    x, y = loc_id.split("_", 1)
    return int(x), int(y)


def _static_loc_ids() -> list[str]:
    return [f"{x}_{y}" for x, y in STATIC_LOCATIONS]


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
