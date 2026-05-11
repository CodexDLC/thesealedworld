from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.monsters.dto.generation import GeneratedMonster


@dataclass(frozen=True, slots=True)
class MonsterGroupAssembly:
    members: list[GeneratedMonster]
    target_budget: float
    adjusted_budget: float
    total_power: int


class MonsterGroupAssembler:
    """Selects generated monsters for a group budget.

    MVP policy: mono-family subset selection without duplicating generated variants.
    """

    def assemble(
        self,
        members: Sequence[GeneratedMonster],
        *,
        budget: float,
        tier: int,
        danger: float,
        force_single_family: bool = True,
    ) -> MonsterGroupAssembly:
        del force_single_family  # Current caller already passes members from one clan.
        target_budget = max(1.0, float(budget))
        adjusted_budget = self.adjust_budget(target_budget, tier=tier, danger=danger)
        candidates = sorted(members, key=lambda member: (member.threat_rating, member.role, member.variant_key))
        if not candidates:
            return MonsterGroupAssembly([], target_budget, adjusted_budget, 0)

        selected = self._best_subset(candidates, adjusted_budget)
        total_power = sum(member.threat_rating for member in selected)
        return MonsterGroupAssembly(
            members=list(selected),
            target_budget=target_budget,
            adjusted_budget=adjusted_budget,
            total_power=total_power,
        )

    @staticmethod
    def adjust_budget(budget: float, *, tier: int, danger: float) -> float:
        del tier
        danger_bonus = min(1.0, max(0.0, danger)) * 0.25
        return round(budget * (1.0 + danger_bonus), 2)

    @staticmethod
    def _best_subset(candidates: list[GeneratedMonster], target: float) -> tuple[GeneratedMonster, ...]:
        best: tuple[GeneratedMonster, ...] = (candidates[0],)
        best_score = _score(best, target)
        for size in range(1, len(candidates) + 1):
            for candidate in combinations(candidates, size):
                score = _score(candidate, target)
                if score < best_score:
                    best = candidate
                    best_score = score
        return best


def _score(candidate: tuple[GeneratedMonster, ...], target: float) -> tuple[float, int, int, tuple[str, ...]]:
    total = sum(member.threat_rating for member in candidate)
    overshoot = 1 if total > target else 0
    ids = tuple(member.variant_key for member in candidate)
    return (abs(total - target), overshoot, -len(candidate), ids)
