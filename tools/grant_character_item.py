from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import redis.asyncio as redis

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.backend.config.settings import settings  # noqa: E402
from src.backend.core.arq import GENERATION_AI_ARQ_QUEUE, ArqService  # noqa: E402
from src.backend.core.database import get_session_context  # noqa: E402
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry  # noqa: E402
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository  # noqa: E402
from src.backend.features.generation_ai.services import GenerationAIService  # noqa: E402
from src.backend.features.items.integrations import ItemPersistenceIntegration  # noqa: E402
from src.backend.features.items.repositories import ItemInstanceRepository  # noqa: E402
from src.backend.features.items.services.admin_grant_service import AdminItemGrantService  # noqa: E402
from src.backend.features.items.services.generation_service import ItemGenerationService  # noqa: E402


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def parse_positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grant generated items to a character backpack.")
    parser.add_argument("--char-id", type=int, required=True)
    parser.add_argument("--base-id", required=True, help="Item base id, for example: warhammer, sword, leather_armor.")
    parser.add_argument("--rarity-tier", type=int, default=1)
    parser.add_argument("--count", type=parse_positive_int, default=1)
    parser.add_argument("--material-id", default=None)
    parser.add_argument("--item-grade", default="")
    parser.add_argument("--source", default="admin:grant_character_item")
    parser.add_argument("--monster-family-id", default=None)
    parser.add_argument("--member-role", default=None)
    parser.add_argument("--member-tier", type=int, default=None)
    parser.add_argument("--request-ai-text", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Actually write to DB. Without this, only validates args.")
    parser.add_argument(
        "--keep-inventory-session",
        action="store_true",
        help="Do not delete game:inventory:<char_id> from Redis after granting.",
    )
    return parser.parse_args()


def build_source_context(args: argparse.Namespace) -> dict[str, object]:
    source_context: dict[str, object] = {}
    if args.monster_family_id:
        source_context["monster_family_id"] = args.monster_family_id
        source_context["family_id"] = args.monster_family_id
    if args.member_role:
        source_context["member_role"] = args.member_role
    if args.member_tier is not None:
        source_context["member_tier"] = args.member_tier
    return source_context


async def grant_item(args: argparse.Namespace) -> None:
    results = []
    source_context = build_source_context(args)
    async with get_session_context() as session:
        generation_ai = None
        if args.request_ai_text:
            generation_ai = GenerationAIService(
                repository=AIGenerationTaskRepository(session),
                registry=build_generation_ai_registry(session=session),
                arq=ArqService(queue_name=GENERATION_AI_ARQ_QUEUE),
                auto_schedule=True,
            )
        service = AdminItemGrantService(
            session=session,
            item_generation=ItemGenerationService(ItemPersistenceIntegration(ItemInstanceRepository(session))),
            generation_ai=generation_ai,
        )
        for index in range(args.count):
            result = await service.grant_to_character(
                char_id=args.char_id,
                base_id=args.base_id,
                rarity_tier=args.rarity_tier,
                material_id=args.material_id,
                item_grade=args.item_grade,
                request_ai_text=args.request_ai_text,
                source=args.source,
                source_context=source_context,
                seed_suffix=str(index + 1),
            )
            results.append(result)
    if not args.keep_inventory_session:
        await invalidate_inventory_session(args.char_id)

    print("Granted items:")
    print(f"  char_id: {args.char_id}")
    print(f"  count: {len(results)}")
    if source_context:
        print(f"  source_context: {source_context}")
    for index, result in enumerate(results, start=1):
        print(f"  item_{index}:")
        print(f"    item_id: {result.item_id}")
        print(f"    template_id: {result.generated_template_id or '-'}")
        print(f"    text_visual_hash: {result.text_visual_hash or '-'}")
        print(f"    base_id: {result.base_id}")
        print(f"    rarity_tier: {result.rarity_tier}")
        print(f"    text_status: {result.text_status}")
        print(f"    ai_text_task_requested: {result.ai_text_task_requested}")
        print(f"    name: {result.name}")


async def invalidate_inventory_session(char_id: int) -> None:
    client = redis.from_url(settings.effective_redis_url, decode_responses=True)
    try:
        deleted = await client.delete(f"game:inventory:{char_id}")
        print(f"Invalidated Redis inventory session: {deleted}")
    finally:
        await client.aclose()


async def main() -> int:
    load_env_file(ROOT_DIR / ".env")
    args = parse_args()
    if not args.apply:
        print("DRY RUN: add --apply to create the item.")
        print(
            "Would grant "
            f"count={args.count} base_id={args.base_id!r} rarity_tier={args.rarity_tier} "
            f"material_id={args.material_id!r} source_context={build_source_context(args)!r} "
            f"to char_id={args.char_id}."
        )
        return 0
    await grant_item(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
