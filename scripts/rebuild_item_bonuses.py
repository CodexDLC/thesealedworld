from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from src.backend.core.database import get_manual_session_context
from src.backend.features.items.models import ItemInstance
from src.backend.features.items.runtime import ItemFactory


@dataclass
class RebuildReport:
    scanned: int = 0
    rebuilt: int = 0
    unchanged: int = 0
    missing_affixes: int = 0
    no_mechanics: int = 0
    dry_run: bool = False

    def log(self) -> None:
        print(
            "rebuild_item_bonuses "
            f"dry_run={self.dry_run} "
            f"scanned={self.scanned} rebuilt={self.rebuilt} unchanged={self.unchanged} "
            f"missing_affixes={self.missing_affixes} no_mechanics={self.no_mechanics}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild item mechanics.bonuses from affixes for legacy items.")
    parser.add_argument("--item-id", help="Rebuild only this item id (skip all others).")
    parser.add_argument("--force", action="store_true", help="Recompile even when bonuses is already present.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing DB.")
    return parser.parse_args()


def _repair_bonuses(mechanics: dict[str, Any], *, force: bool) -> tuple[bool, dict[str, str] | None]:
    if not isinstance(mechanics, dict):
        return False, None

    affixes = mechanics.get("affixes")
    if not isinstance(affixes, list) or not affixes:
        return False, None

    bonuses = mechanics.get("bonuses")
    if not force and isinstance(bonuses, dict) and bonuses:
        return False, None

    rebuilt = ItemFactory._compile_affix_bonuses(affixes)
    if not rebuilt:
        return False, None

    if bonuses == rebuilt:
        return False, None

    updated = dict(mechanics)
    updated["bonuses"] = rebuilt
    return True, updated


async def rebuild_item_bonuses(*, item_id: str | None = None, force: bool = False, dry_run: bool = False) -> RebuildReport:
    report = RebuildReport(dry_run=dry_run)

    async with get_manual_session_context() as session:
        stmt = select(ItemInstance.id, ItemInstance.mechanics)
        if item_id is not None:
            stmt = stmt.where(ItemInstance.id == item_id)

        result = await session.execute(stmt)
        for item_id_raw, mechanics_raw in result.all():
            report.scanned += 1
            item_id_str = str(item_id_raw)
            mechanics = dict(mechanics_raw or {})
            if not mechanics:
                report.no_mechanics += 1
                continue

            if "affixes" not in mechanics:
                report.missing_affixes += 1
                continue

            changed, updated = _repair_bonuses(mechanics, force=force)
            if not changed:
                report.unchanged += 1
                continue

            report.rebuilt += 1
            if dry_run:
                continue

            await session.execute(
                select(ItemInstance).where(ItemInstance.id == item_id_str).execution_options(populate_existing=True)
            )
            await session.execute(ItemInstance.__table__.update().where(ItemInstance.id == item_id_str).values(mechanics=updated))

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    return report


def main() -> None:
    args = parse_args()
    report = asyncio.run(
        rebuild_item_bonuses(
            item_id=args.item_id,
            force=args.force,
            dry_run=args.dry_run,
        )
    )
    report.log()


if __name__ == "__main__":
    main()
