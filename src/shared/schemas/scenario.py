from typing import Any

from pydantic import BaseModel, Field


class ScenarioInitDTO(BaseModel):
    """
    DTO для инициализации сценария (переход из другого режима).
    """

    quest_key: str = Field(..., description="Ключ квеста/сценария для запуска")
    node_id: str | None = Field(None, description="Опциональный ID стартовой ноды")


class ScenarioButtonDTO(BaseModel):
    """Схема кнопки действия."""

    label: str = Field(..., description="Текст на кнопке")
    action_id: str = Field(..., description="ID действия, который вернется в step_scenario")


class ScenarioPayloadDTO(BaseModel):
    """Основное тело ответа со сценой."""

    node_key: str = Field(..., description="ID текущей ноды")
    text: str = Field(..., description="Художественный текст без форматирования")
    status_bar: list[str] = Field(default_factory=list, description="Список строк для статус-бара")
    buttons: list[ScenarioButtonDTO] = Field(default_factory=list, description="Список доступных кнопок")
    is_terminal: bool = Field(default=False, description="Является ли сцена финальной (конец квеста)")
    extra_data: dict[str, Any] | None = Field(
        default=None, description="Дополнительные данные (например, для перехода в бой)"
    )
