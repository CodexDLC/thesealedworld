import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ChannelType = Literal["global", "zone", "party", "trade", "system", "dm"]


class IncomingMessageDTO(BaseModel):
    channel: ChannelType
    content: str = Field(min_length=1, max_length=500)
    scope_id: str | None = None


class OutgoingMessageDTO(BaseModel):
    id: str
    channel: ChannelType
    scope_id: str | None
    sender_id: str
    sender_name: str
    content: str
    created_at: datetime

    @classmethod
    def build(
        cls,
        *,
        channel: ChannelType,
        scope_id: str | None,
        sender_id: uuid.UUID,
        sender_name: str,
        content: str,
        created_at: datetime,
    ) -> "OutgoingMessageDTO":
        return cls(
            id=str(uuid.uuid4()),
            channel=channel,
            scope_id=scope_id,
            sender_id=str(sender_id),
            sender_name=sender_name,
            content=content,
            created_at=created_at,
        )
