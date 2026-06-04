from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.backend.features.combat.runtime.analytics.ingestion import CombatAnalyticsIngestionService


@pytest.mark.unit
def test_ingestion_extracts_exchange_fact_from_finalization_analytics_v2() -> None:
    finalization = {
        "combat_id": "combat-1",
        "finished_at": int(datetime(2026, 5, 17, tzinfo=UTC).timestamp()),
        "meta": {"battle_type": "pve", "location_id": "51_58"},
        "analytics": {
            "_profile": {"v": 2, "analytics_schema_version": 2, "combat_math_version": "combat-math:2026-06-01.1"},
            "1:1": {
                "v": 2,
                "analytics_schema_version": 2,
                "combat_math_version": "combat-math:2026-06-01.1",
                "seq": 1,
                "t": 1,
                "w": 1,
                "s": "1",
                "d": "rat-1",
                "a": "armor_slip",
                "act": {"feint_id": "armor_slip", "role": "primary"},
                "m": "ex",
                "o": "C",
                "h": "main_hand",
                "dmg": [18, 8, 10],
                "dt": {
                    "raw": 18.0,
                    "final": 10.0,
                    "min": 16.0,
                    "max": 20.0,
                    "details": {
                        "dbp": {"attribute": 12.0, "weapon": 6.0, "bonus": 0.0},
                        "resl": {"raw": 0.2, "effective": 0.1, "suppression": 0.5},
                        "arm": {"raw": 8.0, "effective": 4.0, "ignored": 4.0, "chance": 0.5, "passed": True},
                    },
                },
                "trga": [["crit.weapon_dagger_pierce", "crit", "w", "iron_dagger", "main_hand", 0.5, 0.2, 1, "merge", []]],
                "mut": [["f", "armor_slip", "m1", "mods.flat_armor_penetration_bonus_pct", 0.5, []]],
                "eq": {
                    "s": {"weapon": {"base_id": "iron_dagger", "tier": 2, "power": 5.0}},
                    "d": {"armor": {"armor_class": "light", "tier": 1}},
                },
            },
        },
    }

    facts = CombatAnalyticsIngestionService.extract_exchange_facts(finalization)

    assert len(facts) == 1
    fact = facts[0]
    assert fact["combat_id"] == "combat-1"
    assert fact["turn"] == 1
    assert fact["seq"] == 1
    assert fact["source_actor_id"] == "1"
    assert fact["target_actor_id"] == "rat-1"
    assert fact["action_id"] == "armor_slip"
    assert fact["feint_id"] == "armor_slip"
    assert fact["outcome"] == "crit"
    assert fact["is_crit"] is True
    assert fact["weapon_base_id"] == "iron_dagger"
    assert fact["weapon_tier"] == 2
    assert fact["armor_class"] == "light"
    assert fact["raw_damage"] == 18.0
    assert fact["final_damage"] == 10.0
    assert fact["armor_raw"] == 8.0
    assert fact["armor_effective"] == 4.0
    assert fact["armor_ignored"] == 4.0
    assert fact["physical_suppression"] == 0.5
    assert "checks" not in fact
    assert "damage_trace" not in fact
    assert "trigger_attempts" not in fact
    assert "mutations" not in fact
    assert "equipment" not in fact
    assert "tags" not in fact

    trace_facts = CombatAnalyticsIngestionService.extract_exchange_facts(finalization, include_trace=True)
    assert trace_facts[0]["trigger_attempts"][0][0] == "crit.weapon_dagger_pierce"
    assert trace_facts[0]["mutations"][0][3] == "mods.flat_armor_penetration_bonus_pct"
    combat_document = CombatAnalyticsIngestionService.build_combat_document(finalization, trace_facts)
    assert combat_document["combat_id"] == "combat-1"
    assert combat_document["exchanges"][0]["damage_trace"]["raw"] == 18.0


@pytest.mark.unit
def test_rollup_builder_is_idempotent_for_same_fact_set_and_version() -> None:
    finished_at = datetime(2026, 5, 17, 12, 0, tzinfo=UTC)
    facts = [
        {
            "combat_id": "combat-1",
            "finished_at": finished_at,
            "battle_type": "pve",
            "location_id": "51_58",
            "weapon_base_id": "iron_dagger",
            "weapon_tier": 2,
            "armor_class": "light",
            "armor_tier": 1,
            "feint_id": "armor_slip",
            "outcome": "crit",
            "is_crit": True,
            "is_counter": False,
            "is_extra_strike": False,
            "raw_damage": 18.0,
            "final_damage": 10.0,
            "armor_raw": 8.0,
            "armor_effective": 4.0,
            "armor_ignored": 4.0,
            "trigger_attempts": [["crit.weapon_dagger_pierce", "crit", "w", "iron_dagger", "main_hand", 0.5, 0.2, 1, "merge", []]],
        }
    ]

    first = CombatAnalyticsIngestionService.build_rollups(facts, aggregate_version=1)
    second = CombatAnalyticsIngestionService.build_rollups(facts, aggregate_version=1)

    assert first == second
    day_rollup = next(row for row in first if row["bucket_grain"] == "day")
    assert day_rollup["aggregate_version"] == 1
    assert day_rollup["dimensions"]["weapon_base_id"] == "iron_dagger"
    assert day_rollup["counters"]["attempts"] == 1
    assert day_rollup["counters"]["hits"] == 1
    assert day_rollup["counters"]["crits"] == 1
    assert day_rollup["counters"]["avg_final_damage"] == 10.0
    assert day_rollup["counters"]["avg_armor_raw"] == 8.0
    assert day_rollup["counters"]["avg_armor_effective"] == 4.0
    assert day_rollup["counters"]["avg_armor_ignored"] == 4.0
    assert day_rollup["counters"]["armor_ignore_rate"] == 1.0
