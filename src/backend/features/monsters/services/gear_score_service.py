from __future__ import annotations

from statistics import mean
from typing import TYPE_CHECKING, Any

from src.backend.features.character.runtime.gear_score import CharacterGearScoreCalculator
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder
from src.backend.features.monsters.runtime.generation_fields import ORGANIZATION_GS_DIVISORS

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster


class MonsterGearScoreService:
    VERSION = 8

    def __init__(self, actor_builder: MonsterCombatActorInputBuilder | None = None) -> None:
        self.actor_builder = actor_builder or MonsterCombatActorInputBuilder()

    def calculate_raw_monster_gear_score(self, monster: GeneratedMonster) -> int:
        snapshot = self.actor_builder.build_snapshot(monster)
        combat = snapshot["combat"]
        return CharacterGearScoreCalculator.calculate_from_raw(
            combat["math_model"],
            skills=combat["skills"],
            loadout=combat["loadout"],
        )

    def calculate_monster_gear_score(self, monster: GeneratedMonster) -> int:
        return self._effective_score(self.calculate_raw_monster_gear_score(monster), monster)

    def apply_monster_gear_score(self, monster: GeneratedMonster) -> int:
        raw_score = self.calculate_raw_monster_gear_score(monster)
        score = self._effective_score(raw_score, monster)
        generation_meta = dict(monster.generation_meta or {})
        balance = dict(generation_meta.get("balance") or {})
        balance.pop("base_cost", None)
        balance.pop("effective_cost", None)
        balance.pop("threat_rating", None)
        balance["raw_gear_score"] = raw_score
        balance["assembly_cost"] = score
        balance["gear_score"] = score
        balance["gear_score_version"] = self.VERSION
        generation_meta["balance"] = balance
        monster.generation_meta = generation_meta
        if hasattr(monster, "threat_rating"):
            monster.threat_rating = score
        return score

    def refresh_stale_monster_scores(self, members: list[GeneratedMonster]) -> int:
        refreshed = 0
        for member in members:
            if not self.needs_recalculation(member):
                continue
            self.apply_monster_gear_score(member)
            refreshed += 1
        return refreshed

    def needs_recalculation(self, monster: GeneratedMonster) -> bool:
        generation_meta = monster.generation_meta if isinstance(monster.generation_meta, dict) else {}
        balance = generation_meta.get("balance")
        if not isinstance(balance, dict):
            return True
        try:
            version = int(balance["gear_score_version"])
            int(balance["gear_score"])
            int(balance["raw_gear_score"])
            int(balance["assembly_cost"])
        except (KeyError, TypeError, ValueError):
            return True
        return version != self.VERSION

    def apply_clan_summary(self, clan: GeneratedClan) -> dict[str, Any]:
        summary = self.build_clan_summary(clan.members)
        raw_tags = dict(clan.raw_tags or {})
        raw_tags["gear_score_summary"] = summary
        clan.raw_tags = raw_tags
        return summary

    def build_clan_summary(self, members: list[GeneratedMonster]) -> dict[str, Any]:
        scores_by_role: dict[str, list[int]] = {}
        raw_scores_by_role: dict[str, list[int]] = {}
        all_scores: list[int] = []
        all_raw_scores: list[int] = []
        for member in members:
            score = self._stored_gear_score(member)
            if score is not None:
                all_scores.append(score)
                scores_by_role.setdefault(member.role, []).append(score)
            raw_score = self._stored_raw_gear_score(member)
            if raw_score is not None:
                all_raw_scores.append(raw_score)
                raw_scores_by_role.setdefault(member.role, []).append(raw_score)

        return {
            "version": self.VERSION,
            "count": len(all_scores),
            "min": min(all_scores) if all_scores else 0,
            "avg": round(mean(all_scores), 2) if all_scores else 0.0,
            "max": max(all_scores) if all_scores else 0,
            "total": sum(all_scores),
            "by_role": {role: self._score_bucket(scores) for role, scores in sorted(scores_by_role.items())},
            "raw_count": len(all_raw_scores),
            "raw_min": min(all_raw_scores) if all_raw_scores else 0,
            "raw_avg": round(mean(all_raw_scores), 2) if all_raw_scores else 0.0,
            "raw_max": max(all_raw_scores) if all_raw_scores else 0,
            "raw_total": sum(all_raw_scores),
            "raw_by_role": {role: self._score_bucket(scores) for role, scores in sorted(raw_scores_by_role.items())},
        }

    @staticmethod
    def _effective_score(score: int, monster: GeneratedMonster) -> int:
        divisor = MonsterGearScoreService._organization_divisor(monster)
        return max(1, int(round(score / divisor)))

    @staticmethod
    def _organization_divisor(monster: GeneratedMonster) -> float:
        generation_meta = monster.generation_meta if isinstance(monster.generation_meta, dict) else {}
        balance = generation_meta.get("balance")
        if not isinstance(balance, dict):
            return 1.0

        raw_divisor = balance.get("organization_divisor")
        if raw_divisor is not None:
            try:
                divisor = float(raw_divisor)
                if divisor > 0:
                    return divisor
            except (TypeError, ValueError):
                pass

        organization_type = str(balance.get("organization_type") or "")
        return float(ORGANIZATION_GS_DIVISORS.get(organization_type, 1.0))

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
    def _stored_raw_gear_score(monster: GeneratedMonster) -> int | None:
        generation_meta = monster.generation_meta if isinstance(monster.generation_meta, dict) else {}
        balance = generation_meta.get("balance")
        if not isinstance(balance, dict):
            return None
        try:
            return int(balance["raw_gear_score"])
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
