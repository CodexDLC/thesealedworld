from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

import asyncpg
import redis.asyncio as redis


KEEP_ITEM_IDS = {
    "5f73b414-13a7-4640-b5f8-b1fa434b4098",
    "149ec287-d68c-470e-ae63-2ff50d984eab",
    "fcd583c6-45d6-431c-abcc-631cfd7deb96",
    "9022af27-c81f-41e5-a63e-0e89df469ac8",
    "49331d30-e6f2-4907-955c-15b70f3df33c",
    "e61f276d-5a73-4d50-a694-b4e51607f871",
    "c09eb9e2-2bc7-4c4e-8d4d-142f4a2832c6",
}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def asyncpg_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def preview(conn: asyncpg.Connection, char_id: int) -> tuple[list[asyncpg.Record], list[asyncpg.Record]]:
    keep_rows = await conn.fetch(
        """
        select ii.id, ii.base_id, ii.name, ip.storage_type, ip.slot
        from item_instances ii
        join item_placements ip on ip.item_id = ii.id
        where ip.holder_type = 'character'
          and ip.holder_id = $1
          and ii.id = any($2::text[])
        order by ip.slot nulls last, ii.name, ii.id
        """,
        str(char_id),
        sorted(KEEP_ITEM_IDS),
    )
    delete_rows = await conn.fetch(
        """
        select ii.id, ii.base_id, ii.name, ip.storage_type, ip.slot
        from item_instances ii
        join item_placements ip on ip.item_id = ii.id
        where ip.holder_type = 'character'
          and ip.holder_id = $1
          and not (ii.id = any($2::text[]))
        order by ip.storage_type, ip.slot nulls last, ii.name, ii.id
        """,
        str(char_id),
        sorted(KEEP_ITEM_IDS),
    )
    return keep_rows, delete_rows


async def apply_cleanup(conn: asyncpg.Connection, char_id: int) -> int:
    result = await conn.execute(
        """
        delete from item_instances ii
        using item_placements ip
        where ip.item_id = ii.id
          and ip.holder_type = 'character'
          and ip.holder_id = $1
          and not (ii.id = any($2::text[]))
        """,
        str(char_id),
        sorted(KEEP_ITEM_IDS),
    )
    return int(result.rsplit(" ", 1)[-1])


async def reset_redis(redis_url: str, char_id: int) -> int:
    client = redis.from_url(redis_url)
    try:
        return int(await client.delete(f"game:ac:{char_id}", f"game:inventory:{char_id}"))
    finally:
        await client.aclose()


def print_rows(title: str, rows: list[asyncpg.Record], *, limit: int = 20) -> None:
    print(f"{title}: {len(rows)}")
    for row in rows[:limit]:
        print(
            "  "
            f"{row['id']} | {row['base_id']} | {row['storage_type']} | "
            f"{row['slot'] or '-'} | {row['name']}"
        )
    if len(rows) > limit:
        print(f"  ... {len(rows) - limit} more")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Clean duplicated character item instances.")
    parser.add_argument("--char-id", type=int, default=5)
    parser.add_argument("--apply", action="store_true", help="Actually delete DB rows and reset Redis keys.")
    args = parser.parse_args()

    load_env_file(Path(".env"))
    database_url = os.environ.get("DATABASE_URL") or os.environ["SITE_DATABASE_URL"]
    redis_url = os.environ["REDIS_URL"]

    conn = await asyncpg.connect(asyncpg_url(database_url))
    try:
        keep_rows, delete_rows = await preview(conn, args.char_id)
        print_rows("Keep rows", keep_rows)
        print_rows("Delete rows", delete_rows)

        missing = KEEP_ITEM_IDS - {str(row["id"]) for row in keep_rows}
        if missing:
            print("Missing keep ids:")
            for item_id in sorted(missing):
                print(f"  {item_id}")

        if not args.apply:
            print("DRY RUN: no DB or Redis changes were made.")
            return

        async with conn.transaction():
            deleted = await apply_cleanup(conn, args.char_id)
        redis_deleted = await reset_redis(redis_url, args.char_id)
        print(f"Deleted DB item_instances: {deleted}")
        print(f"Deleted Redis keys: {redis_deleted}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
