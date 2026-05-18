"""
FeintService - сервис для работы с системой "руки" финтов.

Отвечает за:
- Пополнение руки финтов
- Формирование данных для UI
"""

import random

from src.backend.features.combat.dto.actor import ActorMetaDTO
from src.backend.features.combat.integrations import CombatCatalogIntegrator

FEINT_STAMINA_PER_TOKEN = 5

# === ОСНОВНОЙ СЕРВИС ===


class FeintService:
    """
    Статический сервис для работы с финтами.
    Используется MechanicService, Viewer.
    """

    @staticmethod
    def refill_hand(actor: ActorMetaDTO, hand_size: int = 3) -> None:
        """
        Пополняет руку до hand_size финтов.
        Временно списывает токены за добавленные финты.

        Вызывается в MechanicService после начисления токенов.

        Алгоритм:
        1. Собираем available_pool (финты по токенам из arsenal)
        2. Фильтруем дубли (исключаем уже в руке)
        3. Случайно добавляем до hand_size
        4. Временно списываем токены
        """

        # Если рука уже полная - выходим
        if actor.feints.get_hand_size() >= hand_size:
            return

        # 1. Собираем доступные финты по токенам
        available_pool = []

        for feint_id in actor.feints.arsenal:
            feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)
            if not feint_entry:
                continue

            # Берем стоимость напрямую из DTO (dict[str, int])
            cost_dict = feint_entry.technical.cost.tactics

            # Проверяем хватает ли токенов
            if FeintService._can_afford(actor.tokens, cost_dict):
                available_pool.append(feint_id)

        # 2. Фильтруем дубли (исключаем уже в руке)
        available_pool = [f for f in available_pool if not actor.feints.is_in_hand(f)]

        # 3. Добавляем случайные до hand_size
        while actor.feints.get_hand_size() < hand_size and available_pool:
            # Выбираем случайный финт
            feint_id = random.choice(available_pool)  # nosec B311
            feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)

            if not feint_entry:
                available_pool.remove(feint_id)
                continue

            cost_dict = feint_entry.technical.cost.tactics

            # Добавляем в руку
            actor.feints.add_to_hand(feint_id, cost_dict)

            # Временно списываем токены
            FeintService._deduct_tokens(actor.tokens, cost_dict)

            # Убираем из пула
            available_pool.remove(feint_id)

    @staticmethod
    def reroll_hand(actor: ActorMetaDTO, hand_size: int = 3) -> None:
        """
        Обновляет руку после размена.

        Закрепленный финт остается в руке и продолжает держать токены замороженными.
        Все остальные неиспользованные финты возвращают стоимость в свободные токены,
        удаляются из руки, затем рука снова случайно пополняется до hand_size.
        """
        pinned = actor.feints.pinned
        if pinned and pinned not in actor.feints.hand:
            actor.feints.pinned = None
            pinned = None

        for feint_id, cost in list(actor.feints.hand.items()):
            if feint_id == pinned:
                continue
            FeintService._return_tokens(actor.tokens, cost)
            actor.feints.remove_from_hand(feint_id)

        FeintService.refill_hand(actor, hand_size=hand_size)

    @staticmethod
    def return_to_hand(actor: ActorMetaDTO, feint_key: str, cost: dict[str, int]) -> None:
        """
        Возвращает финт в руку (атака провалилась, цель мертва).
        Токены НЕ возвращаем, так как они "заморожены" в стоимости карты.

        Вызывается в CombatResolver если атака не состоялась.
        """
        # Возвращаем финт в руку
        actor.feints.add_to_hand(feint_key, cost)

    @staticmethod
    def refund_cost(actor: ActorMetaDTO, cost: dict[str, int]) -> None:
        """Возвращает замороженную стоимость использованного финта в свободные токены."""
        FeintService._return_tokens(actor.tokens, cost)

    @staticmethod
    def activation_stamina_cost(cost: dict[str, int]) -> int:
        return max(0, sum(max(0, int(amount)) for amount in cost.values())) * FEINT_STAMINA_PER_TOKEN

    @staticmethod
    def get_hand_for_dashboard(actor: ActorMetaDTO) -> dict[str, str]:
        """
        Возвращает словарь {feint_key: button_text} для UI.

        Вызывается в Viewer при формировании дашборда.

        Пример:
            {
                "true_strike": "⚔️ Верный удар",
                "sand_throw": "💨 Бросок песка"
            }
        """
        result = {}

        for feint_key in actor.feints.hand:
            feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_key)
            if feint_entry:
                variant = feint_entry.descriptive.variants.get(feint_entry.descriptive.default_taxonomy)
                button_text = variant.display_name if variant else feint_key
            else:
                button_text = f"❓ {feint_key}"

            result[feint_key] = button_text

        return result

    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===

    @staticmethod
    def _can_afford(tokens: dict[str, int], cost: dict[str, int]) -> bool:
        """Проверяет хватает ли токенов на финт"""
        for token_type, amount in cost.items():
            current = tokens.get(token_type, 0)
            if current < amount:
                return False
        return True

    @staticmethod
    def _deduct_tokens(tokens: dict[str, int], cost: dict[str, int]) -> None:
        """Списывает токены (временно)"""
        for token_type, amount in cost.items():
            current = tokens.get(token_type, 0)
            tokens[token_type] = max(0, current - amount)

    @staticmethod
    def _return_tokens(tokens: dict[str, int], cost: dict[str, int]) -> None:
        """Возвращает токены"""
        for token_type, amount in cost.items():
            current = tokens.get(token_type, 0)
            tokens[token_type] = current + amount
