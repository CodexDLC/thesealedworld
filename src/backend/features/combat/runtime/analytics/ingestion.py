from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from src.backend.features.combat.runtime.support.analytics_builder import ANALYTICS_SCHEMA_VERSION
from src.backend.infrastructure.combat.repositories import CombatAnalyticsRepository

OUTCOME_BY_CODE = {
    "H": "hit",
    "C": "crit",
    "M": "miss",
    "D": "dodge",
    "P": "parry",
    "B": "block",
    "E": "effect",
    "R": "heal",
    "N": "none",
}


class CombatAnalyticsIngestionService:
    """Turns archived combat analytics v2 into normalized facts and dashboard rollups."""

    @classmethod
    async def ingest_finalization(
        cls,
        session: Any,
        finalization: dict[str, Any],
        *,
        aggregate_version: int = 1,
    ) -> None:
        facts = cls.extract_exchange_facts(finalization)
        if not facts:
            return

        repo = CombatAnalyticsRepository(session)
        await repo.replace_facts_for_combat(str(finalization["combat_id"]), facts)
        finished_values = [fact["finished_at"] for fact in facts if fact.get("finished_at") is not None]
        if not finished_values:
            return
        start = min(finished_values).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = cls._next_month(max(finished_values))
        bucket_facts = await repo.facts_for_buckets(start=start, end=end)
        rollups = cls.build_rollups(bucket_facts, aggregate_version=aggregate_version)
        await repo.replace_rollups(rollups, aggregate_version=aggregate_version, start=start, end=end)

    @classmethod
    def extract_exchange_facts(cls, finalization: dict[str, Any]) -> list[dict[str, Any]]:
        analytics: dict[str, Any] = (
            finalization.get("analytics") if isinstance(finalization.get("analytics"), dict) else {}
        )
        profile_entry = analytics.get("_profile")
        profile = (
            profile_entry.get("_profile")
            if isinstance(profile_entry, dict) and "_profile" in profile_entry
            else profile_entry
        )
        if (
            not isinstance(profile, dict)
            or int(profile.get("analytics_schema_version") or 0) < ANALYTICS_SCHEMA_VERSION
        ):
            return []

        combat_id = str(finalization.get("combat_id") or profile.get("combat_id") or "")
        if not combat_id:
            return []
        finished_at = cls._datetime_from_epoch(finalization.get("finished_at"))
        meta: dict[str, Any] = finalization.get("meta") if isinstance(finalization.get("meta"), dict) else {}
        battle_type = meta.get("battle_type") or profile.get("battle_type")
        location_id = meta.get("location_id") or profile.get("location_id")

        facts: list[dict[str, Any]] = []
        for key in sorted(analytics, key=cls._analytics_sort_key):
            if key == "_profile":
                continue
            entry = analytics.get(key)
            if not isinstance(entry, dict):
                continue
            if int(entry.get("analytics_schema_version") or entry.get("v") or 0) < ANALYTICS_SCHEMA_VERSION:
                continue
            fact = cls._exchange_fact(
                combat_id=combat_id,
                finished_at=finished_at,
                battle_type=battle_type,
                location_id=location_id,
                entry=entry,
            )
            if fact is not None:
                facts.append(fact)
        return facts

    _METRIC_CONFIGS: list[tuple[str, str]] = [
        ("damage_by_weapon_armor", "_dimensions_damage"),
        ("action_usage", "_dimensions_action"),
    ]

    @classmethod
    def build_rollups(cls, facts: list[dict[str, Any]], *, aggregate_version: int) -> list[dict[str, Any]]:
        buckets: dict[tuple[datetime, str, str, str], dict[str, Any]] = {}
        for fact in facts:
            finished_at = fact.get("finished_at")
            if not isinstance(finished_at, datetime):
                continue
            for grain in ("day", "month"):
                bucket_start = cls._bucket_start(finished_at, grain)
                for metric_key, dim_fn_name in cls._METRIC_CONFIGS:
                    dim_fn = getattr(cls, dim_fn_name)
                    dimensions = dim_fn(fact)
                    dimensions_hash = cls._dimensions_hash(dimensions)
                    key = (bucket_start, grain, metric_key, dimensions_hash)
                    bucket = buckets.setdefault(
                        key,
                        {
                            "bucket_start": bucket_start,
                            "bucket_grain": grain,
                            "metric_key": metric_key,
                            "dimensions_hash": dimensions_hash,
                            "dimensions": dimensions,
                            "aggregate_version": int(aggregate_version),
                            "_acc": cls._empty_accumulator(),
                        },
                    )
                    cls._accumulate(bucket["_acc"], fact)

        rows: list[dict[str, Any]] = []
        for bucket in buckets.values():
            counters = cls._finalize_counters(bucket.pop("_acc"))
            rows.append({**bucket, "counters": counters, "source_count": counters["attempts"]})
        return sorted(rows, key=lambda row: (row["bucket_start"], row["bucket_grain"], row["dimensions_hash"]))

    @staticmethod
    def _exchange_fact(
        *,
        combat_id: str,
        finished_at: datetime | None,
        battle_type: Any,
        location_id: Any,
        entry: dict[str, Any],
    ) -> dict[str, Any] | None:
        damage_trace: dict[str, Any] = entry.get("dt") if isinstance(entry.get("dt"), dict) else {}
        details: dict[str, Any] = damage_trace.get("details") if isinstance(damage_trace.get("details"), dict) else {}
        arm: dict[str, Any] = details.get("arm") if isinstance(details.get("arm"), dict) else {}
        resl: dict[str, Any] = details.get("resl") if isinstance(details.get("resl"), dict) else {}
        equipment: dict[str, Any] = entry.get("eq") if isinstance(entry.get("eq"), dict) else {}
        weapon: dict[str, Any] = (
            ((equipment.get("s") or {}).get("weapon") or {}) if isinstance(equipment.get("s"), dict) else {}
        )
        armor: dict[str, Any] = (
            ((equipment.get("d") or {}).get("armor") or {}) if isinstance(equipment.get("d"), dict) else {}
        )
        action: dict[str, Any] = entry.get("act") if isinstance(entry.get("act"), dict) else {}
        outcome = OUTCOME_BY_CODE.get(str(entry.get("o") or ""), str(entry.get("o") or "none"))
        damage = entry.get("dmg") if isinstance(entry.get("dmg"), list) else []
        raw_damage = CombatAnalyticsIngestionService._float_at(damage, 0, damage_trace.get("raw"))
        final_damage = CombatAnalyticsIngestionService._float_at(damage, 2, damage_trace.get("final"))
        return {
            "schema_version": 2,
            "combat_id": combat_id,
            "turn": CombatAnalyticsIngestionService._int_value(entry.get("t")),
            "wave": CombatAnalyticsIngestionService._int_value(entry.get("w")),
            "seq": CombatAnalyticsIngestionService._int_value(entry.get("seq")),
            "finished_at": finished_at,
            "battle_type": CombatAnalyticsIngestionService._optional_str(battle_type),
            "location_id": CombatAnalyticsIngestionService._optional_str(location_id),
            "source_actor_id": CombatAnalyticsIngestionService._optional_str(entry.get("s")),
            "target_actor_id": CombatAnalyticsIngestionService._optional_str(entry.get("d")),
            "action_id": CombatAnalyticsIngestionService._optional_str(action.get("id") or entry.get("a")),
            "feint_id": CombatAnalyticsIngestionService._optional_str(action.get("feint_id")),
            "outcome": outcome,
            "source_type": CombatAnalyticsIngestionService._optional_str(entry.get("h")),
            "is_crit": outcome == "crit",
            "is_counter": "ctr" in (entry.get("chn") or []) or bool((entry.get("x") or {}).get("ctr")),
            "is_extra_strike": "xs" in (entry.get("chn") or []),
            "weapon_base_id": CombatAnalyticsIngestionService._optional_str(weapon.get("base_id")),
            "weapon_tier": CombatAnalyticsIngestionService._optional_int(weapon.get("tier")),
            "weapon_power": CombatAnalyticsIngestionService._optional_float(weapon.get("power")),
            "armor_class": CombatAnalyticsIngestionService._optional_str(armor.get("armor_class")),
            "armor_tier": CombatAnalyticsIngestionService._optional_int(armor.get("tier")),
            "raw_damage": raw_damage,
            "final_damage": final_damage,
            "armor_raw": CombatAnalyticsIngestionService._optional_float(arm.get("raw")),
            "armor_effective": CombatAnalyticsIngestionService._optional_float(arm.get("effective")),
            "armor_ignored": CombatAnalyticsIngestionService._optional_float(arm.get("ignored")),
            "phys_res_raw": CombatAnalyticsIngestionService._optional_float(resl.get("raw")),
            "phys_res_effective": CombatAnalyticsIngestionService._optional_float(resl.get("effective")),
            "physical_suppression": CombatAnalyticsIngestionService._optional_float(resl.get("suppression")),
            "checks": entry.get("chk") if isinstance(entry.get("chk"), list) else [],
            "damage_trace": damage_trace,
            "trigger_attempts": entry.get("trga") if isinstance(entry.get("trga"), list) else [],
            "mutations": entry.get("mut") if isinstance(entry.get("mut"), list) else [],
            "equipment": equipment,
            "tags": CombatAnalyticsIngestionService._tags(entry),
        }

    @staticmethod
    def _empty_accumulator() -> dict[str, Any]:
        return defaultdict(
            float,
            {
                "attempts": 0,
                "min_raw_damage": None,
                "max_raw_damage": None,
                "min_final_damage": None,
                "max_final_damage": None,
            },
        )

    @staticmethod
    def _accumulate(acc: dict[str, Any], fact: dict[str, Any]) -> None:
        acc["attempts"] += 1
        outcome = fact.get("outcome")
        if outcome in {"hit", "crit"}:
            acc["hits"] += 1
        if outcome == "crit":
            acc["crits"] += 1
        if outcome == "dodge":
            acc["dodges"] += 1
        if outcome == "parry":
            acc["parries"] += 1
        if outcome == "block":
            acc["blocks"] += 1
        raw_damage = CombatAnalyticsIngestionService._optional_float(fact.get("raw_damage")) or 0.0
        final_damage = CombatAnalyticsIngestionService._optional_float(fact.get("final_damage")) or 0.0
        armor_raw = CombatAnalyticsIngestionService._optional_float(fact.get("armor_raw")) or 0.0
        armor_effective = CombatAnalyticsIngestionService._optional_float(fact.get("armor_effective")) or 0.0
        armor_ignored = CombatAnalyticsIngestionService._optional_float(fact.get("armor_ignored")) or 0.0
        acc["sum_raw_damage"] += raw_damage
        acc["sum_final_damage"] += final_damage
        acc["sum_damage_after_armor"] += final_damage
        acc["sum_armor_raw"] += armor_raw
        acc["sum_armor_effective"] += armor_effective
        acc["sum_armor_ignored"] += armor_ignored
        acc["min_raw_damage"] = raw_damage if acc["min_raw_damage"] is None else min(acc["min_raw_damage"], raw_damage)
        acc["max_raw_damage"] = raw_damage if acc["max_raw_damage"] is None else max(acc["max_raw_damage"], raw_damage)
        acc["min_final_damage"] = (
            final_damage if acc["min_final_damage"] is None else min(acc["min_final_damage"], final_damage)
        )
        acc["max_final_damage"] = (
            final_damage if acc["max_final_damage"] is None else max(acc["max_final_damage"], final_damage)
        )
        if armor_ignored > 0.0:
            acc["armor_ignore_count"] += 1
        if fact.get("is_counter"):
            acc["counters"] += 1
        if fact.get("is_extra_strike"):
            acc["extra_strikes"] += 1
        for attempt in fact.get("trigger_attempts") or []:
            if isinstance(attempt, list) and len(attempt) > 7:
                acc["trigger_attempts"] += 1
                if attempt[7]:
                    acc["trigger_passes"] += 1

    @staticmethod
    def _finalize_counters(acc: dict[str, Any]) -> dict[str, Any]:
        attempts = max(1, int(acc["attempts"]))
        trigger_attempts = max(1, int(acc["trigger_attempts"] or 0))
        return {
            "attempts": int(acc["attempts"]),
            "hits": int(acc["hits"]),
            "crits": int(acc["crits"]),
            "dodges": int(acc["dodges"]),
            "parries": int(acc["parries"]),
            "blocks": int(acc["blocks"]),
            "sum_raw_damage": round(float(acc["sum_raw_damage"]), 6),
            "sum_final_damage": round(float(acc["sum_final_damage"]), 6),
            "sum_armor_raw": round(float(acc["sum_armor_raw"]), 6),
            "sum_armor_effective": round(float(acc["sum_armor_effective"]), 6),
            "sum_armor_ignored": round(float(acc["sum_armor_ignored"]), 6),
            "avg_raw_damage": round(float(acc["sum_raw_damage"]) / attempts, 6),
            "avg_final_damage": round(float(acc["sum_final_damage"]) / attempts, 6),
            "avg_armor_raw": round(float(acc["sum_armor_raw"]) / attempts, 6),
            "avg_armor_effective": round(float(acc["sum_armor_effective"]) / attempts, 6),
            "avg_armor_ignored": round(float(acc["sum_armor_ignored"]) / attempts, 6),
            "min_raw_damage": acc["min_raw_damage"],
            "max_raw_damage": acc["max_raw_damage"],
            "min_final_damage": acc["min_final_damage"],
            "max_final_damage": acc["max_final_damage"],
            "proc_rate": round(float(acc["trigger_passes"]) / trigger_attempts, 6) if acc["trigger_attempts"] else 0.0,
            "armor_ignore_rate": round(float(acc["armor_ignore_count"]) / attempts, 6),
            "damage_after_armor_avg": round(float(acc["sum_damage_after_armor"]) / attempts, 6),
            "counters": int(acc["counters"]),
            "extra_strikes": int(acc["extra_strikes"]),
        }

    @staticmethod
    def _dimensions_damage(fact: dict[str, Any]) -> dict[str, Any]:
        trigger_id = None
        attempts = fact.get("trigger_attempts") or []
        if attempts and isinstance(attempts[0], list) and attempts[0]:
            trigger_id = attempts[0][0]
        return {
            "weapon_base_id": fact.get("weapon_base_id"),
            "weapon_tier": fact.get("weapon_tier"),
            "armor_class": fact.get("armor_class"),
            "armor_tier": fact.get("armor_tier"),
            "feint_id": fact.get("feint_id"),
            "trigger_id": trigger_id,
            "battle_type": fact.get("battle_type"),
            "location_id": fact.get("location_id"),
            "source_type": fact.get("source_type"),
        }

    @staticmethod
    def _dimensions_action(fact: dict[str, Any]) -> dict[str, Any]:
        return {
            "action_id": fact.get("action_id"),
            "feint_id": fact.get("feint_id"),
            "source_type": fact.get("source_type"),
            "battle_type": fact.get("battle_type"),
            "location_id": fact.get("location_id"),
        }

    @staticmethod
    def _dimensions_hash(dimensions: dict[str, Any]) -> str:
        payload = json.dumps(dimensions, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _bucket_start(value: datetime, grain: str) -> datetime:
        if grain == "month":
            return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return value.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _next_month(value: datetime) -> datetime:
        base = value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if base.month == 12:
            return base.replace(year=base.year + 1, month=1)
        return base.replace(month=base.month + 1)

    @staticmethod
    def _datetime_from_epoch(value: Any) -> datetime | None:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return None
        if numeric <= 0:
            return None
        return datetime.fromtimestamp(numeric, tz=UTC)

    @staticmethod
    def _analytics_sort_key(key: Any) -> tuple[int, int, str]:
        if key == "_profile":
            return (0, 0, str(key))
        parts = str(key).split(":", 1)
        try:
            turn = int(parts[0])
        except (TypeError, ValueError):
            turn = 0
        try:
            seq = int(parts[1]) if len(parts) > 1 else 0
        except (TypeError, ValueError):
            seq = 0
        return (turn, seq, str(key))

    @staticmethod
    def _float_at(values: list[Any], index: int, fallback: Any) -> float | None:
        if len(values) > index:
            return CombatAnalyticsIngestionService._optional_float(values[index])
        return CombatAnalyticsIngestionService._optional_float(fallback)

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int_value(value: Any) -> int:
        return CombatAnalyticsIngestionService._optional_int(value) or 0

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

    @staticmethod
    def _tags(entry: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        for value in entry.get("chn") or []:
            tags.append(str(value))
        if entry.get("x"):
            tags.extend(str(key) for key in entry["x"])
        return sorted(set(tags))
