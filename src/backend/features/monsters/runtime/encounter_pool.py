from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster, MonsterGenerationContext


DIFFICULTY_ROLES: dict[str, tuple[str, ...]] = {
    "easy": ("minion",),
    "mid": ("minion", "veteran"),
    "normal": ("minion", "veteran"),
    "hard": ("veteran", "elite"),
    "elite": ("elite",),
    "boss": ("boss", "elite"),
}


class EncounterPoolSelector:
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()  # nosec B311

    def choose_existing_clan(
        self,
        clans: Sequence[GeneratedClan],
        context: MonsterGenerationContext,
    ) -> GeneratedClan | None:
        suitable = [clan for clan in clans if self._select_members(list(clan.members), context)]
        if not suitable:
            return None
        return self._rng.choice(suitable)

    def select_monsters(
        self,
        members: Sequence[GeneratedMonster],
        context: MonsterGenerationContext,
    ) -> list[GeneratedMonster]:
        selected = self._select_members(members, context)
        return selected[: context.count]

    def _select_members(
        self,
        members: Sequence[GeneratedMonster],
        context: MonsterGenerationContext,
    ) -> list[GeneratedMonster]:
        if not members:
            return []

        candidates = list(members)
        if context.role:
            role_filtered = [monster for monster in candidates if monster.role == context.role]
            if role_filtered:
                candidates = role_filtered
        else:
            roles = DIFFICULTY_ROLES.get(context.difficulty, DIFFICULTY_ROLES["mid"])
            role_filtered = [monster for monster in candidates if monster.role in roles]
            if role_filtered:
                candidates = role_filtered

        if context.threat is not None:
            threat_val = context.threat
            candidates.sort(key=lambda monster: (abs(monster.threat_rating - threat_val), monster.threat_rating))
        else:
            candidates.sort(key=lambda monster: (monster.threat_rating, monster.variant_key))
        return candidates
