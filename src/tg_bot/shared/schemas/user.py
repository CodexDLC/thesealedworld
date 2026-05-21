from pydantic import BaseModel


class UserUpsertDTO(BaseModel):
    """DTO for creating or updating a user profile."""

    telegram_id: int
    first_name: str
    username: str | None = None
    last_name: str | None = None
    language_code: str | None = None
    is_premium: bool = False
