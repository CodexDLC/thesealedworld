from typing import Any, Literal

from pydantic import BaseModel, Field

PanelWidgetType = Literal[
    "avatar",
    "attribute_grid",
    "badges",
    "key_value",
    "list",
    "meter_list",
    "progress",
    "skill_groups",
    "text",
    "vitals",
]


class PanelWidgetDTO(BaseModel):
    type: PanelWidgetType | str
    id: str | None = None
    title: str | None = None
    variant: str | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    visible: bool = True


class PanelDTO(BaseModel):
    id: str
    title: str | None = None
    variant: str | None = None
    widgets: list[PanelWidgetDTO] = Field(default_factory=list)
