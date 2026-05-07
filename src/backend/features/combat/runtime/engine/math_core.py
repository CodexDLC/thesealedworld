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
        return MathCore.roll_chance(chance)[1]

    @staticmethod
    def roll_chance(chance: float) -> tuple[float | None, bool]:
        """
        Возвращает raw roll и результат проверки шанса.

        Для гарантированных исходов roll=None: это делает combat trace понятнее и
        не тратит случайное число там, где его результат не влияет на механику.
        """
        if chance >= 1.0:
            return None, True
        if chance <= 0.0:
            return None, False
        roll = random.random()  # nosec B311
        return roll, roll < chance

    @staticmethod
    def random_range(min_val: float, max_val: float) -> float:
        """
        Возвращает случайное число между min и max (включительно для int, float для float).
        """
        return random.uniform(min_val, max_val)  # nosec B311
