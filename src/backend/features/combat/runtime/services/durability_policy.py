from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CombatDurabilityDamageRequest:
    char_id: int
    amount: float
    scope: str
    reason: str
    source: str = "combat_finalization"
    combat_id: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_payload(self) -> dict[str, Any]:
        return {
            "char_id": self.char_id,
            "amount": self.amount,
            "scope": self.scope,
            "reason": self.reason,
            "source": self.source,
            "combat_id": self.combat_id,
            "idempotency_key": self.idempotency_key,
            "metadata": self.metadata,
        }


class CombatDurabilityPolicy:
    """Maps combat finalization facts to inventory durability consequences."""

    SURVIVED_COMBAT_DAMAGE = 0.1
    DEATH_DAMAGE = 2.0

    def resolve(self, finalization: dict[str, Any]) -> list[CombatDurabilityDamageRequest]:
        if self._is_arena(finalization):
            return []

        combat_id = str(finalization.get("combat_id") or "")
        requests: list[CombatDurabilityDamageRequest] = []
        for actor in self._player_actors(finalization):
            char_id = actor.get("char_id")
            if not isinstance(char_id, int):
                continue
            is_dead = bool(actor.get("is_dead"))
            reason = "death" if is_dead else "combat_completed"
            amount = self.DEATH_DAMAGE if is_dead else self.SURVIVED_COMBAT_DAMAGE
            scope = "all_carried" if is_dead else "equipped"
            requests.append(
                CombatDurabilityDamageRequest(
                    char_id=char_id,
                    amount=amount,
                    scope=scope,
                    reason=reason,
                    combat_id=combat_id or None,
                    idempotency_key=f"combat:{combat_id}:durability:{char_id}:{reason}" if combat_id else None,
                    metadata={
                        "winner_team": finalization.get("winner_team"),
                        "battle_type": (finalization.get("meta") or {}).get("battle_type"),
                    },
                )
            )
        return requests

    @staticmethod
    def _is_arena(finalization: dict[str, Any]) -> bool:
        meta = finalization.get("meta") if isinstance(finalization.get("meta"), dict) else {}
        battle_type = str(meta.get("battle_type") or "").lower()
        return bool(meta.get("arena_session_id")) or battle_type in {"arena", "duel", "pvp_arena"}

    @staticmethod
    def _player_actors(finalization: dict[str, Any]) -> list[dict[str, Any]]:
        actors = finalization.get("actors")
        if not isinstance(actors, dict):
            return []
        return [
            actor
            for actor in actors.values()
            if isinstance(actor, dict) and actor.get("char_id") is not None and not bool(actor.get("is_ai"))
        ]
