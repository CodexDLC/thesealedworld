from pydantic import BaseModel, ConfigDict


class OnboardingDraftDTO(BaseModel):
    """
    Черновик данных персонажа в процессе создания.
    """

    name: str | None = None
    gender: str | None = None


class OnboardingViewDTO(BaseModel):
    """
    DTO для отображения состояния онбординга (старая версия, возможно deprecated).
    """

    step: str
    draft: OnboardingDraftDTO
    error: str | None = None


# --- UI Payload DTOs (New) ---


class ButtonDTO(BaseModel):
    """
    DTO для кнопки.
    """

    text: str
    action: str
    value: str | None = None


class OnboardingUIPayloadDTO(BaseModel):
    """
    DTO с готовыми данными для UI (Текст + Кнопки).
    Отправляется клиенту для рендеринга.
    """

    step: str
    title: str
    description: str
    buttons: list[ButtonDTO]

    # Дополнительные данные (например, драфт), если нужны клиенту для логики
    draft: OnboardingDraftDTO | None = None
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)
