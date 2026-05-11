from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.shared.schemas.combat import (
        CombatActionOptionDTO,
        CombatActorCardDTO,
        CombatDashboardDTO,
        CombatEffectBadgeDTO,
        CombatEventDTO,
        CombatFeintOptionDTO,
        CombatResultDTO,
    )

DEFAULT_PLAYER_AVATAR_URL = "/static/images/avatars/silhouette_m.png"
DEFAULT_SHADOW_AVATAR_URL = "/static/images/avatars/veil4.png"
DEFAULT_MONSTER_AVATAR_URL = "/static/images/avatars/silhouette_f.png"
COMBAT_ICON_ROOT = "/static/images/ui/combat-icons"


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


class CombatActorPanelVM(BaseModel):
    actor_id: str
    name: str
    actor_type: str
    team: str
    avatar_url: str
    exchange_counter: int = 0
    is_shadow: bool = False
    is_ai: bool = False
    is_dead: bool = False
    is_target: bool = False
    vitals: CombatVitalsVM
    effects: list[CombatEffectBadgeVM] = Field(default_factory=list)
    quick_belt: list[CombatQuickSlotVM] = Field(default_factory=list)


class CombatRosterRowVM(BaseModel):
    actor_id: str
    name: str
    hp_current: int
    hp_max: int
    hp_percent: int
    target_queue_size: int = 0
    pending_action_count: int = 0
    is_target: bool = False
    is_dead: bool = False
    queue_state: str = "NO_DATA"
    queue_indicator: str = "unknown"


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
    allied_team: CombatTeamSummaryVM
    enemy_team: CombatTeamSummaryVM
    primary_attack: CombatActionVM | None = None
    feint_options: list[CombatActionVM] = Field(default_factory=list)
    ability_options: list[CombatActionVM] = Field(default_factory=list)
    token_bar: list[CombatTokenVM] = Field(default_factory=list)
    log_lines: list[CombatLogLineVM] = Field(default_factory=list)
    log_turns: list[CombatLogTurnVM] = Field(default_factory=list)
    log_total: int = 0
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


def build_combat_screen_from_result_vm(result: CombatResultDTO) -> CombatScreenVM:
    from src.shared.schemas.combat import CombatDashboardDTO

    actors = result.actors if isinstance(result.actors, dict) else {}
    teams = result.teams if isinstance(result.teams, dict) else {}
    report = result.report if isinstance(result.report, dict) else {}
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    viewer_team = _optional_str(metadata.get("viewer_team")) or _viewer_team(result.char_id, teams)
    hero_id = str(result.char_id)
    if hero_id not in actors:
        hero_id = _first_actor_id(teams.get(viewer_team) if viewer_team else None) or hero_id
    enemy_team = _first_enemy_team(teams, viewer_team)

    hero = _result_actor_card(hero_id, actors.get(hero_id), fallback_team=viewer_team or "team_1")
    ally_ids = (
        [str(actor_id) for actor_id in teams.get(viewer_team, []) if viewer_team and str(actor_id) != hero.actor_id]
        if isinstance(teams.get(viewer_team), list)
        else []
    )
    enemy_ids = (
        [str(actor_id) for actor_id in teams.get(enemy_team, [])] if isinstance(teams.get(enemy_team), list) else []
    )
    enemies = [
        _result_actor_card(actor_id, actors.get(actor_id), fallback_team=enemy_team or "team_2", is_target=index == 0)
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


def build_combat_screen_vm(dashboard: CombatDashboardDTO) -> CombatScreenVM:
    primary_attack, feints, abilities = _split_actions(dashboard.available_actions, dashboard.hero.feints)
    allied_actors = [dashboard.hero, *dashboard.allies]
    enemy_actors = dashboard.enemies or ([dashboard.target] if dashboard.target else [])
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
        enemies=[_roster_row(actor) for actor in dashboard.enemies],
        allied_team=_team_summary("ALLIES", allied_actors),
        enemy_team=_team_summary("ENEMIES", enemy_actors),
        primary_attack=primary_attack,
        feint_options=feints,
        ability_options=abilities,
        token_bar=_token_bar(dashboard.hero.tokens),
        log_lines=[_log_line(event) for event in dashboard.events_delta.events[-8:]],
        log_turns=_log_turns(dashboard),
        log_total=dashboard.log_total,
        winner_team=dashboard.winner_team,
    )


def _result_actor_card(
    actor_id: str,
    value: object,
    *,
    fallback_team: str,
    is_target: bool = False,
) -> object:
    from src.shared.schemas.combat import CombatActorCardDTO, CombatActorVitalsDTO

    data = value if isinstance(value, dict) else {}
    vitals = data.get("vitals_final") if isinstance(data.get("vitals_final"), dict) else {}
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


def _viewer_team(char_id: int, teams: dict[str, object]) -> str | None:
    actor_id = str(char_id)
    for team, members in teams.items():
        if isinstance(members, list) and actor_id in {str(member) for member in members}:
            return str(team)
    return None


def _first_enemy_team(teams: dict[str, object], viewer_team: str | None) -> str | None:
    for team, members in teams.items():
        if team != viewer_team and isinstance(members, list) and members:
            return str(team)
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

    teams = result.teams if isinstance(result.teams, dict) else {}
    if teams:
        result_teams = [
            _result_team_from_member_ids(
                str(team),
                [str(member) for member in members],
                actors,
                _team_outcome_for_result(str(team), result),
            )
            for team, members in teams.items()
            if isinstance(members, list)
        ]
        return _order_result_teams(result_teams, result)

    grouped: dict[str, list[str]] = {}
    for actor_id, value in actors.items():
        data = value if isinstance(value, dict) else {}
        grouped.setdefault(str(data.get("team") or "neutral"), []).append(str(actor_id))
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
    vitals = data.get("vitals_final") if isinstance(data.get("vitals_final"), dict) else {}
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
    viewer_team = _optional_str(metadata.get("viewer_team")) or _viewer_team(result.char_id, result.teams)
    return sorted(teams, key=lambda team: (team.team != viewer_team, team.team))


def _team_outcome_for_result(team: str, result: CombatResultDTO) -> str:
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    winner = _optional_str(metadata.get("winner"))
    if winner == "draw":
        return "draw"
    if winner:
        return "victory" if team == winner else "defeat"
    viewer_team = _optional_str(metadata.get("viewer_team")) or _viewer_team(result.char_id, result.teams)
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
    source = _model_dict(getattr(event, "source", None)) or _event_data_dict(event.data, "source")
    target = _model_dict(getattr(event, "target", None)) or _event_data_dict(event.data, "target")
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


def _log_turns(dashboard: CombatDashboardDTO) -> list[CombatLogTurnVM]:
    turns = dashboard.events_delta.turns
    if not turns:
        grouped: dict[int | None, list[CombatEventDTO]] = {}
        for event in dashboard.events_delta.events[-8:]:
            grouped.setdefault(_event_data_int(event, "global_turn"), []).append(event)
        return [
            CombatLogTurnVM(
                global_turn=turn,
                title=f"Ход {turn}" if turn is not None else "Ход NO_DATA",
                lines=[_log_line(event) for event in events],
            )
            for turn, events in grouped.items()
        ]

    return [
        CombatLogTurnVM(
            global_turn=turn.global_turn,
            title=turn.title,
            lines=[_log_line(event) for event in turn.entries],
        )
        for turn in turns[-8:]
    ]


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


def _model_dict(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json")
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
        exchange_counter=actor.exchange_counter,
        is_shadow=_is_shadow(actor),
        is_ai=actor.is_ai,
        is_dead=actor.is_dead,
        is_target=actor.is_target,
        vitals=_vitals(actor),
        effects=[_effect_badge(effect, actor.exchange_counter) for effect in actor.active_effects],
        quick_belt=_quick_belt(actor.quick_items) if include_belt else [],
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
        hp_current=vitals.hp_current,
        hp_max=vitals.hp_max,
        hp_percent=vitals.hp_percent,
        target_queue_size=actor.target_queue_size,
        pending_action_count=sum(actor.pending_actions.values()),
        is_target=actor.is_target,
        is_dead=actor.is_dead,
        queue_state=_queue_state(actor),
        queue_indicator=_queue_indicator(actor),
    )


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
    title = _effect_title(effect.effect_id, frame_kind)
    impact_text = _effect_impact_text(effect.impact)
    duration = str(remaining) if remaining is not None else None
    tooltip_parts = [title]
    if remaining is not None:
        tooltip_parts.append(_turns_left_text(remaining))
    if impact_text:
        tooltip_parts.append(impact_text)
    return CombatEffectBadgeVM(
        effect_id=effect.effect_id,
        icon_url=f"{COMBAT_ICON_ROOT}/{_effect_icon(frame_kind)}.svg",
        frame_kind=frame_kind,
        duration_text=duration,
        title=title,
        tooltip=" // ".join(tooltip_parts),
        catalog_key=effect.effect_id,
    )


def _effect_remaining(expires_at_exchange: int | None, exchange_counter: int) -> int | None:
    if expires_at_exchange is None:
        return None
    return max(1, int(expires_at_exchange) - int(exchange_counter) + 1)


def _turns_left_text(turns: int) -> str:
    if turns == 1:
        return "остался 1 ход"
    if 2 <= turns <= 4:
        return f"осталось {turns} хода"
    return f"осталось {turns} ходов"


def _effect_impact_text(impact: dict[str, Any]) -> str:
    hp = impact.get("hp")
    if hp in (None, ""):
        return ""
    try:
        value = int(hp)
    except (TypeError, ValueError):
        return f"{hp} HP за ход"
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
    if actor.is_target:
        return "current"
    if sum(actor.pending_actions.values()):
        return "locked"
    if actor.target_queue_size:
        return "ready"
    return "unknown"


def _split_actions(
    actions: list[CombatActionOptionDTO],
    feint_hand: list[CombatFeintOptionDTO],
) -> tuple[CombatActionVM | None, list[CombatActionVM], list[CombatActionVM]]:
    primary: CombatActionVM | None = None
    abilities: list[CombatActionVM] = []

    for action in actions:
        if action.action == "exchange":
            primary = _action_vm(action, kind="attack", icon="attack")
        elif action.ability_id:
            abilities.append(_action_vm(action, kind="ability", icon="gift-token"))

    feints = [
        CombatActionVM(
            id=feint.feint_id,
            label=feint.feint_id,
            kind="feint",
            icon_url=f"{COMBAT_ICON_ROOT}/feint.svg",
            enabled=primary.enabled if primary else False,
            target_id=primary.target_id if primary else None,
            feint_id=feint.feint_id,
            catalog="feints",
            catalog_key=feint.feint_id,
            pinned=feint.pinned,
            cost=feint.cost,
            cost_items=_action_cost_items(feint.cost),
        )
        for feint in feint_hand
    ]
    return primary, feints, abilities


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


def _action_catalog(kind: str) -> str | None:
    if kind == "feint":
        return "feints"
    if kind == "ability":
        return "abilities"
    return None


def _action_cost_items(cost: dict[str, int]) -> list[CombatActionCostVM]:
    return [
        CombatActionCostVM(
            token_id=str(token_id),
            amount=int(amount),
            icon_url=_token_icon_url(str(token_id)),
            catalog_key=str(token_id),
        )
        for token_id, amount in cost.items()
    ]


COMBAT_TOKEN_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("tempo", "TEMPO", "token-tempo"),
    ("hit", "HIT", "token-hit"),
    ("crit", "CRIT", "token-crit"),
    ("dodge", "DODGE", "token-dodge"),
    ("parry", "PARRY", "token-parry"),
    ("block", "BLOCK", "token-block"),
    ("counter", "COUNTER", "token-counter"),
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
            value=max(0, int(tokens.get(token_id, 0) or 0)),
            icon_url=f"{COMBAT_ICON_ROOT}/{icon}.svg",
            title=title,
            catalog_key=token_id,
        )
        for token_id, title, icon in COMBAT_TOKEN_CATALOG
    }
    unknown = [
        CombatTokenVM(
            token_id=token_id,
            value=max(0, int(value or 0)),
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
    if _is_shadow(actor):
        return DEFAULT_SHADOW_AVATAR_URL
    if actor.avatar_url:
        return actor.avatar_url
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
    if "stun" in key or "control" in key or "root" in key:
        return "stun"
    if "shield" in key or "guard" in key:
        return "shield"
    return "shield"


def _effect_title(effect_id: str, frame_kind: str) -> str:
    titles = {
        "bleeding": "Кровотечение",
        "poison": "Яд",
        "burn": "Ожог",
        "stun": "Оглушение",
        "shield": "Защита",
    }
    return titles.get(frame_kind, effect_id)


def _effect_icon(frame_kind: str) -> str:
    return {
        "bleeding": "bleeding",
        "poison": "poison",
        "burn": "burn",
        "stun": "stun",
        "shield": "shield",
    }.get(frame_kind, "shield")
