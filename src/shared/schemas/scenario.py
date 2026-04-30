from typing import Any

from pydantic import BaseModel, Field


class ScenarioButtonDTO(BaseModel):
    label: str = Field(..., description="Action button label")
    action_id: str = Field(..., description="Action id passed to ScenarioService.step")
    icon: str | None = Field(None, description="Icon for the action hint")


class ScenarioPayloadDTO(BaseModel):
    node_key: str
    text: str
    alerts: list[str] = Field(default_factory=list)
    status_bar: list[str] = Field(default_factory=list)
    buttons: list[ScenarioButtonDTO] = Field(default_factory=list)
    is_terminal: bool = False
    display_name: str | None = None
    icon: str | None = None
    avatar: str | None = None
    extra_data: dict[str, Any] | None = None
