from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.actor_state.runtime.sections import COMBAT, INVENTORY, RUNTIME, STATUS
from src.backend.infrastructure.actor_state.repositories.db import get_monster_repo

if TYPE_CHECKING:
    from collections.abc import Collection

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.infrastructure.actor_state.models import Monster


async def build_snapshots(
    session: AsyncSession,
    monster_ids: list[str],
    sections: Collection[str],
) -> dict[str, dict[str, Any]]:
    if not monster_ids:
        return {}

    import uuid

    uuids = [uuid.UUID(mid) for mid in monster_ids]
    monsters = await get_monster_repo(session).get_monsters_batch(uuids)
    monsters_by_id = {str(monster.id): monster for monster in monsters}

    snapshots: dict[str, dict[str, Any]] = {}
    for monster_id in monster_ids:
        monster = monsters_by_id.get(monster_id)
        if monster is None:
            continue

        snapshot: dict[str, Any] = {
            "meta": _build_meta(monster),
            "source": _build_source(monster),
        }
        if RUNTIME in sections:
            snapshot["runtime"] = {"vitals": _build_vitals()}
        if COMBAT in sections:
            snapshot["combat"] = _build_combat(monster)
        if INVENTORY in sections:
            snapshot["inventory"] = {}
        if STATUS in sections:
            snapshot["status"] = _build_vitals()
        snapshots[monster_id] = snapshot

    return snapshots


def _build_meta(monster: Monster) -> dict[str, Any]:
    return {
        "actor_type": "monster",
        "actor_id": str(monster.id),
        "name": monster.name_ru,
        "role": monster.role,
        "tags": ["monster", monster.role],
    }


def _build_source(monster: Monster) -> dict[str, Any]:
    return {
        "monster_id": str(monster.id),
        "template_id": monster.variant_key,
        "clan_id": str(monster.clan_id),
        "db_refs": {"generated_monsters": str(monster.id), "generated_clans": str(monster.clan_id)},
    }


def _build_combat(monster: Monster) -> dict[str, Any]:
    return {
        "math_model": {
            "attributes": {
                stat: {"base": value, "flats": {}, "percents": {}}
                for stat, value in (monster.scaled_base_stats or {}).items()
                if value is not None
            },
            "modifiers": {},
            "tags": ["monster", monster.role],
        },
        "loadout": {
            "belt": [],
            "abilities": _ability_ids(monster.skills_snapshot),
            "skills": [],
            "equipment": monster.loadout_ids,
        },
    }


def _build_vitals() -> dict[str, int]:
    return {"hp_current": -1, "energy_current": -1}


def _ability_ids(snapshot: dict[str, Any] | list[Any]) -> list[str]:
    if isinstance(snapshot, dict):
        return [str(key) for key in snapshot]
    ability_ids: list[str] = []
    for item in snapshot:
        if isinstance(item, dict) and "id" in item:
            ability_ids.append(str(item["id"]))
        else:
            ability_ids.append(str(item))
    return ability_ids
