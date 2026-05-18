from __future__ import annotations

from statistics import mean
from typing import TYPE_CHECKING, Any

from src.backend.features.character.runtime.gear_score import CharacterGearScoreCalculator
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster


class MonsterGearScoreService:
    VERSION = 1

    def __init__(self, actor_builder: MonsterCombatActorInputBuilder | None = None) -> None:
        self.actor_builder = actor_builder or MonsterCombatActorInputBuilder()

    def calculate_monster_gear_score(self, monster: GeneratedMonster) -> int:
        snapshot = self.actor_builder.build_snapshot(monster)
        return CharacterGearScoreCalculator.calculate_from_raw(snapshot["combat"]["math_model"])

    def apply_monster_gear_score(self, monster: GeneratedMonster) -> int:
        score = self.calculate_monster_gear_score(monster)
        generation_meta = dict(monster.generation_meta or {})
        balance = dict(generation_meta.get("balance") or {})
        balance["gear_score"] = score
        balance["gear_score_version"] = self.VERSION
        generation_meta["balance"] = balance
        monster.generation_meta = generation_meta
        return score

    def apply_clan_summary(self, clan: GeneratedClan) -> dict[str, Any]:
        summary = self.build_clan_summary(clan.members)
        raw_tags = dict(clan.raw_tags or {})
        raw_tags["gear_score_summary"] = summary
        clan.raw_tags = raw_tags
        return summary

    def build_clan_summary(self, members: list[GeneratedMonster]) -> dict[str, Any]:
        scores_by_role: dict[str, list[int]] = {}
        all_scores: list[int] = []
        for member in members:
            score = self._stored_gear_score(member)
            if score is None:
                continue
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
    def _stored_gear_score(monster: GeneratedMonster) -> int | None:
        generation_meta = monster.generation_meta if isinstance(monster.generation_meta, dict) else {}
        balance = generation_meta.get("balance")
        if not isinstance(balance, dict):
            return None
        try:
            return int(balance["gear_score"])
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _score_bucket(scores: list[int]) -> dict[str, float | int]:
        return {
            "count": len(scores),
            "min": min(scores),
            "avg": round(mean(scores), 2),
            "max": max(scores),
            "total": sum(scores),
        }


__all__ = ["MonsterGearScoreService"]
