from enum import StrEnum


class OnboardingStepEnum(StrEnum):
    """
    Константы для шагов онбординга (Состояния).
    """

    NAME = "NAME"
    GENDER = "GENDER"
    CONFIRM = "CONFIRM"


class OnboardingActionEnum(StrEnum):
    """
    Константы для действий пользователя (Actions).
    """

    SET_NAME = "set_name"
    SET_GENDER = "set_gender"
    FINALIZE = "finalize"
