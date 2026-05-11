from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

GameMessageChannel = Literal["world", "zone", "system", "combat", "dm"]
GameMessageTabKind = Literal["static", "combat", "dm", "system"]
GameMessageTabOpenPolicy = Literal["passive", "force_open", "request_consent"]


class GameMessageJsonDTO(BaseModel):
    model_config = ConfigDict(extra="allow")


class GameMessageTemplateDTO(GameMessageJsonDTO):
    key: str | None = None
    event: str | None = None
    taxonomy: str | None = None
    variant: int = 0
    text: str


class GameMessagePresentationDTO(GameMessageJsonDTO):
    render: str = "text"
    player_visible: bool = True
    severity: str = "normal"


class GameMessageTabDTO(GameMessageJsonDTO):
    kind: GameMessageTabKind
    key: str
    title: str
    open_policy: GameMessageTabOpenPolicy = "passive"
    closeable: bool = False
    accent: str | None = None


class GameMessageDTO(GameMessageJsonDTO):
    id: str | None = None
    channel: GameMessageChannel
    tab: GameMessageTabDTO | None = None
    scope: str | None = None
    scope_id: str | None = None
    timestamp: float | None = None
    recipients: list[str] = Field(default_factory=list)
    template: GameMessageTemplateDTO
    variables: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    presentation: GameMessagePresentationDTO = Field(default_factory=GameMessagePresentationDTO)
    tags: list[str] = Field(default_factory=list)
