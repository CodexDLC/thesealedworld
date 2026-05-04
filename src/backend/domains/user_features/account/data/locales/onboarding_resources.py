from typing import TypedDict

from src.shared.enums.onboarding_enums import OnboardingActionEnum


class ButtonConfig(TypedDict):
    text: str
    action: str
    value: str | None


class OnboardingResources:
    """
    Ресурсы для Onboarding (Тексты и Кнопки).
    Stateless класс.
    """

    # --- Steps ---
    STEP_NAME = "NAME"
    STEP_GENDER = "GENDER"
    STEP_CONFIRM = "CONFIRM"

    # --- Texts ---

    @staticmethod
    def get_name_text() -> str:
        return "Как будут звать вашего героя?\n\n<i>Введите имя сообщением:</i>"

    @staticmethod
    def get_gender_text(name: str) -> str:
        return f"Приятно познакомиться, <b>{name}</b>!\n\nВыберите пол вашего персонажа:"

    @staticmethod
    def get_confirm_text(name: str, gender: str) -> str:
        gender_text = OnboardingResources.get_gender_label(gender)
        return f"Проверьте данные:\n\n👤 Имя: <b>{name}</b>\n⚧ Пол: <b>{gender_text}</b>\n\nВсё верно?"

    @staticmethod
    def get_gender_label(gender_code: str) -> str:
        labels = {"male": "Мужской", "female": "Женский", "other": "Другой"}
        return labels.get(gender_code, gender_code)

    # --- Buttons ---

    @staticmethod
    def get_gender_buttons() -> list[ButtonConfig]:
        return [
            {"text": "Мужской", "action": OnboardingActionEnum.SET_GENDER.value, "value": "male"},
            {"text": "Женский", "action": OnboardingActionEnum.SET_GENDER.value, "value": "female"},
        ]

    @staticmethod
    def get_confirm_buttons() -> list[ButtonConfig]:
        return [{"text": "✅ Открыть глаза", "action": OnboardingActionEnum.FINALIZE.value, "value": None}]
