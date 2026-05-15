import uuid
from datetime import datetime

from pydantic import BaseModel


class DMSessionDTO(BaseModel):
    id: str
    participant_a_id: str
    participant_b_id: str
    created_at: datetime
    last_message_at: datetime


class DMMessageDTO(BaseModel):
    id: str
    session_id: str
    sender_id: str
    content: str
    read_at: datetime | None
    created_at: datetime


class OpenDMSessionRequest(BaseModel):
    target_character_id: uuid.UUID
