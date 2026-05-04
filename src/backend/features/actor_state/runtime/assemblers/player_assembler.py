from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast

from src.backend.features.actor_state.runtime.sections import COMBAT, INVENTORY, RUNTIME, STATUS
from src.backend.infrastructure.actor_state.repositories.db import (
    get_attributes_repo as get_actor_state_attributes_repo,
)
from src.backend.infrastructure.actor_state.repositories.db import (
    get_character_repo as get_actor_state_character_repo,
)
from src.backend.infrastructure.actor_state.repositories.db import (
    get_inventory_repo as get_actor_state_inventory_repo,
)
from src.backend.infrastructure.actor_state.repositories.db import (
    get_skill_repo as get_actor_state_skill_repo,
)
from src.backend.infrastructure.actor_state.repositories.db import (
    get_symbiote_repo as get_actor_state_symbiote_repo,
)
from src.backend.infrastructure.redis.keys import PlayerCoreKey

if TYPE_CHECKING:
    from collections.abc import Collection

    from codex_platform.redis_service import RedisService
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.shared.schemas.character import CharacterAttributesReadDTO, CharacterReadDTO
    from src.shared.schemas.skill import SkillProgressDTO


PRIMARY_STATS = ("strength", "agility", "endurance", "intelligence", "wisdom", "men", "perception", "charisma", "luck")


async def build_snapshots(
    session: AsyncSession,
    redis: RedisService,
    char_ids: list[int],
    sections: Collection[str],
) -> dict[int, dict[str, Any]]:
    if not char_ids:
        return {}

    characters = await get_actor_state_character_repo(session).get_characters_batch(char_ids)
    chars_by_id = {char.character_id: char for char in characters}
    existing_ids = [char_id for char_id in char_ids if char_id in chars_by_id]
    if not existing_ids:
        return {}

    needs_combat = COMBAT in sections
    needs_inventory = INVENTORY in sections
    needs_status = STATUS in sections or RUNTIME in sections

    attributes: list[CharacterAttributesReadDTO] = []
    equipped_by_id: dict[int, list[Any]] = {}
    inventory_by_id: dict[int, list[Any]] = {}
    skills_by_id: dict[int, list[SkillProgressDTO]] = {}
    symbiotes_by_id: dict[int, Any] = {}
    vitals_by_id: dict[int, dict[str, Any] | None] = {}

    tasks: list[Any] = []
    labels: list[str] = []

    if needs_combat:
        tasks.append(get_actor_state_attributes_repo(session).get_attributes_batch(existing_ids))
        labels.append("attributes")
        tasks.append(get_actor_state_skill_repo(session).get_all_skills_progress_batch(existing_ids))
        labels.append("skills")
        tasks.append(get_actor_state_symbiote_repo(session).get_symbiotes_batch(existing_ids))
        labels.append("symbiotes")

    if needs_combat or needs_inventory:
        inv_repo = get_actor_state_inventory_repo(session)
        tasks.append(inv_repo.get_items_by_location_batch(existing_ids, "equipped"))
        labels.append("equipped")

    if needs_inventory:
        tasks.append(get_actor_state_inventory_repo(session).get_items_by_location_batch(existing_ids, "inventory"))
        labels.append("inventory")

    if needs_status:
        tasks.append(_get_vitals_batch(redis, existing_ids))
        labels.append("vitals")

    if tasks:
        results = await asyncio.gather(*tasks)
        for label, result in zip(labels, results, strict=True):
            if label == "attributes":
                attributes = cast("list[CharacterAttributesReadDTO]", result)
            elif label == "skills":
                skills_by_id = cast("dict[int, list[SkillProgressDTO]]", result)
            elif label == "symbiotes":
                symbiotes_by_id = {item.character_id: item for item in result}
            elif label == "equipped":
                equipped_by_id = cast("dict[int, list[Any]]", result)
            elif label == "inventory":
                inventory_by_id = cast("dict[int, list[Any]]", result)
            elif label == "vitals":
                vitals_by_id = cast("dict[int, dict[str, Any] | None]", result)

    attributes_by_id = {attr.character_id: attr for attr in attributes}

    snapshots: dict[int, dict[str, Any]] = {}
    for char_id in existing_ids:
        character = chars_by_id[char_id]
        equipped = equipped_by_id.get(char_id, [])
        inventory = inventory_by_id.get(char_id, [])
        skills = skills_by_id.get(char_id, [])
        vitals = vitals_by_id.get(char_id)

        snapshot: dict[str, Any] = {
            "meta": _build_meta(character),
            "source": _build_source(character, symbiotes_by_id.get(char_id)),
        }
        if RUNTIME in sections:
            snapshot["runtime"] = {}
        if COMBAT in sections:
            snapshot["combat"] = _build_combat(attributes_by_id.get(char_id), equipped, skills)
        if INVENTORY in sections:
            snapshot["inventory"] = {
                "equipped": [_dump(item) for item in equipped],
                "items": [_dump(item) for item in inventory],
            }
        if STATUS in sections:
            snapshot["status"] = _build_status(character, vitals)

        snapshots[char_id] = snapshot

    return snapshots


async def _get_vitals_batch(redis: RedisService, char_ids: list[int]) -> dict[int, dict[str, Any] | None]:
    key_builder = PlayerCoreKey()
    keys = [key_builder.build(char_id=char_id) for char_id in char_ids]
    try:
        redis_client = redis.redis_client if hasattr(redis, "redis_client") else redis.pipeline.client
        async with redis_client.pipeline(transaction=False) as pipe:
            for key in keys:
                pipe.json().get(key, "$")
            results = await pipe.execute(raise_on_error=False)
    except Exception:
        return {char_id: None for char_id in char_ids}

    vitals: dict[int, dict[str, Any] | None] = {}
    for char_id, result in zip(char_ids, results, strict=False):
        doc = result[0] if isinstance(result, list) and result else result
        vitals[char_id] = doc if isinstance(doc, dict) else None
    return vitals


def _build_meta(character: CharacterReadDTO) -> dict[str, Any]:
    return {
        "actor_type": "player",
        "actor_id": character.character_id,
        "name": character.name,
        "role": "player",
        "tags": ["player"],
    }


def _build_source(character: CharacterReadDTO, symbiote: Any | None) -> dict[str, Any]:
    source: dict[str, Any] = {
        "character_id": character.character_id,
        "user_id": str(character.user_id),
        "location_id": character.location_id,
        "game_stage": character.game_stage,
        "db_refs": {"characters": character.character_id},
    }
    if symbiote:
        source["symbiote"] = {
            "symbiote_name": symbiote.symbiote_name,
            "gift_id": symbiote.gift_id,
            "gift_rank": symbiote.gift_rank,
            "gift_xp": symbiote.gift_xp,
            "elements_resonance": symbiote.elements_resonance,
        }
    return source


def _build_combat(
    attributes: CharacterAttributesReadDTO | None,
    equipped: list[Any],
    skills: list[SkillProgressDTO],
) -> dict[str, Any]:
    math_model: dict[str, Any] = {"attributes": {}, "modifiers": {}, "tags": ["player"]}
    if attributes:
        data = attributes.model_dump(mode="json")
        for stat in PRIMARY_STATS:
            math_model["attributes"][stat] = {"base": float(data.get(stat, 0)), "source": {}, "temp": {}}

    for item in equipped:
        item_data = _dump(item)
        source_key = f"item:{item_data.get('inventory_id')}"
        payload = item_data.get("data") or {}
        for key in ("power", "accuracy", "crit_chance", "parry_chance", "block_chance", "evasion_penalty"):
            if key in payload:
                math_model["modifiers"].setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
                math_model["modifiers"][key]["source"][source_key] = payload[key]
        for bonus_key, value in (payload.get("implicit_bonuses") or {}).items():
            math_model["modifiers"].setdefault(bonus_key, {"base": 0.0, "source": {}, "temp": {}})
            math_model["modifiers"][bonus_key]["source"][source_key] = value
        for bonus_key, value in (payload.get("bonuses") or {}).items():
            math_model["modifiers"].setdefault(bonus_key, {"base": 0.0, "source": {}, "temp": {}})
            math_model["modifiers"][bonus_key]["source"][source_key] = value

    return {
        "math_model": math_model,
        "loadout": {
            "belt": [_dump(item) for item in equipped if _dump(item).get("quick_slot_position")],
            "abilities": [],
            "skills": [skill.skill_key for skill in skills if skill.is_unlocked or skill.total_xp > 0],
        },
        "skills": {
            skill.skill_key: float(skill.total_xp) for skill in skills if skill.is_unlocked or skill.total_xp > 0
        },
    }


def _build_status(character: CharacterReadDTO, vitals: dict[str, Any] | None) -> dict[str, Any]:
    if not vitals:
        return character.vitals_snapshot or {}
    vitals_section = vitals.get("vitals")
    return vitals_section if isinstance(vitals_section, dict) else vitals


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value) if isinstance(value, dict) else {}
