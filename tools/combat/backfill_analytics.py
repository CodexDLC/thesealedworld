from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from src.backend.core.database import get_session_context
from src.backend.features.combat.runtime.analytics import CombatAnalyticsIngestionService
from src.backend.infrastructure.combat.models import CombatFinalization
from src.backend.infrastructure.combat.repositories import CombatAnalyticsRepository


def _parse_day(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)


async def _run(args: argparse.Namespace) -> None:
    start = _parse_day(args.from_date)
    end = _parse_day(args.to_date) + timedelta(days=1)

    async with get_session_context() as session:
        result = await session.execute(
            select(CombatFinalization)
            .where(CombatFinalization.finished_at >= start)
            .where(CombatFinalization.finished_at < end)
            .order_by(CombatFinalization.finished_at.asc(), CombatFinalization.id.asc())
        )
        finalizations = result.scalars().all()
        repo = CombatAnalyticsRepository(session)

        extracted: list[dict[str, Any]] = []
        for finalization in finalizations:
            facts = CombatAnalyticsIngestionService.extract_exchange_facts(finalization.finalization)  # type: ignore
            await repo.replace_facts_for_combat(finalization.combat_id, facts)
            extracted.extend(facts)

        rollup_facts = await repo.facts_for_buckets(start=start, end=end)
        rollups = CombatAnalyticsIngestionService.build_rollups(
            rollup_facts,
            aggregate_version=int(args.aggregate_version),
        )
        await repo.replace_rollups(
            rollups,
            aggregate_version=int(args.aggregate_version),
            start=start,
            end=end,
        )
        await session.commit()

    print(
        "CombatAnalyticsBackfill | "
        f"finalizations={len(finalizations)} facts={len(extracted)} rollups={len(rollups)} "
        f"aggregate_version={args.aggregate_version}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill combat analytics facts and balance rollups.")
    parser.add_argument("--from", dest="from_date", required=True, help="Inclusive start date, YYYY-MM-DD.")
    parser.add_argument("--to", dest="to_date", required=True, help="Inclusive end date, YYYY-MM-DD.")
    parser.add_argument("--aggregate-version", type=int, default=1)
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
