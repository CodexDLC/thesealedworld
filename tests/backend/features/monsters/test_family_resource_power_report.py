from __future__ import annotations

import pytest
from tools.monsters.family_resource_power_report import build_rows, summarize


@pytest.mark.unit
def test_family_resource_power_report_covers_starter_variants_without_database() -> None:
    rows = build_rows()

    assert len(rows) == 48
    assert {row.family_id for row in rows} == {"rat_swarm", "wolf_pack", "bandit_gang", "goblin_tribe"}
    assert all(row.resource_power > 0 for row in rows)


@pytest.mark.unit
def test_family_resource_power_report_exposes_wolf_boss_baseline_skew() -> None:
    rows = build_rows()
    role_summary = {row.label: row for row in summarize(rows, key="family_role")}

    assert role_summary["wolf_pack/boss"].avg_attrs > role_summary["bandit_gang/boss"].avg_attrs
    assert role_summary["bandit_gang/boss"].avg_skills > role_summary["wolf_pack/boss"].avg_skills


@pytest.mark.unit
def test_family_resource_power_report_filters_variants_by_context_tier() -> None:
    rows = build_rows(tier=1)

    assert rows
    assert all(row.min_tier <= 1 <= row.max_tier for row in rows)
    assert all(row.context_tier == 1 for row in rows)
