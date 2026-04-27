from pydantic import BaseModel, Field


class HUDDataDTO(BaseModel):
    """
    Данные для отображения HUD (Heads-Up Display).
    """

    hp: int
    max_hp: int
    energy: int
    max_energy: int
    char_name: str
    location_id: str  # ID локации (строка)
    current_mode: str  # Текущий игровой режим (State Enum value)


class MenuButtonDTO(BaseModel):
    """
    Кнопка меню.
    """

    id: str
    text: str  # Смайлик
    is_active: bool = True


class GameMenuDTO(BaseModel):
    """
    Полный объект меню для клиента.
    """

    hud: HUDDataDTO
    buttons: list[MenuButtonDTO]
    legend: dict[str, str] = Field(default_factory=dict)  # Описание кнопок: {"📦": "Inventory"}


class MenuActionRequest(BaseModel):
    """
    Запрос на выполнение действия меню.
    """

    char_id: int
    action_id: str
