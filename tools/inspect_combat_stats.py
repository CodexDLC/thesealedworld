from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import redis

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backend.config.settings import settings
from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder


DEFAULT_STATS = (
    "armor",
    "physical_resistance",
    "armor_penetration",
    "main_hand_damage_base",
    "main_hand_accuracy",
    "physical_damage",
)

ALIASES = {
    "block_chance": "block",
    "damage_reduction_flat": "armor",
    "dodge_chance": "evasion",
    "energy_max": "en",
    "evasion_penalty": "evasion",
    "magical_resistance": "magic_resist",
    "magic_resistance": "magic_resist",
    "parry_chance": "parry",
    "physical_accuracy": "accuracy",
    "physical_crit_chance": "crit_chance",
    "shield_block_chance": "block",
}


@dataclass(frozen=True)
class Contribution:
    stat: str
    value: float
    item_id: str
    base_id: str
    slot: str
    item_type: str
    source: str
    name: str
    note: str = ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect combat stat sources for game:ac:<char_id>.")
    parser.add_argument("char_id", type=int, help="Character id, e.g. 7 for game:ac:7.")
    parser.add_argument("--redis-url", default=settings.effective_redis_url)
    parser.add_argument("--stat", action="append", dest="stats", help="Stat to include; repeatable.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    args = parser.parse_args()

    document = load_active_character(args.char_id, args.redis_url)
    if not isinstance(document, dict):
        print(f"Active character not found: game:ac:{args.char_id}", file=sys.stderr)
        return 1

    report = build_report(document, stats=tuple(args.stats or DEFAULT_STATS))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_text_report(report)
    return 0


def load_active_character(char_id: int, redis_url: str) -> dict[str, Any] | None:
    client = redis.Redis.from_url(redis_url, decode_responses=True)
    key = f"game:ac:{char_id}"
    try:
        try:
            raw = client.get(key)
        except redis.ResponseError:
            raw = None
        if raw:
            result = json.loads(cast(Any, raw))
        else:
            try:
                result = client.json().get(key, "$")
            except redis.ResponseError:
                result = None
    finally:
        client.close()
    if isinstance(result, list):
        result = result[0] if result else None
    return result if isinstance(result, dict) else None


def build_report(active_character: dict[str, Any], *, stats: tuple[str, ...]) -> dict[str, Any]:
    actor_input = CharacterCombatActorInputBuilder().build_input(active_character)
    raw = actor_input["raw"]
    values, explanations = StatsWaterfallCalculator.calculate_waterfall(raw)
    contributions = collect_equipment_contributions(active_character)

    return {
        "character": {
            "char_id": active_character.get("char_id"),
            "name": _dict(active_character.get("bio")).get("name"),
            "key": f"game:ac:{active_character.get('char_id')}",
        },
        "stats": {
            stat: {
                "value": values.get(stat, 0.0),
                "waterfall": explanations.get(stat, "0"),
                "raw": raw.get("modifiers", {}).get(stat),
                "equipment_total": round(sum(item.value for item in contributions if item.stat == stat), 4),
                "equipment": [asdict(item) for item in contributions if item.stat == stat],
            }
            for stat in stats
        },
        "warnings": build_warnings(contributions),
    }


def collect_equipment_contributions(active_character: dict[str, Any]) -> list[Contribution]:
    items = _dict(active_character.get("items"))
    layout = _dict(items.get("layout"))
    equipment_layout = _dict(layout.get("equipment"))
    by_id = _dict(items.get("by_id"))

    contributions: list[Contribution] = []
    for equipped_slot, raw_item_id in equipment_layout.items():
        if not raw_item_id:
            continue
        item_id = str(raw_item_id)
        item = _dict(by_id.get(item_id))
        if not item:
            continue

        mechanics = _mechanics(item)
        slot = str(item.get("slot") or mechanics.get("slot") or equipped_slot)
        combat_slot = "main_hand" if slot == "two_hand" else slot
        item_type = str(item.get("item_type") or item.get("type") or mechanics.get("item_type") or mechanics.get("type") or "")
        tags = _tags(item, mechanics)
        base_id = str(item.get("base_id") or mechanics.get("base_id") or mechanics.get("template_id") or "")
        name = str(item.get("name") or mechanics.get("name_ru") or item_id)

        power = _float_value(mechanics.get("power", mechanics.get("base_power")))
        if power:
            stat, note = power_stat(combat_slot, item_type, tags)
            if stat:
                contributions.append(
                    Contribution(
                        stat=stat,
                        value=power,
                        item_id=item_id,
                        base_id=base_id,
                        slot=slot,
                        item_type=item_type,
                        source="power",
                        name=name,
                        note=note,
                    )
                )

        for source_group in ("implicit_bonuses", "bonuses"):
            for key, value in _dict(mechanics.get(source_group)).items():
                numeric = _float_value(value)
                if numeric is None:
                    continue
                contributions.append(
                    Contribution(
                        stat=item_stat_key(str(key), slot=combat_slot, item_type=item_type, tags=tags),
                        value=numeric,
                        item_id=item_id,
                        base_id=base_id,
                        slot=slot,
                        item_type=item_type,
                        source=f"{source_group}.{key}",
                        name=name,
                    )
                )

    return contributions


def power_stat(slot: str, item_type: str, tags: list[str]) -> tuple[str | None, str]:
    if slot == "main_hand":
        return "main_hand_damage_base", "main-hand power"
    if slot == "off_hand":
        if item_type == "shield" or "shield" in tags:
            return None, "shield/off-hand power is not passive armor"
        return "off_hand_damage_base", "off-hand non-shield power"
    if slot.endswith("_armor"):
        return "armor", "armor slot power"
    return None, ""


def item_stat_key(key: str, *, slot: str, item_type: str, tags: list[str]) -> str:
    key = ALIASES.get(key, key)
    if key == "physical_accuracy":
        if slot == "main_hand":
            return "main_hand_accuracy"
        if slot == "off_hand" and not (item_type == "shield" or "shield" in tags):
            return "off_hand_accuracy"
        return "accuracy"
    if key == "physical_crit_chance":
        if slot == "main_hand":
            return "main_hand_crit_chance"
        if slot == "off_hand" and not (item_type == "shield" or "shield" in tags):
            return "off_hand_crit_chance"
        return "crit_chance"
    return key


def build_warnings(contributions: list[Contribution]) -> list[str]:
    warnings: list[str] = []
    for entry in contributions:
        if entry.stat != "armor" or entry.source != "power":
            continue
        if entry.slot.endswith("_armor"):
            continue
        warnings.append(
            f"{entry.slot} {entry.base_id or entry.item_id} contributes {entry.value:g} armor "
            f"because current builder rule maps item_type={entry.item_type!r}/slot to armor. {entry.note}"
        )
    return warnings


def print_text_report(report: dict[str, Any]) -> None:
    character = report["character"]
    print(f"Character: {character.get('name') or '?'} ({character['key']})")
    print()
    for stat, data in report["stats"].items():
        print(f"{stat}: {data['value']}  waterfall={data['waterfall']}")
        if data["equipment"]:
            print(f"  equipment_total={data['equipment_total']}")
            for entry in data["equipment"]:
                label = entry["base_id"] or entry["item_id"]
                note = f" [{entry['note']}]" if entry["note"] else ""
                print(
                    f"  + {entry['value']:>7g}  {entry['slot']:<13} {entry['item_type']:<8} "
                    f"{label}  {entry['source']}{note}"
                )
        print()

    if report["warnings"]:
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"  - {warning}")


def _mechanics(item: dict[str, Any]) -> dict[str, Any]:
    mechanics = item.get("mechanics")
    if isinstance(mechanics, dict):
        return mechanics
    data = item.get("data")
    return data if isinstance(data, dict) else item


def _tags(item: dict[str, Any], mechanics: dict[str, Any]) -> list[str]:
    raw_tags = (
        item.get("tags")
        or item.get("narrative_tags")
        or mechanics.get("tags")
        or mechanics.get("narrative_tags")
        or []
    )
    return [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _float_value(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
