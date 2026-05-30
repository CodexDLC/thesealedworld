"""Deterministic feature extractor from ActorSnapshot + BattleContext.

Pure read: stats are materialised through :class:`StatsEngine.ensure_stats`
but no snapshot fields are mutated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.backend.features.combat.dto.actor import ActorSnapshot  # noqa: TC001
from src.backend.features.combat.dto.ai_memory_dto import AiMemoryDTO  # noqa: TC001
from src.backend.features.combat.runtime.ai.ai_memory import defence_rate
from src.backend.features.combat.runtime.ai.preparations import extract_preparations
from src.backend.features.combat.runtime.ai.team_awareness import TeamState  # noqa: TC001
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
    my_preparations: frozenset[str] = frozenset()
    # Best-effort awareness of teammate intents already committed this step.
    # Empty when no battle context or empty moves_cache.
    allies_targets: dict[str, int] = field(default_factory=dict)
    allies_pending_control_targets: frozenset[str] = frozenset()
    # Cross-turn memory snapshots — fed from BattleContext.ai_memory.
    last_target_id: str | None = None
    recently_used_feints: frozenset[str] = frozenset()

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
    active_preparations: frozenset[str] = frozenset()
    # Observed defence rates from cross-turn memory: fraction of recent
    # exchanges that resolved as each outcome. 0.0 when no memory yet.
    observed_parry_rate: float = 0.0
    observed_dodge_rate: float = 0.0
    observed_block_rate: float = 0.0


def extract_self(
    bot: ActorSnapshot,
    alive_enemy_count: int,
    team_state: TeamState | None = None,
    memory: AiMemoryDTO | None = None,
) -> SelfObservation:
    """Build a :class:`SelfObservation` for the acting bot.

    ``team_state`` is optional so callers that only have a single bot/target
    pair (no battle context) can still build an observation. It is computed
    once per turn in :meth:`MonsterCombatBrain.decide_turn` and threaded
    through :meth:`decide_exchange` to keep extraction work O(turn).
    """
    StatsEngine.ensure_stats(bot)
    meta = bot.meta
    if team_state is None:
        allies_targets: dict[str, int] = {}
        allies_pending_control: frozenset[str] = frozenset()
    else:
        allies_targets = dict(team_state.allies_targets)
        allies_pending_control = team_state.allies_pending_control_targets
    if memory is None:
        last_target_id: str | None = None
        recently_used_feints: frozenset[str] = frozenset()
    else:
        last_target_id = memory.last_target_id
        recently_used_feints = frozenset(memory.feints_used)
    return SelfObservation(
        hp_pct=_safe_pct(meta.hp, meta.max_hp),
        stamina_pct=_safe_pct(meta.stamina, meta.max_stamina),
        en_pct=_safe_pct(meta.en, meta.max_en),
        tokens=dict(meta.tokens or {}),
        alive_enemy_count=int(alive_enemy_count),
        my_preparations=extract_preparations(bot),
        allies_targets=allies_targets,
        allies_pending_control_targets=allies_pending_control,
        last_target_id=last_target_id,
        recently_used_feints=recently_used_feints,
    )


def extract_target(target: ActorSnapshot, memory: AiMemoryDTO | None = None) -> TargetObservation:
    """Build a :class:`TargetObservation` for one target snapshot.

    ``memory`` is the target's :class:`AiMemoryDTO` from ``BattleContext.ai_memory``
    (or ``None`` if unavailable). When present, observed defence rates are
    derived from the rolling window of past outcomes.
    """
    StatsEngine.ensure_stats(target)
    mods = target.stats.mods if target.stats is not None else None
    armor = float(getattr(mods, "armor", 0.0) or 0.0) if mods is not None else 0.0
    phys_res = float(getattr(mods, "physical_resistance", 0.0) or 0.0) if mods is not None else 0.0
    evasion = _effective_evasion(mods)
    parry = float(getattr(mods, "parry", 0.0) or 0.0) if mods is not None else 0.0
    block = float(getattr(mods, "block", 0.0) or 0.0) if mods is not None else 0.0
    counter = float(getattr(mods, "counter_attack_chance", 0.0) or 0.0) if mods is not None else 0.0

    has_bleed, has_control = _status_flags(target)
    hp_pct = _safe_pct(target.meta.hp, target.meta.max_hp)
    finishable = hp_pct <= 0.25

    if memory is None:
        observed_parry = observed_dodge = observed_block = 0.0
    else:
        observed_parry = defence_rate(memory, "parry")
        observed_dodge = defence_rate(memory, "dodge")
        observed_block = defence_rate(memory, "block")
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
        active_preparations=extract_preparations(target),
        observed_parry_rate=observed_parry,
        observed_dodge_rate=observed_dodge,
        observed_block_rate=observed_block,
    )


def _effective_evasion(mods: Any) -> float:
    if mods is None:
        return 0.0
    evasion = float(getattr(mods, "evasion", 0.0) or 0.0)
    dodge_cap = float(getattr(mods, "dodge_cap", 1.0) or 0.0)
    return max(0.0, min(evasion, dodge_cap))


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
