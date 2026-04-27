import random
from typing import TypeVar

T = TypeVar("T")


class ChanceService:
    """
    Общий сервис для работы с вероятностями и рандомом.
    Используется в Combat, Exploration, Loot и других доменах.
    """

    @staticmethod
    def check_chance(percent: float) -> bool:
        """
        Проверяет срабатывание шанса (в процентах, 0-100 или 0.0-1.0).
        Пример: check_chance(0.45) -> 45% True
        """
        if percent >= 1.0 and isinstance(percent, int):  # Если передали 45 вместо 0.45
            return random.random() < (percent / 100.0)
        return random.random() < percent

    @staticmethod
    def weighted_choice(items: dict[T, float]) -> T:
        """
        Выбирает элемент из словаря {item: weight}.
        Пример: {"wolf": 50, "bear": 10}
        """
        total = sum(items.values())
        if total == 0:
            raise ValueError("Total weight is 0")

        r = random.uniform(0, total)
        upto = 0.0
        for item, weight in items.items():
            if upto + weight >= r:
                return item
            upto += weight
        return list(items.keys())[-1]  # Fallback

    @staticmethod
    def random_range(min_val: int, max_val: int) -> int:
        """
        Возвращает случайное целое число [min, max].
        """
        return random.randint(min_val, max_val)
