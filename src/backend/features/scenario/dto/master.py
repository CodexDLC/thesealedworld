from typing import Any, Literal

from pydantic import BaseModel, Field


class StatusBarFieldSchema(BaseModel):
    key: str
    label: str = ""


class AnalyticsConfigSchema(BaseModel):
    mapping: dict[str, Any] = Field(default_factory=dict)


class BranchSchema(BaseModel):
    condition: str | None = None
    to_node: str | None = None
    math: dict[str, Any] = Field(default_factory=dict)


class ActionLogicSchema(BaseModel):
    label: str | None = None
    icon: str | None = "default"
    condition: str | None = None
    to_node: str | None = None
    math: dict[str, Any] = Field(default_factory=dict)
    branching: list[BranchSchema] = Field(default_factory=list)
    type: Literal["finish_quest", "next", "auto", "logic_gate"] | str | None = None


class QuestMasterSchema(BaseModel):
    quest_key: str
    display_name: str | None = "UNKNOWN_QUEST"
    start_node_id: str
    status_bar_fields: list[StatusBarFieldSchema] = Field(default_factory=list)
    analytics_config: AnalyticsConfigSchema | None = None
    config: dict[str, Any] | None = None
    init_sync: dict[str, Any] | None = None
    export_sync: dict[str, Any] | None = None


class QuestNodeSchema(BaseModel):
    node_key: str
    quest_key: str | None = None
    display_name: str | None = None
    text: str = Field(default="[System: Logic Processing...]")
    system_messages: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    selection_requirements: str | None = None
    is_terminal: bool = False
    actions: list[ActionLogicSchema] = Field(default_factory=list)
    actions_logic: dict[str, ActionLogicSchema] = Field(default_factory=dict)


class QuestFileSchema(BaseModel):
    master: QuestMasterSchema
    nodes: list[QuestNodeSchema]
