from typing import Any

from pydantic import BaseModel


class AnnouncementsEvent(BaseModel):
    """Schema for the Redis Stream event."""

    id: str
    payload: dict[str, Any]
    timestamp: float
