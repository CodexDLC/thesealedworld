from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar, cast

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
_LIVE_BATCH_ANALYSIS_COUNT = 50
_LIVE_BATCH_ANALYSIS_MAX = 50
_EHP_REFERENCE_HIT_DAMAGE = 20.0
_EHP_REGEN_WINDOW_EXCHANGES = 5.0
_SHIELD_TACTICAL_PART_ID = "style_shield_reflect"
_SHIELD_TACTICAL_PART_ALIASES = {"weapon_shield_bash_on_block"}
_RANGED_POSITIONS = ("far", "mid", "close")
_LIVE_LAUNCH_SCENARIOS = {
    "starter_presets_5v5_live",
    "starter_presets_5v5_live_full_skills",
    "starter_presets_5v5_live_latest_training_file",
    "starter_presets_random_draft_live",
}
_STARTER_IMPRINT_OPTIONS = [
    {"value": "starter_guard_01", "label": "Слепок мечника со щитом [МЕ/ЩТ/СБ]"},
    {"value": "starter_breaker_01", "label": "Слепок двуручного молота [БУ/ДВ/ТБ]"},
    {"value": "starter_dual_blades_01", "label": "Слепок двух стилетов [ФЕ/ДУ/ЛБ]"},
    {"value": "starter_dual_sword_01", "label": "Слепок меча и стилета [МЕ/ФЕ/ДУ/СБ]"},
    {"value": "starter_dual_mace_01", "label": "Слепок булавы и даги [БУ/ФЕ/ДУ/ТБ]"},
    {"value": "starter_hunter_01", "label": "Слепок охотника [ЛК/ДБ/ЛБ]"},
    {"value": "starter_archer_01", "label": "Слепок лучника [ЛК/ДБ/ЛБ]"},
    {"value": "starter_heavy_guard_01", "label": "Слепок булавы и щита [БУ/ЩТ/ТБ]"},
    {"value": "starter_tactician_01", "label": "Слепок мечника с баклером [МЕ/ЩТ/СБ]"},
    {"value": "starter_rift_survivor_01", "label": "Слепок алебардиста [ДК/ДВ/СБ]"},
]

_TACTICAL_PART_LABELS = {
    "style_2h_ignore": "Двуручный стиль: давление",
    "style_shield_reflect": "Щит: поглощение и возврат",
    "style_ranged_perfect_backstep": "Дальний бой: идеальный отскок",
    "style_dual_cross_cut": "Две руки: перекрестный крит",
    "weapon_shield_bash_on_block": "Щит: ответный удар",
    "weapon_riposte_on_parry": "Рипост после парирования",
    "counter_attack": "Контратака",
    "offhand_attack": "Off-hand удар",
}
_TACTICAL_SKILL_CHARTS = {
    "skill_two_handed": ("two_handed", "Двуручный стиль", ("style_2h_ignore",)),
    "skill_dual_wield": ("dual_wield", "Две руки", ("offhand_attack", "style_dual_cross_cut")),
    "skill_shield_mastery": ("shield", "Щит", ("style_shield_reflect",)),
    "skill_ranged_combat": ("ranged", "Дальний бой", ("style_ranged_perfect_backstep",)),
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
                "id": f"live_batch:starter_presets_5v5_live:{_LIVE_BATCH_ANALYSIS_COUNT}",
                "scenario": "Live tick: стартовые пресеты 5v5",
                "runs": _LIVE_BATCH_ANALYSIS_COUNT,
                "mode": "фон, пакет live-like",
                "policy": "runtime_default",
                "note": f"запускает {_LIVE_BATCH_ANALYSIS_COUNT} отдельных live-like боёв; состав фиксируется при заказе задачи",
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
                "id": f"live_batch:starter_presets_5v5_live_full_skills:{_LIVE_BATCH_ANALYSIS_COUNT}",
                "scenario": "Live tick: стартовые пресеты 5v5, full skills",
                "runs": _LIVE_BATCH_ANALYSIS_COUNT,
                "mode": "фон, пакет maxed skills",
                "policy": "runtime_default",
                "note": f"{_LIVE_BATCH_ANALYSIS_COUNT} отдельных 5v5 боёв; состав фиксируется при заказе, навыки слепков на 100%",
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
                "id": f"live_batch:starter_presets_5v5_live:{_LIVE_BATCH_ANALYSIS_COUNT}",
                "scenario": "Live tick: стартовые пресеты 5v5 + policy",
                "runs": _LIVE_BATCH_ANALYSIS_COUNT,
                "mode": "фон, пакет live-like",
                "note": f"{_LIVE_BATCH_ANALYSIS_COUNT} отдельных 5v5 боёв с выбранной policy; состав фиксируется при заказе",
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
                "id": f"live_batch:starter_presets_5v5_live_full_skills:{_LIVE_BATCH_ANALYSIS_COUNT}",
                "scenario": "Live tick: стартовые пресеты 5v5 full skills + policy",
                "runs": _LIVE_BATCH_ANALYSIS_COUNT,
                "mode": "фон, пакет maxed skills",
                "note": f"{_LIVE_BATCH_ANALYSIS_COUNT} отдельных 5v5 боёв через выбранную policy; состав фиксируется при заказе",
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


async def _family_pressure_launcher_provider(request: Request) -> TableWidgetMap:
    imprint_options = _starter_imprint_options(selected="starter_breaker_01")
    return TableWidgetMap(
        key="combat_ai_family_pressure_launcher",
        title="Диагностика семей против стартового слепка",
        columns=[
            TableColumnMap(key="scenario", label="Сценарий"),
            TableColumnMap(key="family", label="Семья"),
            TableColumnMap(key="runs", label="Бои"),
            TableColumnMap(key="mode", label="Режим"),
            TableColumnMap(key="note", label="Что сохраняем"),
        ],
        rows=[
            {
                "id": "family_pressure:rat_swarm",
                "scenario": "Стартовый слепок vs лестница семьи",
                "family": "rat_swarm",
                "runs": "5 на состав",
                "mode": "последовательно, 1..6 + veteran/elite mixes",
                "note": "выбери слепок; свежие HP/EN/stamina на каждый бой; отчёт по winrate и effective GS",
                "seed": 3,
                "imprint_options": imprint_options,
            },
            {
                "id": "family_pressure:goblin_tribe",
                "scenario": "Стартовый слепок vs лестница семьи",
                "family": "goblin_tribe",
                "runs": "5 на состав",
                "mode": "последовательно, horde ladder",
                "note": "выбери слепок; проверяет, где гоблинская пачка начинает статистически ломать билд",
                "seed": 7,
                "imprint_options": imprint_options,
            },
            {
                "id": "family_pressure:wolf_pack",
                "scenario": "Стартовый слепок vs лестница семьи",
                "family": "wolf_pack",
                "runs": "5 на состав",
                "mode": "последовательно, pack ladder",
                "note": "выбери слепок; проверяет pack-семью и сдвиг на одного монстра относительно swarm",
                "seed": 11,
                "imprint_options": imprint_options,
            },
            {
                "id": "family_pressure:bandit_gang",
                "scenario": "Стартовый слепок vs лестница семьи",
                "family": "bandit_gang",
                "runs": "5 на состав",
                "mode": "последовательно, gang ladder",
                "note": "выбери слепок; проверяет humanoid gang 1-3 и другую плотность action economy",
                "seed": 13,
                "imprint_options": imprint_options,
            },
        ],
        action_url=f"{_BASE}/run",
        id_key="id",
        actions=[
            TableActionMap(
                action="family_pressure",
                label="Запустить",
                input_name="seed",
                input_value_key="seed",
                input_label="Seed",
                input_min=0,
                input_max=1_000_000,
                select_name="imprint_key",
                select_options_key="imprint_options",
                select_label="Слепок",
            ),
            TableActionMap(
                action="family_pressure_all_imprints",
                label="Все слепки",
                css_class="fc-action-btn--secondary",
                input_name="seed",
                input_value_key="seed",
                input_label="Seed",
                input_min=0,
                input_max=1_000_000,
            ),
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
                "data": [
                    row.get("ordinary_dodge_per_appearance", row.get("dodge_per_appearance", 0.0)) for row in rows
                ],
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
                "label": "Ranged",
                "data": [row.get("ranged_defense_per_appearance", 0.0) for row in rows],
                "backgroundColor": "rgba(99,102,241,0.72)",
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
            TableColumnMap(key="damage_per_event", label="Урон/сраб."),
            TableColumnMap(key="shield_damage", label="Щит-урон"),
            TableColumnMap(key="shield_absorbed", label="Щит-погл."),
            TableColumnMap(key="shield_reflected", label="Щит-возвр."),
            TableColumnMap(key="reflected", label="Возврат"),
            TableColumnMap(key="prevented", label="Предотвр."),
            TableColumnMap(key="defense_per_event", label="Защ./сраб."),
        ],
        rows=await _analytics_tactical_rows_for_request(request),
    )


async def _analytics_tactical_two_handed_table_provider(request: Request) -> TableWidgetMap:
    return await _analytics_tactical_skill_table(request, "skill_two_handed")


async def _analytics_tactical_dual_wield_table_provider(request: Request) -> TableWidgetMap:
    return await _analytics_tactical_skill_table(request, "skill_dual_wield")


async def _analytics_tactical_shield_table_provider(request: Request) -> TableWidgetMap:
    return await _analytics_tactical_skill_table(request, "skill_shield_mastery")


async def _analytics_tactical_ranged_table_provider(request: Request) -> TableWidgetMap:
    runs = await _analytics_runs(request)
    return TableWidgetMap(
        key="combat_ai_analytics_tactical_ranged",
        title="Тактика: дальний бой",
        columns=[
            TableColumnMap(key="position", label="Позиция"),
            TableColumnMap(key="shots", label="Выстрелы"),
            TableColumnMap(key="bow_damage", label="Урон стрелой"),
            TableColumnMap(key="bow_damage_per_shot", label="Урон/выстр."),
            TableColumnMap(key="incoming_melee", label="Melee входы"),
            TableColumnMap(key="ranged_dodge_attempts", label="Лучн. уворот: попытки"),
            TableColumnMap(key="ranged_dodge_success", label="Лучн. уворот: успех"),
            TableColumnMap(key="ranged_dodge_rate", label="Лучн. уворот %"),
            TableColumnMap(key="melee_taken", label="Получено melee"),
            TableColumnMap(key="melee_taken_per_entry", label="Melee урон/вход"),
        ],
        rows=_ranged_position_rows(runs),
    )


async def _analytics_table_provider(request: Request) -> TableWidgetMap:
    rows = _expanded_analytics_table_rows(await _analytics_imprint_rows(request))
    return TableWidgetMap(
        key="combat_ai_analytics_table",
        title="Сводка по слепкам",
        columns=[
            TableColumnMap(key="imprint", label="Слепок"),
            TableColumnMap(key="behavior", label="Роль"),
            TableColumnMap(key="appearances", label="Появл."),
            TableColumnMap(key="win_rate", label="Win %"),
            TableColumnMap(key="survival_rate", label="Выжил %"),
            TableColumnMap(key="gear_score", label="GS"),
            TableColumnMap(key="effective_hp", label="EHP"),
            TableColumnMap(key="avg_damage", label="Ср. урон"),
            TableColumnMap(key="avg_taken", label="Ср. получено"),
            TableColumnMap(key="armor_absorbed_per_event", label="Броня/сраб."),
            TableColumnMap(key="damage_per_action", label="Урон/ход"),
            TableColumnMap(key="attack_checks_per_action", label="Атак/ход"),
            TableColumnMap(key="damage_per_hit", label="Урон/Hit"),
            TableColumnMap(key="hit_rate", label="Hit/Miss %"),
            TableColumnMap(key="crit_rate", label="Crit/Hit %"),
            TableColumnMap(key="avg_overkill", label="Overkill"),
        ],
        rows=rows,
    )


async def _pve_survival_summary_provider(request: Request) -> MetricWidgetMap:
    summaries = await _pve_summary_rows(request)
    completed = [row for row in summaries if row["status"] == "completed"]
    composition_count = sum(_int(row.get("composition_count")) for row in completed)
    return MetricWidgetMap(
        key="combat_ai_pve_survival_summary",
        title="Пары PvE",
        value=str(len(completed)),
        subtitle=f"завершённых пар семья+слепок; составов: {composition_count}",
    )


async def _pve_survival_chart_provider(request: Request) -> ChartWidgetMap:
    rows = _ranked_rows(await _pve_summary_rows(request), key="minions_held_value")[:24]
    labels = [str(row["label"]) for row in rows]
    return ChartWidgetMap(
        key="combat_ai_pve_survival_chart",
        title="Миньон-cap по слепкам",
        chart_type="bar",
        labels=labels,
        datasets=[
            {
                "label": "Чистых миньонов держит",
                "data": [_int(row.get("minions_held_value")) for row in rows],
                "backgroundColor": "rgba(14,165,233,0.78)",
            },
        ],
        options=_ranking_chart_options(),
        height=_ranking_chart_height(rows),
        span=2,
    )


async def _pve_pressure_chart_provider(request: Request) -> ChartWidgetMap:
    rows = sorted(await _pve_summary_rows(request), key=lambda row: str(row.get("label")))[:24]
    labels = [str(row["label"]) for row in rows]
    return ChartWidgetMap(
        key="combat_ai_pve_pressure_chart",
        title="GS ratio удержания и перелома",
        chart_type="bar",
        labels=labels,
        datasets=[
            {
                "label": "Макс. удержанный ratio",
                "data": [_float(row.get("held_ratio_value")) for row in rows],
                "backgroundColor": "rgba(34,197,94,0.72)",
            },
            {
                "label": "Первый перелом ratio",
                "data": [_float(row.get("break_ratio_value")) for row in rows],
                "backgroundColor": "rgba(245,158,11,0.78)",
            },
        ],
        options=_ranking_chart_options(),
        height=_ranking_chart_height(rows),
        span=2,
    )


async def _pve_pressure_table_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="combat_ai_pve_pressure_table",
        title="Сравнение слепков против PvE",
        columns=[
            TableColumnMap(key="created_at", label="Создан"),
            TableColumnMap(key="source", label="Источник"),
            TableColumnMap(key="family", label="Семья"),
            TableColumnMap(key="imprint", label="Слепок"),
            TableColumnMap(key="composition_count", label="Составов"),
            TableColumnMap(key="trials_total", label="Бои"),
            TableColumnMap(key="minions_held", label="Миньонов держит"),
            TableColumnMap(key="minion_breakpoint", label="Миньон-перелом"),
            TableColumnMap(key="first_danger", label="Первый опасный"),
            TableColumnMap(key="held_pressure", label="Макс. удержано"),
            TableColumnMap(key="held_ratio", label="Held ratio"),
            TableColumnMap(key="break_ratio", label="Break ratio"),
            TableColumnMap(key="avg_hp_break", label="HP на переломе"),
        ],
        rows=await _pve_summary_rows(request),
        row_href_key="href",
    )


async def _pve_composition_table_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="combat_ai_pve_composition_table",
        title="Все PvE составы последнего прогона",
        columns=[
            TableColumnMap(key="created_at", label="Создан"),
            TableColumnMap(key="source", label="Источник"),
            TableColumnMap(key="family", label="Семья"),
            TableColumnMap(key="imprint", label="Слепок"),
            TableColumnMap(key="grade", label="Класс"),
            TableColumnMap(key="composition_type", label="Тип"),
            TableColumnMap(key="composition", label="Состав"),
            TableColumnMap(key="trials", label="Бои"),
            TableColumnMap(key="result", label="W/L/D"),
            TableColumnMap(key="winrate_pct", label="Win %"),
            TableColumnMap(key="avg_hp", label="Avg HP"),
            TableColumnMap(key="ratio", label="Ratio"),
            TableColumnMap(key="effective_gs", label="Eff GS"),
            TableColumnMap(key="variants", label="Монстры"),
        ],
        rows=await _pve_pressure_rows(request),
        row_href_key="href",
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
    if run and _is_family_pressure_run(run):
        return TableWidgetMap(
            key="combat_ai_detail_participants",
            title="Параметры family pressure",
            columns=[
                TableColumnMap(key="metric", label="Параметр"),
                TableColumnMap(key="value", label="Значение"),
            ],
            rows=_family_pressure_parameter_rows(run),
        )
    rows = _participant_rows(run)
    return TableWidgetMap(
        key="combat_ai_detail_participants",
        title="Участники",
        columns=[
            TableColumnMap(key="actor", label="Актор"),
            TableColumnMap(key="team", label="Команда"),
            TableColumnMap(key="kind", label="Тип"),
            TableColumnMap(key="archetype", label="Характер"),
            TableColumnMap(key="behavior", label="Роль"),
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
    if run and _is_family_pressure_run(run):
        return TableWidgetMap(
            key="combat_ai_detail_rounds",
            title="Серии боёв",
            columns=[
                TableColumnMap(key="composition", label="Состав"),
                TableColumnMap(key="trials", label="Бои"),
                TableColumnMap(key="result", label="W/L/D"),
                TableColumnMap(key="winrate", label="Winrate"),
                TableColumnMap(key="avg_hp", label="Avg HP"),
                TableColumnMap(key="avg_rounds", label="Раунды/бой"),
                TableColumnMap(key="variants", label="Монстры"),
            ],
            rows=_family_pressure_display_rows(run),
        )
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


async def _detail_family_pressure_chart_provider(request: Request) -> ChartWidgetMap:
    run = await _safe_get_run(request)
    rows = _family_pressure_rows(run) if run and _is_family_pressure_run(run) else []
    player_hp = _float((run.metadata or {}).get("player_start_hp")) if run else 0.0
    max_ratio = max((_float(row.get("ratio")) for row in rows), default=0.0)
    labels = [str(row.get("composition") or "—") for row in rows]
    return ChartWidgetMap(
        key="combat_ai_detail_family_pressure_chart",
        title="Кривая выживаемости PvE",
        chart_type="bar",
        labels=labels,
        datasets=[
            {
                "label": "Win %",
                "data": [_float(row.get("winrate_pct")) for row in rows],
                "backgroundColor": "rgba(34,197,94,0.72)",
                "xAxisID": "x",
            },
            {
                "label": "HP % после боя",
                "data": [
                    round((_float(row.get("avg_hp")) / player_hp) * 100, 2) if player_hp > 0 else 0.0 for row in rows
                ],
                "backgroundColor": "rgba(14,165,233,0.72)",
                "xAxisID": "x",
            },
            {
                "label": "Ratio, норм. к максимуму",
                "data": [
                    round((_float(row.get("ratio")) / max_ratio) * 100, 2) if max_ratio > 0 else 0.0 for row in rows
                ],
                "backgroundColor": "rgba(245,158,11,0.72)",
                "xAxisID": "x",
            },
        ],
        options=_family_pressure_detail_chart_options(),
        height=max(360, min(920, 120 + len(rows) * 34)),
        span=2,
    )


async def _detail_tactical_parts_provider(request: Request) -> TableWidgetMap:
    run = await _safe_get_run(request)
    if run and _is_family_pressure_run(run):
        return TableWidgetMap(
            key="combat_ai_detail_tactical_parts",
            title="Тактические части",
            columns=[
                TableColumnMap(key="metric", label="Метрика"),
                TableColumnMap(key="value", label="Значение"),
            ],
            rows=[
                {
                    "metric": "Статус",
                    "value": "Для family-pressure сохраняется survivability aggregate; per-exchange tactics не пишутся.",
                }
            ],
        )
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
            TableColumnMap(key="damage_per_event", label="Урон/сраб."),
            TableColumnMap(key="shield_damage", label="Щит-урон"),
            TableColumnMap(key="shield_absorbed", label="Щит-погл."),
            TableColumnMap(key="shield_reflected", label="Щит-возвр."),
            TableColumnMap(key="reflected", label="Возврат"),
            TableColumnMap(key="prevented", label="Предотвр."),
            TableColumnMap(key="defense_per_event", label="Защ./сраб."),
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
    if run and _is_family_pressure_run(run):
        return ListWidgetMap(
            key="combat_ai_detail_report",
            title="Технический лог",
            items=["Family pressure показан графиком и ladder-таблицей выше; сырой markdown-лог скрыт."],
        )
    lines = [line for line in (run.report_text if run else "").splitlines() if line.strip()]
    return ListWidgetMap(
        key="combat_ai_detail_report",
        title="Отчёт",
        items=lines or ["Отчёт не найден."],
    )


async def _detail_family_pressure_provider(request: Request) -> TableWidgetMap:
    run = await _safe_get_run(request)
    rows = _family_pressure_display_rows(run)
    return TableWidgetMap(
        key="combat_ai_detail_family_pressure",
        title="Family pressure ladder",
        columns=[
            TableColumnMap(key="composition", label="Состав"),
            TableColumnMap(key="raw_gs", label="Raw GS"),
            TableColumnMap(key="effective_gs", label="Eff GS"),
            TableColumnMap(key="ratio", label="Ratio"),
            TableColumnMap(key="winrate", label="Winrate"),
            TableColumnMap(key="result", label="W/L/D"),
            TableColumnMap(key="avg_hp", label="Avg HP"),
            TableColumnMap(key="avg_rounds", label="Rounds"),
            TableColumnMap(key="trials", label="Бои"),
            TableColumnMap(key="roles", label="Роли"),
            TableColumnMap(key="monster_gs", label="Monster GS"),
            TableColumnMap(key="variants", label="Монстры"),
        ],
        rows=rows,
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
        SidebarItem(key="pve-arena", label="PvE выживаемость", path=f"{_BASE}/pve-arena", order=35),
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
                key="combat_ai_analytics_tactical_two_handed",
                title="Тактика: двуручный стиль",
                provider="combat_ai.analytics.tactical_two_handed",
                order=55,
            ),
            TableWidget(
                key="combat_ai_analytics_tactical_dual_wield",
                title="Тактика: две руки",
                provider="combat_ai.analytics.tactical_dual_wield",
                order=56,
            ),
            TableWidget(
                key="combat_ai_analytics_tactical_shield",
                title="Тактика: щит",
                provider="combat_ai.analytics.tactical_shield",
                order=57,
            ),
            TableWidget(
                key="combat_ai_analytics_tactical_ranged",
                title="Тактика: дальний бой",
                provider="combat_ai.analytics.tactical_ranged",
                order=58,
            ),
            TableWidget(
                key="combat_ai_analytics_table",
                title="Сводка по слепкам",
                provider="combat_ai.analytics.table",
                order=60,
            ),
        ),
        "pve-arena": (
            TableWidget(
                key="combat_ai_family_pressure_launcher",
                title="Запуск PvE pressure",
                provider="combat_ai.family_pressure_launcher",
                order=10,
            ),
            MetricWidget(
                key="combat_ai_pve_survival_summary",
                title="Выборка PvE",
                provider="combat_ai.pve.survival_summary",
                order=20,
            ),
            ChartWidget(
                key="combat_ai_pve_survival_chart",
                title="Миньон-cap по слепкам",
                provider="combat_ai.pve.survival_chart",
                chart_type="bar",
                order=30,
            ),
            ChartWidget(
                key="combat_ai_pve_pressure_chart",
                title="GS ratio удержания и перелома",
                provider="combat_ai.pve.pressure_chart",
                chart_type="bar",
                order=35,
            ),
            TableWidget(
                key="combat_ai_pve_pressure_table",
                title="Сравнение слепков против PvE",
                provider="combat_ai.pve.pressure_table",
                order=40,
            ),
            TableWidget(
                key="combat_ai_pve_composition_table",
                title="Все PvE составы последнего прогона",
                provider="combat_ai.pve.composition_table",
                order=45,
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
            ChartWidget(
                key="combat_ai_detail_family_pressure_chart",
                title="Кривая выживаемости PvE",
                provider="combat_ai.detail.family_pressure_chart",
                chart_type="bar",
                order=43,
            ),
            TableWidget(
                key="combat_ai_detail_tactical_parts",
                title="Тактические части",
                provider="combat_ai.detail.tactical_parts",
                order=45,
            ),
            TableWidget(
                key="combat_ai_detail_family_pressure",
                title="Family pressure ladder",
                provider="combat_ai.detail.family_pressure",
                order=47,
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
        "combat_ai.family_pressure_launcher": _family_pressure_launcher_provider,
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
        "combat_ai.analytics.tactical_two_handed": _analytics_tactical_two_handed_table_provider,
        "combat_ai.analytics.tactical_dual_wield": _analytics_tactical_dual_wield_table_provider,
        "combat_ai.analytics.tactical_shield": _analytics_tactical_shield_table_provider,
        "combat_ai.analytics.tactical_ranged": _analytics_tactical_ranged_table_provider,
        "combat_ai.analytics.table": _analytics_table_provider,
        "combat_ai.pve.survival_summary": _pve_survival_summary_provider,
        "combat_ai.pve.survival_chart": _pve_survival_chart_provider,
        "combat_ai.pve.pressure_chart": _pve_pressure_chart_provider,
        "combat_ai.pve.pressure_table": _pve_pressure_table_provider,
        "combat_ai.pve.composition_table": _pve_composition_table_provider,
        "combat_ai.detail.status": _detail_status_provider,
        "combat_ai.detail.result": _detail_result_provider,
        "combat_ai.detail.summary": _detail_summary_provider,
        "combat_ai.detail.participants": _detail_participants_provider,
        "combat_ai.detail.rounds": _detail_rounds_provider,
        "combat_ai.detail.family_pressure_chart": _detail_family_pressure_chart_provider,
        "combat_ai.detail.tactical_parts": _detail_tactical_parts_provider,
        "combat_ai.detail.family_pressure": _detail_family_pressure_provider,
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
        imprint_key = str(form.get("imprint_key") or "")
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
        if action == "family_pressure":
            run = await _run_family_pressure(
                request,
                request_id=request_id,
                seed=_seed_from_form(form),
                imprint_key=imprint_key,
            )
            return RedirectResponse(f"{_BASE}/run-detail?id={run.id}", status_code=303)
        if action == "family_pressure_all_imprints":
            await _run_family_pressure_all_imprints(request, request_id=request_id, seed=_seed_from_form(form))
            return RedirectResponse(f"{_BASE}/pve-arena", status_code=303)
        if action != "run_demo":
            return RedirectResponse(_BASE, status_code=303)
        if request_id.startswith("live_batch:"):
            scenario_key = _live_batch_scenario_key(request_id)
            if scenario_key not in _LIVE_LAUNCH_SCENARIOS:
                return RedirectResponse(_BASE, status_code=303)
            await _run_live_demo_batch(request, request_id=request_id, policy_run_id=policy_run_id)
            return RedirectResponse(f"{_BASE}/reports", status_code=303)
        if request_id in _LIVE_LAUNCH_SCENARIOS:
            seed = _auto_seed() if request_id == "starter_presets_random_draft_live" else 0
            run = await _run_live_scenario(request, scenario_key=request_id, seed=seed, policy_run_id=policy_run_id)
            return RedirectResponse(f"{_BASE}/run-detail?id={run.id}", status_code=303)
        return RedirectResponse(_BASE, status_code=303)


def _live_batch_scenario_key(request_id: str) -> str:
    parts = request_id.split(":", maxsplit=2)
    return parts[1] if len(parts) == 3 else ""


async def _run_live_demo_batch(request: Request, *, request_id: str, policy_run_id: str = "") -> None:
    _, scenario_key, count_raw = request_id.split(":", maxsplit=2)
    count = min(max(_int(count_raw), 1), _LIVE_BATCH_ANALYSIS_MAX)
    params = _live_scenario_params(scenario_key)
    await _api(request).run_live_demo_batch(
        count=count,
        seed=_auto_seed(),
        policy_run_id=policy_run_id,
        **params,
    )


async def _run_live_scenario(
    request: Request,
    *,
    scenario_key: str,
    seed: int,
    policy_run_id: str = "",
) -> CombatAiSimulationRun:
    params = _live_scenario_params(scenario_key)
    if policy_run_id:
        params["policy_run_id"] = policy_run_id
    return await _api(request).run_live_demo(
        seed=seed,
        **params,
    )


async def _run_family_pressure(
    request: Request,
    *,
    request_id: str,
    seed: int,
    imprint_key: str = "",
) -> CombatAiSimulationRun:
    family_id = request_id.split(":", maxsplit=1)[1] if request_id.startswith("family_pressure:") else "rat_swarm"
    return await _api(request).run_family_pressure(
        family_id=family_id,
        imprint_key=imprint_key,
        seed=seed,
        trials=5,
        max_rounds=80,
        max_minions=6,
        max_scenarios=24,
    )


async def _run_family_pressure_all_imprints(
    request: Request, *, request_id: str, seed: int
) -> list[CombatAiSimulationRun]:
    family_id = request_id.split(":", maxsplit=1)[1] if request_id.startswith("family_pressure:") else "rat_swarm"
    return await _api(request).run_family_pressure_batch(
        family_id=family_id,
        seed=seed,
        trials=5,
        max_rounds=80,
        max_minions=6,
        max_scenarios=24,
    )


def _live_scenario_params(scenario_key: str) -> dict[str, Any]:
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
        "min_team_size": 5,
        "max_team_size": 5,
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
        cast("Any", request)._combat_ai_testing_cache = cache
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


def _family_pressure_detail_chart_options() -> dict[str, object]:
    return {
        "indexAxis": "y",
        "interaction": {"mode": "nearest", "axis": "y", "intersect": False},
        "scales": {
            "x": {
                "min": 0,
                "max": 100,
                "title": {"display": True, "text": "Проценты; ratio нормирован к максимуму в этом отчёте"},
            },
            "y": {"ticks": {"autoSkip": False}},
        },
    }


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
            canonical_part_id = _canonical_tactical_part_id(str(part_id))
            attempts[canonical_part_id] = attempts.get(canonical_part_id, 0) + _int(value)
        for part_id, value in _dict(telemetry.get("tactical_trigger_success_by_id")).items():
            canonical_part_id = _canonical_tactical_part_id(str(part_id))
            successes[canonical_part_id] = successes.get(canonical_part_id, 0) + _int(value)
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
            "part_id": part_id,
            "part": _tactical_part_label(part_id),
            "attempts": _tactical_display_attempts(part_id, attempts=attempts, shield_branch=shield_branch),
            "successes": _tactical_display_successes(part_id, successes=successes, shield_branch=shield_branch),
            "rate": _round(
                _pct(
                    _tactical_display_successes(part_id, successes=successes, shield_branch=shield_branch),
                    _tactical_display_attempts(part_id, attempts=attempts, shield_branch=shield_branch),
                )
            ),
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
                _tactical_display_attempts(part_id, attempts=attempts, shield_branch=shield_branch),
            ),
        }
        for part_id in part_ids
    ]
    rows.sort(
        key=lambda row: (
            -_int(cast("tuple[object, object, object]", row["_sort"])[0]),
            -_int(cast("tuple[object, object, object]", row["_sort"])[1]),
            -_int(cast("tuple[object, object, object]", row["_sort"])[2]),
            str(row["part"]),
        )
    )
    _attach_tactical_rate_metrics(rows)
    for row in rows:
        row.pop("_sort", None)
    return rows


def _attach_tactical_rate_metrics(rows: list[dict[str, object]]) -> None:
    for row in rows:
        event_count = _tactical_event_count(row)
        row["damage_per_event"] = _avg(_int(row.get("damage")) + _int(row.get("reflected")), event_count)
        row["defense_per_event"] = _avg(_int(row.get("prevented")) + _int(row.get("shield_defense")), event_count)


def _tactical_event_count(row: dict[str, object]) -> int:
    chain_hits = _int(row.get("chain_hits"))
    if chain_hits > 0:
        return chain_hits
    shield_events = _int(row.get("shield_defense")) + _int(row.get("shield_counter"))
    if shield_events > 0:
        return shield_events
    successes = _int(row.get("successes"))
    if successes > 0:
        return successes
    return max(1, _int(row.get("attempts")))


def _merge_ranged_position_totals(totals: dict[str, int], value: Any) -> None:
    for actor_positions in _dict(value).values():
        for position, amount in _dict(actor_positions).items():
            position_id = str(position)
            if position_id in totals:
                totals[position_id] += _int(amount)


def _ranged_position_actor_total(value: Any) -> int:
    return sum(_int(amount) for amount in _dict(value).values())


async def _analytics_tactical_skill_table(request: Request, skill_id: str) -> TableWidgetMap:
    key_suffix, title, part_ids = _TACTICAL_SKILL_CHARTS.get(skill_id, (skill_id, skill_id, ()))
    rows_by_part = {str(row.get("part_id") or ""): row for row in await _analytics_tactical_rows_for_request(request)}
    rows = [
        {
            "part_id": part_id,
            "part": _tactical_part_label(part_id),
            "attempts": _int(row.get("attempts")),
            "successes": _int(row.get("successes")),
            "rate": _float(row.get("rate")),
            "chain_hits": _int(row.get("chain_hits")),
            "shield_defense": _int(row.get("shield_defense")),
            "shield_counter": _int(row.get("shield_counter")),
            "damage": _int(row.get("damage")),
            "damage_per_event": _float(row.get("damage_per_event")),
            "shield_damage": _int(row.get("shield_damage")),
            "shield_absorbed": _int(row.get("shield_absorbed")),
            "shield_reflected": _int(row.get("shield_reflected")),
            "reflected": _int(row.get("reflected")),
            "prevented": _int(row.get("prevented")),
            "defense_per_event": _float(row.get("defense_per_event")),
        }
        for part_id in part_ids
        for row in [rows_by_part.get(part_id, {})]
    ]
    return TableWidgetMap(
        key=f"combat_ai_analytics_tactical_{key_suffix}",
        title=f"Тактика: {title}",
        columns=[
            TableColumnMap(key="part", label="Часть"),
            TableColumnMap(key="attempts", label="Попытки"),
            TableColumnMap(key="successes", label="Сработало"),
            TableColumnMap(key="rate", label="%"),
            TableColumnMap(key="chain_hits", label="Chain/off-hand"),
            TableColumnMap(key="shield_defense", label="Блок-защ."),
            TableColumnMap(key="shield_counter", label="Блок-контр."),
            TableColumnMap(key="damage", label="Урон"),
            TableColumnMap(key="damage_per_event", label="Урон/сраб."),
            TableColumnMap(key="shield_damage", label="Щит-урон"),
            TableColumnMap(key="shield_absorbed", label="Щит-погл."),
            TableColumnMap(key="shield_reflected", label="Щит-возвр."),
            TableColumnMap(key="reflected", label="Возврат"),
            TableColumnMap(key="prevented", label="Предотвр."),
            TableColumnMap(key="defense_per_event", label="Защ./сраб."),
        ],
        rows=rows,
    )


def _ranged_position_rows(runs: list[CombatAiSimulationRun]) -> list[dict[str, object]]:
    shots = _ranged_position_totals(runs, "ranged_position_outgoing_by_actor")
    incoming = _ranged_position_totals(runs, "ranged_position_incoming_by_actor")
    attempts = _ranged_position_totals(runs, "ranged_position_defense_attempts_by_actor")
    successes = _ranged_position_totals(runs, "ranged_position_defense_success_by_actor")
    bow_damage = _ranged_position_totals(runs, "ranged_position_outgoing_damage_by_actor")
    melee_taken = _ranged_position_totals(runs, "ranged_position_incoming_damage_by_actor")
    return [
        {
            "position": position,
            "shots": shots.get(position, 0),
            "bow_damage": bow_damage.get(position, 0),
            "bow_damage_per_shot": _round(_avg(bow_damage.get(position, 0), shots.get(position, 0))),
            "incoming_melee": incoming.get(position, 0),
            "ranged_dodge_attempts": attempts.get(position, 0),
            "ranged_dodge_success": successes.get(position, 0),
            "ranged_dodge_rate": _round(_pct(successes.get(position, 0), attempts.get(position, 0))),
            "melee_taken": melee_taken.get(position, 0),
            "melee_taken_per_entry": _round(_avg(melee_taken.get(position, 0), incoming.get(position, 0))),
        }
        for position in _RANGED_POSITIONS
    ]


def _ranged_position_totals(runs: list[CombatAiSimulationRun], telemetry_key: str) -> dict[str, int]:
    totals = {position: 0 for position in _RANGED_POSITIONS}
    for run in runs:
        _merge_ranged_position_totals(totals, run.telemetry.get(telemetry_key))
    return totals


def _tactical_rows(run: CombatAiSimulationRun | None) -> list[dict[str, object]]:
    if run is None:
        return []
    telemetry = run.telemetry
    attempts = _tactical_flat_totals(telemetry.get("tactical_trigger_attempts_by_id"))
    successes = _tactical_flat_totals(telemetry.get("tactical_trigger_success_by_id"))
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
            "attempts": _tactical_display_attempts(part_id, attempts=attempts, shield_branch=shield_branch),
            "successes": _tactical_display_successes(part_id, successes=successes, shield_branch=shield_branch),
            "rate": _round(
                _pct(
                    _tactical_display_successes(part_id, successes=successes, shield_branch=shield_branch),
                    _tactical_display_attempts(part_id, attempts=attempts, shield_branch=shield_branch),
                )
            ),
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
                _tactical_display_attempts(part_id, attempts=attempts, shield_branch=shield_branch),
            ),
        }
        for part_id in part_ids
    ]
    rows.sort(
        key=lambda row: (
            -_int(cast("tuple[object, object, object]", row["_sort"])[0]),
            -_int(cast("tuple[object, object, object]", row["_sort"])[1]),
            -_int(cast("tuple[object, object, object]", row["_sort"])[2]),
            str(row["part"]),
        )
    )
    _attach_tactical_rate_metrics(rows)
    for row in rows:
        row.pop("_sort", None)
    return rows


def _tactical_flat_totals(value: Any) -> dict[str, int]:
    totals: dict[str, int] = {}
    for part_id, raw_value in _dict(value).items():
        canonical_part_id = _canonical_tactical_part_id(str(part_id))
        totals[canonical_part_id] = totals.get(canonical_part_id, 0) + _int(raw_value)
    return totals


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
            canonical_part_id = _canonical_tactical_part_id(str(part_id))
            totals[canonical_part_id] = totals.get(canonical_part_id, 0) + _int(value)


def _merge_tactical_shield_branch_totals(totals: dict[str, int], value: Any) -> None:
    for actor_branches in _dict(value).values():
        for branch, value in _dict(actor_branches).items():
            branch_id = str(branch)
            if branch_id in {"defense", "counter"}:
                totals[branch_id] = totals.get(branch_id, 0) + _int(value)


def _canonical_tactical_part_id(part_id: str) -> str:
    if part_id in _SHIELD_TACTICAL_PART_ALIASES:
        return _SHIELD_TACTICAL_PART_ID
    return part_id


def _shield_block_total(shield_branch: dict[str, int]) -> int:
    return _int(shield_branch.get("defense")) + _int(shield_branch.get("counter"))


def _tactical_display_attempts(
    part_id: str,
    *,
    attempts: dict[str, int],
    shield_branch: dict[str, int],
) -> int:
    if part_id == _SHIELD_TACTICAL_PART_ID and _shield_block_total(shield_branch) > 0:
        return _shield_block_total(shield_branch)
    return attempts.get(part_id, 0)


def _tactical_display_successes(
    part_id: str,
    *,
    successes: dict[str, int],
    shield_branch: dict[str, int],
) -> int:
    if part_id == _SHIELD_TACTICAL_PART_ID and _shield_block_total(shield_branch) > 0:
        return _int(shield_branch.get("counter"))
    return successes.get(part_id, 0)


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
        success_count = (
            0
            if part_id == _SHIELD_TACTICAL_PART_ID
            else _tactical_actor_part_total(success_by_actor, actor_id, part_id)
        )
        chain_hits = _tactical_actor_part_total(chain_hits_by_actor, actor_id, part_id)
        damage = _tactical_actor_part_total(damage_by_actor, actor_id, part_id)
        reflected = _tactical_actor_part_total(reflected_by_actor, actor_id, part_id)
        prevented = _tactical_actor_part_total(prevented_by_actor, actor_id, part_id)
        shield_branches = _dict(shield_branch_by_actor.get(actor_id))
        shield_defense = _int(shield_branches.get("defense")) if part_id == _SHIELD_TACTICAL_PART_ID else 0
        shield_counter = _int(shield_branches.get("counter")) if part_id == _SHIELD_TACTICAL_PART_ID else 0
        shield_damage = _tactical_actor_part_total(shield_damage_by_actor, actor_id, part_id)
        shield_absorbed = _tactical_actor_part_total(shield_absorbed_by_actor, actor_id, part_id)
        shield_reflected = _tactical_actor_part_total(shield_reflected_by_actor, actor_id, part_id)
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


def _tactical_actor_part_total(value: Any, actor_id: str, part_id: str) -> int:
    actor_parts = _dict(_dict(value).get(actor_id))
    total = _int(actor_parts.get(part_id))
    if part_id == _SHIELD_TACTICAL_PART_ID:
        for alias in _SHIELD_TACTICAL_PART_ALIASES:
            total += _int(actor_parts.get(alias))
    return total


def _tactical_part_label(part_id: str) -> str:
    return _TACTICAL_PART_LABELS.get(part_id, part_id)


_BEHAVIOR_PROFILE_ORDER = {"aggressive": 0, "balanced": 1, "defensive": 2}


def _expanded_analytics_table_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    expanded: list[dict[str, object]] = []
    for row in rows:
        aggregate_row = dict(row)
        role_rows = aggregate_row.pop("role_rows", None)
        expanded.append(aggregate_row)
        if not isinstance(role_rows, list) or len(role_rows) <= 1:
            continue
        for role_row in role_rows:
            if isinstance(role_row, dict):
                expanded.append(dict(role_row))
    return expanded


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
        ranged_defense_successes = _dict(run.telemetry.get("ranged_position_defense_success_by_actor"))
        overkill = _dict(run.telemetry.get("overkill_by_actor"))
        deaths = {str(actor_id) for actor_id in run.telemetry.get("deaths") or []}
        for participant in participants:
            actor_id = str(participant.get("actor_id") or "")
            imprint_key = str(participant.get("imprint_key") or actor_id)
            behavior = str(participant.get("behavior_profile") or "balanced")
            if not actor_id or not imprint_key:
                continue
            row = aggregate.setdefault(
                imprint_key,
                {
                    "imprint_key": imprint_key,
                    "imprint": participant.get("imprint_title") or imprint_key,
                    "roles": {},
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
                    "ranged_defense_successes": 0,
                    "armor_absorbed": 0,
                    "armor_absorb_events": 0,
                    "overkill": 0,
                    "gear_score_total": 0.0,
                    "gear_score_offense": 0.0,
                    "gear_score_defense": 0.0,
                    "gear_score_resources": 0.0,
                    "gear_score_skills": 0.0,
                    "gear_score_utility": 0.0,
                    "effective_hp_total": 0.0,
                    "end_hp_pct_total": 0.0,
                },
            )
            role = _analytics_role_bucket(row, behavior)
            row["appearances"] += 1
            role["appearances"] += 1
            if run.winner and str(participant.get("team") or "") == run.winner:
                row["wins"] += 1
                role["wins"] += 1
            end_hp = _int(final_hp.get(actor_id))
            start_hp = max(1, _int(participant.get("start_hp")))
            if end_hp > 0 and actor_id not in deaths:
                row["survived"] += 1
                role["survived"] += 1
            row["end_hp_pct_total"] += max(0.0, min(100.0, end_hp / start_hp * 100))
            role["end_hp_pct_total"] += max(0.0, min(100.0, end_hp / start_hp * 100))
            for target, source in (
                ("damage", damage),
                ("taken", taken),
                ("actions", actions),
                ("hits", hits),
                ("misses", misses),
                ("crits", crits),
                ("overkill", overkill),
            ):
                value = _int(source.get(actor_id))
                row[target] += value
                role[target] += value
            row["dodges"] += _int(dodges.get(actor_id))
            role["dodges"] += _int(dodges.get(actor_id))
            row["parries"] += _int(parries.get(actor_id))
            role["parries"] += _int(parries.get(actor_id))
            row["blocks"] += _int(blocks.get(actor_id))
            role["blocks"] += _int(blocks.get(actor_id))
            ranged_defense = _ranged_position_actor_total(ranged_defense_successes.get(actor_id))
            row["ranged_defense_successes"] += ranged_defense
            role["ranged_defense_successes"] += ranged_defense
            row["armor_absorbed"] += _int(armor_absorbed.get(actor_id))
            role["armor_absorbed"] += _int(armor_absorbed.get(actor_id))
            row["armor_absorb_events"] += _int(armor_absorb_events.get(actor_id))
            role["armor_absorb_events"] += _int(armor_absorb_events.get(actor_id))
            gear_score = _gear_score_breakdown(participant.get("gear_score"))
            row["gear_score_total"] += gear_score["total"]
            role["gear_score_total"] += gear_score["total"]
            row["gear_score_offense"] += gear_score["offense"]
            role["gear_score_offense"] += gear_score["offense"]
            row["gear_score_defense"] += gear_score["defense"]
            role["gear_score_defense"] += gear_score["defense"]
            row["gear_score_resources"] += gear_score["resources"]
            role["gear_score_resources"] += gear_score["resources"]
            row["gear_score_skills"] += gear_score["skills"]
            role["gear_score_skills"] += gear_score["skills"]
            row["gear_score_utility"] += gear_score["utility"]
            role["gear_score_utility"] += gear_score["utility"]
            effective_hp = _effective_hit_points(participant)
            row["effective_hp_total"] += effective_hp
            role["effective_hp_total"] += effective_hp

    rows: list[dict[str, object]] = []
    for item in aggregate.values():
        row = _analytics_metric_row(
            item,
            imprint_key=str(item["imprint_key"]),
            imprint=str(item["imprint"]),
            behavior="Среднее",
        )
        roles = item.get("roles")
        role_rows: list[dict[str, object]] = []
        if isinstance(roles, dict):
            for name, role in sorted(
                roles.items(),
                key=lambda pair: (_BEHAVIOR_PROFILE_ORDER.get(str(pair[0]), 99), str(pair[0])),
            ):
                if not isinstance(role, dict):
                    continue
                role_rows.append(
                    _analytics_metric_row(
                        role,
                        imprint_key=f"{item['imprint_key']}:{name}",
                        imprint="",
                        behavior=str(name),
                    )
                )
        row["role_rows"] = role_rows
        rows.append(row)
    return sorted(rows, key=lambda row: str(row["imprint"]))


def _analytics_metric_row(
    item: dict[str, Any],
    *,
    imprint_key: str,
    imprint: str,
    behavior: str,
) -> dict[str, object]:
    appearances = max(1, _int(item.get("appearances")))
    hits = _int(item.get("hits"))
    accuracy_checks = hits + _int(item.get("misses"))
    ranged_defense = _int(item.get("ranged_defense_successes"))
    dodges = _int(item.get("dodges"))
    ordinary_dodges = max(0, dodges - ranged_defense)
    defence = dodges + _int(item.get("parries")) + _int(item.get("blocks"))
    defence_total = max(1, defence)
    actions = max(1, _int(item.get("actions")))
    armor_events = max(1, _int(item.get("armor_absorb_events")))
    return {
        "imprint_key": imprint_key,
        "imprint": imprint,
        "behavior": behavior,
        "appearances": appearances,
        "win_rate": _pct(item.get("wins"), appearances),
        "survival_rate": _pct(item.get("survived"), appearances),
        "avg_end_hp_pct": _avg(item.get("end_hp_pct_total"), appearances),
        "avg_damage": _avg(item.get("damage"), appearances),
        "avg_taken": _avg(item.get("taken"), appearances),
        "gear_score": _avg(item.get("gear_score_total"), appearances),
        "gear_score_offense": _avg(item.get("gear_score_offense"), appearances),
        "gear_score_defense": _avg(item.get("gear_score_defense"), appearances),
        "gear_score_resources": _avg(item.get("gear_score_resources"), appearances),
        "gear_score_skills": _avg(item.get("gear_score_skills"), appearances),
        "gear_score_utility": _avg(item.get("gear_score_utility"), appearances),
        "effective_hp": _avg(item.get("effective_hp_total"), appearances),
        "damage_per_action": _avg(item.get("damage"), actions),
        "attack_checks_per_action": _avg(accuracy_checks, actions),
        "damage_per_hit": _avg(item.get("damage"), max(1, hits)),
        "hit_rate": _pct(hits, accuracy_checks),
        "crit_rate": _pct(item.get("crits"), hits),
        "avg_overkill": _avg(item.get("overkill"), appearances),
        "dodge_per_appearance": _avg(dodges, appearances),
        "ordinary_dodge_per_appearance": _avg(ordinary_dodges, appearances),
        "parry_per_appearance": _avg(item.get("parries"), appearances),
        "block_per_appearance": _avg(item.get("blocks"), appearances),
        "ranged_defense_per_appearance": _avg(ranged_defense, appearances),
        "armor_absorbed_per_appearance": _avg(item.get("armor_absorbed"), appearances),
        "armor_absorb_events_per_appearance": _avg(item.get("armor_absorb_events"), appearances),
        "armor_absorbed_per_event": _avg(item.get("armor_absorbed"), armor_events),
        "defence_per_appearance": _avg(defence + _int(item.get("armor_absorb_events")), appearances),
        "dodge_defence_share": _pct(item.get("dodges"), defence_total) if defence else 0.0,
        "parry_defence_share": _pct(item.get("parries"), defence_total) if defence else 0.0,
        "block_defence_share": _pct(item.get("blocks"), defence_total) if defence else 0.0,
    }


def _analytics_role_bucket(row: dict[str, Any], behavior: str) -> dict[str, Any]:
    roles = row.setdefault("roles", {})
    if not isinstance(roles, dict):
        roles = {}
        row["roles"] = roles
    return roles.setdefault(
        behavior,
        {
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
            "ranged_defense_successes": 0,
            "armor_absorbed": 0,
            "armor_absorb_events": 0,
            "overkill": 0,
            "gear_score_total": 0.0,
            "gear_score_offense": 0.0,
            "gear_score_defense": 0.0,
            "gear_score_resources": 0.0,
            "gear_score_skills": 0.0,
            "gear_score_utility": 0.0,
            "effective_hp_total": 0.0,
            "end_hp_pct_total": 0.0,
        },
    )


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
            "metric": "ranged_position_outgoing_by_actor",
            "value": telemetry.get("ranged_position_outgoing_by_actor", {}),
        },
        {
            "metric": "ranged_position_incoming_by_actor",
            "value": telemetry.get("ranged_position_incoming_by_actor", {}),
        },
        {
            "metric": "ranged_position_defense_attempts_by_actor",
            "value": telemetry.get("ranged_position_defense_attempts_by_actor", {}),
        },
        {
            "metric": "ranged_position_defense_success_by_actor",
            "value": telemetry.get("ranged_position_defense_success_by_actor", {}),
        },
        {
            "metric": "ranged_position_outgoing_damage_by_actor",
            "value": telemetry.get("ranged_position_outgoing_damage_by_actor", {}),
        },
        {
            "metric": "ranged_position_incoming_damage_by_actor",
            "value": telemetry.get("ranged_position_incoming_damage_by_actor", {}),
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
        {"metric": "storage", "value": metadata.get("storage", "database")},
        {"metric": "best_policy_id", "value": _dict(metadata.get("best_policy")).get("policy_id", "—")},
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
    if _is_family_pressure_run(run):
        rows = _family_pressure_rows(run)
        if run.status == "running" and not rows:
            return [
                (
                    f"Family pressure запущен: {run.metadata.get('imprint_key') or run.telemetry.get('imprint_key')} "
                    f"против {run.metadata.get('family_id') or run.telemetry.get('family_id')}."
                ),
                "Worker считает бои в фоне и пишет Redis progress после каждого боя; обнови страницу, чтобы увидеть partial ladder.",
                (
                    f"План: {_int(run.metadata.get('trials_per_composition') or run.telemetry.get('trials_per_composition'))} "
                    f"боёв на каждый состав, max rounds {run.max_rounds}, seed {run.seed}."
                ),
                "HP, energy и stamina сбрасываются перед каждым отдельным боем.",
            ]
        first_losing = next((row for row in rows if _float(row.get("winrate")) < 0.5), None)
        items = [
            (
                f"Family pressure: {run.metadata.get('imprint_title') or run.metadata.get('imprint_key')} "
                f"против {run.metadata.get('family_id')}; "
                f"{run.telemetry.get('trials_total', run.rounds_completed)} боёв."
            ),
            (
                f"Слепок: GS {run.metadata.get('player_gear_score')} / HP {run.metadata.get('player_start_hp')}; "
                f"серия {_int(run.metadata.get('trials_per_composition'))} боёв на каждый состав."
            ),
        ]
        if first_losing:
            items.append(
                "Первая зона статистического перелома: "
                f"{first_losing['composition']} при effective GS {first_losing['effective_gs']} "
                f"({first_losing['ratio']}x от GS слепка), winrate {first_losing['winrate']}."
            )
        else:
            items.append("В проверенной лестнице нет состава, где winrate слепка упал ниже 50%.")
        items.append("Каждый бой собирался заново: HP, energy и stamina сбрасывались перед прогоном.")
        return items
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
    elif run.metadata.get("roster_mode") in {"mirror_10v10", "mirror_full_roster"}:
        items.append("Составы зеркальные по полному стартовому пулу: в каждой команде есть все слепки матрицы.")
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
    if _is_family_pressure_run(run):
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
                "behavior": participant.get("behavior_profile") or "—",
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
    if _is_family_pressure_run(run):
        rows = _family_pressure_rows(run)
        if not rows:
            return [
                "Family pressure ещё считает бои; partial results появятся из Redis progress после первого завершённого боя.",
                "Эта страница измеряет выживаемость стартового слепка против PvE состава, а не одиночный combat log.",
            ]
        first_losing = next((row for row in rows if _float(row.get("winrate")) < 0.5), None)
        strongest_win = max(
            rows,
            key=lambda row: _float(row.get("effective_gs")) if _float(row.get("winrate")) >= 0.5 else -1,
        )
        items = [
            "Это не PvP-прогон: отчёт измеряет, сколько состава семьи реально держит один стартовый слепок.",
            (
                f"Последний уверенно проходимый состав: {strongest_win['composition']} "
                f"({strongest_win['effective_gs']} eff GS, winrate {strongest_win['winrate']})."
            ),
        ]
        if first_losing:
            items.append(
                f"Для бюджета встречи точка перелома начинается около ratio {first_losing['ratio']} "
                f"на составе {first_losing['composition']}."
            )
        items.append("Эти цифры лучше использовать как коэффициент состава, а не как прямое сложение raw GS монстров.")
        return items
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
        items.append("Control/buffs не применялись: нужен отдельный малый сценарий для командной логики.")
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
    if scenario_key.startswith("family_pressure:"):
        return f"Family pressure: {scenario_key.split(':', maxsplit=1)[1]}"
    labels = {
        "mvp_1v1_player_model_vs_trainer_bot": "MVP 1v1: trainer bot vs player model",
        "starter_presets_5v5": "Стартовые пресеты 5v5",
        "starter_presets_5v5_live": "Live tick: стартовые пресеты 5v5",
        "starter_presets_random_draft": "Random draft 2v2-4v4",
        "starter_presets_random_draft_live": "Live tick: random draft 2v2-4v4",
        "starter_presets_mirror_10v10": "Зеркало полного пула",
        "starter_presets_mirror_10v10_live": "Live tick: зеркало полного пула",
        "starter_presets_5v5_live_full_skills": "Live tick: стартовые пресеты 5v5, full skills",
        "starter_presets_mirror_10v10_live_full_skills": "Live tick: зеркало полного пула, full skills",
        "starter_presets_5v5_latest_training_file": "Стартовые пресеты 5v5 + версия обучения",
        "starter_presets_5v5_live_latest_training_file": "Live tick: стартовые пресеты 5v5 + версия обучения",
        "starter_presets_mirror_10v10_live_latest_training_file": "Live tick: зеркало полного пула + версия обучения",
        "battle_policy_finetune": "Стадия 2: обучение в боях",
        "synthetic_policy_training": "Synthetic training",
    }
    return labels.get(scenario_key, scenario_key or "—")


def _winner_label(run: CombatAiSimulationRun) -> str:
    if _is_family_pressure_run(run):
        rows = _family_pressure_rows(run)
        if not rows:
            return "считается" if run.status == "running" else "нет данных"
        first_losing = next((row for row in rows if _float(row.get("winrate")) < 0.5), None)
        return "перелом найден" if first_losing else "слепок держится"
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
    if _is_family_pressure_run(run):
        return f"battles {run.rounds_completed}"
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


def _is_family_pressure_run(run: CombatAiSimulationRun) -> bool:
    return bool(run.metadata.get("family_pressure")) or str(run.telemetry.get("run_kind") or "") == "family_pressure"


def _family_pressure_rows(run: CombatAiSimulationRun | None) -> list[dict[str, object]]:
    if run is None:
        return []
    raw_rows = run.metadata.get("composition_reports") or run.telemetry.get("pressure_rows") or []
    rows: list[dict[str, object]] = []
    for raw_row in raw_rows:
        row = _dict(raw_row)
        composition = _dict(row.get("composition"))
        role_counts = _dict(composition.get("role_counts"))
        composition_label = " + ".join(
            f"{_int(role_counts.get(role))}x {role}"
            for role in ("minion", "veteran", "elite", "boss")
            if _int(role_counts.get(role))
        )
        rows.append(
            {
                "composition": composition_label or str(composition.get("key") or "—"),
                "role_counts": role_counts,
                "composition_type": _family_pressure_composition_type(role_counts),
                "grade": _family_pressure_grade(role_counts, composition.get("grade") or row.get("grade")),
                "raw_gs": _int(row.get("raw_gear_score")),
                "effective_gs": _round(row.get("effective_gear_score")),
                "ratio": _round(row.get("effective_ratio")),
                "winrate": _round(row.get("player_win_rate")),
                "winrate_pct": _round(_float(row.get("player_win_rate")) * 100),
                "trials": _int(row.get("trials")),
                "result": f"{_int(row.get('player_wins'))}/{_int(row.get('monster_wins'))}/{_int(row.get('draws'))}",
                "avg_hp": _round(row.get("avg_player_hp")),
                "avg_rounds": _round(row.get("avg_rounds")),
                "roles": ", ".join(str(item) for item in row.get("member_roles") or []),
                "monster_gs": ", ".join(str(item) for item in row.get("member_gear_scores") or []),
                "variants": ", ".join(str(item) for item in row.get("member_variants") or []),
            }
        )
    return rows


def _family_pressure_display_rows(run: CombatAiSimulationRun | None) -> list[dict[str, object]]:
    rows = _family_pressure_rows(run)
    if rows:
        return rows
    if run is None or not _is_family_pressure_run(run):
        return []
    return [
        {
            "composition": "ожидает worker" if run.status == "running" else "нет данных",
            "composition_type": "—",
            "grade": "—",
            "raw_gs": "—",
            "effective_gs": "—",
            "ratio": "—",
            "winrate": "—",
            "winrate_pct": "—",
            "trials": 0,
            "result": "—",
            "avg_hp": "—",
            "avg_rounds": "—",
            "roles": "—",
            "monster_gs": "—",
            "variants": "Redis progress появится после первого завершённого боя",
        }
    ]


def _family_pressure_parameter_rows(run: CombatAiSimulationRun) -> list[dict[str, object]]:
    metadata = run.metadata
    telemetry = run.telemetry
    rows = [
        {"metric": "Семья", "value": metadata.get("family_id") or telemetry.get("family_id") or "—"},
        {"metric": "Слепок", "value": metadata.get("imprint_title") or metadata.get("imprint_key") or "—"},
        {"metric": "Статус", "value": run.status},
        {"metric": "Seed", "value": run.seed},
        {
            "metric": "Бои на состав",
            "value": metadata.get("trials_per_composition") or telemetry.get("trials_per_composition") or "—",
        },
        {"metric": "Завершено боёв", "value": telemetry.get("trials_total", run.rounds_completed)},
        {"metric": "Max rounds на бой", "value": run.max_rounds},
        {"metric": "Max minions", "value": metadata.get("max_minions", "—")},
        {"metric": "Max scenarios", "value": metadata.get("max_scenarios", "—")},
        {"metric": "GS слепка", "value": metadata.get("player_gear_score", "после первого боя")},
        {"metric": "HP слепка", "value": metadata.get("player_start_hp", "после первого боя")},
    ]
    return rows


async def _pve_pressure_rows(request: Request) -> list[dict[str, object]]:
    runs = await _latest_family_pressure_runs(request)
    rows: list[dict[str, object]] = []
    for run in runs:
        family = str(run.metadata.get("family_id") or run.telemetry.get("family_id") or run.scenario_key)
        imprint = str(run.metadata.get("imprint_title") or run.metadata.get("imprint_key") or "—")
        for row in _family_pressure_rows(run):
            enriched = {
                **row,
                "created_at": _short_ts(run.created_at),
                "source": "generated/catalog",
                "family": family,
                "imprint": imprint,
                "status": run.status,
                "label": f"{family} / {imprint}",
                "href": _detail_href(run),
            }
            rows.append(enriched)
    return rows


async def _pve_summary_rows(request: Request) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for run in await _latest_family_pressure_runs(request):
        family = str(run.metadata.get("family_id") or run.telemetry.get("family_id") or run.scenario_key)
        imprint = str(run.metadata.get("imprint_title") or run.metadata.get("imprint_key") or "—")
        pressure_rows = _family_pressure_rows(run)
        minion_rows = [row for row in pressure_rows if _is_pure_minion_row(row)]
        held_minion_rows = [row for row in minion_rows if _float(row.get("winrate")) >= 0.5]
        held_rows = [row for row in pressure_rows if _float(row.get("winrate")) >= 0.5]
        first_minion_break = next((row for row in minion_rows if _float(row.get("winrate")) < 0.5), None)
        first_danger = next((row for row in pressure_rows if _float(row.get("winrate")) < 0.5), None)
        best_held = max(held_rows, key=lambda row: _float(row.get("ratio")), default=None)
        minions_held = max((_composition_units(row) for row in held_minion_rows), default=0)
        rows.append(
            {
                "created_at": _short_ts(run.created_at),
                "source": "generated/catalog",
                "family": family,
                "imprint": imprint,
                "label": f"{family} / {imprint}",
                "status": run.status,
                "composition_count": len(pressure_rows),
                "trials_total": run.telemetry.get("trials_total", run.rounds_completed),
                "minions_held": str(minions_held) if minions_held else "—",
                "minions_held_value": minions_held,
                "minion_breakpoint": str(first_minion_break["composition"]) if first_minion_break else "не найден",
                "first_danger": str(first_danger["composition"]) if first_danger else "не найден",
                "held_pressure": str(best_held["composition"]) if best_held else "—",
                "held_ratio": best_held.get("ratio", "—") if best_held else "—",
                "held_ratio_value": _float(best_held.get("ratio")) if best_held else 0.0,
                "break_ratio": first_danger.get("ratio", "—") if first_danger else "—",
                "break_ratio_value": _float(first_danger.get("ratio")) if first_danger else 0.0,
                "avg_hp_break": first_danger.get("avg_hp", "—") if first_danger else "—",
                "href": _detail_href(run),
            }
        )
    return sorted(rows, key=lambda row: (str(row.get("family")), str(row.get("imprint"))))


def _family_pressure_composition_type(role_counts: dict[str, Any]) -> str:
    if _int(role_counts.get("boss")):
        return "босс"
    if _int(role_counts.get("elite")):
        return "элита"
    if _int(role_counts.get("veteran")):
        return "охрана"
    if _int(role_counts.get("minion")):
        return "миньоны"
    return "—"


def _family_pressure_grade(role_counts: dict[str, Any], explicit: Any = None) -> str:
    if explicit:
        return str(explicit)
    if _int(role_counts.get("boss")):
        return "boss_probe"
    if _int(role_counts.get("elite")):
        return "hard"
    veterans = _int(role_counts.get("veteran"))
    minions = _int(role_counts.get("minion"))
    total = veterans + minions
    if veterans:
        return "medium" if veterans <= max(1, total // 2) else "hard"
    if minions >= 6:
        return "medium"
    if minions:
        return "light"
    return "—"


def _is_pure_minion_row(row: dict[str, object]) -> bool:
    role_counts = _dict(row.get("role_counts"))
    minions = _int(role_counts.get("minion"))
    return (
        minions > 0 and sum(_int(role_counts.get(role)) for role in ("minion", "veteran", "elite", "boss")) == minions
    )


def _composition_units(row: dict[str, object]) -> int:
    role_counts = _dict(row.get("role_counts"))
    return sum(_int(role_counts.get(role)) for role in ("minion", "veteran", "elite", "boss"))


async def _latest_family_pressure_runs(request: Request) -> list[CombatAiSimulationRun]:
    latest_by_pair: dict[tuple[str, str], CombatAiSimulationRun] = {}
    for run in await _safe_list_runs(request, limit=200):
        if not _is_family_pressure_run(run) or run.status not in {"running", "completed"}:
            continue
        family = str(run.metadata.get("family_id") or run.telemetry.get("family_id") or run.scenario_key)
        imprint = str(run.metadata.get("imprint_key") or run.telemetry.get("imprint_key") or "")
        key = (family, imprint)
        if key not in latest_by_pair:
            latest_by_pair[key] = run
    return list(latest_by_pair.values())


def _starter_imprint_options(*, selected: str = "") -> list[dict[str, object]]:
    selected_key = selected or "starter_breaker_01"
    return [
        {
            **option,
            "selected": option["value"] == selected_key,
        }
        for option in _STARTER_IMPRINT_OPTIONS
    ]


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


def _effective_hit_points(participant: dict[str, Any]) -> float:
    stats = _dict(participant.get("combat_stats"))
    hp = max(0.0, _float(participant.get("start_hp")))
    hp_regen = max(0.0, _float(stats.get("hp_regen")))
    armor = max(0.0, _float(stats.get("armor")))
    physical_resistance = max(0.0, min(0.85, _float(stats.get("physical_resistance"))))
    protected_hp = hp + (hp_regen * _EHP_REGEN_WINDOW_EXCHANGES)
    damage_after_defense = max(
        1.0,
        (_EHP_REFERENCE_HIT_DAMAGE * (1.0 - physical_resistance)) - armor,
    )
    return round(protected_hp * (_EHP_REFERENCE_HIT_DAMAGE / damage_after_defense), 3)


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
