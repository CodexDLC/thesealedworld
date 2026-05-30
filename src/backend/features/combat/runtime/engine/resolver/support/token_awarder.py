"""Token-grant primitives.

These are the canonical implementations used by Step-classes and by
``trigger_activator``. The bonus-roll chance is read from
``current_tunables()`` rather than a module-level constant so Redis-backed
balance changes apply at runtime.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from src.backend.features.combat.runtime.engine.tunables import current_tunables

if TYPE_CHECKING:
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO

TOKEN_BONUS_EXCLUDED = frozenset({"tempo", "gift"})


def bonus_token_roll() -> bool:
    return random.random() < current_tunables().token_bonus_chance  # nosec B311


def award_token(bucket: dict[str, int], token: str) -> None:
    amount = 1
    if token not in TOKEN_BONUS_EXCLUDED and bonus_token_roll():
        amount = 2
    bucket[token] = bucket.get(token, 0) + amount


def award_attacker_token(res: InteractionResultDTO, token: str) -> None:
    award_token(res.tokens_awarded_attacker, token)


def award_defender_token(res: InteractionResultDTO, token: str) -> None:
    award_token(res.tokens_awarded_defender, token)
