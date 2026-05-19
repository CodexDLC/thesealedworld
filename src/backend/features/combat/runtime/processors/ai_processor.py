import random
from typing import Any

from src.backend.features.combat.dto.actor import ActorSnapshot


class AiProcessor:
    """Produce runtime move payloads for NPC-controlled combat actors.

    The current implementation is intentionally simple and heuristic-driven. It
    chooses an exchange attack against a specific target and may attach a feint
    from the bot hand. This keeps AI on the same intent contract as players.
    """

    def decide_exchange(self, bot: ActorSnapshot, target: ActorSnapshot) -> dict[str, Any]:
        """Build one exchange move payload for a concrete bot-target pairing.

        Args:
            bot: Full acting NPC snapshot.
            target: Full chosen target snapshot.

        Returns:
            A normalized move payload that can be sent through the turn-manager
            registration path without any AI-specific contract branch.
        """
        payload = {
            "action": "attack",
            "target_id": target.char_id,
        }

        # Извлечение финтов из meta
        available_feints: dict[str, Any] = {}
        if hasattr(bot.meta, "feints") and bot.meta.feints:
            available_feints = bot.meta.feints if isinstance(bot.meta.feints, dict) else {}

        # Если feints - это объект FeintHandDTO, то берем .hand
        # Если это dict (из Redis), то берем ["hand"]
        hand = {}
        if hasattr(available_feints, "hand"):
            hand = available_feints.hand
        elif isinstance(available_feints, dict):
            hand = available_feints.get("hand", {})

        # Логика выбора финта (50% шанс использовать, если есть)
        if hand and random.random() > 0.5:  # nosec B311
            feint_id = random.choice(list(hand.keys()))  # nosec B311
            payload["feint_id"] = feint_id

        # TODO (v3.0): Добавить тактические решения
        # - Проверить HP бота (если < 30% → защитная стойка)
        # - Проверить HP цели (приоритизировать слабых)
        # - Проверить экипировку (дистанция, тип оружия)
        # - Проверить статусы (баффы/дебаффы)

        return payload
