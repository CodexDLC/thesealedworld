"""
FeintService - сервис для работы с системой "руки" финтов.

Отвечает за:
- Пополнение руки финтов
- Формирование данных для UI
"""

import random

from src.backend.features.combat.dto.actor import ActorMetaDTO
from src.backend.features.combat.integrations import CombatCatalogIntegrator

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
            feint_config = CombatCatalogIntegrator.get_feint(feint_id)
            if not feint_config:
                continue

            # Берем стоимость напрямую из DTO (dict[str, int])
            cost_dict = feint_config.cost.tactics

            # Проверяем хватает ли токенов
            if FeintService._can_afford(actor.tokens, cost_dict):
                available_pool.append(feint_id)

        # 2. Фильтруем дубли (исключаем уже в руке)
        available_pool = [f for f in available_pool if not actor.feints.is_in_hand(f)]

        # 3. Добавляем случайные до hand_size
        while actor.feints.get_hand_size() < hand_size and available_pool:
            # Выбираем случайный финт
            feint_id = random.choice(available_pool)
            feint_config = CombatCatalogIntegrator.get_feint(feint_id)

            if not feint_config:
                available_pool.remove(feint_id)
                continue

            cost_dict = feint_config.cost.tactics

            # Добавляем в руку
            actor.feints.add_to_hand(feint_id, cost_dict)

            # Временно списываем токены
            FeintService._deduct_tokens(actor.tokens, cost_dict)

            # Убираем из пула
            available_pool.remove(feint_id)

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
            feint_config = CombatCatalogIntegrator.get_feint(feint_key)
            button_text = feint_config.name_ru if feint_config else f"❓ {feint_key}"

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
