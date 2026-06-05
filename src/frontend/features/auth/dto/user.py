import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator, model_validator

from src.shared.schemas.base import BaseRequest, BaseResponse

PASSWORD_MIN_LENGTH = 10


class UserCreate(BaseRequest):
    email: EmailStr
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_email_in_password(self) -> "UserCreate":
        local = str(self.email).split("@", maxsplit=1)[0].lower()
        if local and local in self.password.lower():
            raise ValueError("Password must not contain the email local part")
        return self


class UserResponse(BaseResponse):
    id: uuid.UUID
    email: str
    is_active: bool
    is_superuser: bool
    tester_status: str = "none"
    tester_approved_at: datetime | None = None
    created_at: datetime
