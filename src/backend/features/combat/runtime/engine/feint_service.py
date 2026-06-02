"""
FeintService - сервис для работы с системой "руки" финтов.

Отвечает за:
- Пополнение руки финтов
- Формирование данных для UI
"""

import random
from typing import Any

from src.backend.features.combat.dto.actor import ActorMetaDTO
from src.backend.features.combat.integrations import CombatCatalogIntegrator

FEINT_STAMINA_PER_TOKEN = 3
FEINT_PURCHASE_GROUP_ORDER = ("weapon", "tactical", "basic")

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
        1. Сначала пытаемся заполнить целевые слоты weapon/tactical/basic.
        2. Для каждого целевого слота берем самый дорогой доступный финт.
        3. Если остаются свободные места, добираем случайно, но basic остается последней группой.
        4. Временно списываем токены за зарезервированные финты.
        """

        # Если рука уже полная - выходим
        if actor.feints.get_hand_size() >= hand_size:
            return

        occupied_groups = FeintService._occupied_purchase_groups(actor)
        for group in FEINT_PURCHASE_GROUP_ORDER:
            if actor.feints.get_hand_size() >= hand_size:
                return
            if group in occupied_groups:
                continue

            candidate = FeintService._best_affordable_in_group(actor, group)
            if candidate is None:
                continue

            FeintService._reserve_feint(actor, candidate)
            occupied_groups.add(group)

        while actor.feints.get_hand_size() < hand_size:
            available_pool = FeintService._fallback_pool_by_purchase_priority(actor)
            if not available_pool:
                return

            FeintService._reserve_feint(actor, random.choice(available_pool))  # nosec B311

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

        Пример: `{}` пока новый каталог финтов не собран.
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
    def _available_feints(actor: ActorMetaDTO) -> list[tuple[str, Any]]:
        available: list[tuple[str, Any]] = []
        for feint_id in actor.feints.arsenal:
            if actor.feints.is_in_hand(feint_id):
                continue
            feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)
            if not feint_entry:
                continue
            cost_dict = dict(feint_entry.technical.cost.tactics)
            if FeintService._can_afford(actor.tokens, cost_dict):
                available.append((feint_id, feint_entry))
        return available

    @staticmethod
    def _occupied_purchase_groups(actor: ActorMetaDTO) -> set[str]:
        groups: set[str] = set()
        for feint_id in actor.feints.hand:
            feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)
            if not feint_entry:
                continue
            groups.add(FeintService._purchase_group(feint_entry))
        return groups

    @staticmethod
    def _best_affordable_in_group(actor: ActorMetaDTO, group: str) -> str | None:
        best_feint_id: str | None = None
        best_cost = -1
        for feint_id, feint_entry in FeintService._available_feints(actor):
            if FeintService._purchase_group(feint_entry) != group:
                continue
            total_cost = FeintService._total_cost(feint_entry.technical.cost.tactics)
            if total_cost > best_cost:
                best_feint_id = feint_id
                best_cost = total_cost
        return best_feint_id

    @staticmethod
    def _fallback_pool_by_purchase_priority(actor: ActorMetaDTO) -> list[str]:
        available = FeintService._available_feints(actor)
        for group in FEINT_PURCHASE_GROUP_ORDER:
            group_pool = [
                feint_id for feint_id, feint_entry in available if FeintService._purchase_group(feint_entry) == group
            ]
            if group_pool:
                return group_pool
        return []

    @staticmethod
    def _reserve_feint(actor: ActorMetaDTO, feint_id: str) -> None:
        feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)
        if not feint_entry:
            return
        cost_dict = dict(feint_entry.technical.cost.tactics)
        if not FeintService._can_afford(actor.tokens, cost_dict):
            return
        actor.feints.add_to_hand(feint_id, cost_dict)
        FeintService._deduct_tokens(actor.tokens, cost_dict)

    @staticmethod
    def _purchase_group(feint_entry: Any) -> str:
        group = getattr(feint_entry.technical, "purchase_group", "basic")
        if group in FEINT_PURCHASE_GROUP_ORDER:
            return str(group)
        return "basic"

    @staticmethod
    def _total_cost(cost: dict[str, int]) -> int:
        return sum(max(0, int(amount)) for amount in cost.values())

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
