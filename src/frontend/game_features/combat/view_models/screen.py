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


def _actor_panel(actor: CombatActorCardDTO, *, include_belt: bool) -> CombatActorPanelVM:
    return CombatActorPanelVM(
        actor_id=actor.actor_id,
        name=actor.name,
        actor_type=actor.actor_type,
        team=actor.team,
        avatar_url=_avatar_url(actor),
        is_shadow=_is_shadow(actor),
        is_ai=actor.is_ai,
        is_dead=actor.is_dead,
        is_target=actor.is_target,
        vitals=_vitals(actor),
        effects=[_effect_badge(effect) for effect in actor.active_effects],
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


def _effect_badge(effect: CombatEffectBadgeDTO) -> CombatEffectBadgeVM:
    frame_kind = _effect_kind(effect.effect_id)
    duration = str(effect.expires_at_exchange) if effect.expires_at_exchange is not None else None
    return CombatEffectBadgeVM(
        effect_id=effect.effect_id,
        icon_url=f"{COMBAT_ICON_ROOT}/{_effect_icon(frame_kind)}.svg",
        frame_kind=frame_kind,
        duration_text=duration,
        title=effect.effect_id,
        catalog_key=effect.effect_id,
    )


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


def _effect_icon(frame_kind: str) -> str:
    return {
        "bleeding": "bleeding",
        "poison": "poison",
        "burn": "burn",
        "stun": "stun",
        "shield": "shield",
    }.get(frame_kind, "shield")
