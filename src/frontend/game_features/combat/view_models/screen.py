from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.shared.schemas.combat import (
        CombatActionOptionDTO,
        CombatActorCardDTO,
        CombatDashboardDTO,
        CombatEffectBadgeDTO,
        CombatEventDTO,
        CombatExchangeStateDTO,
        CombatResultDTO,
    )

DEFAULT_PLAYER_AVATAR_URL = "/static/images/avatars/silhouette_m.webp"
DEFAULT_SHADOW_AVATAR_URL = "/static/images/avatars/veil4.webp"
DEFAULT_MONSTER_AVATAR_URL = "/static/images/avatars/silhouette_f.webp"
COMBAT_ICON_ROOT = "/static/images/ui/combat-icons"
COMBAT_LOG_PAGE_SIZE = 8
FEINT_STAMINA_PER_TOKEN = 3
BASIC_ABILITY_ICON_FILES: dict[str, str] = {
    "basic_punish_mistake": "basic_punish_mistake",
    "basic_finish_moment": "basic_finish_moment",
    "basic_break_stance": "basic_break_stance",
    "basic_expose_weakness": "basic_expose_weakness",
    "basic_wipe_blood": "basic_wipe_blood",
    "basic_grit_teeth": "basic_grit_teeth",
    "basic_bloody_answer": "basic_bloody_answer",
    "basic_last_push": "basic_last_push",
}

FEINT_GROUP_ICON_FILES: dict[str, str] = {
    "basic": "group-basic",
    "tactical": "group-tactical",
    "weapon": "group-weapon",
}

FEINT_SPECIFIC_ICON_FILES: set[str] = set()


class CombatEffectBadgeVM(BaseModel):
    effect_id: str
    icon_url: str
    frame_kind: str = "default"
    duration_text: str | None = None
    title: str
    description: str = "NO_DATA"
    tooltip: str
    catalog: str = "effects"
    catalog_key: str


class CombatVitalsVM(BaseModel):
    hp_current: int
    hp_max: int
    hp_percent: int
    energy_current: int
    energy_max: int
    energy_percent: int
    stamina_current: int
    stamina_max: int
    stamina_percent: int
    tactics: int


class CombatQuickSlotVM(BaseModel):
    slot_index: int
    is_empty: bool = True
    item_id: str | None = None
    label: str = "NO_DATA"
    icon_url: str | None = None
    enabled: bool = False
    reason: str = "quick_belt_not_exposed"


class CombatStatValueVM(BaseModel):
    key: str
    label: str
    value_text: str
    tooltip: str | None = None


class CombatStatSectionVM(BaseModel):
    key: str
    label: str
    items: list[CombatStatValueVM] = Field(default_factory=list)


class CombatActorStatSheetVM(BaseModel):
    actor_id: str
    name: str
    sections: list[CombatStatSectionVM] = Field(default_factory=list)
    total_count: int = 0


class CombatActorPanelVM(BaseModel):
    actor_id: str
    name: str
    actor_type: str
    team: str
    avatar_url: str
    archetype: str | None = None
    role: str | None = None
    template_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: dict[str, Any] = Field(default_factory=dict)
    visual: dict[str, Any] = Field(default_factory=dict)
    exchange_counter: int = 0
    is_shadow: bool = False
    is_ai: bool = False
    is_dead: bool = False
    is_target: bool = False
    committed: bool = False
    commit_state: str = "idle"
    commit_tooltip: str = "Ход не выбран"
    remaining_ms: int | None = None
    vitals: CombatVitalsVM
    effects: list[CombatEffectBadgeVM] = Field(default_factory=list)
    quick_belt: list[CombatQuickSlotVM] = Field(default_factory=list)
    stat_sheet: CombatActorStatSheetVM | None = None


class CombatRosterRowVM(BaseModel):
    actor_id: str
    name: str
    team: str
    actor_type: str = "unknown"
    avatar_url: str
    vitals: CombatVitalsVM
    hp_current: int
    hp_max: int
    hp_percent: int
    target_queue_size: int = 0
    pending_action_count: int = 0
    is_target: bool = False
    is_dead: bool = False
    committed: bool = False
    commit_state: str = "idle"
    commit_tooltip: str = "Ход не выбран"
    remaining_ms: int | None = None
    queue_state: str = "NO_DATA"
    queue_indicator: str = "unknown"
    effects: list[CombatEffectBadgeVM] = Field(default_factory=list)
    stat_sheet: CombatActorStatSheetVM | None = None


class CombatRosterGroupVM(BaseModel):
    team: str
    label: str
    rows: list[CombatRosterRowVM] = Field(default_factory=list)
    alive_count: int = 0
    total_count: int = 0


class CombatTeamSummaryVM(BaseModel):
    label: str
    hp_current: int
    hp_max: int
    hp_percent: int
    alive_count: int
    total_count: int
    target_queue_size: int = 0
    pending_action_count: int = 0
    effects_count: int = 0


class CombatActionCostVM(BaseModel):
    token_id: str
    amount: int
    icon_url: str
    catalog: str = "combat_tokens"
    catalog_key: str


class CombatActionVM(BaseModel):
    id: str
    label: str
    kind: str
    icon_url: str
    enabled: bool = True
    target_id: str | None = None
    feint_id: str | None = None
    ability_id: str | None = None
    reason: str | None = None
    catalog: str | None = None
    catalog_key: str | None = None
    pinned: bool = False
    cost: dict[str, int] = Field(default_factory=dict)
    cost_items: list[CombatActionCostVM] = Field(default_factory=list)
    cost_tooltip: str | None = None


class CombatTokenVM(BaseModel):
    token_id: str
    value: int
    icon_url: str
    title: str
    description: str = "NO_DATA"
    catalog: str = "combat_tokens"
    catalog_key: str


class CombatLogLineVM(BaseModel):
    id: str | None = None
    text: str
    kind: str = "log"
    severity: str = "normal"
    icon_url: str | None = None
    timestamp: int | float | None = None
    global_turn: int | None = None
    source: dict[str, object] | None = None
    target: dict[str, object] | None = None
    action: dict[str, object] | None = None
    template: dict[str, object] | None = None
    outcome: str | None = None
    resources: list[dict[str, object]] = Field(default_factory=list)
    badges: list[dict[str, object]] = Field(default_factory=list)
    effects: list[dict[str, object]] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
    catalog: str | None = None
    catalog_key: str | None = None
    catalog_event: str | None = None
    catalog_taxonomy: str = "humanoid"
    catalog_tooltip: str | None = None


class CombatLogTurnVM(BaseModel):
    global_turn: int | None = None
    title: str
    lines: list[CombatLogLineVM] = Field(default_factory=list)


class CombatActorRefVM(BaseModel):
    id: str
    name: str
    team: str | None = None
    actor_type: str | None = None


class CombatExchangeBadgeVM(BaseModel):
    kind: str
    value: int | float | None = None
    resource: str | None = None
    direction: str | None = None


class CombatExchangeStateVM(BaseModel):
    pair_status: str = "unknown"
    opponent_response_state: str = "unknown"
    title: str = "COMBAT"
    summary_text: str = "Бой начался. Противники выбирают позицию для первого размена."
    turn: int | None = None
    source: CombatActorRefVM | None = None
    target: CombatActorRefVM | None = None
    outcome: str | None = None
    badges: list[CombatExchangeBadgeVM] = Field(default_factory=list)


class CombatScreenVM(BaseModel):
    session_id: str
    status: str
    turn_number: int
    phase: str | None = None
    battle_type: str | None = None
    location_id: str | None = None
    personal_turn_number: int | None = None
    round_size: int | None = None
    action_state: str = "NO_DATA"
    target_queue_size: int = 0
    pending_action_count: int = 0
    hero: CombatActorPanelVM
    target: CombatActorPanelVM | None
    allies: list[CombatRosterRowVM] = Field(default_factory=list)
    enemies: list[CombatRosterRowVM] = Field(default_factory=list)
    enemy_groups: list[CombatRosterGroupVM] = Field(default_factory=list)
    allied_team: CombatTeamSummaryVM
    enemy_team: CombatTeamSummaryVM
    primary_attack: CombatActionVM | None = None
    feint_options: list[CombatActionVM] = Field(default_factory=list)
    ability_options: list[CombatActionVM] = Field(default_factory=list)
    token_bar: list[CombatTokenVM] = Field(default_factory=list)
    log_lines: list[CombatLogLineVM] = Field(default_factory=list)
    log_turns: list[CombatLogTurnVM] = Field(default_factory=list)
    target_exchange_turn: CombatLogTurnVM | None = None
    log_total: int = 0
    log_page: int = 1
    log_page_size: int = 8
    log_total_pages: int = 1
    log_pages: list[int] = Field(default_factory=lambda: [1])
    exchange_state: CombatExchangeStateVM = Field(default_factory=CombatExchangeStateVM)
    winner_team: str | None = None


class CombatResultProgressionVM(BaseModel):
    key: str
    label: str
    amount_text: str
    percent_text: str


class CombatResultExperienceVM(BaseModel):
    amount_text: str = "+0.0000"
    percent_text: str = "+0.00%"
    has_rewards: bool = False


class CombatResultActorVM(BaseModel):
    actor_id: str
    name: str
    team: str
    actor_type: str = "unknown"
    is_dead: bool = False
    hp_current: int = 0
    hp_max: int = 1
    hp_percent: int = 0


class CombatResultTeamVM(BaseModel):
    team: str
    label: str
    outcome: str
    actors: list[CombatResultActorVM] = Field(default_factory=list)
    alive_count: int = 0
    total_count: int = 0


class CombatOutcomeScreenVM(BaseModel):
    mode: str = "final"
    combat_id: str = "NO_DATA"
    title: str
    message: str
    summary: str
    outcome: str
    battle_type: str | None = None
    turns: int | None = None
    last_turn: int | None = None
    teams: list[CombatResultTeamVM] = Field(default_factory=list)
    progression: list[CombatResultProgressionVM] = Field(default_factory=list)
    experience: CombatResultExperienceVM = Field(default_factory=CombatResultExperienceVM)
    primary_label: str = "Продолжить"
    primary_target_state: str = "exploration"
    primary_action_kind: str = "continue"
    log_panel_id: str = "combat-outcome-log-panel"


class CombatResultScreenVM(BaseModel):
    combat_id: str
    title: str
    message: str
    summary: str
    outcome: str
    reason: str
    archived: bool
    battle_type: str | None = None
    turns: int | None = None
    last_turn: int | None = None
    teams: list[CombatResultTeamVM] = Field(default_factory=list)
    progression: list[CombatResultProgressionVM] = Field(default_factory=list)
    experience: CombatResultExperienceVM = Field(default_factory=CombatResultExperienceVM)
    primary_label: str = "Продолжить"
    primary_target_state: str = "exploration"


def build_combat_result_screen_vm(result: CombatResultDTO) -> CombatResultScreenVM:
    report = result.report if isinstance(result.report, dict) else {}
    actors = result.actors if isinstance(result.actors, dict) else {}
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    return CombatResultScreenVM(
        combat_id=result.combat_id or "NO_DATA",
        title=result.title,
        message=result.message,
        summary=result.summary,
        outcome=result.outcome,
        reason=result.reason,
        archived=result.archived,
        battle_type=_optional_str(metadata.get("battle_type")),
        turns=_optional_int(report.get("turns")),
        last_turn=_optional_int(report.get("last_turn")),
        teams=_result_teams(result, actors),
        progression=_result_progression(result),
        experience=_result_experience(result),
        primary_label=result.primary_action.label,
        primary_target_state=result.primary_action.target_state or "exploration",
    )


def build_combat_outcome_screen_from_result_vm(result: CombatResultDTO) -> CombatOutcomeScreenVM:
    report = result.report if isinstance(result.report, dict) else {}
    actors = result.actors if isinstance(result.actors, dict) else {}
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    return CombatOutcomeScreenVM(
        mode="final",
        combat_id=result.combat_id or "NO_DATA",
        title=result.title,
        message=result.message,
        summary=result.summary,
        outcome=result.outcome,
        battle_type=_optional_str(metadata.get("battle_type")),
        turns=_optional_int(report.get("turns")),
        last_turn=_optional_int(report.get("last_turn")),
        teams=_result_teams(result, actors),
        progression=_result_progression(result),
        experience=_result_experience(result),
        primary_label=result.primary_action.label,
        primary_target_state=result.primary_action.target_state or "exploration",
        primary_action_kind="continue",
    )


def build_combat_screen_from_result_vm(result: CombatResultDTO) -> CombatScreenVM:
    from src.shared.schemas.combat import CombatDashboardDTO

    actors = result.actors if isinstance(result.actors, dict) else {}
    teams = cast("dict[str, Any]", result.teams) if isinstance(result.teams, dict) else {}
    report = result.report if isinstance(result.report, dict) else {}
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    viewer_team = _optional_str(metadata.get("viewer_team")) or _viewer_team(
        result.char_id, cast("Mapping[str, object]", teams)
    )
    hero_id = str(result.char_id)
    if hero_id not in actors:
        hero_id = _first_actor_id(teams.get(viewer_team) if viewer_team else None) or hero_id
    enemy_team_ids = _enemy_team_ids(cast("Mapping[str, object]", teams), viewer_team)

    hero = _result_actor_card(hero_id, actors.get(hero_id), fallback_team=viewer_team or "team_1")
    ally_ids = (
        [str(actor_id) for actor_id in cast("list[Any]", teams.get(viewer_team, [])) if str(actor_id) != hero.actor_id]
        if viewer_team and isinstance(teams.get(viewer_team), list)
        else []
    )
    enemy_ids = [
        str(actor_id)
        for team in enemy_team_ids
        if isinstance(teams.get(team), list)
        for actor_id in cast("list[Any]", teams.get(team, []))
    ]
    enemies = [
        _result_actor_card(
            actor_id,
            actors.get(actor_id),
            fallback_team=_actor_team_from_result_teams(actor_id, teams) or "team_2",
            is_target=index == 0,
        )
        for index, actor_id in enumerate(enemy_ids)
    ]
    target = enemies[0] if enemies else None
    dashboard = CombatDashboardDTO(
        session_id=result.combat_id or "NO_DATA",
        turn_number=_optional_int(report.get("last_turn")) or 0,
        status="finished",
        phase="finalized",
        battle_type=_optional_str(metadata.get("battle_type")),
        action_state="COMBAT_FINALIZED",
        winner_team=_optional_str(metadata.get("winner")),
        hero=hero,
        target=target,
        allies=[
            _result_actor_card(actor_id, actors.get(actor_id), fallback_team=viewer_team or hero.team)
            for actor_id in ally_ids
        ],
        enemies=enemies,
    )
    return build_combat_screen_vm(dashboard)


def build_combat_outcome_screen_from_dashboard_vm(dashboard: CombatDashboardDTO) -> CombatOutcomeScreenVM | None:
    if dashboard.status != "spectating" or not dashboard.hero.is_dead:
        return None
    allied_actors = [dashboard.hero, *dashboard.allies]
    enemy_groups = _dashboard_team_groups(dashboard.enemies or ([dashboard.target] if dashboard.target else []))
    summary = (
        f"Ты выбыл на {dashboard.turn_number} ходу. Бой продолжается, можно следить за исходом и полным логом."
        if dashboard.turn_number
        else "Ты выбыл из боя. Бой продолжается, можно следить за исходом и полным логом."
    )
    return CombatOutcomeScreenVM(
        mode="spectating",
        combat_id=dashboard.session_id,
        title="Ты пал",
        message="Бой продолжается",
        summary=summary,
        outcome="defeat",
        battle_type=dashboard.battle_type,
        turns=dashboard.turn_number,
        last_turn=dashboard.turn_number,
        teams=[
            _dashboard_team_vm(dashboard.hero.team or "team_1", allied_actors),
            *[_dashboard_team_vm(team, members) for team, members in enemy_groups],
        ],
        primary_label="Обновить статус боя",
        primary_target_state="combat",
        primary_action_kind="refresh_status",
    )


def build_combat_screen_vm(dashboard: CombatDashboardDTO) -> CombatScreenVM:
    primary_attack, feints, abilities = _split_actions(dashboard.available_actions, dashboard.hero)
    allied_actors = [dashboard.hero, *dashboard.allies]
    enemy_actors = dashboard.enemies or ([dashboard.target] if dashboard.target else [])
    enemy_rows = [_roster_row(actor) for actor in dashboard.enemies]
    log_turns = _log_turns(dashboard)
    log_page_size = COMBAT_LOG_PAGE_SIZE
    log_total = dashboard.log_total or len(log_turns)
    log_total_pages = max(1, (log_total + log_page_size - 1) // log_page_size)
    return CombatScreenVM(
        session_id=dashboard.session_id,
        status=dashboard.status,
        turn_number=dashboard.turn_number,
        phase=dashboard.phase,
        battle_type=dashboard.battle_type,
        location_id=dashboard.location_id,
        personal_turn_number=dashboard.personal_turn_number,
        round_size=dashboard.round_size,
        action_state=dashboard.action_state,
        target_queue_size=dashboard.target_queue_size,
        pending_action_count=dashboard.pending_action_count,
        hero=_actor_panel(dashboard.hero, include_belt=True),
        target=_actor_panel(dashboard.target, include_belt=False) if dashboard.target else None,
        allies=[_roster_row(actor) for actor in allied_actors],
        enemies=enemy_rows,
        enemy_groups=_roster_groups(enemy_rows),
        allied_team=_team_summary("ALLIES", allied_actors),
        enemy_team=_team_summary("ENEMIES", enemy_actors),
        primary_attack=primary_attack,
        feint_options=feints,
        ability_options=abilities,
        token_bar=_token_bar(dashboard.hero.tokens),
        log_lines=[_log_line(event) for event in dashboard.events_delta.events[-8:]],
        log_turns=log_turns,
        target_exchange_turn=_target_exchange_turn(
            log_turns,
            hero_id=dashboard.hero.actor_id,
            target_id=dashboard.target.actor_id if dashboard.target else None,
        ),
        log_total=log_total,
        log_page=1,
        log_page_size=log_page_size,
        log_total_pages=log_total_pages,
        log_pages=_page_window(1, log_total_pages),
        exchange_state=_exchange_state(dashboard.exchange_state),
        winner_team=dashboard.winner_team,
    )


def _result_actor_card(
    actor_id: str,
    value: object,
    *,
    fallback_team: str,
    is_target: bool = False,
) -> CombatActorCardDTO:
    from src.shared.schemas.combat import CombatActorCardDTO, CombatActorVitalsDTO

    data = value if isinstance(value, dict) else {}
    raw_vitals = data.get("vitals_final")
    vitals = raw_vitals if isinstance(raw_vitals, dict) else {}
    return CombatActorCardDTO(
        actor_id=actor_id,
        name=str(data.get("name") or actor_id),
        actor_type=str(data.get("actor_type") or "unknown"),
        team=str(data.get("team") or fallback_team),
        is_ai=bool(data.get("is_ai", False)),
        is_dead=bool(data.get("is_dead", False)),
        is_target=is_target,
        vitals=CombatActorVitalsDTO(
            hp_current=_optional_int(vitals.get("hp")) or 0,
            hp_max=max(_optional_int(vitals.get("max_hp")) or 1, 1),
            energy_current=_optional_int(vitals.get("en")) or 0,
            energy_max=max(_optional_int(vitals.get("max_en")) or 1, 1),
            stamina_current=_optional_int(vitals.get("stamina")) or 0,
            stamina_max=max(_optional_int(vitals.get("max_stamina")) or 1, 1),
        ),
    )


def _viewer_team(char_id: int, teams: Mapping[str, object]) -> str | None:
    actor_id = str(char_id)
    for team, members in teams.items():
        if isinstance(members, list) and actor_id in {str(member) for member in members}:
            return team
    return None


def _enemy_team_ids(teams: Mapping[str, object], viewer_team: str | None) -> list[str]:
    return [team for team, members in teams.items() if team != viewer_team and isinstance(members, list) and members]


def _actor_team_from_result_teams(actor_id: str, teams: Mapping[str, object]) -> str | None:
    for team, members in teams.items():
        if isinstance(members, list) and actor_id in {str(member) for member in members}:
            return team
    return None


def _first_actor_id(members: object) -> str | None:
    if not isinstance(members, list) or not members:
        return None
    return str(members[0])


def _result_teams(result: CombatResultDTO, actors: dict[str, object]) -> list[CombatResultTeamVM]:
    report = result.report if isinstance(result.report, dict) else {}
    report_teams = report.get("teams")
    if isinstance(report_teams, list) and report_teams:
        teams = [_result_team_from_report(team, actors) for team in report_teams if isinstance(team, dict)]
        return _order_result_teams(teams, result)

    raw_teams = result.teams if isinstance(result.teams, dict) else {}
    if raw_teams:
        result_teams = [
            _result_team_from_member_ids(
                str(team),
                [str(member) for member in members],
                actors,
                _team_outcome_for_result(str(team), result),
            )
            for team, members in raw_teams.items()
            if isinstance(members, list)
        ]
        return _order_result_teams(result_teams, result)

    grouped: dict[str, list[str]] = {}
    for actor_id, value in actors.items():
        data = value if isinstance(value, dict) else {}
        grouped.setdefault(str(data.get("team") or "neutral"), []).append(actor_id)
    result_teams = [
        _result_team_from_member_ids(team, member_ids, actors, _team_outcome_for_result(team, result))
        for team, member_ids in grouped.items()
    ]
    return _order_result_teams(result_teams, result)


def _result_team_from_report(team_report: dict[str, object], actors: dict[str, object]) -> CombatResultTeamVM:
    team_id = str(team_report.get("team") or "neutral")
    actor_rows = team_report.get("actors")
    member_ids = (
        [
            str(actor.get("actor_id"))
            for actor in actor_rows
            if isinstance(actor, dict) and actor.get("actor_id") not in (None, "")
        ]
        if isinstance(actor_rows, list)
        else []
    )
    outcome = str(team_report.get("outcome") or "unknown")
    return _result_team_from_member_ids(team_id, member_ids, actors, outcome)


def _result_team_from_member_ids(
    team_id: str,
    member_ids: list[str],
    actors: dict[str, object],
    outcome: str,
) -> CombatResultTeamVM:
    rows = [_result_actor(actor_id, actors.get(actor_id)) for actor_id in member_ids]
    return CombatResultTeamVM(
        team=team_id,
        label=_team_result_label(outcome),
        outcome=outcome,
        actors=rows,
        alive_count=sum(1 for actor in rows if not actor.is_dead),
        total_count=len(rows),
    )


def _result_actor(actor_id: str, value: object) -> CombatResultActorVM:
    data = value if isinstance(value, dict) else {}
    raw_vitals = data.get("vitals_final")
    vitals = raw_vitals if isinstance(raw_vitals, dict) else {}
    hp_current = _optional_int(vitals.get("hp")) or 0
    hp_max = max(_optional_int(vitals.get("max_hp")) or 1, 1)
    return CombatResultActorVM(
        actor_id=actor_id,
        name=str(data.get("name") or actor_id),
        team=str(data.get("team") or "neutral"),
        actor_type=str(data.get("actor_type") or "unknown"),
        is_dead=bool(data.get("is_dead", hp_current <= 0)),
        hp_current=hp_current,
        hp_max=hp_max,
        hp_percent=max(0, min(100, round(hp_current / hp_max * 100))),
    )


def _dashboard_team_groups(actors: list[CombatActorCardDTO]) -> list[tuple[str, list[CombatActorCardDTO]]]:
    grouped: dict[str, list[CombatActorCardDTO]] = {}
    for actor in actors:
        grouped.setdefault(actor.team or "neutral", []).append(actor)
    return list(grouped.items())


def _dashboard_team_vm(team_id: str, actors: list[CombatActorCardDTO]) -> CombatResultTeamVM:
    rows = [_dashboard_result_actor(actor) for actor in actors]
    return CombatResultTeamVM(
        team=team_id,
        label=_combat_team_label(team_id),
        outcome="ongoing",
        actors=rows,
        alive_count=sum(1 for actor in rows if not actor.is_dead),
        total_count=len(rows),
    )


def _dashboard_result_actor(actor: CombatActorCardDTO) -> CombatResultActorVM:
    vitals = _vitals(actor)
    return CombatResultActorVM(
        actor_id=actor.actor_id,
        name=actor.name,
        team=actor.team,
        actor_type=actor.actor_type,
        is_dead=actor.is_dead,
        hp_current=vitals.hp_current,
        hp_max=vitals.hp_max,
        hp_percent=vitals.hp_percent,
    )


def _result_progression(result: CombatResultDTO) -> list[CombatResultProgressionVM]:
    rewards = result.rewards if isinstance(result.rewards, dict) else {}
    progression = rewards.get("progression")
    if not isinstance(progression, dict):
        return []
    rows: list[CombatResultProgressionVM] = []
    for key, raw_value in progression.items():
        value = _optional_float(raw_value)
        if value is None:
            continue
        rows.append(
            CombatResultProgressionVM(
                key=str(key),
                label=_progression_label(str(key)),
                amount_text=f"+{value:.4f}",
                percent_text=f"+{value * 100:.2f}%",
            )
        )
    return rows


def _result_experience(result: CombatResultDTO) -> CombatResultExperienceVM:
    rewards = result.rewards if isinstance(result.rewards, dict) else {}
    progression = rewards.get("progression")
    if not isinstance(progression, dict):
        return CombatResultExperienceVM()
    total = sum(value for value in (_optional_float(raw) for raw in progression.values()) if value is not None)
    return CombatResultExperienceVM(
        amount_text=f"+{total:.4f}",
        percent_text=f"+{total * 100:.2f}%",
        has_rewards=total > 0,
    )


def _order_result_teams(teams: list[CombatResultTeamVM], result: CombatResultDTO) -> list[CombatResultTeamVM]:
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    viewer_team = _optional_str(metadata.get("viewer_team")) or _viewer_team(result.char_id, cast("Any", result.teams))
    return sorted(teams, key=lambda team: (team.team != viewer_team, team.team))


def _team_outcome_for_result(team: str, result: CombatResultDTO) -> str:
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    winner = _optional_str(metadata.get("winner"))
    if winner == "draw":
        return "draw"
    if winner:
        return "victory" if team == winner else "defeat"
    viewer_team = _optional_str(metadata.get("viewer_team")) or _viewer_team(result.char_id, cast("Any", result.teams))
    if viewer_team and team == viewer_team:
        return result.outcome
    if result.outcome == "victory":
        return "defeat"
    if result.outcome == "defeat":
        return "victory"
    return "unknown"


def _team_result_label(outcome: str) -> str:
    return {"victory": "Победили", "defeat": "Проиграли", "draw": "Ничья"}.get(outcome, "Команда")


def _progression_label(key: str) -> str:
    labels = {
        "skill_swords": "Мечи",
        "skill_parrying": "Парирование",
        "free_xp": "Свободный опыт",
    }
    return labels.get(key, key.removeprefix("skill_").replace("_", " ").title())


def _log_line(event: CombatEventDTO) -> CombatLogLineVM:
    action = _model_dict(getattr(event, "action", None)) or _event_data_dict(event.data, "action")
    template = _model_dict(getattr(event, "template", None)) or _event_data_dict(event.data, "template")
    source = (
        _model_dict(getattr(event, "source", None))
        or _event_data_dict(event.data, "source")
        or _event_actor_ref_from_id(event, "source")
    )
    target = (
        _model_dict(getattr(event, "target", None))
        or _event_data_dict(event.data, "target")
        or _event_actor_ref_from_id(event, "target")
    )
    catalog = _event_data_str(event.data, "catalog") or _dict_str(action, "catalog")
    catalog_key = _event_data_str(event.data, "catalog_key") or _dict_str(action, "catalog_key")
    catalog_event = _event_data_str(event.data, "catalog_event") or _dict_str(action, "event")
    catalog_taxonomy = _event_data_str(event.data, "catalog_taxonomy") or _dict_str(action, "taxonomy") or "humanoid"
    return CombatLogLineVM(
        id=getattr(event, "id", None),
        text=event.text or "NO_DATA",
        kind=getattr(event, "kind", None) or event.type,
        severity=getattr(event, "severity", None) or "normal",
        icon_url=_combat_log_icon_url(catalog, catalog_key),
        timestamp=event.timestamp,
        global_turn=_event_data_int(event, "global_turn"),
        source=source,
        target=target,
        action=action,
        template=template,
        outcome=getattr(event, "outcome", None) or _event_data_str(event.data, "outcome"),
        resources=[_model_dict(resource) for resource in getattr(event, "resources", [])],
        badges=[_model_dict(badge) for badge in getattr(event, "badges", [])],
        effects=[dict(effect) for effect in getattr(event, "effects", []) if isinstance(effect, dict)],
        flags=dict(getattr(event, "flags", {}) or {}),
        catalog=catalog,
        catalog_key=catalog_key,
        catalog_event=catalog_event,
        catalog_taxonomy=catalog_taxonomy,
        catalog_tooltip=_event_data_str(event.data, "catalog_tooltip"),
    )


def _target_exchange_turn(
    log_turns: list[CombatLogTurnVM],
    *,
    hero_id: str,
    target_id: str | None,
) -> CombatLogTurnVM | None:
    if not target_id:
        return None
    hero_key = str(hero_id)
    target_key = str(target_id)
    ordered_turns = sorted(
        log_turns,
        key=lambda turn: turn.global_turn if turn.global_turn is not None else -1,
        reverse=True,
    )
    for turn in ordered_turns:
        lines = [
            line
            for line in turn.lines
            if _combat_log_line_matches_actor_pair(line, actor_a=hero_key, actor_b=target_key)
        ]
        if lines:
            return CombatLogTurnVM(global_turn=turn.global_turn, title=turn.title, lines=lines)
    return None


def _page_window(active_page: int, total_pages: int) -> list[int]:
    first = max(1, active_page - 1)
    last = min(total_pages, first + 3)
    first = max(1, last - 3)
    return list(range(first, last + 1))


def _combat_log_line_matches_actor_pair(line: CombatLogLineVM, *, actor_a: str, actor_b: str) -> bool:
    source_id = _dict_str(line.source, "id")
    target_id = _dict_str(line.target, "id")
    return {source_id, target_id} == {actor_a, actor_b}


def _log_turns(dashboard: CombatDashboardDTO) -> list[CombatLogTurnVM]:
    turns = dashboard.events_delta.turns
    if not turns:
        grouped: dict[int | None, list[CombatEventDTO]] = {}
        for event in dashboard.events_delta.events:
            grouped.setdefault(_event_data_int(event, "global_turn"), []).append(event)
        return _latest_log_turns(
            [
                CombatLogTurnVM(
                    global_turn=turn,
                    title=f"Ход {turn}" if turn is not None else "Ход NO_DATA",
                    lines=[_log_line(event) for event in events],
                )
                for turn, events in grouped.items()
            ],
            limit=COMBAT_LOG_PAGE_SIZE,
        )

    return _latest_log_turns(
        [
            CombatLogTurnVM(
                global_turn=turn.global_turn,
                title=turn.title,
                lines=[_log_line(event) for event in turn.entries],
            )
            for turn in turns
        ],
        limit=COMBAT_LOG_PAGE_SIZE,
    )


def _latest_log_turns(log_turns: list[CombatLogTurnVM], *, limit: int) -> list[CombatLogTurnVM]:
    indexed = list(enumerate(log_turns))
    indexed.sort(
        key=lambda item: (
            item[1].global_turn is not None,
            item[1].global_turn if item[1].global_turn is not None else -1,
            -item[0],
        ),
        reverse=True,
    )
    return [turn for _, turn in indexed[:limit]]


def _exchange_state(exchange: CombatExchangeStateDTO | None) -> CombatExchangeStateVM:
    if exchange is None:
        return CombatExchangeStateVM()
    return CombatExchangeStateVM(
        pair_status=exchange.pair_status,
        opponent_response_state=exchange.opponent_response_state,
        title=exchange.title,
        summary_text=exchange.summary_text,
        turn=exchange.turn,
        source=_actor_ref(exchange.source),
        target=_actor_ref(exchange.target),
        outcome=exchange.outcome,
        badges=[
            CombatExchangeBadgeVM(
                kind=badge.kind,
                value=badge.value,
                resource=badge.resource,
                direction=badge.direction,
            )
            for badge in exchange.badges
        ],
    )


def _actor_ref(value: object) -> CombatActorRefVM | None:
    if value is None:
        return None
    data = _model_dict(value)
    actor_id = _dict_str(data, "id")
    name = _dict_str(data, "name")
    if not actor_id or not name:
        return None
    return CombatActorRefVM(
        id=actor_id,
        name=name,
        team=_dict_str(data, "team"),
        actor_type=_dict_str(data, "actor_type"),
    )


def _event_data_int(event: CombatEventDTO, key: str) -> int | None:
    value = getattr(event, key, None)
    if value in (None, ""):
        value = event.data.get(key)
    if value in (None, ""):
        return None
    try:
        return int(cast("Any", value))
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(cast("Any", value))
    except (TypeError, ValueError):
        return None


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(cast("Any", value))
    except (TypeError, ValueError):
        return None


def _optional_str(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _event_data_str(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value in (None, ""):
        return None
    return str(value)


def _event_data_dict(data: dict[str, object], key: str) -> dict[str, object] | None:
    value = data.get(key)
    return dict(value) if isinstance(value, dict) else None


def _event_actor_ref_from_id(event: CombatEventDTO, key: str) -> dict[str, object] | None:
    value = getattr(event, f"{key}_id", None)
    if value in (None, ""):
        value = event.data.get(f"{key}_id")
    if value in (None, ""):
        return None
    return {"id": str(value), "name": f"#{value}", "team": None, "actor_type": None}


def _model_dict(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return cast("dict[str, object]", model_dump(mode="json"))
    return {}


def _dict_str(data: dict[str, object] | None, key: str) -> str | None:
    if not data:
        return None
    value = data.get(key)
    if value in (None, ""):
        return None
    return str(value)


def _combat_log_icon_url(catalog: str | None, catalog_key: str | None) -> str | None:
    if catalog == "feints" or (catalog_key or "").startswith("combat.feint."):
        return f"{COMBAT_ICON_ROOT}/feint.svg"
    return None


def _actor_panel(actor: CombatActorCardDTO, *, include_belt: bool) -> CombatActorPanelVM:
    return CombatActorPanelVM(
        actor_id=actor.actor_id,
        name=actor.name,
        actor_type=actor.actor_type,
        team=actor.team,
        avatar_url=_avatar_url(actor),
        archetype=actor.archetype,
        role=actor.role,
        template_id=actor.template_id,
        tags=list(actor.tags),
        source=dict(actor.source),
        visual=dict(actor.visual),
        exchange_counter=actor.exchange_counter,
        is_shadow=_is_shadow(actor),
        is_ai=actor.is_ai,
        is_dead=actor.is_dead,
        is_target=actor.is_target,
        committed=actor.committed,
        commit_state=actor.commit_state,
        commit_tooltip=_commit_tooltip(actor),
        remaining_ms=actor.remaining_ms,
        vitals=_vitals(actor),
        effects=[_effect_badge(effect, actor.exchange_counter) for effect in actor.active_effects],
        quick_belt=_quick_belt(actor.quick_items) if include_belt else [],
        stat_sheet=_stat_sheet(actor),
    )


def _stat_sheet(actor: CombatActorCardDTO) -> CombatActorStatSheetVM | None:
    sheet = actor.stat_sheet
    if sheet is None or not sheet.sections:
        return None
    return CombatActorStatSheetVM(
        actor_id=sheet.actor_id,
        name=sheet.name,
        total_count=sheet.total_count,
        sections=[
            CombatStatSectionVM(
                key=section.key,
                label=section.label,
                items=[
                    CombatStatValueVM(
                        key=item.key,
                        label=item.label,
                        value_text=item.value_text,
                        tooltip=item.tooltip,
                    )
                    for item in section.items
                ],
            )
            for section in sheet.sections
            if section.items
        ],
    )


def _vitals(actor: CombatActorCardDTO) -> CombatVitalsVM:
    hp_max = max(actor.vitals.hp_max, 1)
    energy_max = max(actor.vitals.energy_max, 1)
    stamina_max = max(actor.vitals.stamina_max, 1)
    return CombatVitalsVM(
        hp_current=actor.vitals.hp_current,
        hp_max=hp_max,
        hp_percent=max(0, min(100, round(actor.vitals.hp_current / hp_max * 100))),
        energy_current=actor.vitals.energy_current,
        energy_max=energy_max,
        energy_percent=max(0, min(100, round(actor.vitals.energy_current / energy_max * 100))),
        stamina_current=actor.vitals.stamina_current,
        stamina_max=stamina_max,
        stamina_percent=max(0, min(100, round(actor.vitals.stamina_current / stamina_max * 100))),
        tactics=actor.vitals.tactics,
    )


def _roster_row(actor: CombatActorCardDTO) -> CombatRosterRowVM:
    vitals = _vitals(actor)
    return CombatRosterRowVM(
        actor_id=actor.actor_id,
        name=actor.name,
        team=actor.team,
        actor_type=actor.actor_type,
        avatar_url=_avatar_url(actor),
        vitals=vitals,
        hp_current=vitals.hp_current,
        hp_max=vitals.hp_max,
        hp_percent=vitals.hp_percent,
        target_queue_size=actor.target_queue_size,
        pending_action_count=sum(actor.pending_actions.values()),
        is_target=actor.is_target,
        is_dead=actor.is_dead,
        committed=actor.committed,
        commit_state=actor.commit_state,
        commit_tooltip=_commit_tooltip(actor),
        remaining_ms=actor.remaining_ms,
        queue_state=_queue_state(actor),
        queue_indicator=_queue_indicator(actor),
        effects=[_effect_badge(effect, actor.exchange_counter) for effect in actor.active_effects],
        stat_sheet=_stat_sheet(actor),
    )


def _roster_groups(rows: list[CombatRosterRowVM]) -> list[CombatRosterGroupVM]:
    grouped: dict[str, list[CombatRosterRowVM]] = {}
    for row in rows:
        grouped.setdefault(row.team or "neutral", []).append(row)
    return [
        CombatRosterGroupVM(
            team=team,
            label=_combat_team_label(team),
            rows=team_rows,
            alive_count=sum(1 for row in team_rows if not row.is_dead),
            total_count=len(team_rows),
        )
        for team, team_rows in grouped.items()
    ]


def _combat_team_label(team: str) -> str:
    if team == "neutral":
        return "NEUTRAL"
    suffix = team.removeprefix("team_")
    return f"TEAM {suffix.upper()}" if suffix else team.upper()


def _team_summary(label: str, actors: list[CombatActorCardDTO]) -> CombatTeamSummaryVM:
    hp_current = sum(max(0, _vitals(actor).hp_current) for actor in actors)
    hp_max = sum(max(0, _vitals(actor).hp_max) for actor in actors)
    total_count = len(actors)
    return CombatTeamSummaryVM(
        label=label,
        hp_current=hp_current,
        hp_max=hp_max,
        hp_percent=max(0, min(100, round(hp_current / hp_max * 100))) if hp_max else 0,
        alive_count=sum(1 for actor in actors if not actor.is_dead),
        total_count=total_count,
        target_queue_size=sum(actor.target_queue_size for actor in actors),
        pending_action_count=sum(sum(actor.pending_actions.values()) for actor in actors),
        effects_count=sum(len(actor.active_effects) + len(actor.active_abilities) for actor in actors),
    )


def _effect_badge(effect: CombatEffectBadgeDTO, exchange_counter: int) -> CombatEffectBadgeVM:
    frame_kind = _effect_kind(effect.effect_id)
    remaining = _effect_remaining(effect.expires_at_exchange, exchange_counter)
    title = effect.title or _effect_title(effect.effect_id, frame_kind)
    description = effect.description or "NO_DATA"
    impact_text = _effect_impact_text(effect.impact)
    duration_label = effect.duration_label
    duration = None if duration_label else str(remaining) if remaining is not None else None
    tooltip_parts = [title]
    if duration_label:
        tooltip_parts.append(duration_label)
    elif remaining is not None:
        tooltip_parts.append(_turns_left_text(remaining))
    if effect.description:
        tooltip_parts.append(effect.description)
    if impact_text:
        tooltip_parts.append(impact_text)
    return CombatEffectBadgeVM(
        effect_id=effect.effect_id,
        icon_url=f"{COMBAT_ICON_ROOT}/{_effect_icon(frame_kind)}.svg",
        frame_kind=frame_kind,
        duration_text=duration,
        title=title,
        description=description,
        tooltip=" // ".join(tooltip_parts),
        catalog_key=effect.effect_id,
    )


def _effect_remaining(expires_at_exchange: int | None, exchange_counter: int) -> int | None:
    if expires_at_exchange is None:
        return None
    return max(1, expires_at_exchange - exchange_counter + 1)


def _turns_left_text(turns: int) -> str:
    if turns == 1:
        return "остался 1 ход"
    if 2 <= turns <= 4:
        return f"осталось {turns} хода"
    return f"осталось {turns} ходов"


def _effect_impact_text(impact: dict[str, Any]) -> str:
    raw_hp = impact.get("hp")
    if not isinstance(raw_hp, (int, str)) or raw_hp == "":
        return ""
    try:
        value = int(raw_hp)
    except (TypeError, ValueError):
        return f"{raw_hp} HP за ход"
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value} HP за ход"


def _quick_belt(items: list[dict]) -> list[CombatQuickSlotVM]:
    slots: dict[int, CombatQuickSlotVM] = {}
    for item in items:
        index = _belt_slot_index(item.get("belt_slot") or item.get("slot"))
        if index is None:
            continue
        item_id = item.get("item_id") or item.get("inventory_id") or item.get("id")
        label = item.get("name") or item.get("title") or item.get("display_name") or item_id or f"SLOT {index}"
        slots[index] = CombatQuickSlotVM(
            slot_index=index,
            is_empty=False,
            item_id=str(item_id) if item_id else None,
            label=str(label),
            enabled=False,
            reason=str(item.get("item_type") or item.get("type") or "item_action_not_bound"),
        )
    return [slots.get(index) or CombatQuickSlotVM(slot_index=index) for index in range(1, 9)]


def _belt_slot_index(value: object) -> int | None:
    if value is None:
        return None
    text = str(value)
    digits = "".join(char for char in text if char.isdigit())
    if not digits:
        return None
    index = int(digits)
    return index if 1 <= index <= 8 else None


def _queue_state(actor: CombatActorCardDTO) -> str:
    pending_count = sum(actor.pending_actions.values())
    if actor.is_dead:
        return "DOWN"
    if pending_count:
        return f"LOCKED {pending_count}"
    if actor.target_queue_size:
        return f"QUEUE {actor.target_queue_size}"
    return "EMPTY"


def _queue_indicator(actor: CombatActorCardDTO) -> str:
    if actor.is_dead:
        return "dead"
    if actor.commit_state in {"committed", "half_time", "timeout_warning"}:
        return actor.commit_state
    if actor.is_target:
        return "current"
    if sum(actor.pending_actions.values()):
        return "locked"
    if actor.target_queue_size:
        return "ready"
    return "unknown"


def _commit_tooltip(actor: CombatActorCardDTO) -> str:
    if actor.is_dead:
        return "Выведен из боя"
    if actor.commit_state == "timeout_warning":
        return _remaining_text(actor.remaining_ms, prefix="До force attack")
    if actor.commit_state == "half_time":
        return _remaining_text(actor.remaining_ms, prefix="До force attack")
    if actor.commit_state == "committed":
        return "Ход выбран"
    return "Ход не выбран"


def _remaining_text(remaining_ms: int | None, *, prefix: str) -> str:
    if remaining_ms is None:
        return prefix
    seconds = max(0, round(remaining_ms / 1000))
    return f"{prefix}: {seconds} сек."


def _split_actions(
    actions: list[CombatActionOptionDTO],
    hero: CombatActorCardDTO,
) -> tuple[CombatActionVM | None, list[CombatActionVM], list[CombatActionVM]]:
    primary: CombatActionVM | None = None
    abilities: list[CombatActionVM] = []

    for action in actions:
        if action.action == "exchange":
            primary = _action_vm(action, kind="attack", icon="attack")
        elif action.ability_id:
            abilities.append(_action_vm(action, kind="ability", icon=_ability_icon(action.ability_id)))

    feints: list[CombatActionVM] = []
    for feint in hero.feints:
        stamina_cost = _feint_stamina_cost(feint.cost)
        has_concentration = hero.vitals.stamina_current >= stamina_cost
        enabled = bool(primary.enabled if primary else False) and has_concentration
        feints.append(
            CombatActionVM(
                id=feint.feint_id,
                label=feint.feint_id,
                kind="feint",
                icon_url=_feint_icon_url(feint.feint_id, feint.purchase_group),
                enabled=enabled,
                target_id=primary.target_id if primary else None,
                feint_id=feint.feint_id,
                catalog="feints",
                catalog_key=feint.feint_id,
                pinned=feint.pinned,
                cost=feint.cost,
                cost_items=_action_cost_items(feint.cost),
                cost_tooltip=_feint_cost_tooltip(feint.cost),
                reason=None if enabled else f"CONC {hero.vitals.stamina_current}/{stamina_cost}",
            )
        )
    return primary, feints, abilities


def _feint_stamina_cost(cost: dict[str, int]) -> int:
    return max(0, sum(max(0, int(amount or 0)) for amount in cost.values()) * FEINT_STAMINA_PER_TOKEN)


def _action_vm(action: CombatActionOptionDTO, *, kind: str, icon: str) -> CombatActionVM:
    action_id = action.feint_id or action.ability_id or action.action
    catalog = _action_catalog(kind)
    catalog_key = action.feint_id or action.ability_id
    return CombatActionVM(
        id=str(action_id),
        label=action.label,
        kind=kind,
        icon_url=f"{COMBAT_ICON_ROOT}/{icon}.svg",
        enabled=action.enabled,
        target_id=action.target_id,
        feint_id=action.feint_id,
        ability_id=action.ability_id,
        reason=action.reason,
        catalog=catalog,
        catalog_key=catalog_key,
    )


def _ability_icon(ability_id: str | None) -> str:
    icon_file = BASIC_ABILITY_ICON_FILES.get(str(ability_id or ""))
    if icon_file:
        return f"abilities/{icon_file}"
    return "gift-token"


def _feint_icon_url(feint_id: str | None, purchase_group: str | None) -> str:
    fid = str(feint_id or "")
    if fid and fid in FEINT_SPECIFIC_ICON_FILES:
        return f"{COMBAT_ICON_ROOT}/feints/{fid}.svg"
    group_file = FEINT_GROUP_ICON_FILES.get(str(purchase_group or "basic"))
    if group_file:
        return f"{COMBAT_ICON_ROOT}/feints/{group_file}.svg"
    return f"{COMBAT_ICON_ROOT}/feint.svg"


def _action_catalog(kind: str) -> str | None:
    if kind == "feint":
        return "feints"
    if kind == "ability":
        return "abilities"
    return None


def _action_cost_items(cost: dict[str, int]) -> list[CombatActionCostVM]:
    return [
        CombatActionCostVM(
            token_id=token_id,
            amount=amount,
            icon_url=_token_icon_url(token_id),
            catalog_key=token_id,
        )
        for token_id, amount in cost.items()
    ]


def _feint_cost_tooltip(cost: dict[str, int]) -> str:
    items = _action_cost_items(cost)
    if not items:
        return "Стоимость: токены не требуются"
    return "Стоимость: " + ", ".join(f"{item.token_id.upper()} x{item.amount}" for item in items)


COMBAT_TOKEN_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("tempo", "TEMPO", "token-tempo"),
    ("hit", "HIT", "token-hit"),
    ("crit", "CRIT", "token-crit"),
    ("dodge", "DODGE", "token-dodge"),
    ("parry", "PARRY", "token-parry"),
    ("block", "BLOCK", "token-block"),
    ("pressure", "PRESSURE", "token-pressure"),
    ("blood", "BLOOD", "token-blood"),
    ("gift", "GIFT", "token-gift"),
)


def _token_icon_url(token_id: str) -> str:
    icons = {known_id: icon for known_id, _, icon in COMBAT_TOKEN_CATALOG}
    icon = icons.get(token_id)
    return f"{COMBAT_ICON_ROOT}/{icon}.svg" if icon else f"{COMBAT_ICON_ROOT}/token.svg"


def _token_bar(tokens: dict[str, int]) -> list[CombatTokenVM]:
    known = {
        token_id: CombatTokenVM(
            token_id=token_id,
            value=max(0, tokens.get(token_id, 0) or 0),
            icon_url=f"{COMBAT_ICON_ROOT}/{icon}.svg",
            title=title,
            catalog_key=token_id,
        )
        for token_id, title, icon in COMBAT_TOKEN_CATALOG
    }
    unknown = [
        CombatTokenVM(
            token_id=token_id,
            value=max(0, value or 0),
            icon_url=f"{COMBAT_ICON_ROOT}/token.svg",
            title=token_id.upper(),
            catalog_key=token_id,
        )
        for token_id, value in sorted(tokens.items())
        if token_id not in known
    ]
    return [
        *known.values(),
        *unknown,
    ]


def _avatar_url(actor: CombatActorCardDTO) -> str:
    if actor.avatar_url:
        return actor.avatar_url
    if _is_shadow(actor):
        return DEFAULT_SHADOW_AVATAR_URL
    if actor.actor_type == "monster":
        return DEFAULT_MONSTER_AVATAR_URL
    return DEFAULT_PLAYER_AVATAR_URL


def _is_shadow(actor: CombatActorCardDTO) -> bool:
    return actor.actor_id.startswith("-") or actor.actor_type == "shadow" or actor.name.lower().startswith("shadow ")


def _effect_kind(effect_id: str) -> str:
    key = effect_id.lower()
    if "bleed" in key or "blood" in key:
        return "bleeding"
    if "poison" in key or "venom" in key:
        return "poison"
    if "burn" in key or "fire" in key:
        return "burn"
    if any(token in key for token in ("stun", "control", "root", "sleep", "knockdown")):
        return "stun"
    if key.startswith("prep_") or "preparation" in key:
        return "preparation"
    if key.startswith("debuff_") or "debuff" in key:
        return "debuff"
    if key.startswith("buff_") or "buff" in key:
        return "buff"
    if "heal" in key or "regen" in key:
        return "heal"
    if "shield" in key or "guard" in key:
        return "shield"
    return "effect"


def _effect_title(effect_id: str, frame_kind: str) -> str:
    titles = {
        "bleeding": "Кровотечение",
        "poison": "Яд",
        "burn": "Ожог",
        "stun": "Оглушение",
        "shield": "Защита",
        "preparation": "Подготовка",
        "buff": "Усиление",
        "debuff": "Ослабление",
        "heal": "Восстановление",
        "effect": "Эффект",
    }
    return titles.get(frame_kind, effect_id)


def _effect_icon(frame_kind: str) -> str:
    return {
        "bleeding": "bleeding",
        "poison": "poison",
        "burn": "burn",
        "stun": "stun",
        "shield": "shield",
        "preparation": "feint",
        "buff": "token",
        "debuff": "token",
        "heal": "token",
        "effect": "token",
    }.get(frame_kind, "token")
