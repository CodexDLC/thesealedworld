import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime | None = None
