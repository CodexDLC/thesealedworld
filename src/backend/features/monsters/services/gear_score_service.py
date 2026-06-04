from __future__ import annotations

from statistics import mean
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster


class MonsterGearScoreService:
    VERSION = 9

    def calculate_raw_monster_gear_score(self, monster: GeneratedMonster) -> int:
        snapshot = dict(monster.active_snapshot or {})
        return _int(snapshot.get("gear_score"), default=1)

    def calculate_monster_gear_score(self, monster: GeneratedMonster) -> int:
        return self.calculate_raw_monster_gear_score(monster)

    def apply_monster_gear_score(self, monster: GeneratedMonster) -> int:
        return self.calculate_monster_gear_score(monster)

    def refresh_stale_monster_scores(self, members: list[GeneratedMonster]) -> int:
        return 0

    def needs_recalculation(self, monster: GeneratedMonster) -> bool:
        return False

    def apply_clan_summary(self, clan: GeneratedClan) -> dict[str, Any]:
        return self.build_clan_summary(clan.members)

    def build_clan_summary(self, members: list[GeneratedMonster]) -> dict[str, Any]:
        scores_by_role: dict[str, list[int]] = {}
        all_scores: list[int] = []
        for member in members:
            score = self.calculate_monster_gear_score(member)
            all_scores.append(score)
            scores_by_role.setdefault(member.role, []).append(score)

        return {
            "version": self.VERSION,
            "count": len(all_scores),
            "min": min(all_scores) if all_scores else 0,
            "avg": round(mean(all_scores), 2) if all_scores else 0.0,
            "max": max(all_scores) if all_scores else 0,
            "total": sum(all_scores),
            "by_role": {role: self._score_bucket(scores) for role, scores in sorted(scores_by_role.items())},
        }

    @staticmethod
    def _score_bucket(scores: list[int]) -> dict[str, float | int]:
        return {
            "count": len(scores),
            "min": min(scores),
            "avg": round(mean(scores), 2),
            "max": max(scores),
            "total": sum(scores),
        }


def _int(value: object, *, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore
    except (TypeError, ValueError):
        return default


__all__ = ["MonsterGearScoreService"]
