from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ScenarioNodeType(StrEnum):
    DIALOG = "dialog"
    EVENT = "event"
    ROUTER = "router"
    REWARD_CHOICE = "reward_choice"
    REWARD_RESULT = "reward_result"
    TRANSITION = "transition"
    EXIT = "exit"


class ScenarioType(StrEnum):
    UNIQUE = "unique_scenario"
    DIALOGUE = "dialogue_scenario"


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
    action_id: str | None = None
    label: str | None = None
    icon: str | None = "default"
    condition: str | None = None
    to_node: str | None = None
    math: dict[str, Any] = Field(default_factory=dict)
    branching: list[BranchSchema] = Field(default_factory=list)
    effects: list[dict[str, Any]] = Field(default_factory=list)
    type: Literal["finish_quest", "next", "auto", "logic_gate"] | str | None = None


class QuestMasterSchema(BaseModel):
    quest_key: str
    scenario_type: ScenarioType
    display_name: str | None = "UNKNOWN_QUEST"
    npc_key: str | None = None
    background_url: str | None = None
    start_node_id: str
    status_bar_fields: list[StatusBarFieldSchema] = Field(default_factory=list)
    analytics_config: AnalyticsConfigSchema | None = None
    config: dict[str, Any] | None = None
    init_sync: dict[str, Any] | None = None
    export_sync: dict[str, Any] | None = None
    ui: dict[str, Any] = Field(default_factory=dict)


class QuestNodeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_key: str
    quest_key: str | None = None
    node_type: ScenarioNodeType = ScenarioNodeType.EVENT
    phase: str | None = None
    speaker: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    ui: dict[str, Any] = Field(default_factory=dict)
    display_name: str | None = None
    icon: str | None = None
    avatar: str | None = None
    background_url: str | None = None
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
