from enum import StrEnum


class SkillProgressState(StrEnum):
    """
    Состояние развития навыка.

    - PLUS: Навык развивается.
    - PAUSE: Навык отключён.
    - MINUS: Навык деградирует.
    """

    PLUS = "PLUS"
    PAUSE = "PAUSE"
    MINUS = "MINUS"
