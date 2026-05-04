from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.shared.schemas.combat import (
        CombatActionOptionDTO,
        CombatActorCardDTO,
        CombatDashboardDTO,
        CombatEffectBadgeDTO,
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


class CombatVitalsVM(BaseModel):
    hp_current: int
    hp_max: int
    hp_percent: int
    energy_current: int
    energy_max: int
    energy_percent: int
    tactics: int


class CombatQuickSlotVM(BaseModel):
    slot_index: int
    is_empty: bool = True
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
    is_target: bool = False
    is_dead: bool = False
    queue_state: str = "NO_DATA"
    queue_indicator: str = "unknown"


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


class CombatTokenVM(BaseModel):
    token_id: str
    value: int
    icon_url: str
    title: str
    description: str = "NO_DATA"


class CombatLogLineVM(BaseModel):
    text: str
    kind: str = "log"


class CombatScreenVM(BaseModel):
    session_id: str
    status: str
    turn_number: int
    hero: CombatActorPanelVM
    target: CombatActorPanelVM | None
    allies: list[CombatRosterRowVM] = Field(default_factory=list)
    enemies: list[CombatRosterRowVM] = Field(default_factory=list)
    primary_attack: CombatActionVM | None = None
    feint_options: list[CombatActionVM] = Field(default_factory=list)
    ability_options: list[CombatActionVM] = Field(default_factory=list)
    token_bar: list[CombatTokenVM] = Field(default_factory=list)
    log_lines: list[CombatLogLineVM] = Field(default_factory=list)
    winner_team: str | None = None


def build_combat_screen_vm(dashboard: CombatDashboardDTO) -> CombatScreenVM:
    primary_attack, feints, abilities = _split_actions(dashboard.available_actions, dashboard.hero.feints)
    return CombatScreenVM(
        session_id=dashboard.session_id,
        status=dashboard.status,
        turn_number=dashboard.turn_number,
        hero=_actor_panel(dashboard.hero, include_belt=True),
        target=_actor_panel(dashboard.target, include_belt=False) if dashboard.target else None,
        allies=[_roster_row(actor) for actor in dashboard.allies],
        enemies=[_roster_row(actor) for actor in dashboard.enemies],
        primary_attack=primary_attack,
        feint_options=feints,
        ability_options=abilities,
        token_bar=_token_bar(dashboard.hero.tokens),
        log_lines=[
            CombatLogLineVM(text=event.text or "NO_DATA", kind=event.type)
            for event in dashboard.events_delta.events[-8:]
        ],
        winner_team=dashboard.winner_team,
    )


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
        quick_belt=_quick_belt() if include_belt else [],
    )


def _vitals(actor: CombatActorCardDTO) -> CombatVitalsVM:
    hp_max = max(actor.vitals.hp_max, 1)
    energy_max = max(actor.vitals.energy_max, 1)
    return CombatVitalsVM(
        hp_current=actor.vitals.hp_current,
        hp_max=hp_max,
        hp_percent=max(0, min(100, round(actor.vitals.hp_current / hp_max * 100))),
        energy_current=actor.vitals.energy_current,
        energy_max=energy_max,
        energy_percent=max(0, min(100, round(actor.vitals.energy_current / energy_max * 100))),
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
        is_target=actor.is_target,
        is_dead=actor.is_dead,
        queue_indicator="current" if actor.is_target else "unknown",
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
    )


def _quick_belt() -> list[CombatQuickSlotVM]:
    return [CombatQuickSlotVM(slot_index=index) for index in range(1, 9)]


def _split_actions(
    actions: list[CombatActionOptionDTO],
    feint_hand: list[CombatFeintOptionDTO],
) -> tuple[CombatActionVM | None, list[CombatActionVM], list[CombatActionVM]]:
    feint_ids = {feint.feint_id for feint in feint_hand}
    primary: CombatActionVM | None = None
    feints: list[CombatActionVM] = []
    abilities: list[CombatActionVM] = []

    for action in actions:
        if action.action == "exchange":
            primary = _action_vm(action, kind="attack", icon="attack")
        elif action.feint_id or (action.action == "instant" and action.label in feint_ids):
            feints.append(_action_vm(action, kind="feint", icon="feint"))
        elif action.ability_id:
            abilities.append(_action_vm(action, kind="ability", icon="gift-token"))

    return primary, feints, abilities


def _action_vm(action: CombatActionOptionDTO, *, kind: str, icon: str) -> CombatActionVM:
    action_id = action.feint_id or action.ability_id or action.action
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
    )


def _token_bar(tokens: dict[str, int]) -> list[CombatTokenVM]:
    return [
        CombatTokenVM(
            token_id=token_id,
            value=value,
            icon_url=f"{COMBAT_ICON_ROOT}/{'gift-token' if token_id == 'gift' else 'token'}.svg",  # nosec B105
            title=token_id,
        )
        for token_id, value in sorted(tokens.items())
        if value
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
