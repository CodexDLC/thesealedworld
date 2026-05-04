from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserUpsertDTO(BaseModel):
    """
    DTO для создания или обновления пользователя.
    """

    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None
    is_premium: bool = False


class UserDTO(UserUpsertDTO):
    """
    DTO для чтения данных пользователя.
    """

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
