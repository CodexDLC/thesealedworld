"""Deterministic feature extractor from ActorSnapshot + BattleContext.

Pure read: stats are materialised through :class:`StatsEngine.ensure_stats`
but no snapshot fields are mutated.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.backend.features.combat.dto.actor import ActorSnapshot  # noqa: TC001
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine


def _safe_pct(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return max(0.0, min(1.0, value / max_value))


@dataclass(frozen=True)
class SelfObservation:
    """Features describing the acting bot."""

    hp_pct: float
    stamina_pct: float
    en_pct: float
    tokens: dict[str, int]
    alive_enemy_count: int

    @property
    def low_hp(self) -> bool:
        return self.hp_pct <= 0.3

    @property
    def low_stamina(self) -> bool:
        return self.stamina_pct <= 0.3


@dataclass(frozen=True)
class TargetObservation:
    """Features describing one candidate target."""

    target_id: str
    hp_pct: float
    armor: float
    physical_resistance: float
    evasion: float
    parry: float
    block: float
    counter_attack_chance: float
    has_bleed: bool
    has_control: bool
    finishable: bool


def extract_self(bot: ActorSnapshot, alive_enemy_count: int) -> SelfObservation:
    """Build a :class:`SelfObservation` for the acting bot."""
    StatsEngine.ensure_stats(bot)
    meta = bot.meta
    return SelfObservation(
        hp_pct=_safe_pct(meta.hp, meta.max_hp),
        stamina_pct=_safe_pct(meta.stamina, meta.max_stamina),
        en_pct=_safe_pct(meta.en, meta.max_en),
        tokens=dict(meta.tokens or {}),
        alive_enemy_count=int(alive_enemy_count),
    )


def extract_target(target: ActorSnapshot) -> TargetObservation:
    """Build a :class:`TargetObservation` for one target snapshot."""
    StatsEngine.ensure_stats(target)
    mods = target.stats.mods if target.stats is not None else None
    armor = float(getattr(mods, "armor", 0.0) or 0.0) if mods is not None else 0.0
    phys_res = float(getattr(mods, "physical_resistance", 0.0) or 0.0) if mods is not None else 0.0
    evasion = float(getattr(mods, "evasion", 0.0) or 0.0) if mods is not None else 0.0
    parry = float(getattr(mods, "parry", 0.0) or 0.0) if mods is not None else 0.0
    block = float(getattr(mods, "block", 0.0) or 0.0) if mods is not None else 0.0
    counter = float(getattr(mods, "counter_attack_chance", 0.0) or 0.0) if mods is not None else 0.0

    has_bleed, has_control = _status_flags(target)
    hp_pct = _safe_pct(target.meta.hp, target.meta.max_hp)
    finishable = hp_pct <= 0.25

    return TargetObservation(
        target_id=str(target.meta.id),
        hp_pct=hp_pct,
        armor=armor,
        physical_resistance=phys_res,
        evasion=evasion,
        parry=parry,
        block=block,
        counter_attack_chance=counter,
        has_bleed=has_bleed,
        has_control=has_control,
        finishable=finishable,
    )


_CONTROL_EFFECT_HINTS = ("stun", "control", "root", "freeze", "knockdown", "fear")


def _status_flags(target: ActorSnapshot) -> tuple[bool, bool]:
    has_bleed = False
    has_control = False
    for effect in target.statuses.effects:
        effect_id = str(effect.effect_id or "").lower()
        if "bleed" in effect_id:
            has_bleed = True
        if effect.control is not None or any(hint in effect_id for hint in _CONTROL_EFFECT_HINTS):
            has_control = True
    return has_bleed, has_control
