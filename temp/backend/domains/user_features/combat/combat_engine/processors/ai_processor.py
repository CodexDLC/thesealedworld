import random
from typing import Any

from src.backend.domains.user_features.combat.dto.combat_actor_dto import ActorSnapshot


class AiProcessor:
    """
    Процессор принятия решений для AI (NPC).
    v2.0: Работает с полными данными ActorSnapshot.
    """

    def decide_exchange(self, bot: ActorSnapshot, target: ActorSnapshot) -> dict[str, Any]:
        """
        Генерирует payload для атаки на конкретную цель.

        Простая реализация: всегда атакует, иногда использует финт.

        Args:
            bot: Полные данные бота (HP, EN, экипировка, финты).
            target: Полные данные цели (HP, EN, команда).

        Returns:
            Payload для регистрации хода.
        """
        payload = {
            "action": "attack",
            "target_id": int(target.char_id),
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
        if hand and random.random() > 0.5:
            feint_id = random.choice(list(hand.keys()))
            payload["feint_id"] = feint_id

        # TODO (v3.0): Добавить тактические решения
        # - Проверить HP бота (если < 30% → защитная стойка)
        # - Проверить HP цели (приоритизировать слабых)
        # - Проверить экипировку (дистанция, тип оружия)
        # - Проверить статусы (баффы/дебаффы)

        return payload
