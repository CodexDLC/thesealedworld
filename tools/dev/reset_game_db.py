from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.config.settings import settings  # noqa: E402
from src.backend.core.database.session import async_engine  # noqa: E402

SITE_TABLES = {
    "alembic_version",
    "auth_refresh_tokens",
    "auth_users",
}

SCENARIO_CONTENT_TABLES = {
    "scenario_master",
    "scenario_nodes",
}

GAME_TABLES = [
    "character_quest_state",
    "character_skill_progress",
    "character_symbiotes",
    "character_attributes",
    "inventory_items",
    "resource_wallets",
    "item_transactions",
    "resource_transactions",
    "item_placements",
    "item_origins",
    "resource_balances",
    "item_instances",
    "generated_monsters",
    "generated_clans",
    "characters",
    "world_grid",
    "world_zones",
    "world_regions",
    "scenario_nodes",
    "scenario_master",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset game data in the current dev database while preserving site auth users.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually truncate tables. Without this flag the script prints a dry-run plan.",
    )
    parser.add_argument(
        "--keep-scenario-content",
        action="store_true",
        help="Do not truncate scenario_master/scenario_nodes, only character scenario state.",
    )
    return parser.parse_args()


def build_table_list(*, keep_scenario_content: bool) -> list[str]:
    tables = list(GAME_TABLES)
    if keep_scenario_content:
        tables = [table for table in tables if table not in SCENARIO_CONTENT_TABLES]
    return tables


def quote_table_names(tables: list[str]) -> str:
    return ", ".join(f'"{table}"' for table in tables)


async def truncate_game_tables(tables: list[str]) -> None:
    if not tables:
        return

    statement = text(f"TRUNCATE TABLE {quote_table_names(tables)} RESTART IDENTITY CASCADE")
    async with async_engine.begin() as conn:
        await conn.execute(statement)


def print_plan(tables: list[str], *, will_execute: bool) -> None:
    mode = "EXECUTE" if will_execute else "DRY RUN"
    print(f"Reset game DB | mode={mode}")
    print(f"Database URL: {settings.database_url}")
    print("Preserved site tables:")
    for table in sorted(SITE_TABLES):
        print(f"  - {table}")
    print("Tables to truncate:")
    for table in tables:
        print(f"  - {table}")


async def main() -> int:
    args = parse_args()
    tables = build_table_list(keep_scenario_content=args.keep_scenario_content)
    print_plan(tables, will_execute=args.yes)

    if not args.yes:
        print("\nNo changes made. Re-run with --yes to truncate these tables.")
        return 0

    await truncate_game_tables(tables)
    print("\nGame data reset complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
