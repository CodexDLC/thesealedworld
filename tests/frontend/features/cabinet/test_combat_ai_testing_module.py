from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import FormData

import src.frontend.features.cabinet.modules.combat_ai_testing.cabinet as combat_ai_testing
from fastapi_cabinet import include_cabinet
from fastapi_cabinet.contracts.widgets import ChartWidgetMap, TableWidgetMap
from src.frontend.features.cabinet.modules.combat_ai_testing.cabinet import CombatAiTestingAdmin
from src.frontend.integrations.backend_api.combat_ai_testing import CombatAiSimulationRun


def test_combat_ai_testing_admin_declares_testing_section() -> None:
    assert CombatAiTestingAdmin.key == "combat_ai_testing"
    assert CombatAiTestingAdmin.path == "/admin/combat-ai-testing"
    assert CombatAiTestingAdmin.label == "Тренировка монстров"
    assert [item.key for item in CombatAiTestingAdmin.sidebar] == [
        "overview",
        "training",
        "analytics",
        "pve-arena",
        "reports",
    ]
    assert "run" in CombatAiTestingAdmin.action_routes
    assert "training" in CombatAiTestingAdmin.sub_pages
    assert "run-detail" in CombatAiTestingAdmin.sub_pages


def test_analytics_page_orders_comparison_charts_for_balance_review() -> None:
    widgets = sorted(CombatAiTestingAdmin.sub_pages["analytics"], key=lambda widget: widget.order)

    assert [widget.key for widget in widgets[:7]] == [
        "combat_ai_clear_reports",
        "combat_ai_analytics_filter",
        "combat_ai_analytics_summary",
        "combat_ai_analytics_gear_score_chart",
        "combat_ai_analytics_survival_chart",
        "combat_ai_analytics_damage_chart",
        "combat_ai_analytics_efficiency_chart",
    ]
    assert widgets[7].key == "combat_ai_analytics_defence_chart"


@pytest.mark.asyncio
async def test_recent_runs_provider_maps_backend_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApi:
        async def list_runs(self, *, limit: int, run_kind: str | None = None):
            assert limit == 50
            assert run_kind is None
            return [
                CombatAiSimulationRun(
                    id="run-1",
                    run_kind="simulation",
                    scenario_key="mvp",
                    status="completed",
                    policy_ref="runtime_default",
                    seed=0,
                    max_rounds=5,
                    rounds_completed=2,
                    winner="red",
                    reward=12.5,
                    metadata={"completed_at": "2026-05-28T10:00:07+00:00"},
                    created_at="2026-05-28T10:00:00+00:00",
                )
            ]

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())
    request = SimpleNamespace(query_params={})

    table = await combat_ai_testing._recent_runs_provider(request)

    assert isinstance(table, TableWidgetMap)
    assert [column.key for column in table.columns[:2]] == ["created_at", "completed_at"]
    assert table.rows[0]["created_at"] == "2026-05-28 10:00:00"
    assert table.rows[0]["completed_at"] == "2026-05-28 10:00:07"
    assert table.rows[0]["scenario"] == "mvp"
    assert table.rows[0]["href"] == "/admin/combat-ai-testing/run-detail?id=run-1"


@pytest.mark.asyncio
async def test_policy_launcher_uses_training_run_dropdown(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_safe_list_runs(request, *, limit: int, run_kind: str | None = None):
        assert limit == 50
        assert run_kind == "training"
        return [
            CombatAiSimulationRun(
                id="training-1",
                run_kind="training",
                scenario_key="synthetic_policy_training",
                status="completed",
                policy_ref="candidate_not_activated",
                seed=0,
                max_rounds=60,
                rounds_completed=60,
                winner="",
                reward=21.8,
                metadata={"best_policy": {"policy_id": "candidate-v1"}},
                created_at="2026-05-29T16:34:03Z",
            )
        ]

    monkeypatch.setattr(combat_ai_testing, "_safe_list_runs", fake_safe_list_runs)

    table = await combat_ai_testing._policy_run_launcher_provider(SimpleNamespace(query_params={}))

    assert table.key == "combat_ai_policy_run_launcher"
    assert len(table.rows) == 4
    assert {row["id"] for row in table.rows} == {
        "starter_presets_5v5_live",
        "live_batch:starter_presets_5v5_live:100",
        "starter_presets_5v5_live_full_skills",
        "live_batch:starter_presets_5v5_live_full_skills:100",
    }
    assert table.actions[0].select_name == "policy_run_id"
    assert table.rows[0]["policy_options"] == [
        {
            "value": "training-1",
            "label": "2026-05-29T16:34 | reward 21.800 | candidate-v1",
            "selected": True,
        }
    ]


@pytest.mark.asyncio
async def test_battle_training_launcher_uses_training_run_dropdown(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_safe_list_runs(request, *, limit: int, run_kind: str | None = None):
        assert limit == 50
        assert run_kind == "training"
        return [
            CombatAiSimulationRun(
                id="training-1",
                run_kind="training",
                scenario_key="synthetic_policy_training",
                status="completed",
                policy_ref="candidate_not_activated",
                seed=0,
                max_rounds=60,
                rounds_completed=60,
                winner="",
                reward=21.8,
                metadata={"best_policy": {"policy_id": "candidate-v1"}},
                created_at="2026-05-29T16:34:03Z",
            )
        ]

    monkeypatch.setattr(combat_ai_testing, "_safe_list_runs", fake_safe_list_runs)

    table = await combat_ai_testing._battle_training_launcher_provider(SimpleNamespace(query_params={}))

    assert table.key == "combat_ai_battle_training_launcher"
    assert table.rows[0]["id"] == "battle_finetune"
    assert table.rows[0]["generations"] == 12
    assert table.actions[0].action == "train_battle"
    assert table.actions[0].select_name == "policy_run_id"
    assert table.actions[0].input_name == "seed"
    assert table.actions[0].input_value_key == "seed"
    assert table.rows[0]["policy_options"] == [
        {
            "value": "training-1",
            "label": "2026-05-29T16:34 | reward 21.800 | candidate-v1",
            "selected": True,
        }
    ]


@pytest.mark.asyncio
async def test_training_launcher_exposes_seed_input() -> None:
    table = await combat_ai_testing._training_launcher_provider(SimpleNamespace(query_params={}))

    assert table.rows[0]["seed"] == 0
    assert table.actions[0].action == "train_synthetic"
    assert table.actions[0].input_name == "seed"
    assert table.actions[0].input_value_key == "seed"
    assert table.actions[0].input_min == 0
    assert table.actions[0].input_max == 1_000_000


@pytest.mark.asyncio
async def test_live_limit_report_does_not_render_fake_winner() -> None:
    run = CombatAiSimulationRun(
        id="run-live",
        run_kind="simulation_live",
        scenario_key="starter_presets_5v5_live",
        status="completed",
        policy_ref="runtime_default",
        seed=0,
        max_rounds=500,
        rounds_completed=500,
        winner="",
        reward=5.3,
        telemetry={"damage_by_actor": {"blue_a": 15, "red_a": 54}},
        metadata={
            "completion_reason": "max_exchanges_reached",
            "simulation_mode": "live_tick",
            "participants": [
                {"actor_id": "blue_a", "team": "blue"},
                {"actor_id": "red_a", "team": "red"},
            ],
        },
    )

    result = await combat_ai_testing._detail_result_provider(SimpleNamespace(query_params={}))
    assert result.value == "—"

    assert combat_ai_testing._result_label(run) == "лимит"
    assert combat_ai_testing._winner_label(run) == "нет победителя"
    assert combat_ai_testing._progress_label(run) == "exchanges 500/500"
    assert "Победителя нет" in combat_ai_testing._summary_items(run)[0]


@pytest.mark.asyncio
async def test_running_battle_training_renders_training_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    run = CombatAiSimulationRun(
        id="run-training",
        run_kind="training",
        scenario_key="battle_policy_finetune",
        status="running",
        policy_ref="training:source",
        seed=0,
        max_rounds=12,
        rounds_completed=2,
        winner="",
        reward=12.5,
        telemetry={
            "run_kind": "battle_training",
            "generations": 12,
            "population": 8,
            "progress_stage": "scenario_completed",
            "current_scenario": "random_5v5_baseline_blue",
            "battles_done": 17,
            "battles_total": 384,
            "best_reward_so_far": 12.5,
        },
        metadata={"training_stage": "battle_finetune"},
    )

    async def fake_safe_get_run(_request):
        return run

    monkeypatch.setattr(combat_ai_testing, "_safe_get_run", fake_safe_get_run)

    result = await combat_ai_testing._detail_result_provider(SimpleNamespace(query_params={}))
    summary = combat_ai_testing._summary_items(run)
    telemetry_rows = combat_ai_testing._training_telemetry_rows(run)

    assert result.subtitle.startswith("battles 17/384")
    assert "battle fine-tune" in summary[0]
    assert not any("Живых актёров" in item for item in summary)
    assert {"metric": "battles_done", "value": 17} in telemetry_rows


def test_participant_rows_show_actor_analytics_and_damage_share() -> None:
    run = CombatAiSimulationRun(
        id="run-live",
        run_kind="simulation_live",
        scenario_key="starter_presets_5v5_live",
        status="completed",
        policy_ref="runtime_default",
        seed=0,
        max_rounds=500,
        rounds_completed=164,
        winner="blue",
        reward=200.0,
        telemetry={
            "damage_by_actor": {"blue_berserker": 176, "blue_guard": 34, "red_staff": 108},
            "damage_taken_by_actor": {"blue_berserker": 33},
            "action_count_by_actor": {"blue_berserker": 22},
            "target_count_by_actor": {"blue_berserker": {"red_staff": 9, "red_archer": 4}},
            "hit_by_actor": {"blue_berserker": 18},
            "crit_by_actor": {"blue_berserker": 3},
            "dodge_by_actor": {"blue_berserker": 2},
            "overkill_by_actor": {"blue_berserker": 12},
        },
        metadata={
            "completion_reason": "victory",
            "simulation_mode": "live_tick",
            "roster_mode": "seeded_random_draft",
            "roster_seed": 123,
            "roster_team_size": 2,
            "unused_imprints": ["starter_guard_01", "starter_staff_01"],
            "final_hp_by_actor": {"blue_berserker": 49},
            "participants": [
                {
                    "actor_id": "blue_berserker",
                    "label": "Borin Breaker",
                    "team": "blue",
                    "start_hp": 59,
                    "behavior_profile": "aggressive",
                },
                {"actor_id": "blue_guard", "label": "Ada Guard", "team": "blue", "start_hp": 56},
                {"actor_id": "red_staff", "label": "Hara Staff", "team": "red", "start_hp": 60},
                {"actor_id": "red_archer", "label": "Galen Archer", "team": "red", "start_hp": 55},
            ],
        },
    )

    row = combat_ai_testing._participant_rows(run)[0]

    assert row["actions"] == 22
    assert row["behavior"] == "aggressive"
    assert row["damage_per_action"] == "8.0"
    assert row["targets"] == "Hara Staff: 9, Galen Archer: 4"
    assert row["checks"] == "hit 18, crit 3, dodge 2, overkill 12"
    assert any("Borin Breaker сделал" in item for item in combat_ai_testing._finding_items(run))
    assert any("random draft" in item for item in combat_ai_testing._summary_items(run))


def test_imprint_analytics_rows_aggregate_saved_reports() -> None:
    run = CombatAiSimulationRun(
        id="run-analytics",
        run_kind="simulation_live",
        scenario_key="starter_presets_mirror_10v10",
        status="completed",
        policy_ref="runtime_default",
        seed=0,
        max_rounds=1000,
        rounds_completed=20,
        winner="blue",
        reward=100.0,
        telemetry={
            "damage_by_actor": {"blue_breaker": 120, "red_breaker": 80},
            "damage_taken_by_actor": {"blue_breaker": 40, "red_breaker": 90},
            "armor_absorbed_by_actor": {"blue_breaker": 12, "red_breaker": 8},
            "armor_absorb_events_by_actor": {"blue_breaker": 3, "red_breaker": 1},
            "action_count_by_actor": {"blue_breaker": 20, "red_breaker": 16},
            "hit_by_actor": {"blue_breaker": 12, "red_breaker": 8},
            "miss_by_actor": {"blue_breaker": 4, "red_breaker": 8},
            "crit_by_actor": {"blue_breaker": 2},
            "dodge_by_actor": {"blue_breaker": 3, "red_breaker": 1},
            "parry_by_actor": {"blue_breaker": 1},
            "block_by_actor": {"red_breaker": 2},
            "overkill_by_actor": {"blue_breaker": 10},
            "deaths": ["red_breaker"],
        },
        metadata={
            "final_hp_by_actor": {"blue_breaker": 19, "red_breaker": 0},
            "participants": [
                {
                    "actor_id": "blue_breaker",
                    "team": "blue",
                    "imprint_key": "starter_breaker_01",
                    "imprint_title": "Слепок проломщика",
                    "behavior_profile": "aggressive",
                    "start_hp": 59,
                    "combat_stats": {"armor": 6, "physical_resistance": 0.2, "hp_regen": 1.0},
                    "gear_score": {"total": 260, "offense": 120, "defense": 95, "resources": 35, "utility": 10},
                },
                {
                    "actor_id": "red_breaker",
                    "team": "red",
                    "imprint_key": "starter_breaker_01",
                    "imprint_title": "Слепок проломщика",
                    "behavior_profile": "aggressive",
                    "start_hp": 59,
                    "combat_stats": {"armor": 2, "physical_resistance": 0.1, "hp_regen": 0.0},
                    "gear_score": {"total": 280, "offense": 130, "defense": 100, "resources": 40, "utility": 10},
                },
            ],
        },
    )

    rows = combat_ai_testing._imprint_analytics_rows([run])
    expected_aggregate = {
        "imprint_key": "starter_breaker_01",
        "imprint": "Слепок проломщика",
        "behavior": "Среднее",
        "appearances": 2,
        "win_rate": 50.0,
        "survival_rate": 50.0,
        "avg_end_hp_pct": 16.102,
        "avg_damage": 100.0,
        "avg_taken": 65.0,
        "gear_score": 270.0,
        "gear_score_offense": 125.0,
        "gear_score_defense": 97.5,
        "gear_score_resources": 37.5,
        "gear_score_skills": 0.0,
        "gear_score_utility": 10.0,
        "effective_hp": 100.875,
        "armor_absorbed_per_appearance": 10.0,
        "armor_absorb_events_per_appearance": 2.0,
        "armor_absorbed_per_event": 5.0,
        "damage_per_action": 5.556,
        "hit_rate": 62.5,
        "crit_rate": 6.2,
        "avg_overkill": 5.0,
        "dodge_per_appearance": 2.0,
        "parry_per_appearance": 0.5,
        "block_per_appearance": 1.0,
        "defence_per_appearance": 5.5,
        "dodge_defence_share": 57.1,
        "parry_defence_share": 14.3,
        "block_defence_share": 28.6,
    }
    expected_role = expected_aggregate | {
        "imprint_key": "starter_breaker_01:aggressive",
        "imprint": "",
        "behavior": "aggressive",
    }

    assert rows == [expected_aggregate | {"role_rows": [expected_role]}]
    assert combat_ai_testing._expanded_analytics_table_rows(rows) == [expected_aggregate]


def test_analytics_table_expands_role_rows_only_when_multiple_behaviors() -> None:
    aggregate = {"imprint_key": "starter_breaker_01", "imprint": "Слепок проломщика", "behavior": "Среднее"}
    aggressive = {"imprint_key": "starter_breaker_01:aggressive", "imprint": "", "behavior": "aggressive"}
    defensive = {"imprint_key": "starter_breaker_01:defensive", "imprint": "", "behavior": "defensive"}

    assert combat_ai_testing._expanded_analytics_table_rows([aggregate | {"role_rows": [aggressive]}]) == [aggregate]
    assert combat_ai_testing._expanded_analytics_table_rows(
        [aggregate | {"role_rows": [aggressive, defensive]}]
    ) == [
        aggregate,
        aggressive,
        defensive,
    ]


def test_tactical_rows_show_trigger_rates_damage_and_actors() -> None:
    run = CombatAiSimulationRun(
        id="run-tactics",
        run_kind="simulation_live",
        scenario_key="starter_presets_5v5",
        status="completed",
        policy_ref="runtime_default",
        seed=0,
        max_rounds=100,
        rounds_completed=20,
        winner="blue",
        reward=20.0,
        telemetry={
            "tactical_trigger_attempts_by_id": {"style_shield_reflect": 5, "style_dual_extra": 4},
            "tactical_trigger_success_by_id": {"style_shield_reflect": 2, "style_dual_extra": 3},
            "tactical_trigger_success_by_actor": {
                "blue_guard": {"style_shield_reflect": 2},
                "blue_duelist": {"style_dual_extra": 3},
            },
            "tactical_damage_by_actor": {
                "blue_guard": {"weapon_shield_bash_on_block": 9},
                "blue_duelist": {"style_dual_extra": 21},
            },
            "tactical_reflected_by_actor": {"blue_guard": {"style_shield_reflect": 14}},
            "tactical_prevented_by_actor": {"blue_guard": {"style_shield_reflect": 30}},
            "tactical_chain_hits_by_actor": {"blue_duelist": {"style_dual_extra": 2}},
            "tactical_shield_branch_by_actor": {"blue_guard": {"defense": 3, "counter": 1}},
            "tactical_shield_damage_by_actor": {"blue_guard": {"weapon_shield_bash_on_block": 9}},
            "tactical_shield_absorbed_by_actor": {"blue_guard": {"style_shield_reflect": 30}},
            "tactical_shield_reflected_by_actor": {"blue_guard": {"style_shield_reflect": 14}},
        },
        metadata={
            "participants": [
                {"actor_id": "blue_guard", "label": "Ada Guard", "team": "blue"},
                {"actor_id": "blue_duelist", "label": "Dax Twinblades", "team": "blue"},
            ]
        },
    )

    rows = combat_ai_testing._tactical_rows(run)

    assert rows[0] == {
        "part": "Щит: поглощение и возврат",
        "attempts": 4,
        "successes": 1,
        "rate": "25.0",
        "chain_hits": 0,
        "shield_defense": 3,
        "shield_counter": 1,
        "damage": 9,
        "shield_damage": 9,
        "shield_absorbed": 30,
        "shield_reflected": 14,
        "reflected": 14,
        "prevented": 30,
        "actors": (
            "Ada Guard: 3 защ.блок, 1 контр.блок, 9 урон, 9 щит-урон, "
            "30 щит-погл., 14 щит-возвр., 14 возврат, 30 предотвр."
        ),
    }
    assert rows[1] == {
        "part": "Две руки: второй удар",
        "attempts": 4,
        "successes": 3,
        "rate": "75.0",
        "chain_hits": 2,
        "shield_defense": 0,
        "shield_counter": 0,
        "damage": 21,
        "shield_damage": 0,
        "shield_absorbed": 0,
        "shield_reflected": 0,
        "reflected": 0,
        "prevented": 0,
        "actors": "Dax Twinblades: 3 сраб., 2 chain, 21 урон",
    }
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_analytics_chart_provider_maps_saved_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApi:
        async def list_runs(self, *, limit: int, run_kind: str | None = None):
            assert limit == 200
            assert run_kind is None
            return [
                CombatAiSimulationRun(
                    id="run-analytics",
                    run_kind="simulation",
                    scenario_key="starter_presets_5v5",
                    status="completed",
                    policy_ref="runtime_default",
                    seed=0,
                    max_rounds=8,
                    rounds_completed=8,
                    winner="blue",
                    reward=10.0,
                    telemetry={"damage_by_actor": {"blue_guard": 40}, "damage_taken_by_actor": {"blue_guard": 20}},
                    metadata={
                        "participants": [
                            {
                                "actor_id": "blue_guard",
                                "team": "blue",
                                "imprint_key": "starter_guard_01",
                                "imprint_title": "Слепок стража",
                                "start_hp": 56,
                            }
                        ],
                        "final_hp_by_actor": {"blue_guard": 36},
                    },
                )
            ]

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    chart = await combat_ai_testing._analytics_damage_chart_provider(SimpleNamespace(query_params={}))

    assert isinstance(chart, ChartWidgetMap)
    assert chart.labels == ["Слепок стража"]
    assert chart.datasets[0]["data"] == [40.0]


@pytest.mark.asyncio
async def test_analytics_widgets_reuse_request_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApi:
        def __init__(self) -> None:
            self.calls = 0

        async def list_runs(self, *, limit: int, run_kind: str | None = None):
            self.calls += 1
            assert limit == 200
            assert run_kind is None
            return [
                CombatAiSimulationRun(
                    id="run-analytics",
                    run_kind="simulation_live",
                    scenario_key="starter_presets_5v5",
                    status="completed",
                    policy_ref="runtime_default",
                    seed=0,
                    max_rounds=500,
                    rounds_completed=10,
                    winner="blue",
                    reward=10.0,
                    telemetry={
                        "damage_by_actor": {"blue_guard": 40},
                        "damage_taken_by_actor": {"blue_guard": 20},
                        "action_count_by_actor": {"blue_guard": 10},
                        "tactical_trigger_attempts_by_id": {"style_shield_reflect": 2},
                    },
                    metadata={
                        "participants": [
                            {
                                "actor_id": "blue_guard",
                                "team": "blue",
                                "imprint_key": "starter_guard_01",
                                "imprint_title": "Слепок стража",
                                "start_hp": 56,
                            }
                        ],
                        "final_hp_by_actor": {"blue_guard": 36},
                    },
                )
            ]

    api = FakeApi()
    aggregate_calls = 0
    original_aggregate = combat_ai_testing._imprint_analytics_rows

    def counting_aggregate(runs):
        nonlocal aggregate_calls
        aggregate_calls += 1
        return original_aggregate(runs)

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: api)
    monkeypatch.setattr(combat_ai_testing, "_imprint_analytics_rows", counting_aggregate)
    request = SimpleNamespace(query_params={}, state=SimpleNamespace())

    await combat_ai_testing._analytics_summary_provider(request)
    await combat_ai_testing._analytics_damage_chart_provider(request)
    await combat_ai_testing._analytics_efficiency_chart_provider(request)
    await combat_ai_testing._analytics_survival_chart_provider(request)
    await combat_ai_testing._analytics_gear_score_chart_provider(request)
    await combat_ai_testing._analytics_defence_chart_provider(request)
    await combat_ai_testing._analytics_tactical_parts_provider(request)
    await combat_ai_testing._analytics_table_provider(request)

    assert api.calls == 1
    assert aggregate_calls == 1


@pytest.mark.asyncio
async def test_analytics_charts_rank_imprints_from_best_to_worst(monkeypatch: pytest.MonkeyPatch) -> None:
    run = CombatAiSimulationRun(
        id="run-analytics",
        run_kind="simulation_live",
        scenario_key="starter_presets_5v5",
        status="completed",
        policy_ref="runtime_default",
        seed=0,
        max_rounds=8,
        rounds_completed=8,
        winner="red",
        reward=10.0,
        telemetry={
            "damage_by_actor": {"blue_guard": 20, "red_staff": 60},
            "damage_taken_by_actor": {"blue_guard": 80, "red_staff": 30},
            "action_count_by_actor": {"blue_guard": 20, "red_staff": 10},
            "dodge_by_actor": {"blue_guard": 1, "red_staff": 5},
            "parry_by_actor": {"blue_guard": 0, "red_staff": 2},
            "block_by_actor": {"blue_guard": 0, "red_staff": 1},
            "armor_absorb_events_by_actor": {"blue_guard": 1, "red_staff": 4},
        },
        metadata={
            "participants": [
                {
                    "actor_id": "blue_guard",
                    "team": "blue",
                    "imprint_key": "starter_guard_01",
                    "imprint_title": "Слепок стража",
                    "start_hp": 56,
                    "gear_score": {"total": 180, "offense": 50, "defense": 90, "resources": 30, "utility": 10},
                },
                {
                    "actor_id": "red_staff",
                    "team": "red",
                    "imprint_key": "starter_staff_01",
                    "imprint_title": "Слепок боевого посоха",
                    "start_hp": 55,
                    "gear_score": {"total": 260, "offense": 130, "defense": 80, "resources": 40, "utility": 10},
                },
            ],
            "final_hp_by_actor": {"blue_guard": 0, "red_staff": 25},
        },
    )

    async def fake_analytics_runs(_request):
        return [run]

    monkeypatch.setattr(combat_ai_testing, "_analytics_runs", fake_analytics_runs)

    request = SimpleNamespace(query_params={})
    damage = await combat_ai_testing._analytics_damage_chart_provider(request)
    efficiency = await combat_ai_testing._analytics_efficiency_chart_provider(request)
    survival = await combat_ai_testing._analytics_survival_chart_provider(request)
    gear_score = await combat_ai_testing._analytics_gear_score_chart_provider(request)
    defence = await combat_ai_testing._analytics_defence_chart_provider(request)

    assert damage.labels == ["Слепок боевого посоха", "Слепок стража"]
    assert efficiency.labels == ["Слепок боевого посоха", "Слепок стража"]
    assert survival.labels == ["Слепок боевого посоха", "Слепок стража"]
    assert gear_score.labels == ["Слепок боевого посоха", "Слепок стража"]
    assert defence.labels == ["Слепок боевого посоха", "Слепок стража"]
    assert damage.options["indexAxis"] == "y"
    assert damage.options["scales"]["y"]["ticks"]["autoSkip"] is False


@pytest.mark.asyncio
async def test_analytics_ranking_charts_include_all_imprints(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "imprint": f"Слепок {index:02d}",
            "avg_damage": float(index),
            "avg_taken": float(30 - index),
            "damage_per_action": float(index) / 10,
            "win_rate": float(index),
            "survival_rate": float(30 - index),
            "gear_score": float(index),
            "gear_score_offense": float(index),
            "gear_score_defense": float(index),
            "gear_score_resources": 0.0,
            "gear_score_skills": 0.0,
            "gear_score_utility": 0.0,
            "defence_per_appearance": float(index),
            "dodge_per_appearance": float(index),
            "parry_per_appearance": 0.0,
            "block_per_appearance": 0.0,
            "armor_absorb_events_per_appearance": 0.0,
        }
        for index in range(1, 13)
    ]

    async def fake_analytics_imprint_rows(_request):
        return rows

    monkeypatch.setattr(combat_ai_testing, "_analytics_imprint_rows", fake_analytics_imprint_rows)

    request = SimpleNamespace(query_params={})
    charts = [
        await combat_ai_testing._analytics_damage_chart_provider(request),
        await combat_ai_testing._analytics_efficiency_chart_provider(request),
        await combat_ai_testing._analytics_survival_chart_provider(request),
        await combat_ai_testing._analytics_gear_score_chart_provider(request),
        await combat_ai_testing._analytics_defence_chart_provider(request),
    ]

    for chart in charts:
        assert len(chart.labels) == 12
        assert chart.labels[0] == "Слепок 12"
        assert chart.labels[-1] == "Слепок 01"


@pytest.mark.asyncio
async def test_analytics_runs_can_filter_default_and_policy_cohorts(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(run_id: str, policy_ref: str, metadata: dict[str, object]) -> CombatAiSimulationRun:
        return CombatAiSimulationRun(
            id=run_id,
            run_kind="simulation_live",
            scenario_key="starter_presets_5v5_live",
            status="completed",
            policy_ref=policy_ref,
            seed=0,
            max_rounds=500,
            rounds_completed=10,
            winner="blue",
            reward=1.0,
            metadata={"participants": [{"actor_id": f"{run_id}_actor"}], **metadata},
        )

    class FakeApi:
        async def list_runs(self, *, limit: int, run_kind: str | None = None):
            assert limit == 200
            assert run_kind is None
            return [
                run("default-run", "runtime_default", {}),
                run("policy-run", "training:training-1", {"policy_source_run_id": "training-1"}),
            ]

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    default_runs = await combat_ai_testing._analytics_runs(SimpleNamespace(query_params={"cohort": "default"}))
    policy_runs = await combat_ai_testing._analytics_runs(SimpleNamespace(query_params={"cohort": "policy"}))
    all_runs = await combat_ai_testing._analytics_runs(SimpleNamespace(query_params={"cohort": "all"}))

    assert [row.id for row in default_runs] == ["default-run"]
    assert [row.id for row in policy_runs] == ["policy-run"]
    assert [row.id for row in all_runs] == ["default-run", "policy-run"]


@pytest.mark.asyncio
async def test_analytics_filter_provider_marks_selected_cohort() -> None:
    table = await combat_ai_testing._analytics_filter_provider(SimpleNamespace(query_params={"cohort": "policy"}))

    assert table.row_href_key == "href"
    assert [row["cohort"] for row in table.rows] == ["Все бои", "Runtime default", "Training policy"]
    assert table.rows[2]["selected"] == "✓"


@pytest.mark.asyncio
async def test_analytics_gear_score_chart_uses_stacked_breakdown(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApi:
        async def list_runs(self, *, limit: int, run_kind: str | None = None):
            assert limit == 200
            assert run_kind is None
            return [
                CombatAiSimulationRun(
                    id="run-analytics",
                    run_kind="simulation",
                    scenario_key="starter_presets_5v5",
                    status="completed",
                    policy_ref="runtime_default",
                    seed=0,
                    max_rounds=8,
                    rounds_completed=8,
                    winner="blue",
                    reward=10.0,
                    metadata={
                        "participants": [
                            {
                                "actor_id": "blue_guard",
                                "team": "blue",
                                "imprint_key": "starter_guard_01",
                                "imprint_title": "Слепок стража",
                                "start_hp": 56,
                                "gear_score": {
                                    "total": 180,
                                    "offense": 60,
                                    "defense": 80,
                                    "resources": 30,
                                    "skills": 20,
                                    "utility": 10,
                                },
                            }
                        ],
                        "final_hp_by_actor": {"blue_guard": 36},
                    },
                )
            ]

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    chart = await combat_ai_testing._analytics_gear_score_chart_provider(SimpleNamespace(query_params={}))

    assert chart.title == "Gear score по слепкам"
    assert chart.options["scales"]["x"]["stacked"] is True
    assert chart.options["scales"]["y"]["stacked"] is True
    assert [dataset["label"] for dataset in chart.datasets] == [
        "Offense GS",
        "Defense GS",
        "Resources GS",
        "Skill GS",
        "Utility GS",
    ]
    assert chart.datasets[0]["data"] == [60.0]
    assert chart.datasets[1]["data"] == [80.0]
    assert chart.datasets[2]["data"] == [30.0]
    assert chart.datasets[3]["data"] == [20.0]
    assert chart.datasets[4]["data"] == [10.0]


@pytest.mark.asyncio
async def test_analytics_defence_chart_uses_stacked_defence_volume(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApi:
        async def list_runs(self, *, limit: int, run_kind: str | None = None):
            assert limit == 200
            assert run_kind is None
            return [
                CombatAiSimulationRun(
                    id="run-analytics",
                    run_kind="simulation_live",
                    scenario_key="starter_presets_5v5",
                    status="completed",
                    policy_ref="runtime_default",
                    seed=0,
                    max_rounds=8,
                    rounds_completed=8,
                    winner="blue",
                    reward=10.0,
                    telemetry={
                        "dodge_by_actor": {"blue_guard": 3},
                        "parry_by_actor": {"blue_guard": 1},
                        "block_by_actor": {"blue_guard": 2},
                        "armor_absorbed_by_actor": {"blue_guard": 400},
                        "armor_absorb_events_by_actor": {"blue_guard": 4},
                    },
                    metadata={
                        "participants": [
                            {
                                "actor_id": "blue_guard",
                                "team": "blue",
                                "imprint_key": "starter_guard_01",
                                "imprint_title": "Слепок стража",
                                "start_hp": 56,
                            }
                        ],
                        "final_hp_by_actor": {"blue_guard": 36},
                    },
                )
            ]

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    chart = await combat_ai_testing._analytics_defence_chart_provider(SimpleNamespace(query_params={}))

    assert chart.title == "Защитные срабатывания за появление"
    assert chart.options["scales"]["x"]["stacked"] is True
    assert chart.options["scales"]["y"]["stacked"] is True
    assert [dataset["label"] for dataset in chart.datasets] == ["Dodge", "Parry", "Block", "Armor"]
    assert chart.datasets[0]["data"] == [3.0]
    assert chart.datasets[1]["data"] == [1.0]
    assert chart.datasets[2]["data"] == [2.0]
    assert chart.datasets[3]["data"] == [4.0]


@pytest.mark.asyncio
async def test_batch_launcher_runs_safe_number_of_live_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeApi:
        async def run_live_demo_batch(
            self,
            *,
            count: int,
            seed: int,
            max_rounds: int,
            tick_interval_seconds: float,
            timeout_ticks: int,
            min_team_size: int = 6,
            max_team_size: int = 6,
            scenario_key: str,
            policy_run_id: str = "",
        ):
            calls.append(
                {
                    "count": count,
                    "seed": seed,
                    "max_rounds": max_rounds,
                    "tick": tick_interval_seconds,
                    "timeout": timeout_ticks,
                    "min_team_size": min_team_size,
                    "max_team_size": max_team_size,
                    "scenario_key": scenario_key,
                    "policy_run_id": policy_run_id,
                }
            )
            return []

    class FakeRequest:
        async def form(self):
            return FormData({"action": "run_demo", "request_id": "live_batch:starter_presets_random_draft_live:150"})

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())
    monkeypatch.setattr(combat_ai_testing, "_auto_seed", lambda: 999_990)

    response = await CombatAiTestingAdmin().handle_run(FakeRequest())

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/combat-ai-testing/reports"
    assert calls == [
        {
            "count": 100,
            "seed": 999990,
            "max_rounds": 500,
            "tick": 0.05,
            "timeout": 8,
            "min_team_size": 2,
            "max_team_size": 4,
            "scenario_key": "starter_presets_random_draft_live",
            "policy_run_id": "",
        }
    ]


@pytest.mark.asyncio
async def test_family_pressure_launcher_starts_async_report(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeApi:
        async def run_family_pressure(
            self,
            *,
            family_id: str,
            imprint_key: str = "",
            seed: int,
            trials: int,
            max_rounds: int,
            max_minions: int,
            max_scenarios: int,
        ):
            calls.append(
                {
                    "family_id": family_id,
                    "imprint_key": imprint_key,
                    "seed": seed,
                    "trials": trials,
                    "max_rounds": max_rounds,
                    "max_minions": max_minions,
                    "max_scenarios": max_scenarios,
                }
            )
            return CombatAiSimulationRun(
                id="family-run-1",
                run_kind="simulation",
                scenario_key=f"family_pressure:{family_id}",
                status="running",
                policy_ref="runtime_default",
                seed=seed,
                max_rounds=max_rounds,
                rounds_completed=0,
                winner="",
                reward=None,
                metadata={"family_pressure": True, "composition_reports": []},
            )

    class FakeRequest:
        async def form(self):
            return FormData(
                {
                    "action": "family_pressure",
                    "request_id": "family_pressure:rat_swarm",
                    "seed": "31",
                    "imprint_key": "starter_guard_01",
                }
            )

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    response = await CombatAiTestingAdmin().handle_run(FakeRequest())

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/combat-ai-testing/run-detail?id=family-run-1"
    assert calls == [
        {
            "family_id": "rat_swarm",
            "imprint_key": "starter_guard_01",
            "seed": 31,
            "trials": 5,
            "max_rounds": 80,
            "max_minions": 6,
            "max_scenarios": 24,
        }
    ]


@pytest.mark.asyncio
async def test_family_pressure_launcher_starts_all_imprints_for_one_family(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeApi:
        async def run_family_pressure_batch(
            self,
            *,
            family_id: str,
            seed: int,
            trials: int,
            max_rounds: int,
            max_minions: int,
            max_scenarios: int,
        ):
            calls.append(
                {
                    "family_id": family_id,
                    "seed": seed,
                    "trials": trials,
                    "max_rounds": max_rounds,
                    "max_minions": max_minions,
                    "max_scenarios": max_scenarios,
                }
            )
            return []

    class FakeRequest:
        async def form(self):
            return FormData(
                {
                    "action": "family_pressure_all_imprints",
                    "request_id": "family_pressure:goblin_tribe",
                    "seed": "71",
                }
            )

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    response = await CombatAiTestingAdmin().handle_run(FakeRequest())

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/combat-ai-testing/pve-arena"
    assert calls == [
        {
            "family_id": "goblin_tribe",
            "seed": 71,
            "trials": 5,
            "max_rounds": 80,
            "max_minions": 6,
            "max_scenarios": 24,
        }
    ]


@pytest.mark.asyncio
async def test_family_pressure_launcher_exposes_imprint_select() -> None:
    table = await combat_ai_testing._family_pressure_launcher_provider(SimpleNamespace(query_params={}))

    assert table.actions[0].select_name == "imprint_key"
    assert table.actions[0].select_label == "Слепок"
    assert table.actions[0].select_options_key == "imprint_options"
    assert table.rows[0]["imprint_options"][0]["value"] == "starter_guard_01"
    assert any(option["value"] == "starter_breaker_01" and option["selected"] for option in table.rows[0]["imprint_options"])
    assert table.actions[1].action == "family_pressure_all_imprints"
    assert table.actions[1].label == "Все слепки"
    assert table.actions[1].input_name == "seed"
    assert "случайный слепок" not in table.rows[0]["note"]
    assert table.rows[0]["runs"] == "5 на состав"
    assert [row["family"] for row in table.rows] == ["rat_swarm", "goblin_tribe", "wolf_pack", "bandit_gang"]


def test_running_family_pressure_detail_does_not_show_generic_combat_fallback() -> None:
    run = CombatAiSimulationRun(
        id="family-run",
        run_kind="simulation",
        scenario_key="family_pressure:rat_swarm",
        status="running",
        policy_ref="runtime_default",
        seed=3,
        max_rounds=80,
        rounds_completed=0,
        winner="",
        reward=None,
        telemetry={
            "run_kind": "family_pressure",
            "family_id": "rat_swarm",
            "imprint_key": "starter_breaker_01",
            "trials_per_composition": 30,
            "trials_total": 0,
        },
        metadata={
            "family_pressure": True,
            "family_id": "rat_swarm",
            "imprint_key": "starter_breaker_01",
            "trials_per_composition": 30,
            "max_minions": 6,
            "max_scenarios": 12,
            "composition_reports": [],
        },
    )

    summary = combat_ai_testing._summary_items(run)
    participant_rows = combat_ai_testing._participant_rows(run)
    parameter_rows = combat_ai_testing._family_pressure_parameter_rows(run)
    ladder_rows = combat_ai_testing._family_pressure_display_rows(run)

    assert "запущен" in summary[0]
    assert "worker" in summary[1].lower()
    assert not any(row.get("actor") == "Player model" for row in participant_rows)
    assert parameter_rows[0]["metric"] == "Семья"
    assert ladder_rows[0]["composition"] == "ожидает worker"
    assert combat_ai_testing._winner_label(run) == "считается"


def test_completed_family_pressure_rows_show_monster_roles_and_gear_scores() -> None:
    run = CombatAiSimulationRun(
        id="family-run",
        run_kind="simulation",
        scenario_key="family_pressure:rat_swarm",
        status="completed",
        policy_ref="runtime_default",
        seed=3,
        max_rounds=80,
        rounds_completed=60,
        winner="",
        reward=None,
        telemetry={"run_kind": "family_pressure", "trials_total": 60},
        metadata={
            "family_pressure": True,
            "family_id": "rat_swarm",
            "imprint_key": "starter_breaker_01",
            "imprint_title": "Breaker",
            "player_gear_score": 281,
            "player_start_hp": 61,
            "trials_per_composition": 30,
            "composition_reports": [
                {
                    "composition": {"key": "minionx2", "role_counts": {"minion": 2}},
                    "member_variants": ["rat_biter", "rat_biter"],
                    "member_roles": ["minion", "minion"],
                    "member_gear_scores": [188, 188],
                    "raw_gear_score": 376,
                    "effective_gear_score": 376.0,
                    "effective_ratio": 1.338,
                    "trials": 30,
                    "player_wins": 29,
                    "monster_wins": 1,
                    "draws": 0,
                    "player_win_rate": 0.967,
                    "avg_player_hp": 40.6,
                    "avg_rounds": 16.3,
                }
            ],
        },
    )

    rows = combat_ai_testing._family_pressure_rows(run)
    display_rows = combat_ai_testing._family_pressure_display_rows(run)

    assert rows[0]["composition"] == "2x minion"
    assert rows[0]["roles"] == "minion, minion"
    assert rows[0]["monster_gs"] == "188, 188"
    assert rows == display_rows
    assert "GS 281 / HP 61" in combat_ai_testing._summary_items(run)[1]


@pytest.mark.asyncio
async def test_family_pressure_detail_renders_chart_instead_of_raw_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    run = CombatAiSimulationRun(
        id="family-run",
        run_kind="simulation",
        scenario_key="family_pressure:rat_swarm",
        status="completed",
        policy_ref="runtime_default",
        seed=3,
        max_rounds=80,
        rounds_completed=10,
        winner="",
        reward=None,
        report_text="| composition | raw_gs |\n|---|---|\n| 3x minion | 507 |",
        telemetry={"run_kind": "family_pressure"},
        metadata={
            "family_pressure": True,
            "family_id": "rat_swarm",
            "imprint_key": "starter_breaker_01",
            "player_start_hp": 92,
            "composition_reports": [
                {
                    "composition": {"key": "minionx3", "role_counts": {"minion": 3}, "grade": "light"},
                    "member_variants": ["scavenger_rat", "scavenger_rat", "sewer_rat"],
                    "member_roles": ["minion", "minion", "minion"],
                    "member_gear_scores": [169, 169, 169],
                    "raw_gear_score": 507,
                    "effective_gear_score": 547.56,
                    "effective_ratio": 1.942,
                    "trials": 5,
                    "player_wins": 4,
                    "monster_wins": 0,
                    "draws": 1,
                    "player_win_rate": 0.8,
                    "avg_player_hp": 46,
                    "avg_rounds": 51.6,
                },
                {
                    "composition": {"key": "veteranx6", "role_counts": {"veteran": 6}, "grade": "hard"},
                    "member_variants": ["pack_rat"],
                    "member_roles": ["veteran"],
                    "member_gear_scores": [192],
                    "raw_gear_score": 1151,
                    "effective_gear_score": 1461.77,
                    "effective_ratio": 5.184,
                    "trials": 5,
                    "player_wins": 0,
                    "monster_wins": 5,
                    "draws": 0,
                    "player_win_rate": 0,
                    "avg_player_hp": 0,
                    "avg_rounds": 20,
                },
            ],
        },
    )

    async def fake_safe_get_run(_request):
        return run

    monkeypatch.setattr(combat_ai_testing, "_safe_get_run", fake_safe_get_run)

    chart = await combat_ai_testing._detail_family_pressure_chart_provider(SimpleNamespace(query_params={"id": run.id}))
    report = await combat_ai_testing._detail_report_provider(SimpleNamespace(query_params={"id": run.id}))

    assert chart.labels == ["3x minion", "6x veteran"]
    assert [dataset["label"] for dataset in chart.datasets] == ["Win %", "HP % после боя", "Ratio, норм. к максимуму"]
    assert chart.datasets[0]["data"] == [80.0, 0.0]
    assert chart.datasets[1]["data"] == [50.0, 0.0]
    assert chart.datasets[2]["data"] == [37.46, 100.0]
    assert "xRatio" not in chart.options["scales"]
    assert all("| composition |" not in item for item in report.items)


@pytest.mark.asyncio
async def test_pve_survival_chart_compares_family_imprint_breakpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    family_run = CombatAiSimulationRun(
        id="family-run",
        run_kind="simulation",
        scenario_key="family_pressure:rat_swarm",
        status="completed",
        policy_ref="runtime_default",
        seed=3,
        max_rounds=80,
        rounds_completed=30,
        winner="",
        reward=None,
        created_at="2026-05-31T12:00:00Z",
        telemetry={"run_kind": "family_pressure"},
        metadata={
            "family_pressure": True,
            "family_id": "rat_swarm",
            "imprint_key": "starter_breaker_01",
            "imprint_title": "Слепок проломщика",
            "composition_reports": [
                {
                    "composition": {"key": "minionx1", "role_counts": {"minion": 1}, "grade": "light"},
                    "member_variants": ["rat_biter"],
                    "member_roles": ["minion"],
                    "member_gear_scores": [188],
                    "raw_gear_score": 188,
                    "effective_gear_score": 188.0,
                    "effective_ratio": 0.669,
                    "trials": 30,
                    "player_wins": 30,
                    "monster_wins": 0,
                    "draws": 0,
                    "player_win_rate": 1.0,
                    "avg_player_hp": 59.0,
                    "avg_rounds": 12.0,
                },
                {
                    "composition": {"key": "minionx2", "role_counts": {"minion": 2}, "grade": "medium"},
                    "member_variants": ["rat_biter", "rat_biter"],
                    "member_roles": ["minion", "minion"],
                    "member_gear_scores": [188, 188],
                    "raw_gear_score": 376,
                    "effective_gear_score": 376.0,
                    "effective_ratio": 1.338,
                    "trials": 30,
                    "player_wins": 14,
                    "monster_wins": 16,
                    "draws": 0,
                    "player_win_rate": 0.467,
                    "avg_player_hp": 12.0,
                    "avg_rounds": 20.0,
                },
                {
                    "composition": {"key": "guard", "role_counts": {"minion": 1, "veteran": 1}, "grade": "hard"},
                    "member_variants": ["rat_biter", "pack_rat"],
                    "member_roles": ["minion", "veteran"],
                    "member_gear_scores": [188, 227],
                    "raw_gear_score": 415,
                    "effective_gear_score": 415.0,
                    "effective_ratio": 1.477,
                    "trials": 30,
                    "player_wins": 8,
                    "monster_wins": 22,
                    "draws": 0,
                    "player_win_rate": 0.267,
                    "avg_player_hp": 5.0,
                    "avg_rounds": 24.0,
                }
            ],
        },
    )

    class FakeApi:
        async def list_runs(self, *, limit: int, run_kind: str | None = None):
            assert limit == 200
            assert run_kind is None
            return [family_run]

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    chart = await combat_ai_testing._pve_survival_chart_provider(SimpleNamespace(query_params={}))
    pressure_chart = await combat_ai_testing._pve_pressure_chart_provider(SimpleNamespace(query_params={}))
    table = await combat_ai_testing._pve_pressure_table_provider(SimpleNamespace(query_params={}))
    detail_table = await combat_ai_testing._pve_composition_table_provider(SimpleNamespace(query_params={}))

    assert chart.labels == ["rat_swarm / Слепок проломщика"]
    assert chart.datasets[0]["label"] == "Чистых миньонов держит"
    assert chart.datasets[0]["data"] == [1]
    assert pressure_chart.labels == ["rat_swarm / Слепок проломщика"]
    assert pressure_chart.datasets[0]["data"] == [0.669]
    assert pressure_chart.datasets[1]["data"] == [1.338]
    assert table.rows[0]["family"] == "rat_swarm"
    assert table.rows[0]["imprint"] == "Слепок проломщика"
    assert table.rows[0]["minions_held"] == "1"
    assert table.rows[0]["minion_breakpoint"] == "2x minion"
    assert table.rows[0]["first_danger"] == "2x minion"
    assert table.rows[0]["held_pressure"] == "1x minion"
    assert detail_table.rows[0]["composition_type"] == "миньоны"
    assert detail_table.rows[0]["grade"] == "light"
    assert detail_table.rows[2]["composition_type"] == "охрана"
    assert detail_table.rows[2]["grade"] == "hard"


@pytest.mark.asyncio
async def test_pve_survival_keeps_latest_run_per_family_and_imprint(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(run_id: str, created_at: str, win_rate: float) -> CombatAiSimulationRun:
        return CombatAiSimulationRun(
            id=run_id,
            run_kind="simulation",
            scenario_key="family_pressure:rat_swarm",
            status="completed",
            policy_ref="runtime_default",
            seed=3,
            max_rounds=80,
            rounds_completed=30,
            winner="",
            reward=None,
            created_at=created_at,
            telemetry={"run_kind": "family_pressure"},
            metadata={
                "family_pressure": True,
                "family_id": "rat_swarm",
                "imprint_key": "starter_breaker_01",
                "composition_reports": [
                    {
                        "composition": {"key": "minionx1", "role_counts": {"minion": 1}},
                        "member_variants": ["rat_biter"],
                        "member_roles": ["minion"],
                        "member_gear_scores": [188],
                        "raw_gear_score": 188,
                        "effective_gear_score": 188.0,
                        "effective_ratio": 0.669,
                        "trials": 30,
                        "player_wins": int(win_rate * 30),
                        "monster_wins": 30 - int(win_rate * 30),
                        "draws": 0,
                        "player_win_rate": win_rate,
                        "avg_player_hp": 20.0,
                        "avg_rounds": 12.0,
                    }
                ],
            },
        )

    class FakeApi:
        async def list_runs(self, *, limit: int, run_kind: str | None = None):
            assert limit == 200
            assert run_kind is None
            return [
                run("new", "2026-05-31T12:00:00Z", 1.0),
                run("old", "2026-05-31T11:00:00Z", 0.0),
            ]

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    rows = await combat_ai_testing._pve_pressure_rows(SimpleNamespace(query_params={}))

    assert len(rows) == 1
    assert rows[0]["href"].endswith("id=new")
    assert rows[0]["winrate_pct"] == "100.0"


@pytest.mark.asyncio
async def test_policy_live_launcher_passes_selected_training_run(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeApi:
        async def run_live_demo(
            self,
            *,
            seed: int,
            max_rounds: int,
            tick_interval_seconds: float,
            timeout_ticks: int,
            min_team_size: int = 6,
            max_team_size: int = 6,
            scenario_key: str,
            policy_run_id: str = "",
        ):
            calls.append(
                {
                    "seed": seed,
                    "max_rounds": max_rounds,
                    "tick": tick_interval_seconds,
                    "timeout": timeout_ticks,
                    "min_team_size": min_team_size,
                    "max_team_size": max_team_size,
                    "scenario_key": scenario_key,
                    "policy_run_id": policy_run_id,
                }
            )
            return CombatAiSimulationRun(
                id="run-policy",
                run_kind="simulation_live",
                scenario_key=scenario_key,
                status="running",
                policy_ref="training:training-1",
                seed=seed,
                max_rounds=max_rounds,
                rounds_completed=0,
                winner="",
                reward=None,
            )

    class FakeRequest:
        async def form(self):
            return FormData(
                {
                    "action": "run_demo",
                    "request_id": "starter_presets_5v5_live",
                    "policy_run_id": "training-1",
                }
            )

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    response = await CombatAiTestingAdmin().handle_run(FakeRequest())

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/combat-ai-testing/run-detail?id=run-policy"
    assert calls == [
        {
            "seed": 0,
            "max_rounds": 500,
            "tick": 0.05,
            "timeout": 8,
            "min_team_size": 5,
            "max_team_size": 5,
            "scenario_key": "starter_presets_5v5_live",
            "policy_run_id": "training-1",
        }
    ]


@pytest.mark.asyncio
async def test_synthetic_training_launcher_passes_custom_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeApi:
        async def train_synthetic(self, *, generations: int, population: int, seed: int):
            calls.append({"generations": generations, "population": population, "seed": seed})
            return CombatAiSimulationRun(
                id="synthetic-train-1",
                run_kind="training",
                scenario_key="synthetic_policy_training",
                status="running",
                policy_ref="candidate_not_activated",
                seed=seed,
                max_rounds=generations,
                rounds_completed=0,
                winner="",
                reward=None,
            )

    class FakeRequest:
        async def form(self):
            return FormData({"action": "train_synthetic", "request_id": "train_60", "seed": "42"})

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    response = await CombatAiTestingAdmin().handle_run(FakeRequest())

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/combat-ai-testing/training-detail?id=synthetic-train-1"
    assert calls == [{"generations": 60, "population": 32, "seed": 42}]


@pytest.mark.asyncio
async def test_battle_training_launcher_passes_selected_training_run(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeApi:
        async def train_battle(
            self,
            *,
            source_policy_run_id: str,
            generations: int,
            population: int,
            seed: int,
        ):
            calls.append(
                {
                    "source_policy_run_id": source_policy_run_id,
                    "generations": generations,
                    "population": population,
                    "seed": seed,
                }
            )
            return CombatAiSimulationRun(
                id="battle-train-1",
                run_kind="training",
                scenario_key="battle_policy_finetune",
                status="running",
                policy_ref=f"training:{source_policy_run_id}",
                seed=seed,
                max_rounds=generations,
                rounds_completed=0,
                winner="",
                reward=None,
            )

    class FakeRequest:
        async def form(self):
            return FormData(
                {
                    "action": "train_battle",
                    "request_id": "battle_finetune",
                    "policy_run_id": "training-1",
                    "seed": "77",
                }
            )

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    response = await CombatAiTestingAdmin().handle_run(FakeRequest())

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/combat-ai-testing/training-detail?id=battle-train-1"
    assert calls == [
        {
            "source_policy_run_id": "training-1",
            "generations": 12,
            "population": 8,
            "seed": 77,
        }
    ]


@pytest.mark.asyncio
async def test_clear_reports_action_calls_backend_and_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeApi:
        async def clear_runs(self):
            calls.append("clear")
            return 12

    class FakeRequest:
        async def form(self):
            return FormData({"action": "clear_reports", "request_id": "all_reports"})

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    response = await CombatAiTestingAdmin().handle_run(FakeRequest())

    assert calls == ["clear"]
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/combat-ai-testing/reports"


@pytest.mark.asyncio
async def test_clear_training_action_calls_backend_and_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeApi:
        async def clear_training_runs(self):
            calls.append("clear_training")
            return 7

    class FakeRequest:
        async def form(self):
            return FormData({"action": "clear_training", "request_id": "training_runs"})

    monkeypatch.setattr(combat_ai_testing, "_api", lambda request: FakeApi())

    response = await CombatAiTestingAdmin().handle_run(FakeRequest())

    assert calls == ["clear_training"]
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/combat-ai-testing/training"


def test_combat_ai_testing_pages_render() -> None:
    app = FastAPI()
    include_cabinet(
        app,
        modules=("src.frontend.features.cabinet.modules.combat_ai_testing.cabinet",),
        mount_path="/admin",
    )
    client = TestClient(app)

    response = client.get("/admin/combat-ai-testing")

    assert response.status_code == 200
    assert "Тренировка монстров" in response.text
    assert "Live tick: стартовые пресеты 5v5" in response.text
    assert "random draft 2v2-4v4" not in response.text
    assert "фон, пакет live-like" in response.text
    assert "зеркало полного пула" not in response.text
    assert "Диагностика семей против стартового слепка" not in response.text
    assert "Запуск тестов: выбранная policy" in response.text
    assert "Нет завершённых policy" in response.text
    assert "память + CombatExecutor" not in response.text
    assert "Smoke 1v1" not in response.text
    assert "Запустить" in response.text
    assert "Последние отчёты" in response.text

    training = client.get("/admin/combat-ai-testing/training")
    assert training.status_code == 200
    assert "Запуск обучения весов" in training.text
    assert "Полное обучение" in training.text
    assert "Стадия 2: обучение в боях" in training.text
    assert "Очистка истории обучения" in training.text
    assert "Очистить историю" in training.text

    analytics = client.get("/admin/combat-ai-testing/analytics")
    assert analytics.status_code == 200
    assert "Аналитика слепков" in analytics.text
    assert "Очистить таблицу" in analytics.text

    pve = client.get("/admin/combat-ai-testing/pve-arena")
    assert pve.status_code == 200
    assert "PvE выживаемость" in pve.text
    assert "Диагностика семей против стартового слепка" in pve.text
    assert "Миньон-cap по слепкам" in pve.text
    assert "Сравнение слепков против PvE" in pve.text
    assert "Все PvE составы последнего прогона" in pve.text
