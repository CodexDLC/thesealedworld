"""Per-session cross-turn memory for combat AI.

Memory lives on :attr:`BattleContext.ai_memory` and survives worker restarts
through the standard battle-session serialisation. It is reset when the
battle ends — there is no global "knows everything about this player"
state.

Three signal kinds are recorded:

* **Defence outcomes** (per actor as defender): a rolling list of recent
  resolver outcomes (``hit/crit/miss/dodge/parry/block``). Derived rates
  feed the scorer's observed-defence branches so the AI can adapt when a
  player's *behaviour* outpaces what raw stats predict.
* **Feints used** (per actor as attacker): a rolling list of recently
  chosen feint ids — used to penalise monotonous repetition.
* **Last target id** (per attacker): supports a small sticky-focus bias so
  the bot does not flit between targets without reason.

The recording hook lives in the combat executor, called once per resolved
exchange. There is exactly one writer per (attacker, defender) pair per
exchange; the AI runtime is read-only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.ai_memory_dto import AiMemoryDTO

if TYPE_CHECKING:
    from src.backend.features.combat.dto.session import BattleContext

# Rolling window sizes — kept small so the signal reflects *recent* behaviour
# and doesn't keep punishing a player for one early parry forever.
DEFENCE_MEMORY_WINDOW: int = 8
FEINT_MEMORY_WINDOW: int = 6

_DEFENCE_OUTCOMES: frozenset[str] = frozenset({"hit", "crit", "miss", "dodge", "parry", "block"})

# Re-exported so the runtime can keep ``from .ai_memory import AiMemoryDTO``.
__all__ = [
    "AiMemoryDTO",
    "DEFENCE_MEMORY_WINDOW",
    "FEINT_MEMORY_WINDOW",
    "defence_rate",
    "get_memory",
    "record_exchange_outcome",
]


def get_memory(battle: BattleContext | None, actor_id: str) -> AiMemoryDTO:
    """Read the actor's memory entry, returning an empty DTO when absent.

    Read-only: never lazily creates an entry. The recording hook is the only
    writer.
    """
    if battle is None:
        return AiMemoryDTO()
    entry = battle.ai_memory.get(str(actor_id))
    if entry is None:
        return AiMemoryDTO()
    return entry


def record_exchange_outcome(
    battle: BattleContext | None,
    attacker_id: str | None,
    defender_id: str | None,
    outcome: str,
    feint_id: str | None,
) -> None:
    """Record one resolved exchange into both actors' memory entries.

    Defender's :attr:`AiMemoryDTO.defence_outcomes` gains the outcome when
    it belongs to the resolver-shared vocabulary. Attacker's
    :attr:`AiMemoryDTO.feints_used` gains the feint id when one was used,
    and their :attr:`AiMemoryDTO.last_target_id` is updated regardless.
    Silent no-op when ``battle`` or either id is missing — callers must not
    have to guard the call site.
    """
    if battle is None or attacker_id is None or defender_id is None:
        return

    if outcome in _DEFENCE_OUTCOMES:
        defender_entry = _ensure_entry(battle, defender_id)
        defender_entry.defence_outcomes.append(outcome)
        _truncate(defender_entry.defence_outcomes, DEFENCE_MEMORY_WINDOW)

    attacker_entry = _ensure_entry(battle, attacker_id)
    attacker_entry.last_target_id = str(defender_id)
    if feint_id:
        attacker_entry.feints_used.append(str(feint_id))
        _truncate(attacker_entry.feints_used, FEINT_MEMORY_WINDOW)


def defence_rate(memory: AiMemoryDTO, outcome: str) -> float:
    """Fraction of recent exchanges where the defender produced ``outcome``.

    Returns ``0.0`` for an empty window. The denominator is the window size,
    not just defensive outcomes — a target with one parry in eight exchanges
    has a rate of ``0.125``.
    """
    if not memory.defence_outcomes:
        return 0.0
    matches = sum(1 for o in memory.defence_outcomes if o == outcome)
    return matches / len(memory.defence_outcomes)


def _ensure_entry(battle: BattleContext, actor_id: str) -> AiMemoryDTO:
    key = str(actor_id)
    entry = battle.ai_memory.get(key)
    if entry is None:
        entry = AiMemoryDTO()
        battle.ai_memory[key] = entry
    return entry


def _truncate(buffer: list[str], window: int) -> None:
    overflow = len(buffer) - window
    if overflow > 0:
        del buffer[:overflow]
