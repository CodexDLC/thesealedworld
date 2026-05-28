from __future__ import annotations

import argparse
import asyncio
import json

from src.backend.core.database import get_manual_session_context
from src.backend.features.monsters.dto.generated_view import MonsterDataRebuildRequestDTO
from src.backend.features.monsters.services.generated_rebuild_service import MonsterGeneratedRebuildService


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild generated monster mechanics from current resources.")
    parser.add_argument("--family-id", help="Only rebuild one monster family, e.g. bandit_gang.")
    parser.add_argument("--clan-id", help="Only rebuild one generated clan UUID.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum clans to scan.")
    parser.add_argument("--force", action="store_true", help="Rebuild selected clans even if no drift is detected.")
    parser.add_argument(
        "--keep-obsolete-members",
        action="store_true",
        help="Do not remove members whose variant no longer exists in current resources.",
    )
    parser.add_argument("--apply", action="store_true", help="Write changes. Without this flag the command is dry-run.")
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace | None = None) -> None:
    options = args or parse_args()
    request = MonsterDataRebuildRequestDTO(
        family_id=options.family_id,
        clan_id=options.clan_id,
        limit=options.limit,
        force=options.force,
        remove_obsolete_members=not options.keep_obsolete_members,
    )
    async with get_manual_session_context() as session:
        service = MonsterGeneratedRebuildService(session=session)
        result = await service.apply(request) if options.apply else await service.plan(request)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
