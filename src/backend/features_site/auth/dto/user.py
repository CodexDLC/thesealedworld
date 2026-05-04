import uuid
from datetime import datetime

from pydantic import Field, field_validator

from src.backend.core.schemas.base import BaseRequest, BaseResponse


class UserCreate(BaseRequest):
    email: str
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", maxsplit=1)[-1]:
            raise ValueError("Invalid email address")
        return normalized


class UserResponse(BaseResponse):
    id: uuid.UUID
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
