from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

import httpx
from fastapi import Request
from starlette.responses import RedirectResponse, Response

from fastapi_cabinet import CabinetAdmin, ChartWidget, ListWidget, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import (
    ChartWidgetMap,
    ListWidgetMap,
    MetricWidgetMap,
    TableActionMap,
    TableColumnMap,
    TableWidgetMap,
)
from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.combat_ai_testing import CombatAiSimulationRun, CombatAiTestingApi

_BASE = "/admin/combat-ai-testing"

_TACTICAL_PART_LABELS = {
    "style_2h_ignore": "Двуручный стиль: давление",
    "style_shield_reflect": "Щит: поглощение и возврат",
    "style_ranged_perfect_backstep": "Дальний бой: идеальный отскок",
    "style_dual_extra": "Две руки: второй удар",
    "weapon_shield_bash_on_block": "Щит: ответный удар",
    "weapon_riposte_on_parry": "Рипост после парирования",
    "counter_attack": "Контратака",
    "offhand_attack": "Off-hand удар",
}


def _api(request: Request) -> CombatAiTestingApi:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    return CombatAiTestingApi(client=client, base_url=settings.backend_base_url)


async def _run_launcher_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="combat_ai_run_launcher",
        title="Запуск тестов: runtime default",
        columns=[
            TableColumnMap(key="scenario", label="Сценарий"),
            TableColumnMap(key="runs", label="Прогонов"),
            TableColumnMap(key="mode", label="Режим"),
            TableColumnMap(key="policy", label="Policy"),
            TableColumnMap(key="note", label="Что сохраняем"),
        ],
        rows=[
            {
                "id": "starter_presets_5v5_live",
                "scenario": "Live tick: стартовые пресеты 5v5",
                "runs": 1,
                "mode": "фон, 0.05 сек/tick",
                "policy": "runtime_default",
                "note": "до победы, максимум 500 exchanges; target queue, polling отчёта; live-бой не меняет",
            },
            {
                "id": "live_batch:starter_presets_5v5_live:100",
                "scenario": "Live tick: стартовые пресеты 5v5",
                "runs": 100,
                "mode": "фон, пакет live-like",
                "policy": "runtime_default",
                "note": "запускает 100 отдельных live-like боёв; состав фиксируется при заказе задачи",
            },
            {
                "id": "starter_presets_5v5_live_full_skills",
                "scenario": "Live tick: стартовые пресеты 5v5, full skills",
                "runs": 1,
                "mode": "фон, maxed existing skills",
                "policy": "runtime_default",
                "note": "та же экипировка и статы; только уже имеющиеся навыки слепков подняты до 100%",
            },
            {
                "id": "live_batch:starter_presets_5v5_live_full_skills:100",
                "scenario": "Live tick: стартовые пресеты 5v5, full skills",
                "runs": 100,
                "mode": "фон, пакет maxed skills",
                "policy": "runtime_default",
                "note": "100 отдельных 5v5 боёв; состав фиксируется при заказе, навыки слепков на 100%",
            },
            {
                "id": "starter_presets_mirror_10v10_live",
                "scenario": "Live tick: зеркало 10v10",
                "runs": 1,
                "mode": "фон, полный baseline",
                "policy": "runtime_default",
                "note": "в каждой команде все 10 стартовых слепков; удобно искать перекосы классов",
            },
            {
                "id": "live_batch:starter_presets_mirror_10v10_live:10",
                "scenario": "Live tick: зеркало 10v10",
                "runs": 10,
                "mode": "фон, пакет live-like",
                "policy": "runtime_default",
                "note": "10 зеркальных live-like боёв 10v10; самый тяжёлый baseline",
            },
            {
                "id": "starter_presets_mirror_10v10_live_full_skills",
                "scenario": "Live tick: зеркало 10v10, full skills",
                "runs": 1,
                "mode": "фон, полный baseline, maxed skills",
                "policy": "runtime_default",
                "note": "зеркальный 10v10 с той же экипировкой, но существующие навыки слепков на 100%",
            },
            {
                "id": "live_batch:starter_presets_mirror_10v10_live_full_skills:10",
                "scenario": "Live tick: зеркало 10v10, full skills",
                "runs": 10,
                "mode": "фон, пакет maxed skills",
                "policy": "runtime_default",
                "note": "10 зеркальных 10v10 боёв с прокачанными существующими навыками",
            },
        ],
        action_url=f"{_BASE}/run",
        id_key="id",
        actions=[TableActionMap(action="run_demo", label="Запустить")],
    )


async def _policy_run_launcher_provider(request: Request) -> TableWidgetMap:
    policy_options = _training_policy_options(await _safe_list_runs(request, limit=50, run_kind="training"))
    return TableWidgetMap(
        key="combat_ai_policy_run_launcher",
        title="Запуск тестов: выбранная policy",
        columns=[
            TableColumnMap(key="scenario", label="Сценарий"),
            TableColumnMap(key="runs", label="Прогонов"),
            TableColumnMap(key="mode", label="Режим"),
            TableColumnMap(key="note", label="Что сохраняем"),
        ],
        rows=[
            {
                "id": "starter_presets_5v5_live",
                "scenario": "Live tick: стартовые пресеты 5v5 + policy",
                "runs": 1,
                "mode": "фон, 0.05 сек/tick",
                "note": "один live-like бой; решения берутся из выбранной версии обучения в БД",
                "policy_options": policy_options,
            },
            {
                "id": "live_batch:starter_presets_5v5_live:100",
                "scenario": "Live tick: стартовые пресеты 5v5 + policy",
                "runs": 100,
                "mode": "фон, пакет live-like",
                "note": "100 отдельных 5v5 боёв с выбранной policy; состав фиксируется при заказе",
                "policy_options": policy_options,
            },
            {
                "id": "starter_presets_5v5_live_full_skills",
                "scenario": "Live tick: стартовые пресеты 5v5 full skills + policy",
                "runs": 1,
                "mode": "фон, maxed existing skills",
                "note": "один 5v5 бой через выбранную policy; существующие навыки слепков подняты до 100%",
                "policy_options": policy_options,
            },
            {
                "id": "live_batch:starter_presets_5v5_live_full_skills:100",
                "scenario": "Live tick: стартовые пресеты 5v5 full skills + policy",
                "runs": 100,
                "mode": "фон, пакет maxed skills",
                "note": "100 отдельных 5v5 боёв через выбранную policy; состав фиксируется при заказе",
                "policy_options": policy_options,
            },
            {
                "id": "starter_presets_mirror_10v10_live",
                "scenario": "Live tick: зеркало 10v10 + policy",
                "runs": 1,
                "mode": "фон, полный baseline",
                "note": "зеркальный live-like baseline через выбранную policy",
                "policy_options": policy_options,
            },
            {
                "id": "live_batch:starter_presets_mirror_10v10_live:10",
                "scenario": "Live tick: зеркало 10v10 + policy",
                "runs": 10,
                "mode": "фон, пакет live-like",
                "note": "10 зеркальных 10v10 боёв с выбранной policy",
                "policy_options": policy_options,
            },
            {
                "id": "starter_presets_mirror_10v10_live_full_skills",
                "scenario": "Live tick: зеркало 10v10 full skills + policy",
                "runs": 1,
                "mode": "фон, полный baseline, maxed skills",
                "note": "зеркальный 10v10 через выбранную policy; существующие навыки слепков на 100%",
                "policy_options": policy_options,
            },
            {
                "id": "live_batch:starter_presets_mirror_10v10_live_full_skills:10",
                "scenario": "Live tick: зеркало 10v10 full skills + policy",
                "runs": 10,
                "mode": "фон, пакет maxed skills",
                "note": "10 зеркальных 10v10 боёв через выбранную policy с навыками слепков на 100%",
                "policy_options": policy_options,
            },
        ],
        action_url=f"{_BASE}/run",
        id_key="id",
        actions=[
            TableActionMap(
                action="run_demo",
                label="Запустить",
                select_name="policy_run_id",
                select_options_key="policy_options",
                select_label="Policy",
            )
        ],
    )


async def _training_launcher_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="combat_ai_training_launcher",
        title="Запуск обучения весов",
        columns=[
            TableColumnMap(key="preset", label="Пресет"),
            TableColumnMap(key="generations", label="Итерации"),
            TableColumnMap(key="population", label="Популяция"),
            TableColumnMap(key="seed", label="Seed"),
            TableColumnMap(key="note", label="Что сохраняем"),
        ],
        rows=[
            {
                "id": "train_60",
                "preset": "Быстрая проверка",
                "generations": 60,
                "population": 32,
                "seed": 0,
                "note": "best policy, reward-график, дельты весов, scenario rewards",
            },
        ],
        action_url=f"{_BASE}/run",
        id_key="id",
        actions=[
            TableActionMap(
                action="train_synthetic",
                label="Запустить обучение",
                input_name="seed",
                input_value_key="seed",
                input_label="Seed",
                input_min=0,
                input_max=1_000_000,
            )
        ],
    )


async def _battle_training_launcher_provider(request: Request) -> TableWidgetMap:
    policy_options = _training_policy_options(await _safe_list_runs(request, limit=50, run_kind="training"))
    return TableWidgetMap(
        key="combat_ai_battle_training_launcher",
        title="Стадия 2: обучение в боях",
        columns=[
            TableColumnMap(key="preset", label="Режим"),
            TableColumnMap(key="generations", label="Итерации"),
            TableColumnMap(key="population", label="Популяция"),
            TableColumnMap(key="seed", label="Seed"),
            TableColumnMap(key="note", label="Что проверяем"),
        ],
        rows=[
            {
                "id": "battle_finetune",
                "preset": "Полное обучение",
                "generations": 12,
                "population": 8,
                "seed": 0,
                "note": "candidate против выбранной policy в live-like 5v5 боях; live-бой не меняет",
                "policy_options": policy_options,
            }
        ],
        action_url=f"{_BASE}/run",
        id_key="id",
        actions=[
            TableActionMap(
                action="train_battle",
                label="Запустить стадию 2",
                select_name="policy_run_id",
                select_options_key="policy_options",
                select_label="Policy",
                input_name="seed",
                input_value_key="seed",
                input_label="Seed",
                input_min=0,
                input_max=1_000_000,
            )
        ],
    )


async def _latest_runs_metric_provider(request: Request) -> MetricWidgetMap:
    runs = await _safe_list_runs(request, limit=20)
    return MetricWidgetMap(
        key="combat_ai_runs_total",
        title="Сохранённых прогонов",
        value=str(len(runs)),
        subtitle="последние 20 из таблицы результатов",
    )


async def _recent_runs_provider(request: Request) -> TableWidgetMap:
    runs = await _safe_list_runs(request, limit=50)
    return TableWidgetMap(
        key="combat_ai_recent_runs",
        title="Последние отчёты",
        columns=[
            TableColumnMap(key="created_at", label="Начало"),
            TableColumnMap(key="completed_at", label="Завершение"),
            TableColumnMap(key="scenario", label="Сценарий"),
            TableColumnMap(key="status", label="Статус"),
            TableColumnMap(key="winner", label="Победитель"),
            TableColumnMap(key="rounds", label="Шаги"),
            TableColumnMap(key="damage", label="Урон"),
            TableColumnMap(key="reward", label="Reward"),
        ],
        rows=[
            {
                "created_at": _short_ts(run.created_at),
                "completed_at": _short_ts(str(run.metadata.get("completed_at") or "")),
                "scenario": _scenario_label(run.scenario_key),
                "status": run.status,
                "winner": _winner_label(run),
                "rounds": _progress_label(run),
                "damage": _damage_summary(run.telemetry),
                "reward": "—" if run.reward is None else round(run.reward, 2),
                "href": _detail_href(run),
            }
            for run in runs
        ],
        row_href_key="href",
    )


async def _clear_reports_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="combat_ai_clear_reports",
        title="Очистка выборки",
        columns=[
            TableColumnMap(key="target", label="Что очистить"),
            TableColumnMap(key="note", label="Что будет удалено"),
        ],
        rows=[
            {
                "id": "all_reports",
                "target": "Боевая аналитика AI testing",
                "note": "удаляет только simulation/live отчёты; training-версии policy остаются в базе",
            }
        ],
        action_url=f"{_BASE}/run",
        id_key="id",
        actions=[TableActionMap(action="clear_reports", label="Очистить таблицу", css_class="fc-action-btn--danger")],
    )


async def _clear_training_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="combat_ai_clear_training",
        title="Очистка истории обучения",
        columns=[
            TableColumnMap(key="target", label="Что очистить"),
            TableColumnMap(key="note", label="Что будет удалено"),
        ],
        rows=[
            {
                "id": "training_runs",
                "target": "Все итерации обучения",
                "note": "удаляет только training-записи: synthetic и battle fine-tune; simulation/live отчёты не трогает",
            }
        ],
        action_url=f"{_BASE}/run",
        id_key="id",
        actions=[TableActionMap(action="clear_training", label="Очистить историю", css_class="fc-action-btn--danger")],
    )


async def _analytics_filter_provider(request: Request) -> TableWidgetMap:
    cohort = _analytics_cohort(request)
    rows = [
        {
            "selected": "✓" if cohort == "all" else "",
            "cohort": "Все бои",
            "note": "simulation/live отчёты вместе: default и policy",
            "href": f"{_BASE}/analytics?cohort=all",
        },
        {
            "selected": "✓" if cohort == "default" else "",
            "cohort": "Runtime default",
            "note": "только бои без выбранной training policy",
            "href": f"{_BASE}/analytics?cohort=default",
        },
        {
            "selected": "✓" if cohort == "policy" else "",
            "cohort": "Training policy",
            "note": "только бои, запущенные с policy_run_id/training row",
            "href": f"{_BASE}/analytics?cohort=policy",
        },
    ]
    return TableWidgetMap(
        key="combat_ai_analytics_filter",
        title="Выборка аналитики",
        columns=[
            TableColumnMap(key="selected", label=""),
            TableColumnMap(key="cohort", label="Вариант"),
            TableColumnMap(key="note", label="Что попадёт в графики"),
        ],
        rows=rows,
        row_href_key="href",
    )


async def _recent_training_runs_provider(request: Request) -> TableWidgetMap:
    runs = await _safe_list_runs(request, limit=50, run_kind="training")
    return TableWidgetMap(
        key="combat_ai_recent_training_runs",
        title="История обучения",
        columns=[
            TableColumnMap(key="created_at", label="Создан"),
            TableColumnMap(key="iterations", label="Итерации"),
            TableColumnMap(key="population", label="Популяция"),
            TableColumnMap(key="seed", label="Seed"),
            TableColumnMap(key="best", label="Best reward"),
            TableColumnMap(key="mean", label="Mean final"),
            TableColumnMap(key="policy", label="Policy"),
        ],
        rows=[
            {
                "created_at": _short_ts(run.created_at),
                "iterations": f"{run.rounds_completed}/{_int(run.telemetry.get('generations'))}",
                "population": _int(run.telemetry.get("population")),
                "seed": run.seed,
                "best": _round(run.telemetry.get("final_best_reward")),
                "mean": _round(run.telemetry.get("final_mean_reward")),
                "policy": run.policy_ref or "—",
                "href": f"{_BASE}/training-detail?id={run.id}",
            }
            for run in runs
        ],
        row_href_key="href",
    )


async def _analytics_summary_provider(request: Request) -> MetricWidgetMap:
    runs = await _analytics_runs(request)
    rows = await _analytics_imprint_rows(request)
    appearances = sum(_int(row.get("appearances")) for row in rows)
    return MetricWidgetMap(
        key="combat_ai_analytics_summary",
        title="Выборка",
        value=str(len(runs)),
        subtitle=f"{_analytics_cohort_label(_analytics_cohort(request))}; появлений слепков {appearances}",
    )


async def _analytics_damage_chart_provider(request: Request) -> ChartWidgetMap:
    rows = _ranked_rows(await _analytics_imprint_rows(request), key="avg_damage")
    return ChartWidgetMap(
        key="combat_ai_analytics_damage_chart",
        title="Средний урон / получено",
        chart_type="bar",
        labels=[str(row["imprint"]) for row in rows],
        datasets=[
            {"label": "Нанёс", "data": [row["avg_damage"] for row in rows], "backgroundColor": "rgba(99,102,241,0.8)"},
            {"label": "Получил", "data": [row["avg_taken"] for row in rows], "backgroundColor": "rgba(239,68,68,0.65)"},
        ],
        options=_ranking_chart_options(),
        height=_ranking_chart_height(rows),
        span=2,
    )


async def _analytics_efficiency_chart_provider(request: Request) -> ChartWidgetMap:
    rows = _ranked_rows(await _analytics_imprint_rows(request), key="damage_per_action")
    return ChartWidgetMap(
        key="combat_ai_analytics_efficiency_chart",
        title="Урон за действие",
        chart_type="bar",
        labels=[str(row["imprint"]) for row in rows],
        datasets=[
            {
                "label": "Урон/действ.",
                "data": [row["damage_per_action"] for row in rows],
                "backgroundColor": "rgba(34,197,94,0.75)",
            }
        ],
        options=_ranking_chart_options(),
        height=_ranking_chart_height(rows),
        span=2,
    )


async def _analytics_survival_chart_provider(request: Request) -> ChartWidgetMap:
    rows = _ranked_rows(await _analytics_imprint_rows(request), key="win_rate", tie_breakers=("survival_rate",))
    return ChartWidgetMap(
        key="combat_ai_analytics_survival_chart",
        title="Выживаемость и winrate",
        chart_type="bar",
        labels=[str(row["imprint"]) for row in rows],
        datasets=[
            {
                "label": "Выжил %",
                "data": [row["survival_rate"] for row in rows],
                "backgroundColor": "rgba(14,165,233,0.75)",
            },
            {"label": "Win %", "data": [row["win_rate"] for row in rows], "backgroundColor": "rgba(168,85,247,0.65)"},
        ],
        options=_ranking_chart_options(),
        height=_ranking_chart_height(rows),
        span=2,
    )


async def _analytics_gear_score_chart_provider(request: Request) -> ChartWidgetMap:
    rows = _ranked_rows(await _analytics_imprint_rows(request), key="gear_score")
    return ChartWidgetMap(
        key="combat_ai_analytics_gear_score_chart",
        title="Gear score по слепкам",
        chart_type="bar",
        labels=[str(row["imprint"]) for row in rows],
        datasets=[
            {
                "label": "Offense GS",
                "data": [row["gear_score_offense"] for row in rows],
                "backgroundColor": "rgba(99,102,241,0.78)",
            },
            {
                "label": "Defense GS",
                "data": [row["gear_score_defense"] for row in rows],
                "backgroundColor": "rgba(20,184,166,0.78)",
            },
            {
                "label": "Resources GS",
                "data": [row["gear_score_resources"] for row in rows],
                "backgroundColor": "rgba(245,158,11,0.78)",
            },
            {
                "label": "Skill GS",
                "data": [row["gear_score_skills"] for row in rows],
                "backgroundColor": "rgba(16,185,129,0.78)",
            },
            {
                "label": "Utility GS",
                "data": [row["gear_score_utility"] for row in rows],
                "backgroundColor": "rgba(100,116,139,0.78)",
            },
        ],
        options=_ranking_chart_options(stacked=True),
        height=_ranking_chart_height(rows),
        span=2,
    )


async def _analytics_defence_chart_provider(request: Request) -> ChartWidgetMap:
    rows = _ranked_rows(await _analytics_imprint_rows(request), key="defence_per_appearance")
    return ChartWidgetMap(
        key="combat_ai_analytics_defence_chart",
        title="Защитные срабатывания за появление",
        chart_type="bar",
        labels=[str(row["imprint"]) for row in rows],
        datasets=[
            {
                "label": "Dodge",
                "data": [row["dodge_per_appearance"] for row in rows],
                "backgroundColor": "rgba(20,184,166,0.78)",
            },
            {
                "label": "Parry",
                "data": [row["parry_per_appearance"] for row in rows],
                "backgroundColor": "rgba(245,158,11,0.78)",
            },
            {
                "label": "Block",
                "data": [row["block_per_appearance"] for row in rows],
                "backgroundColor": "rgba(100,116,139,0.78)",
            },
            {
                "label": "Armor",
                "data": [row["armor_absorb_events_per_appearance"] for row in rows],
                "backgroundColor": "rgba(120,113,108,0.78)",
            },
        ],
        options=_ranking_chart_options(stacked=True),
        height=_ranking_chart_height(rows),
        span=2,
    )


async def _analytics_tactical_parts_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="combat_ai_analytics_tactical_parts",
        title="Тактические части",
        columns=[
            TableColumnMap(key="part", label="Часть"),
            TableColumnMap(key="attempts", label="Попытки"),
            TableColumnMap(key="successes", label="Сработало"),
            TableColumnMap(key="rate", label="%"),
            TableColumnMap(key="chain_hits", label="Chain hits"),
            TableColumnMap(key="shield_defense", label="Блок-защ."),
            TableColumnMap(key="shield_counter", label="Блок-контр."),
            TableColumnMap(key="damage", label="Урон"),
            TableColumnMap(key="shield_damage", label="Щит-урон"),
            TableColumnMap(key="shield_absorbed", label="Щит-погл."),
            TableColumnMap(key="shield_reflected", label="Щит-возвр."),
            TableColumnMap(key="reflected", label="Возврат"),
            TableColumnMap(key="prevented", label="Предотвр."),
        ],
        rows=await _analytics_tactical_rows_for_request(request),
    )


async def _analytics_table_provider(request: Request) -> TableWidgetMap:
    rows = await _analytics_imprint_rows(request)
    return TableWidgetMap(
        key="combat_ai_analytics_table",
        title="Сводка по слепкам",
        columns=[
            TableColumnMap(key="imprint", label="Слепок"),
            TableColumnMap(key="appearances", label="Появл."),
            TableColumnMap(key="win_rate", label="Win %"),
            TableColumnMap(key="survival_rate", label="Выжил %"),
            TableColumnMap(key="gear_score", label="GS"),
            TableColumnMap(key="avg_damage", label="Ср. урон"),
            TableColumnMap(key="avg_taken", label="Ср. получено"),
            TableColumnMap(key="armor_absorbed_per_event", label="Броня/сраб."),
            TableColumnMap(key="damage_per_action", label="Урон/действ."),
            TableColumnMap(key="hit_rate", label="Hit %"),
            TableColumnMap(key="crit_rate", label="Crit %"),
            TableColumnMap(key="avg_overkill", label="Overkill"),
        ],
        rows=rows,
    )


async def _detail_status_provider(request: Request) -> MetricWidgetMap:
    run = await _safe_get_run(request)
    if run is None:
        return MetricWidgetMap(key="combat_ai_detail_status", title="Статус", value="—", subtitle="отчёт не найден")
    return MetricWidgetMap(
        key="combat_ai_detail_status",
        title="Статус",
        value=run.status,
        subtitle=f"{_scenario_label(run.scenario_key)} / policy {run.policy_ref or '—'}",
    )


async def _detail_result_provider(request: Request) -> MetricWidgetMap:
    run = await _safe_get_run(request)
    if run is None:
        return MetricWidgetMap(key="combat_ai_detail_result", title="Результат", value="—")
    if run.run_kind == "training":
        if run.status != "completed":
            return MetricWidgetMap(
                key="combat_ai_detail_result",
                title="Результат",
                value=run.status,
                subtitle=f"{_training_progress_label(run)}, обнови страницу позже",
            )
        return MetricWidgetMap(
            key="combat_ai_detail_result",
            title="Результат",
            value=str(_round(run.telemetry.get("final_best_reward"))),
            subtitle=(
                f"iterations {run.rounds_completed}/{_int(run.telemetry.get('generations'))}, "
                f"mean {_round(run.telemetry.get('final_mean_reward'))}"
            ),
        )
    if run.status == "running":
        return MetricWidgetMap(
            key="combat_ai_detail_result",
            title="Результат",
            value="running",
            subtitle=f"{_progress_label(run)}, обнови страницу",
        )
    reward = "—" if run.reward is None else round(run.reward, 2)
    return MetricWidgetMap(
        key="combat_ai_detail_result",
        title="Результат",
        value=_result_label(run),
        subtitle=f"{_progress_label(run)}, reward {reward}",
    )


async def _detail_summary_provider(request: Request) -> ListWidgetMap:
    run = await _safe_get_run(request)
    return ListWidgetMap(
        key="combat_ai_detail_summary",
        title="Что произошло",
        items=_summary_items(run),
    )


async def _detail_participants_provider(request: Request) -> TableWidgetMap:
    run = await _safe_get_run(request)
    rows = _participant_rows(run)
    return TableWidgetMap(
        key="combat_ai_detail_participants",
        title="Участники",
        columns=[
            TableColumnMap(key="actor", label="Актор"),
            TableColumnMap(key="team", label="Команда"),
            TableColumnMap(key="kind", label="Тип"),
            TableColumnMap(key="archetype", label="Характер"),
            TableColumnMap(key="imprint", label="Пресет"),
            TableColumnMap(key="hp", label="HP"),
            TableColumnMap(key="combat_stats", label="Боевые статы"),
            TableColumnMap(key="gear_score", label="GS"),
            TableColumnMap(key="actions", label="Действия"),
            TableColumnMap(key="damage_done", label="Нанёс"),
            TableColumnMap(key="damage_taken", label="Получил"),
            TableColumnMap(key="damage_per_action", label="Урон/действ."),
            TableColumnMap(key="targets", label="Цели"),
            TableColumnMap(key="checks", label="Проверки"),
        ],
        rows=rows,
    )


async def _detail_rounds_provider(request: Request) -> TableWidgetMap:
    run = await _safe_get_run(request)
    return TableWidgetMap(
        key="combat_ai_detail_rounds",
        title="События по раундам",
        columns=[
            TableColumnMap(key="round", label="Раунд"),
            TableColumnMap(key="source", label="Кто"),
            TableColumnMap(key="target", label="Цель"),
            TableColumnMap(key="damage", label="Урон"),
            TableColumnMap(key="healing", label="Лечение"),
            TableColumnMap(key="result", label="Итог"),
        ],
        rows=_round_rows(run),
    )


async def _detail_tactical_parts_provider(request: Request) -> TableWidgetMap:
    run = await _safe_get_run(request)
    return TableWidgetMap(
        key="combat_ai_detail_tactical_parts",
        title="Тактические части",
        columns=[
            TableColumnMap(key="part", label="Часть"),
            TableColumnMap(key="attempts", label="Попытки"),
            TableColumnMap(key="successes", label="Сработало"),
            TableColumnMap(key="rate", label="%"),
            TableColumnMap(key="chain_hits", label="Chain hits"),
            TableColumnMap(key="shield_defense", label="Блок-защ."),
            TableColumnMap(key="shield_counter", label="Блок-контр."),
            TableColumnMap(key="damage", label="Урон"),
            TableColumnMap(key="shield_damage", label="Щит-урон"),
            TableColumnMap(key="shield_absorbed", label="Щит-погл."),
            TableColumnMap(key="shield_reflected", label="Щит-возвр."),
            TableColumnMap(key="reflected", label="Возврат"),
            TableColumnMap(key="prevented", label="Предотвр."),
            TableColumnMap(key="actors", label="Акторы"),
        ],
        rows=_tactical_rows(run),
    )


async def _detail_training_metrics_provider(request: Request) -> TableWidgetMap:
    run = await _safe_get_run(request)
    metrics = []
    if run and run.run_kind == "training":
        metrics = [row for row in run.telemetry.get("metrics") or [] if isinstance(row, dict)]
    sampled = _sample_metrics(metrics)
    return TableWidgetMap(
        key="combat_ai_detail_training_metrics",
        title="Динамика обучения",
        columns=[
            TableColumnMap(key="generation", label="Итерация"),
            TableColumnMap(key="best_reward", label="Best reward"),
            TableColumnMap(key="mean_reward", label="Mean reward"),
            TableColumnMap(key="elapsed", label="Сек."),
        ],
        rows=[
            {
                "generation": row.get("generation", "—"),
                "best_reward": _round(row.get("best_reward")),
                "mean_reward": _round(row.get("mean_reward")),
                "elapsed": _round(row.get("elapsed_seconds")),
            }
            for row in sampled
        ],
    )


async def _detail_weight_deltas_provider(request: Request) -> TableWidgetMap:
    run = await _safe_get_run(request)
    deltas = []
    if run and run.run_kind == "training":
        deltas = [row for row in run.telemetry.get("top_weight_deltas") or [] if isinstance(row, dict)]
    return TableWidgetMap(
        key="combat_ai_detail_weight_deltas",
        title="Главные сдвиги весов",
        columns=[
            TableColumnMap(key="weight", label="Вес"),
            TableColumnMap(key="before", label="До"),
            TableColumnMap(key="after", label="После"),
            TableColumnMap(key="delta", label="Δ"),
        ],
        rows=[
            {
                "weight": row.get("weight", "—"),
                "before": _round(row.get("before")),
                "after": _round(row.get("after")),
                "delta": _signed(row.get("delta")),
            }
            for row in deltas[:20]
        ],
    )


async def _detail_scenario_rewards_provider(request: Request) -> TableWidgetMap:
    run = await _safe_get_run(request)
    rewards = {}
    if run and run.run_kind == "training":
        rewards = _dict(run.telemetry.get("scenario_rewards"))
    return TableWidgetMap(
        key="combat_ai_detail_scenario_rewards",
        title="Reward по сценариям",
        columns=[TableColumnMap(key="scenario", label="Сценарий"), TableColumnMap(key="reward", label="Reward")],
        rows=[{"scenario": key, "reward": _round(value)} for key, value in sorted(rewards.items())],
    )


async def _detail_findings_provider(request: Request) -> ListWidgetMap:
    run = await _safe_get_run(request)
    return ListWidgetMap(
        key="combat_ai_detail_findings",
        title="Выводы для баланса",
        items=_finding_items(run),
    )


async def _detail_telemetry_provider(request: Request) -> TableWidgetMap:
    run = await _safe_get_run(request)
    rows = (
        _training_telemetry_rows(run)
        if run and run.run_kind == "training"
        else _telemetry_rows(run.telemetry if run else {})
    )
    return TableWidgetMap(
        key="combat_ai_detail_telemetry",
        title="Сырые метрики",
        columns=[TableColumnMap(key="metric", label="Метрика"), TableColumnMap(key="value", label="Значение")],
        rows=rows,
    )


async def _detail_report_provider(request: Request) -> ListWidgetMap:
    run = await _safe_get_run(request)
    lines = [line for line in (run.report_text if run else "").splitlines() if line.strip()]
    return ListWidgetMap(
        key="combat_ai_detail_report",
        title="Отчёт",
        items=lines or ["Отчёт не найден."],
    )


class CombatAiTestingAdmin(CabinetAdmin):
    key = "combat_ai_testing"
    label = "Тренировка монстров"
    group = "game_server"
    group_label = "Гейм Сервер"
    path = _BASE
    order = 21
    sidebar: ClassVar = (
        SidebarItem(key="overview", label="Прогоны", path=_BASE, order=10),
        SidebarItem(key="training", label="Обучение весов", path=f"{_BASE}/training", order=20),
        SidebarItem(key="analytics", label="Аналитика слепков", path=f"{_BASE}/analytics", order=30),
        SidebarItem(key="reports", label="Отчёты", path=f"{_BASE}/reports", order=40),
    )
    dashboard_widgets: ClassVar = (
        MetricWidget(
            key="combat_ai_runs_total", title="Сохранённых прогонов", provider="combat_ai.runs_total", order=10
        ),
        TableWidget(key="combat_ai_run_launcher", title="Запуск тестов", provider="combat_ai.run_launcher", order=20),
        TableWidget(
            key="combat_ai_policy_run_launcher",
            title="Запуск тестов с policy",
            provider="combat_ai.policy_run_launcher",
            order=25,
        ),
        TableWidget(key="combat_ai_recent_runs", title="Последние отчёты", provider="combat_ai.recent_runs", order=30),
    )
    sub_pages: ClassVar[dict[str, Any]] = {
        "training": (
            TableWidget(
                key="combat_ai_training_launcher",
                title="Запуск обучения весов",
                provider="combat_ai.training_launcher",
                order=10,
            ),
            TableWidget(
                key="combat_ai_recent_training_runs",
                title="История обучения",
                provider="combat_ai.recent_training_runs",
                order=30,
            ),
            TableWidget(
                key="combat_ai_battle_training_launcher",
                title="Стадия 2: обучение в боях",
                provider="combat_ai.battle_training_launcher",
                order=20,
            ),
            TableWidget(
                key="combat_ai_clear_training",
                title="Очистка истории обучения",
                provider="combat_ai.clear_training",
                order=25,
            ),
        ),
        "reports": (
            TableWidget(
                key="combat_ai_clear_reports", title="Очистка выборки", provider="combat_ai.clear_reports", order=5
            ),
            TableWidget(
                key="combat_ai_recent_runs", title="Последние отчёты", provider="combat_ai.recent_runs", order=10
            ),
        ),
        "analytics": (
            TableWidget(
                key="combat_ai_clear_reports", title="Очистка выборки", provider="combat_ai.clear_reports", order=5
            ),
            TableWidget(
                key="combat_ai_analytics_filter",
                title="Выборка аналитики",
                provider="combat_ai.analytics.filter",
                order=6,
            ),
            MetricWidget(
                key="combat_ai_analytics_summary",
                title="Выборка",
                provider="combat_ai.analytics.summary",
                order=10,
            ),
            ChartWidget(
                key="combat_ai_analytics_gear_score_chart",
                title="Gear score по слепкам",
                provider="combat_ai.analytics.gear_score_chart",
                chart_type="bar",
                order=20,
            ),
            ChartWidget(
                key="combat_ai_analytics_survival_chart",
                title="Выживаемость и winrate",
                provider="combat_ai.analytics.survival_chart",
                chart_type="bar",
                order=30,
            ),
            ChartWidget(
                key="combat_ai_analytics_damage_chart",
                title="Средний урон / получено",
                provider="combat_ai.analytics.damage_chart",
                chart_type="bar",
                order=40,
            ),
            ChartWidget(
                key="combat_ai_analytics_efficiency_chart",
                title="Урон за действие",
                provider="combat_ai.analytics.efficiency_chart",
                chart_type="bar",
                order=45,
            ),
            ChartWidget(
                key="combat_ai_analytics_defence_chart",
                title="Защитные срабатывания",
                provider="combat_ai.analytics.defence_chart",
                chart_type="bar",
                order=50,
            ),
            TableWidget(
                key="combat_ai_analytics_tactical_parts",
                title="Тактические части",
                provider="combat_ai.analytics.tactical_parts",
                order=55,
            ),
            TableWidget(
                key="combat_ai_analytics_table",
                title="Сводка по слепкам",
                provider="combat_ai.analytics.table",
                order=60,
            ),
        ),
        "run-detail": (
            MetricWidget(key="combat_ai_detail_status", title="Статус", provider="combat_ai.detail.status", order=10),
            MetricWidget(
                key="combat_ai_detail_result", title="Результат", provider="combat_ai.detail.result", order=20
            ),
            ListWidget(
                key="combat_ai_detail_summary", title="Что произошло", provider="combat_ai.detail.summary", order=25
            ),
            TableWidget(
                key="combat_ai_detail_participants",
                title="Участники",
                provider="combat_ai.detail.participants",
                order=30,
            ),
            TableWidget(
                key="combat_ai_detail_rounds",
                title="События по раундам",
                provider="combat_ai.detail.rounds",
                order=40,
            ),
            TableWidget(
                key="combat_ai_detail_tactical_parts",
                title="Тактические части",
                provider="combat_ai.detail.tactical_parts",
                order=45,
            ),
            ListWidget(
                key="combat_ai_detail_findings",
                title="Выводы для баланса",
                provider="combat_ai.detail.findings",
                order=50,
            ),
            TableWidget(
                key="combat_ai_detail_telemetry",
                title="Сырые метрики",
                provider="combat_ai.detail.telemetry",
                order=60,
            ),
            ListWidget(
                key="combat_ai_detail_report", title="Технический лог", provider="combat_ai.detail.report", order=70
            ),
        ),
        "training-detail": (
            MetricWidget(key="combat_ai_detail_status", title="Статус", provider="combat_ai.detail.status", order=10),
            MetricWidget(
                key="combat_ai_detail_result", title="Результат", provider="combat_ai.detail.result", order=20
            ),
            ListWidget(
                key="combat_ai_detail_summary", title="Что произошло", provider="combat_ai.detail.summary", order=25
            ),
            TableWidget(
                key="combat_ai_detail_training_metrics",
                title="Динамика обучения",
                provider="combat_ai.detail.training_metrics",
                order=30,
            ),
            TableWidget(
                key="combat_ai_detail_weight_deltas",
                title="Главные сдвиги весов",
                provider="combat_ai.detail.weight_deltas",
                order=40,
            ),
            TableWidget(
                key="combat_ai_detail_scenario_rewards",
                title="Reward по сценариям",
                provider="combat_ai.detail.scenario_rewards",
                order=50,
            ),
            ListWidget(
                key="combat_ai_detail_findings",
                title="Выводы для баланса",
                provider="combat_ai.detail.findings",
                order=60,
            ),
            TableWidget(
                key="combat_ai_detail_telemetry",
                title="Сырые метрики",
                provider="combat_ai.detail.telemetry",
                order=70,
            ),
            ListWidget(
                key="combat_ai_detail_report", title="Технический лог", provider="combat_ai.detail.report", order=80
            ),
        ),
    }
    action_routes: ClassVar = {"run": ("POST", "handle_run")}
    providers: ClassVar = {
        "combat_ai.runs_total": _latest_runs_metric_provider,
        "combat_ai.run_launcher": _run_launcher_provider,
        "combat_ai.policy_run_launcher": _policy_run_launcher_provider,
        "combat_ai.training_launcher": _training_launcher_provider,
        "combat_ai.battle_training_launcher": _battle_training_launcher_provider,
        "combat_ai.recent_runs": _recent_runs_provider,
        "combat_ai.clear_reports": _clear_reports_provider,
        "combat_ai.clear_training": _clear_training_provider,
        "combat_ai.recent_training_runs": _recent_training_runs_provider,
        "combat_ai.analytics.filter": _analytics_filter_provider,
        "combat_ai.analytics.summary": _analytics_summary_provider,
        "combat_ai.analytics.damage_chart": _analytics_damage_chart_provider,
        "combat_ai.analytics.efficiency_chart": _analytics_efficiency_chart_provider,
        "combat_ai.analytics.survival_chart": _analytics_survival_chart_provider,
        "combat_ai.analytics.gear_score_chart": _analytics_gear_score_chart_provider,
        "combat_ai.analytics.defence_chart": _analytics_defence_chart_provider,
        "combat_ai.analytics.tactical_parts": _analytics_tactical_parts_provider,
        "combat_ai.analytics.table": _analytics_table_provider,
        "combat_ai.detail.status": _detail_status_provider,
        "combat_ai.detail.result": _detail_result_provider,
        "combat_ai.detail.summary": _detail_summary_provider,
        "combat_ai.detail.participants": _detail_participants_provider,
        "combat_ai.detail.rounds": _detail_rounds_provider,
        "combat_ai.detail.tactical_parts": _detail_tactical_parts_provider,
        "combat_ai.detail.training_metrics": _detail_training_metrics_provider,
        "combat_ai.detail.weight_deltas": _detail_weight_deltas_provider,
        "combat_ai.detail.scenario_rewards": _detail_scenario_rewards_provider,
        "combat_ai.detail.findings": _detail_findings_provider,
        "combat_ai.detail.telemetry": _detail_telemetry_provider,
        "combat_ai.detail.report": _detail_report_provider,
    }

    async def handle_run(self, request: Request) -> Response:
        form = await request.form()
        action = str(form.get("action") or "")
        request_id = str(form.get("request_id") or "")
        policy_run_id = str(form.get("policy_run_id") or "")
        if action == "clear_reports":
            await _api(request).clear_runs()
            return RedirectResponse(f"{_BASE}/reports", status_code=303)
        if action == "clear_training":
            await _api(request).clear_training_runs()
            return RedirectResponse(f"{_BASE}/training", status_code=303)
        if action == "train_synthetic":
            run = await _api(request).train_synthetic(generations=60, population=32, seed=_seed_from_form(form))
            return RedirectResponse(f"{_BASE}/training-detail?id={run.id}", status_code=303)
        if action == "train_battle":
            if not policy_run_id:
                return RedirectResponse(f"{_BASE}/training", status_code=303)
            run = await _api(request).train_battle(
                source_policy_run_id=policy_run_id,
                generations=12,
                population=8,
                seed=_seed_from_form(form),
            )
            return RedirectResponse(f"{_BASE}/training-detail?id={run.id}", status_code=303)
        if action != "run_demo":
            return RedirectResponse(_BASE, status_code=303)
        if request_id.startswith("live_batch:"):
            await _run_live_demo_batch(request, request_id=request_id, policy_run_id=policy_run_id)
            return RedirectResponse(f"{_BASE}/analytics", status_code=303)
        if request_id in {
            "starter_presets_5v5_live",
            "starter_presets_5v5_live_full_skills",
            "starter_presets_5v5_live_latest_training_file",
            "starter_presets_random_draft_live",
            "starter_presets_mirror_10v10_live",
            "starter_presets_mirror_10v10_live_full_skills",
            "starter_presets_mirror_10v10_live_latest_training_file",
        }:
            seed = _auto_seed() if request_id == "starter_presets_random_draft_live" else 0
            run = await _run_live_scenario(request, scenario_key=request_id, seed=seed, policy_run_id=policy_run_id)
            return RedirectResponse(f"{_BASE}/run-detail?id={run.id}", status_code=303)
        return RedirectResponse(_BASE, status_code=303)


async def _run_live_demo_batch(request: Request, *, request_id: str, policy_run_id: str = "") -> None:
    _, scenario_key, count_raw = request_id.split(":", maxsplit=2)
    count = min(max(_int(count_raw), 1), 100)
    await _api(request).run_live_demo_batch(
        count=count,
        seed=_auto_seed(),
        policy_run_id=policy_run_id,
        **_live_scenario_params(scenario_key),
    )


async def _run_live_scenario(
    request: Request,
    *,
    scenario_key: str,
    seed: int,
    policy_run_id: str = "",
) -> CombatAiSimulationRun:
    policy_kwargs = {"policy_run_id": policy_run_id} if policy_run_id else {}
    return await _api(request).run_live_demo(
        seed=seed,
        **policy_kwargs,
        **_live_scenario_params(scenario_key),
    )


def _live_scenario_params(scenario_key: str) -> dict[str, object]:
    if scenario_key == "starter_presets_random_draft_live":
        return {
            "max_rounds": 500,
            "tick_interval_seconds": 0.05,
            "timeout_ticks": 8,
            "min_team_size": 2,
            "max_team_size": 4,
            "scenario_key": scenario_key,
        }
    if scenario_key in {
        "starter_presets_mirror_10v10_live",
        "starter_presets_mirror_10v10_live_full_skills",
        "starter_presets_mirror_10v10_live_latest_training_file",
    }:
        return {
            "max_rounds": 1000,
            "tick_interval_seconds": 0.05,
            "timeout_ticks": 8,
            "scenario_key": scenario_key,
        }
    return {
        "max_rounds": 500,
        "tick_interval_seconds": 0.05,
        "timeout_ticks": 8,
        "scenario_key": scenario_key,
    }


async def _safe_list_runs(
    request: Request,
    *,
    limit: int,
    run_kind: str | None = None,
) -> list[CombatAiSimulationRun]:
    cache = _request_cache(request)
    cache_key = ("list_runs", int(limit), str(run_kind or ""))
    if cache_key in cache:
        return cache[cache_key]
    try:
        runs = await _api(request).list_runs(limit=limit, run_kind=run_kind)
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError):
        runs = []
    cache[cache_key] = runs
    return runs


def _request_cache(request: Request) -> dict[object, Any]:
    state = getattr(request, "state", None)
    if state is not None:
        cache = getattr(state, "combat_ai_testing_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            state.combat_ai_testing_cache = cache
        return cache
    cache = getattr(request, "_combat_ai_testing_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        request._combat_ai_testing_cache = cache
    return cache


def _training_policy_options(runs: list[CombatAiSimulationRun]) -> list[dict[str, object]]:
    options: list[dict[str, object]] = []
    for run in runs:
        best_policy = _dict(run.metadata.get("best_policy"))
        if run.status != "completed" or not best_policy:
            continue
        created = run.created_at[:16] if run.created_at else run.id[:8]
        reward = f"{run.reward:.3f}" if run.reward is not None else "n/a"
        policy_id = str(best_policy.get("policy_id") or run.policy_ref or "candidate")
        options.append(
            {
                "value": run.id,
                "label": f"{created} | reward {reward} | {policy_id}",
                "selected": not options,
            }
        )
    return options or [{"value": "", "label": "Нет завершённых policy", "selected": True}]


async def _analytics_runs(request: Request) -> list[CombatAiSimulationRun]:
    cache = _request_cache(request)
    cohort = _analytics_cohort(request)
    cache_key = ("analytics_runs", cohort)
    if cache_key in cache:
        return cache[cache_key]
    runs = await _safe_list_runs(request, limit=200)
    filtered = [
        run
        for run in runs
        if run.status == "completed"
        and run.run_kind in {"simulation", "simulation_live"}
        and run.metadata.get("participants")
        if _analytics_cohort_matches(run, cohort)
    ]
    cache[cache_key] = filtered
    return filtered


async def _analytics_imprint_rows(request: Request) -> list[dict[str, object]]:
    cache = _request_cache(request)
    cache_key = ("analytics_imprint_rows", _analytics_cohort(request))
    if cache_key in cache:
        return cache[cache_key]
    rows = _imprint_analytics_rows(await _analytics_runs(request))
    cache[cache_key] = rows
    return rows


async def _analytics_tactical_rows_for_request(request: Request) -> list[dict[str, object]]:
    cache = _request_cache(request)
    cache_key = ("analytics_tactical_rows", _analytics_cohort(request))
    if cache_key in cache:
        return cache[cache_key]
    rows = _analytics_tactical_rows(await _analytics_runs(request))
    cache[cache_key] = rows
    return rows


def _analytics_cohort(request: Request) -> str:
    raw = str(getattr(request, "query_params", {}).get("cohort", "all") or "all")
    return raw if raw in {"all", "default", "policy"} else "all"


def _analytics_cohort_matches(run: CombatAiSimulationRun, cohort: str) -> bool:
    if cohort == "all":
        return True
    is_policy = bool(run.metadata.get("policy_source_run_id")) or str(run.policy_ref or "").startswith("training:")
    if cohort == "policy":
        return is_policy
    return not is_policy


def _analytics_cohort_label(cohort: str) -> str:
    return {
        "all": "все бои",
        "default": "runtime default",
        "policy": "training policy",
    }.get(cohort, "все бои")


async def _safe_get_run(request: Request) -> CombatAiSimulationRun | None:
    run_id = request.query_params.get("id", "")
    if not run_id:
        return None
    try:
        return await _api(request).get_run(run_id)
    except (AttributeError, httpx.HTTPStatusError, httpx.RequestError):
        return None


def _top_analytics_rows(
    runs: list[CombatAiSimulationRun],
    *,
    key: str,
    limit: int,
    tie_breakers: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    return _top_rows(_imprint_analytics_rows(runs), key=key, limit=limit, tie_breakers=tie_breakers)


def _ranked_rows(
    rows: list[dict[str, object]],
    *,
    key: str,
    tie_breakers: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    sort_keys = (key, *tie_breakers)
    return sorted(
        rows,
        key=lambda row: (*(-_float(row.get(sort_key)) for sort_key in sort_keys), str(row["imprint"])),
    )


def _ranking_chart_height(rows: list[dict[str, object]]) -> int:
    return max(300, min(900, 90 + len(rows) * 28))


def _ranking_chart_options(*, stacked: bool = False) -> dict[str, object]:
    scales: dict[str, object] = {
        "x": {"min": 0},
        "y": {"ticks": {"autoSkip": False}},
    }
    if stacked:
        scales["x"] = {"stacked": True, "min": 0}
        scales["y"] = {"stacked": True, "ticks": {"autoSkip": False}}
    return {"indexAxis": "y", "scales": scales}


def _top_rows(
    rows: list[dict[str, object]],
    *,
    key: str,
    limit: int,
    tie_breakers: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    sort_keys = (key, *tie_breakers)
    return sorted(
        rows,
        key=lambda row: (*(-_float(row.get(sort_key)) for sort_key in sort_keys), str(row["imprint"])),
    )[:limit]


def _analytics_tactical_rows(runs: list[CombatAiSimulationRun]) -> list[dict[str, object]]:
    attempts: dict[str, int] = {}
    successes: dict[str, int] = {}
    damage: dict[str, int] = {}
    reflected: dict[str, int] = {}
    prevented: dict[str, int] = {}
    chain_hits: dict[str, int] = {}
    shield_branch: dict[str, int] = {}
    shield_damage: dict[str, int] = {}
    shield_absorbed: dict[str, int] = {}
    shield_reflected: dict[str, int] = {}
    for run in runs:
        telemetry = run.telemetry
        for part_id, value in _dict(telemetry.get("tactical_trigger_attempts_by_id")).items():
            attempts[str(part_id)] = attempts.get(str(part_id), 0) + _int(value)
        for part_id, value in _dict(telemetry.get("tactical_trigger_success_by_id")).items():
            successes[str(part_id)] = successes.get(str(part_id), 0) + _int(value)
        _merge_tactical_nested_totals(damage, telemetry.get("tactical_damage_by_actor"))
        _merge_tactical_nested_totals(reflected, telemetry.get("tactical_reflected_by_actor"))
        _merge_tactical_nested_totals(prevented, telemetry.get("tactical_prevented_by_actor"))
        _merge_tactical_nested_totals(chain_hits, telemetry.get("tactical_chain_hits_by_actor"))
        _merge_tactical_shield_branch_totals(shield_branch, telemetry.get("tactical_shield_branch_by_actor"))
        _merge_tactical_nested_totals(shield_damage, telemetry.get("tactical_shield_damage_by_actor"))
        _merge_tactical_nested_totals(shield_absorbed, telemetry.get("tactical_shield_absorbed_by_actor"))
        _merge_tactical_nested_totals(shield_reflected, telemetry.get("tactical_shield_reflected_by_actor"))

    part_ids = set(attempts) | set(successes) | set(damage) | set(reflected) | set(prevented) | set(chain_hits)
    if shield_branch:
        part_ids.add("style_shield_reflect")
    part_ids |= set(shield_damage) | set(shield_absorbed) | set(shield_reflected)
    rows = [
        {
            "part": _tactical_part_label(part_id),
            "attempts": attempts.get(part_id, 0),
            "successes": successes.get(part_id, 0),
            "rate": _round(_pct(successes.get(part_id, 0), attempts.get(part_id, 0))),
            "chain_hits": chain_hits.get(part_id, 0),
            "shield_defense": shield_branch.get("defense", 0) if part_id == "style_shield_reflect" else 0,
            "shield_counter": shield_branch.get("counter", 0) if part_id == "style_shield_reflect" else 0,
            "damage": damage.get(part_id, 0),
            "shield_damage": shield_damage.get(part_id, 0),
            "shield_absorbed": shield_absorbed.get(part_id, 0),
            "shield_reflected": shield_reflected.get(part_id, 0),
            "reflected": reflected.get(part_id, 0),
            "prevented": prevented.get(part_id, 0),
            "_sort": (
                damage.get(part_id, 0)
                + reflected.get(part_id, 0)
                + prevented.get(part_id, 0)
                + shield_damage.get(part_id, 0)
                + shield_absorbed.get(part_id, 0)
                + shield_reflected.get(part_id, 0),
                successes.get(part_id, 0)
                + chain_hits.get(part_id, 0)
                + (shield_branch.get("defense", 0) if part_id == "style_shield_reflect" else 0)
                + (shield_branch.get("counter", 0) if part_id == "style_shield_reflect" else 0),
                attempts.get(part_id, 0),
            ),
        }
        for part_id in part_ids
    ]
    rows.sort(
        key=lambda row: (-_int(row["_sort"][0]), -_int(row["_sort"][1]), -_int(row["_sort"][2]), str(row["part"]))
    )
    for row in rows:
        row.pop("_sort", None)
    return rows


def _tactical_rows(run: CombatAiSimulationRun | None) -> list[dict[str, object]]:
    if run is None:
        return []
    telemetry = run.telemetry
    attempts = {str(key): _int(value) for key, value in _dict(telemetry.get("tactical_trigger_attempts_by_id")).items()}
    successes = {str(key): _int(value) for key, value in _dict(telemetry.get("tactical_trigger_success_by_id")).items()}
    damage = _tactical_damage_by_part(telemetry)
    reflected = _tactical_nested_totals(telemetry.get("tactical_reflected_by_actor"))
    prevented = _tactical_nested_totals(telemetry.get("tactical_prevented_by_actor"))
    chain_hits = _tactical_nested_totals(telemetry.get("tactical_chain_hits_by_actor"))
    shield_branch = _tactical_shield_branch_totals(telemetry.get("tactical_shield_branch_by_actor"))
    shield_damage = _tactical_nested_totals(telemetry.get("tactical_shield_damage_by_actor"))
    shield_absorbed = _tactical_nested_totals(telemetry.get("tactical_shield_absorbed_by_actor"))
    shield_reflected = _tactical_nested_totals(telemetry.get("tactical_shield_reflected_by_actor"))
    part_ids = set(attempts) | set(successes) | set(damage) | set(reflected) | set(prevented) | set(chain_hits)
    if shield_branch:
        part_ids.add("style_shield_reflect")
    part_ids |= set(shield_damage) | set(shield_absorbed) | set(shield_reflected)
    rows = [
        {
            "part": _tactical_part_label(part_id),
            "attempts": attempts.get(part_id, 0),
            "successes": successes.get(part_id, 0),
            "rate": _round(_pct(successes.get(part_id, 0), attempts.get(part_id, 0))),
            "chain_hits": chain_hits.get(part_id, 0),
            "shield_defense": shield_branch.get("defense", 0) if part_id == "style_shield_reflect" else 0,
            "shield_counter": shield_branch.get("counter", 0) if part_id == "style_shield_reflect" else 0,
            "damage": damage.get(part_id, 0),
            "shield_damage": shield_damage.get(part_id, 0),
            "shield_absorbed": shield_absorbed.get(part_id, 0),
            "shield_reflected": shield_reflected.get(part_id, 0),
            "reflected": reflected.get(part_id, 0),
            "prevented": prevented.get(part_id, 0),
            "actors": _tactical_actor_label(run, part_id),
            "_sort": (
                damage.get(part_id, 0)
                + reflected.get(part_id, 0)
                + prevented.get(part_id, 0)
                + shield_damage.get(part_id, 0)
                + shield_absorbed.get(part_id, 0)
                + shield_reflected.get(part_id, 0),
                successes.get(part_id, 0)
                + chain_hits.get(part_id, 0)
                + (shield_branch.get("defense", 0) if part_id == "style_shield_reflect" else 0)
                + (shield_branch.get("counter", 0) if part_id == "style_shield_reflect" else 0),
                attempts.get(part_id, 0),
            ),
        }
        for part_id in part_ids
    ]
    rows.sort(
        key=lambda row: (-_int(row["_sort"][0]), -_int(row["_sort"][1]), -_int(row["_sort"][2]), str(row["part"]))
    )
    for row in rows:
        row.pop("_sort", None)
    return rows


def _tactical_damage_by_part(telemetry: dict[str, Any]) -> dict[str, int]:
    return _tactical_nested_totals(telemetry.get("tactical_damage_by_actor"))


def _tactical_nested_totals(value: Any) -> dict[str, int]:
    totals: dict[str, int] = {}
    _merge_tactical_nested_totals(totals, value)
    return totals


def _tactical_shield_branch_totals(value: Any) -> dict[str, int]:
    totals: dict[str, int] = {}
    _merge_tactical_shield_branch_totals(totals, value)
    return totals


def _merge_tactical_nested_totals(totals: dict[str, int], value: Any) -> None:
    for actor_parts in _dict(value).values():
        for part_id, value in _dict(actor_parts).items():
            totals[str(part_id)] = totals.get(str(part_id), 0) + _int(value)


def _merge_tactical_shield_branch_totals(totals: dict[str, int], value: Any) -> None:
    for actor_branches in _dict(value).values():
        for branch, value in _dict(actor_branches).items():
            branch_id = str(branch)
            if branch_id in {"defense", "counter"}:
                totals[branch_id] = totals.get(branch_id, 0) + _int(value)


def _tactical_actor_label(run: CombatAiSimulationRun, part_id: str) -> str:
    labels = _actor_labels(run)
    success_by_actor = _dict(run.telemetry.get("tactical_trigger_success_by_actor"))
    damage_by_actor = _dict(run.telemetry.get("tactical_damage_by_actor"))
    reflected_by_actor = _dict(run.telemetry.get("tactical_reflected_by_actor"))
    prevented_by_actor = _dict(run.telemetry.get("tactical_prevented_by_actor"))
    chain_hits_by_actor = _dict(run.telemetry.get("tactical_chain_hits_by_actor"))
    shield_branch_by_actor = _dict(run.telemetry.get("tactical_shield_branch_by_actor"))
    shield_damage_by_actor = _dict(run.telemetry.get("tactical_shield_damage_by_actor"))
    shield_absorbed_by_actor = _dict(run.telemetry.get("tactical_shield_absorbed_by_actor"))
    shield_reflected_by_actor = _dict(run.telemetry.get("tactical_shield_reflected_by_actor"))
    parts: list[str] = []
    actor_ids = (
        set(success_by_actor)
        | set(damage_by_actor)
        | set(reflected_by_actor)
        | set(prevented_by_actor)
        | set(chain_hits_by_actor)
        | set(shield_branch_by_actor)
        | set(shield_damage_by_actor)
        | set(shield_absorbed_by_actor)
        | set(shield_reflected_by_actor)
    )
    for actor_id in sorted(actor_ids):
        success_count = _int(_dict(success_by_actor.get(actor_id)).get(part_id))
        chain_hits = _int(_dict(chain_hits_by_actor.get(actor_id)).get(part_id))
        damage = _int(_dict(damage_by_actor.get(actor_id)).get(part_id))
        reflected = _int(_dict(reflected_by_actor.get(actor_id)).get(part_id))
        prevented = _int(_dict(prevented_by_actor.get(actor_id)).get(part_id))
        shield_branches = _dict(shield_branch_by_actor.get(actor_id))
        shield_defense = _int(shield_branches.get("defense")) if part_id == "style_shield_reflect" else 0
        shield_counter = _int(shield_branches.get("counter")) if part_id == "style_shield_reflect" else 0
        shield_damage = _int(_dict(shield_damage_by_actor.get(actor_id)).get(part_id))
        shield_absorbed = _int(_dict(shield_absorbed_by_actor.get(actor_id)).get(part_id))
        shield_reflected = _int(_dict(shield_reflected_by_actor.get(actor_id)).get(part_id))
        if not any(
            (
                success_count,
                chain_hits,
                damage,
                reflected,
                prevented,
                shield_defense,
                shield_counter,
                shield_damage,
                shield_absorbed,
                shield_reflected,
            )
        ):
            continue
        label = labels.get(str(actor_id), str(actor_id))
        details = []
        if success_count:
            details.append(f"{success_count} сраб.")
        if chain_hits:
            details.append(f"{chain_hits} chain")
        if shield_defense:
            details.append(f"{shield_defense} защ.блок")
        if shield_counter:
            details.append(f"{shield_counter} контр.блок")
        if damage:
            details.append(f"{damage} урон")
        if shield_damage:
            details.append(f"{shield_damage} щит-урон")
        if shield_absorbed:
            details.append(f"{shield_absorbed} щит-погл.")
        if shield_reflected:
            details.append(f"{shield_reflected} щит-возвр.")
        if reflected:
            details.append(f"{reflected} возврат")
        if prevented:
            details.append(f"{prevented} предотвр.")
        parts.append(f"{label}: {', '.join(details)}")
    return " / ".join(parts) if parts else "—"


def _tactical_part_label(part_id: str) -> str:
    return _TACTICAL_PART_LABELS.get(part_id, part_id)


def _imprint_analytics_rows(runs: list[CombatAiSimulationRun]) -> list[dict[str, object]]:
    aggregate: dict[str, dict[str, Any]] = {}
    for run in runs:
        participants = [row for row in (run.metadata.get("participants") or []) if isinstance(row, dict)]
        final_hp = _dict(run.metadata.get("final_hp_by_actor"))
        damage = _dict(run.telemetry.get("damage_by_actor"))
        taken = _dict(run.telemetry.get("damage_taken_by_actor"))
        actions = _dict(run.telemetry.get("action_count_by_actor"))
        hits = _dict(run.telemetry.get("hit_by_actor"))
        misses = _dict(run.telemetry.get("miss_by_actor"))
        crits = _dict(run.telemetry.get("crit_by_actor"))
        dodges = _dict(run.telemetry.get("dodge_by_actor"))
        parries = _dict(run.telemetry.get("parry_by_actor"))
        blocks = _dict(run.telemetry.get("block_by_actor"))
        armor_absorbed = _dict(run.telemetry.get("armor_absorbed_by_actor"))
        armor_absorb_events = _dict(run.telemetry.get("armor_absorb_events_by_actor"))
        overkill = _dict(run.telemetry.get("overkill_by_actor"))
        deaths = {str(actor_id) for actor_id in run.telemetry.get("deaths") or []}
        for participant in participants:
            actor_id = str(participant.get("actor_id") or "")
            imprint_key = str(participant.get("imprint_key") or actor_id)
            if not actor_id or not imprint_key:
                continue
            row = aggregate.setdefault(
                imprint_key,
                {
                    "imprint_key": imprint_key,
                    "imprint": participant.get("imprint_title") or imprint_key,
                    "appearances": 0,
                    "wins": 0,
                    "survived": 0,
                    "damage": 0,
                    "taken": 0,
                    "actions": 0,
                    "hits": 0,
                    "misses": 0,
                    "crits": 0,
                    "dodges": 0,
                    "parries": 0,
                    "blocks": 0,
                    "armor_absorbed": 0,
                    "armor_absorb_events": 0,
                    "overkill": 0,
                    "gear_score_total": 0.0,
                    "gear_score_offense": 0.0,
                    "gear_score_defense": 0.0,
                    "gear_score_resources": 0.0,
                    "gear_score_skills": 0.0,
                    "gear_score_utility": 0.0,
                    "end_hp_pct_total": 0.0,
                },
            )
            row["appearances"] += 1
            if run.winner and str(participant.get("team") or "") == run.winner:
                row["wins"] += 1
            end_hp = _int(final_hp.get(actor_id))
            start_hp = max(1, _int(participant.get("start_hp")))
            if end_hp > 0 and actor_id not in deaths:
                row["survived"] += 1
            row["end_hp_pct_total"] += max(0.0, min(100.0, end_hp / start_hp * 100))
            row["damage"] += _int(damage.get(actor_id))
            row["taken"] += _int(taken.get(actor_id))
            row["actions"] += _int(actions.get(actor_id))
            row["hits"] += _int(hits.get(actor_id))
            row["misses"] += _int(misses.get(actor_id))
            row["crits"] += _int(crits.get(actor_id))
            row["dodges"] += _int(dodges.get(actor_id))
            row["parries"] += _int(parries.get(actor_id))
            row["blocks"] += _int(blocks.get(actor_id))
            row["armor_absorbed"] += _int(armor_absorbed.get(actor_id))
            row["armor_absorb_events"] += _int(armor_absorb_events.get(actor_id))
            row["overkill"] += _int(overkill.get(actor_id))
            gear_score = _gear_score_breakdown(participant.get("gear_score"))
            row["gear_score_total"] += gear_score["total"]
            row["gear_score_offense"] += gear_score["offense"]
            row["gear_score_defense"] += gear_score["defense"]
            row["gear_score_resources"] += gear_score["resources"]
            row["gear_score_skills"] += gear_score["skills"]
            row["gear_score_utility"] += gear_score["utility"]

    rows: list[dict[str, object]] = []
    for item in aggregate.values():
        appearances = max(1, _int(item["appearances"]))
        attempts = _int(item["hits"]) + _int(item["misses"])
        defence = _int(item["dodges"]) + _int(item["parries"]) + _int(item["blocks"])
        defence_total = max(1, defence)
        actions = max(1, _int(item["actions"]))
        armor_events = max(1, _int(item["armor_absorb_events"]))
        rows.append(
            {
                "imprint_key": item["imprint_key"],
                "imprint": item["imprint"],
                "appearances": appearances,
                "win_rate": _pct(item["wins"], appearances),
                "survival_rate": _pct(item["survived"], appearances),
                "avg_end_hp_pct": _avg(item["end_hp_pct_total"], appearances),
                "avg_damage": _avg(item["damage"], appearances),
                "avg_taken": _avg(item["taken"], appearances),
                "gear_score": _avg(item["gear_score_total"], appearances),
                "gear_score_offense": _avg(item["gear_score_offense"], appearances),
                "gear_score_defense": _avg(item["gear_score_defense"], appearances),
                "gear_score_resources": _avg(item["gear_score_resources"], appearances),
                "gear_score_skills": _avg(item["gear_score_skills"], appearances),
                "gear_score_utility": _avg(item["gear_score_utility"], appearances),
                "damage_per_action": _avg(item["damage"], actions),
                "hit_rate": _pct(item["hits"], attempts),
                "crit_rate": _pct(item["crits"], attempts),
                "avg_overkill": _avg(item["overkill"], appearances),
                "dodge_per_appearance": _avg(item["dodges"], appearances),
                "parry_per_appearance": _avg(item["parries"], appearances),
                "block_per_appearance": _avg(item["blocks"], appearances),
                "armor_absorbed_per_appearance": _avg(item["armor_absorbed"], appearances),
                "armor_absorb_events_per_appearance": _avg(item["armor_absorb_events"], appearances),
                "armor_absorbed_per_event": _avg(item["armor_absorbed"], armor_events),
                "defence_per_appearance": _avg(defence + _int(item["armor_absorb_events"]), appearances),
                "dodge_defence_share": _pct(item["dodges"], defence_total) if defence else 0.0,
                "parry_defence_share": _pct(item["parries"], defence_total) if defence else 0.0,
                "block_defence_share": _pct(item["blocks"], defence_total) if defence else 0.0,
            }
        )
    return sorted(rows, key=lambda row: str(row["imprint"]))


def _telemetry_rows(telemetry: dict[str, Any]) -> list[dict[str, object]]:
    return [
        {"metric": "actions", "value": telemetry.get("action_count", 0)},
        {"metric": "failed_actions", "value": telemetry.get("failed_action_count", 0)},
        {"metric": "damage_by_actor", "value": telemetry.get("damage_by_actor", {})},
        {"metric": "damage_taken_by_actor", "value": telemetry.get("damage_taken_by_actor", {})},
        {"metric": "armor_absorbed_by_actor", "value": telemetry.get("armor_absorbed_by_actor", {})},
        {"metric": "armor_absorb_events_by_actor", "value": telemetry.get("armor_absorb_events_by_actor", {})},
        {"metric": "healing_by_actor", "value": telemetry.get("healing_by_actor", {})},
        {"metric": "resource_spent_by_actor", "value": telemetry.get("resource_spent_by_actor", {})},
        {"metric": "action_count_by_actor", "value": telemetry.get("action_count_by_actor", {})},
        {"metric": "target_count_by_actor", "value": telemetry.get("target_count_by_actor", {})},
        {"metric": "targeted_by_actor", "value": telemetry.get("targeted_by_actor", {})},
        {"metric": "damage_events_by_actor", "value": telemetry.get("damage_events_by_actor", {})},
        {"metric": "incoming_events_by_actor", "value": telemetry.get("incoming_events_by_actor", {})},
        {"metric": "overkill_by_actor", "value": telemetry.get("overkill_by_actor", {})},
        {"metric": "tactical_trigger_attempts_by_id", "value": telemetry.get("tactical_trigger_attempts_by_id", {})},
        {"metric": "tactical_trigger_success_by_id", "value": telemetry.get("tactical_trigger_success_by_id", {})},
        {"metric": "tactical_damage_by_actor", "value": telemetry.get("tactical_damage_by_actor", {})},
        {"metric": "tactical_reflected_by_actor", "value": telemetry.get("tactical_reflected_by_actor", {})},
        {"metric": "tactical_prevented_by_actor", "value": telemetry.get("tactical_prevented_by_actor", {})},
        {"metric": "tactical_chain_hits_by_actor", "value": telemetry.get("tactical_chain_hits_by_actor", {})},
        {"metric": "tactical_shield_branch_by_actor", "value": telemetry.get("tactical_shield_branch_by_actor", {})},
        {"metric": "tactical_shield_damage_by_actor", "value": telemetry.get("tactical_shield_damage_by_actor", {})},
        {
            "metric": "tactical_shield_absorbed_by_actor",
            "value": telemetry.get("tactical_shield_absorbed_by_actor", {}),
        },
        {
            "metric": "tactical_shield_reflected_by_actor",
            "value": telemetry.get("tactical_shield_reflected_by_actor", {}),
        },
        {
            "metric": "checks",
            "value": {
                "hit": telemetry.get("hit_count", 0),
                "miss": telemetry.get("miss_count", 0),
                "dodge": telemetry.get("dodge_count", 0),
                "parry": telemetry.get("parry_count", 0),
                "block": telemetry.get("block_count", 0),
                "crit": telemetry.get("crit_count", 0),
            },
        },
        {"metric": "deaths", "value": telemetry.get("deaths", [])},
        {"metric": "round_events", "value": len(telemetry.get("round_events") or [])},
        {"metric": "feints", "value": telemetry.get("feint_pick_count", {})},
        {"metric": "control_applied", "value": telemetry.get("control_applied", 0)},
        {"metric": "buff_applied", "value": telemetry.get("buff_applied", 0)},
    ]


def _training_telemetry_rows(run: CombatAiSimulationRun) -> list[dict[str, object]]:
    telemetry = run.telemetry
    metadata = run.metadata
    rows = [
        {"metric": "run_kind", "value": run.run_kind},
        {"metric": "status", "value": run.status},
        {"metric": "generations", "value": telemetry.get("generations", 0)},
        {"metric": "population", "value": telemetry.get("population", 0)},
        {"metric": "seed", "value": run.seed},
        {"metric": "sigma", "value": telemetry.get("sigma", "—")},
        {"metric": "progress_stage", "value": telemetry.get("progress_stage", "—")},
        {"metric": "current_generation", "value": telemetry.get("current_generation", "—")},
        {"metric": "current_candidate", "value": telemetry.get("current_candidate_index", "—")},
        {"metric": "current_scenario", "value": telemetry.get("current_scenario", "—")},
        {"metric": "battles_done", "value": telemetry.get("battles_done", "—")},
        {"metric": "battles_total", "value": telemetry.get("battles_total", "—")},
        {"metric": "best_reward_so_far", "value": telemetry.get("best_reward_so_far", "—")},
        {"metric": "metrics_count", "value": telemetry.get("metrics_count", len(telemetry.get("metrics") or []))},
        {"metric": "weight_deltas_count", "value": telemetry.get("weight_deltas_count", "—")},
        {"metric": "output_dir", "value": metadata.get("output_dir", "—")},
        {"metric": "best_policy_id", "value": _dict(metadata.get("best_policy")).get("policy_id", "—")},
        {"metric": "metrics_path", "value": metadata.get("metrics_path", "—")},
        {"metric": "live_policy_activation", "value": metadata.get("live_policy_activation", False)},
    ]
    return [row for row in rows if row["value"] not in {"", None}]


def _summary_items(run: CombatAiSimulationRun | None) -> list[str]:
    if run is None:
        return ["Отчёт не найден."]
    if run.status == "failed":
        error = _dict(run.metadata.get("error"))
        message = str(error.get("message") or run.report_text or "прогон не выполнен")
        return [
            f"Прогон завершился ошибкой: {message}",
            "Live-веса боя не менялись.",
        ]
    if run.run_kind == "training":
        if run.status != "completed":
            if str(run.telemetry.get("run_kind") or "") == "battle_training":
                return [
                    (
                        f"Стадия battle fine-tune: {_training_progress_label(run)}; "
                        f"stage {run.telemetry.get('progress_stage', '—')}."
                    ),
                    (
                        f"Текущий сценарий: {run.telemetry.get('current_scenario', '—')}; "
                        f"best reward so far {_round(run.telemetry.get('best_reward_so_far'))}."
                    ),
                    "Worker пишет Redis snapshot после сценариев и поколений; обнови страницу, чтобы увидеть следующий шаг.",
                ]
            return [
                (
                    f"Обучение весов запущено: {run.rounds_completed}/{_int(run.telemetry.get('generations'))} "
                    f"итераций, population {_int(run.telemetry.get('population'))}, seed {run.seed}."
                ),
                "Запрос уже отпущен; trainer работает в фоне, чтобы не подвешивать админку.",
                "Обнови страницу отчёта позже, здесь появятся reward, дельты весов и scenario rewards.",
            ]
        return [
            (
                f"Обучение весов завершено: {run.rounds_completed}/{_int(run.telemetry.get('generations'))} "
                f"итераций, population {_int(run.telemetry.get('population'))}, seed {run.seed}."
            ),
            (
                f"Best reward: {_round(run.telemetry.get('initial_best_reward'))} -> "
                f"{_round(run.telemetry.get('final_best_reward'))}; "
                f"финальный mean reward {_round(run.telemetry.get('final_mean_reward'))}."
            ),
            "Best policy сохранена как версия обучения в отчёте; live-бой её не использует до выбора ACTIVE_POLICY_ID.",
        ]
    if run.status == "running":
        snapshot = _dict(run.metadata.get("live_snapshot"))
        actors = [row for row in snapshot.get("actors") or [] if isinstance(row, dict)]
        alive = sum(1 for row in actors if not row.get("is_dead"))
        return [
            f"Live tick-бой идёт: resolved exchanges {run.rounds_completed}/{run.max_rounds}.",
            f"Живых актёров сейчас: {alive}/{len(actors)}.",
            "Страница читает сохранённый snapshot; обнови её, чтобы увидеть следующий tick.",
        ]
    damage = _dict(run.telemetry.get("damage_by_actor"))
    deaths = [str(item) for item in run.telemetry.get("deaths") or []]
    team_damage = _team_damage(run)
    top_actor, top_damage = _top_damage(damage)
    if _stopped_by_limit(run):
        items = [
            f"Победителя нет: бой остановлен по лимиту {_progress_label(run)}.",
            f"Урон по командам: blue {team_damage.get('blue', 0)} / red {team_damage.get('red', 0)}.",
        ]
    elif _is_live_run(run):
        items = [
            f"{_winner_label(run)} победил за {_progress_label(run)}.",
            f"Урон по командам: blue {team_damage.get('blue', 0)} / red {team_damage.get('red', 0)}.",
        ]
    else:
        items = [
            f"{_winner_label(run)} победил за {run.rounds_completed} раунда из лимита {run.max_rounds}.",
            f"Урон по командам: blue {team_damage.get('blue', 0)} / red {team_damage.get('red', 0)}.",
        ]
    if run.metadata.get("policy_source_run_id"):
        items.append(f"Policy-версия: training run {run.metadata.get('policy_source_run_id')}.")
    if run.metadata.get("roster_mode") == "seeded_random_draft":
        pool_size = len(run.metadata.get("imprint_pool") or [])
        items.append(
            f"Составы собраны random draft из расширенного пула ({pool_size}): "
            f"{run.metadata.get('roster_team_size')}v{run.metadata.get('roster_team_size')}, "
            f"не участвуют {len(run.metadata.get('unused_imprints') or [])}, "
            f"seed {run.metadata.get('roster_seed')}."
        )
    elif run.metadata.get("roster_mode") == "mirror_10v10":
        items.append("Составы зеркальные 10v10: в каждой команде есть все 10 стартовых слепков.")
    elif run.metadata.get("roster_mode") == "seeded_random_5v5_split":
        pool_size = len(run.metadata.get("imprint_pool") or [])
        items.append(
            f"Составы собраны случайным seed split из расширенного пула ({pool_size}): seed {run.metadata.get('roster_seed')}."
        )
    if run.metadata.get("skill_profile") == "maxed_existing_skills":
        items.append(
            "Skill baseline: у каждого слепка только уже имеющиеся навыки подняты до 100%; экипировка и статы не менялись."
        )
    if top_actor:
        items.append(f"Лучший по урону: {top_actor} ({top_damage}).")
    if deaths:
        items.append(f"Погибли: {', '.join(deaths)}.")
    items.append("Результат сохранён как отчёт тестового прогона; боевые веса для live-боя не активировались.")
    return items


def _participant_rows(run: CombatAiSimulationRun | None) -> list[dict[str, object]]:
    if run is None:
        return []
    metadata = run.metadata or {}
    participants = [row for row in metadata.get("participants") or [] if isinstance(row, dict)]
    if not participants:
        participants = [
            {"actor_id": "player_model", "label": "Player model", "team": "blue", "type": "player-model"},
            {"actor_id": "trainer_bot", "label": "Trainer bot", "team": "red", "type": "monster"},
        ]
    final_hp = _dict(metadata.get("final_hp_by_actor"))
    damage_done = _dict(run.telemetry.get("damage_by_actor"))
    damage_taken = _dict(run.telemetry.get("damage_taken_by_actor"))
    action_count = _dict(run.telemetry.get("action_count_by_actor"))
    rows: list[dict[str, object]] = []
    for participant in participants:
        actor_id = str(participant.get("actor_id") or "")
        start_hp = participant.get("start_hp", "—")
        end_hp = final_hp.get(actor_id, "—")
        actions = _int(action_count.get(actor_id))
        actor_damage = _int(damage_done.get(actor_id))
        rows.append(
            {
                "actor": participant.get("label") or actor_id,
                "team": participant.get("team") or "—",
                "kind": participant.get("type") or "—",
                "archetype": participant.get("ai_archetype") or "—",
                "imprint": participant.get("imprint_title") or participant.get("imprint_key") or "—",
                "hp": f"{start_hp} -> {end_hp}",
                "combat_stats": _combat_stats_label(_dict(participant.get("combat_stats"))),
                "gear_score": _gear_score_label(participant.get("gear_score")),
                "actions": actions,
                "damage_done": actor_damage,
                "damage_taken": damage_taken.get(actor_id, 0),
                "damage_per_action": _round(actor_damage / actions) if actions else "—",
                "targets": _targets_label(run, actor_id),
                "checks": _actor_checks_label(run, actor_id),
            }
        )
    return rows


def _round_rows(run: CombatAiSimulationRun | None) -> list[dict[str, object]]:
    if run is None:
        return []
    events = [event for event in run.telemetry.get("round_events") or [] if isinstance(event, dict)]
    rows: list[dict[str, object]] = []
    for event in events:
        deaths = [str(item) for item in event.get("deaths") or []]
        checks = []
        for key, label in (
            ("is_miss", "miss"),
            ("is_dodged", "dodge"),
            ("is_parried", "parry"),
            ("is_blocked", "block"),
            ("is_crit", "crit"),
        ):
            if event.get(key):
                checks.append(label)
        result = str(event.get("skip_reason") or ", ".join(checks))
        if deaths:
            result = f"death: {', '.join(deaths)}"
        rows.append(
            {
                "round": event.get("round") or "—",
                "source": event.get("source_id") or "—",
                "target": event.get("target_id") or "—",
                "damage": event.get("damage", 0),
                "healing": event.get("healing", 0),
                "result": result or "ok",
            }
        )
    return rows


def _finding_items(run: CombatAiSimulationRun | None) -> list[str]:
    if run is None:
        return ["Нет данных."]
    if run.status == "failed":
        if run.metadata.get("policy_source") == "training_run" and not run.metadata.get("policy_found"):
            return ["Версия обученной policy не найдена. Сначала запусти обучение весов, затем повтори этот тест."]
        return ["Прогон не выполнен; смотри технический лог."]
    if run.status == "running":
        return [
            "Это live-like memory loop: AI ставит одну заявку за tick, цель списывается из target queue.",
            "Exchange считается только когда есть встречная пара или явный timeout.",
            "После каждого exchange состояние и target returns коммитятся перед следующим AI-решением.",
        ]
    if run.run_kind == "training":
        if run.status != "completed":
            return [
                "Идёт фоновое обучение. Пока рано оценивать reward и дельты.",
                "Live-веса боя не меняются во время этого job.",
            ]
        deltas = [row for row in run.telemetry.get("top_weight_deltas") or [] if isinstance(row, dict)]
        items = [
            "Это обучение обновляет только candidate policy внутри отчёта; активные веса боя не менялись.",
        ]
        if deltas:
            top = deltas[0]
            items.append(
                f"Самый сильный сдвиг: {top.get('weight')} "
                f"{_round(top.get('before'))} -> {_round(top.get('after'))} ({_signed(top.get('delta'))})."
            )
        items.append("Перед применением нужны повторные seeds и сравнение по сценариям без регрессий.")
        return items
    telemetry = run.telemetry
    damage = _dict(telemetry.get("damage_by_actor"))
    top_actor, top_damage = _top_damage(damage)
    items = [
        "Этот прогон идёт в памяти через реальный CombatExecutor; live-веса боя не менялись.",
    ]
    if _stopped_by_limit(run):
        items.append("Победы не было: результат остановлен safety-лимитом, поэтому это не балансный итог боя.")
    if run.metadata.get("simulation_actor_source") == "character_starting_imprints":
        items.append(
            "Актёры собраны из реальных стартовых пресетов: attributes, skills, generated runtime items и feint arsenal."
        )
    if top_actor:
        items.append(f"Сильнейший по урону в этом прогоне: {top_actor} ({top_damage}).")
    burst_item = _team_damage_share_item(run)
    if burst_item:
        items.append(burst_item)
    if (
        int(telemetry.get("miss_count") or 0)
        or int(telemetry.get("dodge_count") or 0)
        or int(telemetry.get("parry_count") or 0)
        or int(telemetry.get("block_count") or 0)
    ):
        items.append(
            "В отчёте есть защитные проверки: "
            f"miss {telemetry.get('miss_count', 0)}, dodge {telemetry.get('dodge_count', 0)}, "
            f"parry {telemetry.get('parry_count', 0)}, block {telemetry.get('block_count', 0)}."
        )
    if not telemetry.get("feint_pick_count"):
        items.append("Феинты не использовались: этот прогон нельзя считать проверкой anti-parry/anti-block решений.")
    if not telemetry.get("healing_by_actor"):
        items.append("Лечение не использовалось: bulwark/heal поведение этим сценарием не проверяется.")
    if not telemetry.get("resource_spent_by_actor"):
        items.append("Ресурсы не тратились: stamina discipline этим сценарием не проверяется.")
    if int(telemetry.get("control_applied") or 0) == 0 and int(telemetry.get("buff_applied") or 0) == 0:
        items.append("Control/buffs не применялись: нужен отдельный 2v2/5v5 сценарий для командной логики.")
    return items


def _targets_label(run: CombatAiSimulationRun, actor_id: str) -> str:
    target_counts = _dict(run.telemetry.get("target_count_by_actor"))
    actor_targets = _dict(target_counts.get(actor_id))
    if not actor_targets:
        return "—"
    labels = _actor_labels(run)
    ordered = sorted(actor_targets.items(), key=lambda item: (-_int(item[1]), str(item[0])))
    return ", ".join(f"{labels.get(str(target), str(target))}: {_int(count)}" for target, count in ordered[:4])


def _actor_checks_label(run: CombatAiSimulationRun, actor_id: str) -> str:
    telemetry = run.telemetry
    parts: list[str] = []
    for metric, label in (
        ("hit_by_actor", "hit"),
        ("miss_by_actor", "miss"),
        ("crit_by_actor", "crit"),
        ("failed_by_actor", "fail"),
        ("dodge_by_actor", "dodge"),
        ("parry_by_actor", "parry"),
        ("block_by_actor", "block"),
    ):
        value = _int(_dict(telemetry.get(metric)).get(actor_id))
        if value:
            parts.append(f"{label} {value}")
    overkill = _int(_dict(telemetry.get("overkill_by_actor")).get(actor_id))
    if overkill:
        parts.append(f"overkill {overkill}")
    return ", ".join(parts) if parts else "—"


def _team_damage_share_item(run: CombatAiSimulationRun) -> str | None:
    damage = _dict(run.telemetry.get("damage_by_actor"))
    if not damage:
        return None
    participants = [row for row in (run.metadata.get("participants") or []) if isinstance(row, dict)]
    team_by_actor = {str(row.get("actor_id") or ""): str(row.get("team") or "") for row in participants}
    team_damage: dict[str, int] = {}
    for actor_id, raw_damage in damage.items():
        team = team_by_actor.get(str(actor_id))
        if not team:
            continue
        team_damage[team] = team_damage.get(team, 0) + _int(raw_damage)
    actor_id, actor_damage = _top_damage(damage)
    team = team_by_actor.get(actor_id)
    total = team_damage.get(str(team), 0)
    if not actor_id or total <= 0:
        return None
    share = actor_damage / total
    if share < 0.45:
        return None
    label = _actor_labels(run).get(actor_id, actor_id)
    return f"{label} сделал {_round(share * 100)}% урона своей команды; это явный перекос роли/статов в этом составе."


def _scenario_label(scenario_key: str) -> str:
    labels = {
        "mvp_1v1_player_model_vs_trainer_bot": "MVP 1v1: trainer bot vs player model",
        "starter_presets_5v5": "Стартовые пресеты 5v5",
        "starter_presets_5v5_live": "Live tick: стартовые пресеты 5v5",
        "starter_presets_random_draft": "Random draft 2v2-4v4",
        "starter_presets_random_draft_live": "Live tick: random draft 2v2-4v4",
        "starter_presets_mirror_10v10": "Зеркало 10v10",
        "starter_presets_mirror_10v10_live": "Live tick: зеркало 10v10",
        "starter_presets_5v5_live_full_skills": "Live tick: стартовые пресеты 5v5, full skills",
        "starter_presets_mirror_10v10_live_full_skills": "Live tick: зеркало 10v10, full skills",
        "starter_presets_5v5_latest_training_file": "Стартовые пресеты 5v5 + версия обучения",
        "starter_presets_5v5_live_latest_training_file": "Live tick: стартовые пресеты 5v5 + версия обучения",
        "starter_presets_mirror_10v10_live_latest_training_file": "Live tick: зеркало 10v10 + версия обучения",
        "battle_policy_finetune": "Стадия 2: обучение в боях",
        "synthetic_policy_training": "Synthetic training",
    }
    return labels.get(scenario_key, scenario_key or "—")


def _winner_label(run: CombatAiSimulationRun) -> str:
    if _stopped_by_limit(run):
        return "нет победителя"
    labels = _dict(run.metadata.get("team_labels"))
    if run.winner in labels:
        return f"{labels[run.winner]} ({run.winner})"
    labels = {"red": "trainer_bot (red)", "blue": "player_model (blue)", "draw": "draw"}
    return labels.get(run.winner, run.winner or "—")


def _result_label(run: CombatAiSimulationRun) -> str:
    if _stopped_by_limit(run):
        return "лимит"
    return _winner_label(run)


def _progress_label(run: CombatAiSimulationRun) -> str:
    if run.run_kind == "training":
        return _training_progress_label(run)
    unit = "exchanges" if _is_live_run(run) else "rounds"
    return f"{unit} {run.rounds_completed}/{run.max_rounds}"


def _training_progress_label(run: CombatAiSimulationRun) -> str:
    telemetry = run.telemetry
    if str(telemetry.get("run_kind") or "") == "battle_training":
        battles_done = telemetry.get("battles_done")
        battles_total = telemetry.get("battles_total")
        if battles_done is not None and battles_total:
            return f"battles {battles_done}/{battles_total}"
    return f"iterations {run.rounds_completed}/{_int(telemetry.get('generations'))}"


def _is_live_run(run: CombatAiSimulationRun) -> bool:
    return run.run_kind == "simulation_live" or run.metadata.get("simulation_mode") == "live_tick"


def _stopped_by_limit(run: CombatAiSimulationRun) -> bool:
    return str(run.metadata.get("completion_reason") or "") in {"max_exchanges_reached", "max_ticks_reached"}


def _damage_summary(telemetry: dict[str, Any]) -> str:
    damage = _dict(telemetry.get("damage_by_actor"))
    if not damage:
        return "—"
    return " / ".join(f"{actor}: {value}" for actor, value in sorted(damage.items()))


def _detail_href(run: CombatAiSimulationRun) -> str:
    page = "training-detail" if run.run_kind == "training" else "run-detail"
    return f"{_BASE}/{page}?id={run.id}"


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _actor_labels(run: CombatAiSimulationRun) -> dict[str, str]:
    participants = [row for row in (run.metadata.get("participants") or []) if isinstance(row, dict)]
    labels: dict[str, str] = {}
    for row in participants:
        actor_id = str(row.get("actor_id") or "")
        if actor_id:
            labels[actor_id] = str(row.get("label") or actor_id)
    return labels


def _team_damage(run: CombatAiSimulationRun) -> dict[str, int]:
    participants = [row for row in (run.metadata.get("participants") or []) if isinstance(row, dict)]
    team_by_actor = {str(row.get("actor_id") or ""): str(row.get("team") or "") for row in participants}
    totals: dict[str, int] = {}
    for actor_id, damage in _dict(run.telemetry.get("damage_by_actor")).items():
        team = team_by_actor.get(str(actor_id))
        if not team:
            continue
        totals[team] = totals.get(team, 0) + _int(damage)
    return totals


def _top_damage(damage_by_actor: dict[str, Any]) -> tuple[str, int]:
    if not damage_by_actor:
        return "", 0
    actor_id, damage = max(damage_by_actor.items(), key=lambda item: _int(item[1]))
    return str(actor_id), _int(damage)


def _combat_stats_label(stats: dict[str, Any]) -> str:
    if not stats:
        return "—"
    return (
        f"dmg {_round(stats.get('damage'))}, armor {_round(stats.get('armor'))}, "
        f"eva {_round(stats.get('evasion'))}, par {_round(stats.get('parry'))}, "
        f"blk {_round(stats.get('block'))}, acc {_round(stats.get('accuracy_mod'))}"
    )


def _gear_score_breakdown(value: Any) -> dict[str, float]:
    data = _dict(value)
    return {
        "total": _float(data.get("total")),
        "offense": _float(data.get("offense")),
        "defense": _float(data.get("defense")),
        "resources": _float(data.get("resources")),
        "skills": _float(data.get("skills")),
        "utility": _float(data.get("utility")),
    }


def _gear_score_label(value: Any) -> str:
    gear_score = _gear_score_breakdown(value)
    total = _round(gear_score["total"])
    if total == "0.0":
        return "—"
    return (
        f"{total} "
        f"(off {_round(gear_score['offense'])}, def {_round(gear_score['defense'])}, "
        f"res {_round(gear_score['resources'])}, skill {_round(gear_score['skills'])}, "
        f"util {_round(gear_score['utility'])})"
    )


def _sample_metrics(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(metrics) <= 100:
        return metrics
    indexes = {0, len(metrics) - 1}
    step = max(1, len(metrics) // 98)
    indexes.update(range(0, len(metrics), step))
    return [metrics[index] for index in sorted(indexes)[:100]]


def _round(value: Any) -> str:
    try:
        return str(round(float(value), 3))
    except (TypeError, ValueError):
        return "—"


def _avg(total: Any, count: Any) -> float:
    denominator = _float(count)
    if denominator <= 0:
        return 0.0
    return round(_float(total) / denominator, 3)


def _pct(part: Any, total: Any) -> float:
    denominator = _float(total)
    if denominator <= 0:
        return 0.0
    return round(_float(part) / denominator * 100, 1)


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _signed(value: Any) -> str:
    try:
        return f"{float(value):+.3f}"
    except (TypeError, ValueError):
        return "—"


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _seed_from_form(form: Any) -> int:
    return min(max(_int(form.get("seed")), 0), 1_000_000)


def _auto_seed() -> int:
    return int(datetime.now(UTC).timestamp() * 1000) % 1_000_000


def _short_ts(value: str) -> str:
    if not value:
        return "—"
    return value.replace("T", " ")[:19]


cabinet_site.register(CombatAiTestingAdmin)
