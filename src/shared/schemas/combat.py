from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CombatActionKind = Literal["exchange", "instant", "item", "system"]


class CombatCatalogLinksDTO(BaseModel):
    """Stable catalog entry points for client-side text and descriptions."""

    bootstrap: str = "/game/catalog/bootstrap"
    abilities: str = "/game/catalog/bootstrap#abilities"
    feints: str = "/game/catalog/bootstrap#feints"
    effects: str = "/game/catalog/bootstrap#effects"
    triggers: str = "/game/catalog/bootstrap#triggers"
    gifts: str = "/game/catalog/bootstrap#gifts"


class CombatActorVitalsDTO(BaseModel):
    hp_current: int = 0
    hp_max: int = 0
    energy_current: int = 0
    energy_max: int = 0
    tactics: int = 0


class CombatEffectBadgeDTO(BaseModel):
    uid: str | None = None
    effect_id: str
    expires_at_exchange: int | None = None
    catalog_ref: str = "effects"
    impact: dict[str, Any] = Field(default_factory=dict)


class CombatAbilityBadgeDTO(BaseModel):
    uid: str | None = None
    ability_id: str
    expires_at_exchange: int | None = None
    catalog_ref: str = "abilities"
    impact: dict[str, Any] = Field(default_factory=dict)


class CombatFeintOptionDTO(BaseModel):
    feint_id: str
    cost: dict[str, int] = Field(default_factory=dict)
    catalog_ref: str = "feints"


class CombatActorCardDTO(BaseModel):
    actor_id: str
    name: str
    actor_type: str
    team: str
    avatar_url: str | None = None
    is_ai: bool = False
    is_dead: bool = False
    is_target: bool = False
    vitals: CombatActorVitalsDTO = Field(default_factory=CombatActorVitalsDTO)
    weapon_type: str | None = None
    tokens: dict[str, int] = Field(default_factory=dict)
    active_effects: list[CombatEffectBadgeDTO] = Field(default_factory=list)
    active_abilities: list[CombatAbilityBadgeDTO] = Field(default_factory=list)
    feints: list[CombatFeintOptionDTO] = Field(default_factory=list)
    catalog_links: CombatCatalogLinksDTO = Field(default_factory=CombatCatalogLinksDTO)


class CombatActionOptionDTO(BaseModel):
    action: CombatActionKind
    label: str
    enabled: bool = True
    target_id: str | None = None
    ability_id: str | None = None
    item_id: int | None = None
    feint_id: str | None = None
    catalog_ref: str | None = None
    reason: str | None = None


class CombatEventDTO(BaseModel):
    type: str = "log"
    text: str | None = None
    timestamp: float | None = None
    tags: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class CombatDeltaDTO(BaseModel):
    events: list[CombatEventDTO] = Field(default_factory=list)
    log_cursor: int | None = None


class CombatDashboardDTO(BaseModel):
    session_id: str
    turn_number: int = 0
    status: Literal["active", "waiting", "finished", "spectating"] = "active"
    hero: CombatActorCardDTO
    target: CombatActorCardDTO | None = None
    allies: list[CombatActorCardDTO] = Field(default_factory=list)
    enemies: list[CombatActorCardDTO] = Field(default_factory=list)
    active_effects: list[CombatEffectBadgeDTO] = Field(default_factory=list)
    feints: list[CombatFeintOptionDTO] = Field(default_factory=list)
    available_actions: list[CombatActionOptionDTO] = Field(default_factory=list)
    events_delta: CombatDeltaDTO = Field(default_factory=CombatDeltaDTO)
    catalog_links: CombatCatalogLinksDTO = Field(default_factory=CombatCatalogLinksDTO)
    winner_team: str | None = None


class CombatRegisterMoveRequestDTO(BaseModel):
    action: Literal["attack", "exchange", "use_skill", "cast", "instant", "use_item", "leave", "surrender", "flee"] = (
        "attack"
    )
    target_id: int | str | list[int] | None = None
    ability_id: str | None = None
    skill_id: str | None = None
    item_id: int | None = None
    feint_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CombatLogDTO(BaseModel):
    session_id: str
    entries: list[CombatEventDTO] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total: int = 0
