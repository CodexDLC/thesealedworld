"""Token-grant primitives.

These are the canonical implementations used by Step-классы (Phase 4) and by
``trigger_activator``. ``CombatResolver`` retains a parallel implementation
during Phase 3 to honor the ``_bonus_token_roll`` monkeypatch contract through
``cls.`` chaining; in Phase 4 that parallel impl is migrated to use these
directly and the monkeypatch is rebound.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO

TOKEN_BONUS_CHANCE = 0.30
TOKEN_BONUS_EXCLUDED = frozenset({"tempo", "gift"})


def bonus_token_roll() -> bool:
    return random.random() < TOKEN_BONUS_CHANCE  # nosec B311


def award_token(bucket: dict[str, int], token: str) -> None:
    amount = 1
    if token not in TOKEN_BONUS_EXCLUDED and bonus_token_roll():
        amount = 2
    bucket[token] = bucket.get(token, 0) + amount


def award_attacker_token(res: InteractionResultDTO, token: str) -> None:
    award_token(res.tokens_awarded_attacker, token)


def award_defender_token(res: InteractionResultDTO, token: str) -> None:
    award_token(res.tokens_awarded_defender, token)
