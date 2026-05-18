from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import uuid
    from datetime import datetime


class FeedbackCreate(BaseModel):
    type: str = Field(..., pattern="^(bug|wish|impression|balance)$")
    title: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=10)
    priority: str | None = Field(None, pattern="^(critical|blocking|minor)$")


class FeedbackResponse(BaseModel):
    id: int
    user_id: uuid.UUID
    type: str
    title: str
    body: str
    priority: str | None
    status: str
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
