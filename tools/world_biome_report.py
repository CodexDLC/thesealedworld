from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.backend.config.settings import settings
from src.backend.features.world.runtime.config import REGION_ROWS


@dataclass(frozen=True)
class ZoneRow:
    region_id: str
    zone_id: str
    biome_id: str
    anomaly_id: str | None
    dominant_anchor: str | None
    tier: int
    secondary_biomes: tuple[str, ...]
    biome_mix: dict[str, float]


BIOME_GLYPHS = {
    "badlands": "B",
    "canyon": "C",
    "city_ruins": "R",
    "forest": "F",
    "grassland": "G",
    "highlands": "H",
    "hills": "h",
    "jungle": "J",
    "marsh": "m",
    "meadow": "M",
    "mountains": "^",
    "savanna": "S",
    "swamp": "W",
    "wasteland": ".",
}

ANOMALY_GLYPHS = {
    "bio_mutation": "B",
    "entropy": "E",
    "gravity": "G",
    "stasis": "S",
}


async def main() -> None:
    args = parse_args()
    urls = candidate_urls(args.db)
    selected_name, rows, counts = await load_first_world(urls)

    print(f"database: {selected_name}")
    print(f"regions={counts['regions']} zones={counts['zones']} active_nodes={counts['active_nodes']} clans={counts['clans']} monsters={counts['monsters']}")
    print()
    print_counter("biomes", Counter(row.biome_id for row in rows), len(rows))
    print_counter("anomalies", Counter(row.anomaly_id or "none" for row in rows), len(rows))
    print_counter("tiers", Counter(str(row.tier) for row in rows), len(rows))
    print()
    print("7x7 regions by dominant zone biome")
    print_region_grid(rows)
    print()
    print("21x21 zones by biome")
    print_zone_grid(rows, attr="biome_id", glyphs=BIOME_GLYPHS)
    print()
    print("21x21 zones by anomaly")
    print_zone_grid(rows, attr="anomaly_id", glyphs=ANOMALY_GLYPHS, empty=".")
    print()
    print("legend")
    print_legend(BIOME_GLYPHS, sorted({row.biome_id for row in rows}))
    print_legend(ANOMALY_GLYPHS, sorted({row.anomaly_id for row in rows if row.anomaly_id}), prefix="anomaly")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a read-only summary of generated world biomes and anomalies.")
    parser.add_argument("--db", choices=["auto", "site", "game", "default"], default="auto")
    return parser.parse_args()


def candidate_urls(db: str) -> list[tuple[str, str]]:
    mapping = {
        "default": [("default", settings.database_url)],
        "site": [("site", settings.site_database_url)],
        "game": [("game", settings.game_database_url)],
        "auto": [
            ("default", settings.database_url),
            ("site", settings.site_database_url),
            ("game", settings.game_database_url),
        ],
    }
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for name, url in mapping[db]:
        if url in seen:
            continue
        seen.add(url)
        result.append((name, url))
    return result


async def load_first_world(urls: list[tuple[str, str]]) -> tuple[str, list[ZoneRow], dict[str, int]]:
    errors: list[str] = []
    for name, url in urls:
        try:
            rows, counts = await load_world(name, url)
        except Exception as exc:
            errors.append(f"{name}: {exc.__class__.__name__}: {exc}")
            continue
        if rows:
            return name, rows, counts
        errors.append(f"{name}: no world_zones rows")
    raise SystemExit("No generated world found.\n" + "\n".join(errors))


async def load_world(name: str, url: str) -> tuple[list[ZoneRow], dict[str, int]]:
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            rows_result = await conn.execute(
                text(
                    """
                    SELECT id, region_id, biome_id, tier, flags
                    FROM world_zones
                    ORDER BY region_id, id
                    """
                )
            )
            zones = [zone_row(row) for row in rows_result.mappings().all()]
            counts = {
                "regions": await scalar_count(conn, "world_regions"),
                "zones": await scalar_count(conn, "world_zones"),
                "active_nodes": await scalar_count(conn, "world_grid", "WHERE is_active"),
                "clans": await scalar_count(conn, "generated_clans"),
                "monsters": await scalar_count(conn, "generated_monsters"),
            }
    finally:
        await engine.dispose()
    return zones, counts


async def scalar_count(conn: Any, table: str, where: str = "") -> int:
    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table} {where}"))
    return int(result.scalar_one())


def zone_row(row: Any) -> ZoneRow:
    flags = row["flags"] if isinstance(row["flags"], dict) else {}
    return ZoneRow(
        region_id=str(row["region_id"]),
        zone_id=str(row["id"]),
        biome_id=str(row["biome_id"]),
        anomaly_id=maybe_str(flags.get("anomaly_id")),
        dominant_anchor=maybe_str(flags.get("dominant_anchor")),
        tier=int(row["tier"]),
        secondary_biomes=tuple(str(item) for item in flags.get("secondary_biomes", []) if item),
        biome_mix={str(key): float(value) for key, value in flags.get("biome_mix", {}).items()},
    )


def maybe_str(value: Any) -> str | None:
    return str(value) if value else None


def print_counter(title: str, counter: Counter[str], total: int) -> None:
    print(title)
    for key, count in counter.most_common():
        pct = count / total * 100 if total else 0
        print(f"  {key:16} {count:3d} {pct:5.1f}%")


def print_region_grid(rows: list[ZoneRow]) -> None:
    by_region: dict[str, list[ZoneRow]] = defaultdict(list)
    for row in rows:
        by_region[row.region_id].append(row)

    print("   1 2 3 4 5 6 7")
    for row_name in REGION_ROWS:
        cells = []
        for col in range(1, 8):
            zones = by_region.get(f"{row_name}{col}", [])
            dominant = Counter(zone.biome_id for zone in zones).most_common(1)
            biome = dominant[0][0] if dominant else "?"
            cells.append(BIOME_GLYPHS.get(biome, "?"))
        print(f"{row_name}  {' '.join(cells)}")


def print_zone_grid(rows: list[ZoneRow], *, attr: str, glyphs: dict[str, str], empty: str = "?") -> None:
    by_coord = {zone_coord(row.zone_id): row for row in rows}
    for y in range(21):
        cells = []
        for x in range(21):
            row = by_coord.get((x, y))
            value = getattr(row, attr) if row else None
            cells.append(glyphs.get(str(value), empty) if value else empty)
        print("".join(cells))


def zone_coord(zone_id: str) -> tuple[int, int]:
    region, zx, zy = zone_id.split("_")
    row_index = REGION_ROWS.index(region[0])
    col_index = int(region[1:]) - 1
    return col_index * 3 + int(zx), row_index * 3 + int(zy)


def print_legend(glyphs: dict[str, str], keys: list[str], *, prefix: str = "biome") -> None:
    if not keys:
        return
    print(f"{prefix}: " + ", ".join(f"{glyphs.get(key, '?')}={key}" for key in keys))


if __name__ == "__main__":
    asyncio.run(main())
