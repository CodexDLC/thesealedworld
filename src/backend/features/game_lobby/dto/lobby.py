from pydantic import BaseModel, Field


class LobbySlotDTO(BaseModel):
    index: int
    is_empty: bool = True
    character_id: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    status: str = "VACANT"


class GameLobbyPayloadDTO(BaseModel):
    title: str = "The Threshold"
    description: str = "The neural gate is quiet. Begin the journey when you are ready to shape a new vessel."
    primary_action_label: str = "Начать приключение"
    primary_action: str = "start_adventure"
    message: str | None = None
    max_slots: int = 4
    can_start: bool = True
    slots: list[LobbySlotDTO] = Field(default_factory=list)
