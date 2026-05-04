from enum import StrEnum


class SkillProgressState(StrEnum):
    """
    Перечисление, определяющее состояние развития навыка.

    - PLUS: Навык активно развивается (например, получает бонусный опыт).
    - PAUSE: Развитие навыка приостановлено.
    - MINUS: Развитие навыка замедлено или регрессирует.
    """

    PLUS = "PLUS"
    PAUSE = "PAUSE"
    MINUS = "MINUS"
