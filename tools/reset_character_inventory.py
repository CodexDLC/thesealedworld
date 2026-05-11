from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg
import redis.asyncio as redis

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO, ItemOriginRefDTO
from src.backend.features.items.runtime.item_factory import ItemFactory


STARTER_LOADOUT = [
    ("sword", "main_hand"),
    ("buckler", "off_hand"),
    ("leather_cap", "head_armor"),
    ("jerkin", "chest_armor"),
    ("gauntlets", "arms_armor"),
    ("breeches", "legs_armor"),
    ("boots", "feetwear"),
    ("apron", "chest_garment"),
    ("fur_pants", "legs_garment"),
    ("work_gloves", "gloves_garment"),
    ("winter_cloak", "outer_garment"),
    ("belt", "belt_accessory"),
    ("amulet", "amulet"),
    ("earring", "earring"),
    ("ring", "ring_1"),
    ("ring", "ring_2"),
]
STARTER_BASE_IDS = [base_id for base_id, _slot in STARTER_LOADOUT]


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


async def list_character_items(conn: asyncpg.Connection, char_id: int) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        select ii.id, ii.base_id, ii.name, ip.storage_type, ip.slot
        from item_instances ii
        join item_placements ip on ip.item_id = ii.id
        where ip.holder_type = 'character'
          and ip.holder_id = $1
        order by ip.storage_type, ip.slot nulls last, ii.name, ii.id
        """,
        str(char_id),
    )


async def delete_character_items(conn: asyncpg.Connection, char_id: int) -> int:
    result = await conn.execute(
        """
        delete from item_instances ii
        using item_placements ip
        where ip.item_id = ii.id
          and ip.holder_type = 'character'
          and ip.holder_id = $1
        """,
        str(char_id),
    )
    return int(result.rsplit(" ", 1)[-1])


async def insert_generated_item(
    conn: asyncpg.Connection,
    *,
    char_id: int,
    item_id: str,
    item: GeneratedItemDTO,
    position_index: int,
    slot_override: str | None = None,
) -> None:
    equipped_slot = slot_override or item.slot
    should_equip = _should_equip(item, equipped_slot)
    mechanics = dict(item.mechanics)
    mechanics.update(
        {
            "power": item.power,
            "durability_current": item.durability_max,
            "durability_max": item.durability_max,
            "damage_spread": item.damage_spread,
            "slot": equipped_slot or item.slot,
            "valid_slots": item.valid_slots,
            "triggers": item.triggers,
        }
    )
    metadata = {
        **dict(item.metadata),
        "width_cells": _width_cells(item),
        "height_cells": _height_cells(item),
    }
    generation = {
        "template_id": item.template_id,
        "material_id": item.material_id,
        "affix_bundle_ids": item.affix_bundle_ids,
        "narrative_tags": item.narrative_tags,
    }

    await conn.execute(
        """
        insert into item_instances (
            id, base_id, item_type, rarity, rarity_tier, lifecycle_status, text_status,
            name, description, mechanics, appearance, generation, metadata
        )
        values (
            $1, $2, $3, $4, $5, 'mechanical_ready', 'not_requested',
            $6, $7, $8::jsonb, '{}'::jsonb, $9::jsonb, $10::jsonb
        )
        """,
        item_id,
        item.base_id,
        item.item_type,
        item.rarity,
        item.rarity_tier,
        item.name,
        item.description,
        json.dumps(mechanics, ensure_ascii=False),
        json.dumps(generation, ensure_ascii=False),
        json.dumps(metadata, ensure_ascii=False),
    )
    await conn.execute(
        """
        insert into item_placements (item_id, holder_type, holder_id, storage_type, slot, position_index)
        values ($1, 'character', $2, $3, $4, $5)
        """,
        item_id,
        str(char_id),
        "equipped" if should_equip else "backpack",
        equipped_slot if should_equip else None,
        position_index,
    )
    await conn.execute(
        """
        insert into item_origins (item_id, origin_type, origin_ref, seed, request_hash, correlation_id)
        values ($1, 'admin', 'reset_character_inventory', $2, null, null)
        """,
        item_id,
        f"reset:{char_id}:{position_index}:{item.base_id}",
    )


async def reset_redis(redis_url: str, char_id: int) -> tuple[int, list[str]]:
    client = redis.from_url(redis_url)
    try:
        keys = [
            f"game:ac:{char_id}",
            f"game:inventory:{char_id}",
            *await _character_actor_snapshot_keys(client, char_id),
        ]
        unique_keys = list(dict.fromkeys(keys))
        if not unique_keys:
            return 0, []
        return int(await client.delete(*unique_keys)), unique_keys
    finally:
        await client.aclose()


async def _scan_keys(client: redis.Redis, pattern: str) -> list[str]:
    cursor = 0
    keys: list[str] = []
    while True:
        cursor, batch = await client.scan(cursor=cursor, match=pattern, count=100)
        keys.extend(_decode_key(key) for key in batch)
        if cursor == 0:
            return keys


async def _character_actor_snapshot_keys(client: redis.Redis, char_id: int) -> list[str]:
    keys = await _scan_keys(client, "game:actor:snapshot:*")
    result: list[str] = []
    for key in keys:
        if f":player:{char_id}" in key:
            result.append(key)
            continue
        try:
            raw = await client.json().get(key)
        except Exception:
            continue
        if _snapshot_belongs_to_char(raw, char_id):
            result.append(key)
    return result


def _snapshot_belongs_to_char(raw: object, char_id: int) -> bool:
    expected = str(char_id)
    if isinstance(raw, list):
        return any(_snapshot_belongs_to_char(item, char_id) for item in raw)
    if not isinstance(raw, dict):
        return False

    candidates = [
        raw.get("char_id"),
        raw.get("character_id"),
        raw.get("actor_id"),
        raw.get("id"),
    ]
    for section_name in ("meta", "source", "runtime", "status"):
        section = raw.get(section_name)
        if isinstance(section, dict):
            candidates.extend(
                [
                    section.get("char_id"),
                    section.get("character_id"),
                    section.get("actor_id"),
                    section.get("id"),
                ]
            )
    return any(str(value) == expected for value in candidates if value is not None)


def _decode_key(key: object) -> str:
    if isinstance(key, bytes):
        return key.decode("utf-8", errors="replace")
    return str(key)


def generate_items(
    char_id: int,
    loadout: list[tuple[str, str | None]],
    rarity_tier: int,
) -> list[tuple[GeneratedItemDTO, str | None]]:
    factory = ItemFactory()
    items = []
    for index, (base_id, slot_override) in enumerate(loadout):
        item = factory.generate(
            ItemGenerationRequestDTO(
                base_id=base_id,
                rarity_tier=rarity_tier,
                source="admin:reset_character_inventory",
                char_id=char_id,
                request_ai_text=False,
                origin_ref=ItemOriginRefDTO(
                    origin_type="admin",
                    origin_ref="reset_character_inventory",
                    seed=f"reset:{char_id}:{rarity_tier}:{index}:{base_id}",
                ),
            )
        )
        items.append((item, slot_override))
    return items


def print_existing(rows: list[asyncpg.Record]) -> None:
    print(f"Existing character items: {len(rows)}")
    for row in rows[:30]:
        print(f"  {row['id']} | {row['base_id']} | {row['storage_type']} | {row['slot'] or '-'} | {row['name']}")
    if len(rows) > 30:
        print(f"  ... {len(rows) - 30} more")


def print_generated(items: list[tuple[GeneratedItemDTO, str | None]]) -> None:
    print(f"Generated replacement items: {len(items)}")
    for item, slot_override in items:
        raw_affixes = item.mechanics.get("affixes")
        affixes = raw_affixes if isinstance(raw_affixes, list) else []
        affix_ids = ", ".join(str(affix.get("affix_id")) for affix in affixes if isinstance(affix, dict))
        slot = slot_override or item.slot
        print(f"  {item.base_id} | T{item.rarity_tier} | {slot} | {item.name} | affixes: {affix_ids or '-'}")


def _should_equip(item: GeneratedItemDTO, slot: str | None) -> bool:
    return bool(slot and item.item_type in {"weapon", "armor", "garment", "accessory"})


def _width_cells(item: GeneratedItemDTO) -> int:
    if item.item_type in {"resource", "currency", "material", "consumable", "quest"}:
        return 1
    if item.slot in {"main_hand", "two_hand"}:
        return 1
    return 2


def _height_cells(item: GeneratedItemDTO) -> int:
    if item.item_type in {"resource", "currency", "material", "consumable", "quest"}:
        return 1
    if item.slot == "two_hand":
        return 4
    if item.slot == "main_hand":
        return 3
    if item.slot in {"chest_armor", "outer_garment"}:
        return 3
    return 2


async def main() -> None:
    parser = argparse.ArgumentParser(description="Replace all character items with generated T1 starter equipment.")
    parser.add_argument("--char-id", type=int, required=True)
    parser.add_argument("--rarity-tier", type=int, default=1)
    parser.add_argument("--base-id", action="append", dest="base_ids", help="Override starter base ids; repeatable.")
    parser.add_argument("--apply", action="store_true", help="Actually delete old items, insert new items, and reset Redis.")
    args = parser.parse_args()

    load_env_file(Path(".env"))
    database_url = os.environ.get("DATABASE_URL") or os.environ["SITE_DATABASE_URL"]
    redis_url = os.environ["REDIS_URL"]
    loadout: list[tuple[str, str | None]] = [(base_id, None) for base_id in args.base_ids] if args.base_ids else STARTER_LOADOUT  # type: ignore[assignment]
    generated = generate_items(args.char_id, loadout, args.rarity_tier)

    conn = await asyncpg.connect(asyncpg_url(database_url))
    try:
        existing = await list_character_items(conn, args.char_id)
        print_existing(existing)
        print_generated(generated)
        if not args.apply:
            print("DRY RUN: no DB or Redis changes were made.")
            return

        pre_redis_deleted, pre_redis_keys = await reset_redis(redis_url, args.char_id)
        async with conn.transaction():
            deleted = await delete_character_items(conn, args.char_id)
            for position_index, (item, slot_override) in enumerate(generated):
                await insert_generated_item(
                    conn,
                    char_id=args.char_id,
                    item_id=str(uuid4()),
                    item=item,
                    position_index=position_index,
                    slot_override=slot_override,
                )
        post_redis_deleted, post_redis_keys = await reset_redis(redis_url, args.char_id)
        print(f"Deleted Redis keys before DB replace: {pre_redis_deleted}")
        for key in pre_redis_keys:
            print(f"  pre: {key}")
        print(f"Deleted DB item_instances: {deleted}")
        print(f"Inserted DB item_instances: {len(generated)}")
        print(f"Deleted Redis keys after DB replace: {post_redis_deleted}")
        for key in post_redis_keys:
            print(f"  post: {key}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
