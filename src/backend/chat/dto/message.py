import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ChannelType = Literal["global", "zone", "party", "trade", "system", "dm", "combat"]
IncomingChannelType = Literal["global", "zone", "party", "trade", "system", "dm", "combat"]
TabOpenPolicy = Literal["passive", "force_open", "request_consent"]
TabKind = Literal["static", "combat", "dm", "system"]


class MessageTabDTO(BaseModel):
    kind: TabKind
    key: str
    title: str
    open_policy: TabOpenPolicy = "passive"
    closeable: bool = False
    accent: str | None = None


class IncomingMessageDTO(BaseModel):
    channel: IncomingChannelType
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
    tab: MessageTabDTO | None = None
    template: dict[str, Any] | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    presentation: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)

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
        tab: MessageTabDTO | None = None,
        template: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        presentation: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> "OutgoingMessageDTO":
        return cls(
            id=str(uuid.uuid4()),
            channel=channel,
            scope_id=scope_id,
            sender_id=str(sender_id),
            sender_name=sender_name,
            content=content,
            created_at=created_at,
            tab=tab,
            template=template,
            variables=variables or {},
            result=result or {},
            presentation=presentation or {},
            meta=meta or {},
        )
