"""Run starter imprint vs monster family pressure simulations."""

from __future__ import annotations

import argparse
import asyncio
import random

from src.backend.core.database import async_session_factory
from src.backend.features.combat.runtime.simulation import (
    DEFAULT_STARTER_SIMULATION_IMPRINTS,
    FamilyPressureConfig,
    FamilyPressureSimulator,
    format_family_pressure_report,
)
from src.backend.features.monsters.repositories.monster_generation_repository import MonsterGenerationRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe a starter imprint against a generated monster family ladder.")
    parser.add_argument("--family", default="rat_swarm", help="Monster family id, e.g. rat_swarm")
    parser.add_argument("--imprint", default="", help="Starting imprint key. Empty means seeded random.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--max-rounds", type=int, default=80)
    parser.add_argument("--max-minions", type=int, default=6)
    parser.add_argument("--max-scenarios", type=int, default=24)
    return parser.parse_args()


async def async_main(args: argparse.Namespace | None = None) -> None:
    options = args or parse_args()
    imprint = options.imprint.strip() or random.Random(options.seed).choice(DEFAULT_STARTER_SIMULATION_IMPRINTS)
    async with async_session_factory() as session:
        repository = MonsterGenerationRepository(session)
        clans = await repository.list_generated_clans_page(family_id=options.family, limit=100)
        members = [member for clan in clans for member in clan.members]

    report = await FamilyPressureSimulator().run(
        family_id=options.family,
        imprint_key=imprint,
        members=members,
        seed=options.seed,
        config=FamilyPressureConfig(
            trials_per_composition=max(1, int(options.trials)),
            max_rounds=max(1, int(options.max_rounds)),
            max_minions=max(1, int(options.max_minions)),
            max_scenarios=max(1, int(options.max_scenarios)),
        ),
    )
    print(format_family_pressure_report(report))


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
