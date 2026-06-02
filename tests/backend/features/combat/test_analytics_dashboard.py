from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from src.backend.features.combat.dependencies import get_combat_analytics_dashboard_service
from src.backend.features.combat.dto.analytics_dashboard import CombatAnalyticsFiltersDTO
from src.backend.features.combat.services.analytics_dashboard_service import CombatAnalyticsDashboardService


class FakeAnalyticsDashboardIntegration:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.rollup_rows = [
            {
                "bucket_start": datetime(2026, 5, 17, tzinfo=UTC),
                "bucket_grain": "day",
                "metric_key": "damage_by_weapon_armor",
                "dimensions_hash": "hash-1",
                "dimensions": {
                    "weapon_base_id": "iron_dagger",
                    "weapon_tier": 2,
                    "armor_class": "light",
                    "armor_tier": 1,
                    "feint_id": "armor_slip",
                    "trigger_id": "crit.weapon_dagger_pierce",
                    "battle_type": "pve",
                    "location_id": "51_58",
                },
                "counters": {"attempts": 4, "avg_final_damage": 10.0},
                "source_count": 4,
                "aggregate_version": 3,
                "schema_version": 1,
            }
        ]
        self.fact_rows = [
            {
                "combat_id": "combat-1",
                "turn": 1,
                "wave": 1,
                "seq": 1,
                "finished_at": datetime(2026, 5, 17, 12, tzinfo=UTC),
                "battle_type": "pve",
                "location_id": "51_58",
                "source_actor_id": "1",
                "target_actor_id": "rat-1",
                "action_id": "armor_slip",
                "feint_id": "armor_slip",
                "outcome": "crit",
                "source_type": "main_hand",
                "is_crit": True,
                "is_counter": False,
                "is_extra_strike": False,
                "weapon_base_id": "iron_dagger",
                "weapon_tier": 2,
                "weapon_power": 5.0,
                "armor_class": "light",
                "armor_tier": 1,
                "raw_damage": 18.0,
                "final_damage": 10.0,
                "armor_raw": 8.0,
                "armor_effective": 4.0,
                "armor_ignored": 4.0,
                "phys_res_raw": 0.2,
                "phys_res_effective": 0.1,
                "physical_suppression": 0.5,
                "checks": [],
                "damage_trace": {},
                "trigger_attempts": [["crit.weapon_dagger_pierce"]],
                "mutations": [],
                "equipment": {},
                "tags": [],
                "schema_version": 2,
            }
        ]

    async def latest_aggregate_version(self) -> int | None:
        self.calls.append("latest_aggregate_version")
        return 3

    async def rollup_filter_rows(self, *, aggregate_version: int) -> list[dict[str, Any]]:
        self.calls.append(f"rollup_filter_rows:{aggregate_version}")
        return self.rollup_rows

    async def query_rollups(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(f"query_rollups:{kwargs['aggregate_version']}")
        self.rollup_kwargs = kwargs
        return self.rollup_rows

    async def query_exchange_facts(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append("query_exchange_facts")
        self.fact_kwargs = kwargs
        return self.fact_rows

    async def get_raw_analytics(self, combat_id: str) -> dict[str, Any] | None:
        self.calls.append(f"get_raw_analytics:{combat_id}")
        return {
            "combat_id": combat_id,
            "analytics": {
                "_profile": {
                    "analytics_schema_version": 2,
                    "combat_math_version": "combat-math:2026-06-01.1",
                },
                "1:1": {"o": "C"},
            },
        }


@pytest.mark.unit
async def test_dashboard_filters_use_latest_rollup_version() -> None:
    integration = FakeAnalyticsDashboardIntegration()
    service = CombatAnalyticsDashboardService(integration)  # type: ignore[arg-type]

    result = await service.filters()

    assert result.aggregate_version == 3
    assert result.metric_keys == ["damage_by_weapon_armor"]
    assert result.bucket_grains == ["day"]
    assert result.dimensions["weapon_base_id"][0].value == "iron_dagger"
    assert result.dimensions["weapon_base_id"][0].source_count == 4
    assert integration.calls == ["latest_aggregate_version", "rollup_filter_rows:3"]


@pytest.mark.unit
async def test_dashboard_rollups_query_only_reads_rollups_and_normalizes_filters() -> None:
    integration = FakeAnalyticsDashboardIntegration()
    service = CombatAnalyticsDashboardService(integration)  # type: ignore[arg-type]

    result = await service.rollups(
        bucket_grain="day",
        date_from="2026-05-17",
        date_to="2026-05-17",
        metric_key="damage_by_weapon_armor",
        aggregate_version=None,
        dimensions={"weapon_tier": "2", "armor_class": "light"},
    )

    assert result.aggregate_version == 3
    assert result.rows[0].counters["avg_final_damage"] == 10.0
    assert integration.rollup_kwargs["dimensions"] == {"weapon_tier": 2, "armor_class": "light"}
    assert integration.calls == ["latest_aggregate_version", "query_rollups:3"]


@pytest.mark.unit
async def test_dashboard_drilldown_reads_exchange_facts_not_raw_analytics() -> None:
    integration = FakeAnalyticsDashboardIntegration()
    service = CombatAnalyticsDashboardService(integration)  # type: ignore[arg-type]

    result = await service.drilldown(
        date_from="2026-05-17T00:00:00Z",
        date_to="2026-05-18T00:00:00Z",
        aggregate_version=3,
        dimensions={"weapon_base_id": "iron_dagger", "armor_tier": "1"},
        limit=1000,
        offset=0,
    )

    assert result.limit == 500
    assert result.rows[0].combat_id == "combat-1"
    assert integration.fact_kwargs["dimensions"] == {"weapon_base_id": "iron_dagger", "armor_tier": 1}
    assert integration.calls == ["query_exchange_facts"]


@pytest.mark.unit
async def test_dashboard_raw_debug_is_separate_finalization_layer() -> None:
    integration = FakeAnalyticsDashboardIntegration()
    service = CombatAnalyticsDashboardService(integration)  # type: ignore[arg-type]

    result = await service.raw_debug("combat-1")

    assert result is not None
    assert result.analytics_schema_version == 2
    assert result.combat_math_version == "combat-math:2026-06-01.1"
    assert integration.calls == ["get_raw_analytics:combat-1"]


@pytest.mark.unit
def test_dashboard_filters_route_is_static_and_does_not_hit_character_route(client) -> None:
    class FakeService:
        async def filters(self, *, aggregate_version: int | None = None) -> CombatAnalyticsFiltersDTO:
            return CombatAnalyticsFiltersDTO(aggregate_version=aggregate_version or 7)

    from src.backend.app import app

    app.dependency_overrides[get_combat_analytics_dashboard_service] = lambda: FakeService()
    try:
        response = client.get("/api/game/combat/analytics/filters")
    finally:
        app.dependency_overrides.pop(get_combat_analytics_dashboard_service, None)

    assert response.status_code == 200
    assert response.json()["aggregate_version"] == 7
