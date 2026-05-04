import random


class MathCore:
    """
    Базовые математические утилиты для боевой системы.
    """

    @staticmethod
    def check_chance(chance: float) -> bool:
        """
        Проверяет шанс (0.0 - 1.0+).
        Если chance >= 1.0, всегда True.
        Если chance <= 0.0, всегда False.
        """
        if chance >= 1.0:
            return True
        if chance <= 0.0:
            return False
        return random.random() < chance

    @staticmethod
    def random_range(min_val: float, max_val: float) -> float:
        """
        Возвращает случайное число между min и max (включительно для int, float для float).
        """
        return random.uniform(min_val, max_val)
