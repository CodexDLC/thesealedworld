from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RiftAbsoluteDirection = Literal["north", "east", "south", "west"]
RiftRelativeDirection = Literal["forward", "left", "right", "back"]
RiftPassageState = Literal["open", "void", "blocked_permanent", "blocked_temporary", "locked", "unknown"]
RiftActionStyle = Literal["primary", "secondary", "danger", "disabled"]
RiftTravelKind = Literal["exploration", "return"]
RiftTransitionEventType = Literal["none", "combat"]
RiftNodeEntryEventType = Literal["none", "combat"]
RiftHeartMethod = Literal["shatter", "absorb", "dismantle"]
RiftMapNodeState = Literal["current", "open", "void", "blocked_permanent", "blocked_temporary", "locked", "unknown"]
RiftDebugCellState = Literal["current", "open", "void", "unknown"]
RiftExitMode = Literal["entrance_return_only", "heart_exit_only"]
RiftCompletionExit = Literal["from_heart", "return_to_exit"]
RiftExitAction = Literal["leave_rift", "complete_rift"]


def _default_transition_events() -> list[RiftTransitionEventType]:
    return ["none"]


def _default_node_entry_events() -> list[RiftNodeEntryEventType]:
    return ["none", "combat"]


class RiftCoordinateDTO(BaseModel):
    x: int
    y: int


class RiftScreenMetaDTO(BaseModel):
    rift_instance_id: str
    zone_instance_id: str
    zone_canvas_key: str
    current_zone_key: str | None = None
    zone_depth: int | None = None
    zone_chain_order: list[str] = Field(default_factory=list)
    zone_chain_total: int = 1
    schema_version: int = 1
    debug: bool = False


class RiftCurrentNodeDTO(BaseModel):
    node_id: str
    coord: RiftCoordinateDTO
    title: str
    description: str
    visited: bool = True
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None


class RiftSurroundingLineDTO(BaseModel):
    absolute_direction: RiftAbsoluteDirection
    relative_direction: RiftRelativeDirection | None = None
    state: RiftPassageState
    target_node_id: str | None = None
    text: str
    tone: Literal["open", "warning", "blocked", "unknown"] = "open"


class RiftTravelPreviewDTO(BaseModel):
    kind: RiftTravelKind
    duration_ms: int
    tick_interval_ms: int = 1000
    event_check_count: int = 0
    event_scope: Literal["transition"] = "transition"
    possible_events: list[RiftTransitionEventType] = Field(default_factory=_default_transition_events)
    can_trigger_event: bool = False
    event_chance: float = 0.0
    suppressed_by_target_node_event: bool = False
    target_node_event_key: str | None = None


class RiftNodeEntryCombatPolicyDTO(BaseModel):
    random_combat_suppressed_by_transition_combat: bool = True
    scripted_combat_suppresses_transition_combat: bool = True
    scripted_combat_tags: list[str] = Field(
        default_factory=lambda: [
            "boss",
            "crystal_guard",
            "objective_gate",
            "story_combat",
            "key_combat",
            "crystal_chamber",
        ]
    )


class RiftNodeEntryEventPreviewDTO(BaseModel):
    event_scope: Literal["node_entry"] = "node_entry"
    state: Literal["placeholder", "ready", "cleared"] = "placeholder"
    event_type: RiftNodeEntryEventType = "none"
    event_key: str | None = None
    title: str | None = None
    description: str | None = None
    is_required: bool = False
    grants_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    possible_events: list[RiftNodeEntryEventType] = Field(default_factory=_default_node_entry_events)
    combat_policy: RiftNodeEntryCombatPolicyDTO = Field(default_factory=RiftNodeEntryCombatPolicyDTO)


class RiftTravelResultDTO(BaseModel):
    from_node_id: str
    to_node_id: str
    kind: RiftTravelKind
    duration_ms: int
    event_scope: Literal["transition"] = "transition"
    event_triggered: bool = False
    event_type: RiftTransitionEventType = "none"
    title: str | None = None
    description: str | None = None


class RiftTravelStateDTO(BaseModel):
    travel_id: str
    status: Literal["moving", "interrupted", "completed"]
    event_scope: Literal["transition"] = "transition"
    tick_result: RiftTransitionEventType = "none"
    from_node_id: str
    to_node_id: str
    kind: RiftTravelKind
    duration_ms: int
    tick_interval_ms: int = 1000
    checks_done: int = 0
    checks_total: int = 0
    remaining_ms: int = 0
    possible_events: list[RiftTransitionEventType] = Field(default_factory=_default_transition_events)
    suppressed_by_target_node_event: bool = False
    target_node_event_key: str | None = None


class RiftCombatPromptEnemyDTO(BaseModel):
    name: str | None = None
    tier: int | None = None
    member_tier: int | None = None
    threat_rating: int | None = None
    hp_percent: int | None = None
    image: str | None = None
    visual: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    role: str | None = None
    variant_key: str | None = None
    monster_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    intel: dict[str, Any] = Field(default_factory=dict)


class RiftCombatPromptActionDTO(BaseModel):
    id: str
    label: str
    action: Literal["attack"]
    style: Literal["danger"] = "danger"
    is_active: bool = True


class RiftCombatPromptDTO(BaseModel):
    source: Literal["rift_transition"]
    title: str
    description: str
    enemies: list[RiftCombatPromptEnemyDTO] = Field(default_factory=list)
    actions: list[RiftCombatPromptActionDTO] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiftMovementActionDTO(BaseModel):
    id: str
    label: str
    action: Literal["move", "inspect_blocker", "none"] = "move"
    style: RiftActionStyle = "primary"
    is_active: bool = True
    target_node_id: str | None = None
    target_coord: RiftCoordinateDTO | None = None
    absolute_direction: RiftAbsoluteDirection
    relative_direction: RiftRelativeDirection | None = None
    state: RiftPassageState
    travel: RiftTravelPreviewDTO | None = None
    tooltip: str | None = None
    debug_text_parts: dict[str, Any] = Field(default_factory=dict)


class RiftRadarArmDTO(BaseModel):
    absolute_direction: RiftAbsoluteDirection
    relative_direction: RiftRelativeDirection | None = None
    state: RiftPassageState
    target_node_id: str | None = None
    target_coord: RiftCoordinateDTO | None = None
    is_available: bool = False
    is_visited: bool = False
    color_hint: str | None = None


class RiftRadarDTO(BaseModel):
    center_node_id: str
    heading: RiftAbsoluteDirection | None = None
    arms: list[RiftRadarArmDTO] = Field(default_factory=list)


class RiftMapViewNodeDTO(BaseModel):
    node_id: str
    coord: RiftCoordinateDTO
    title: str
    state: RiftMapNodeState
    visited: bool = False
    discovered: bool = True


class RiftMapViewEdgeDTO(BaseModel):
    from_node_id: str
    to_node_id: str | None = None
    absolute_direction: RiftAbsoluteDirection
    relative_direction: RiftRelativeDirection | None = None
    state: RiftPassageState


class RiftMapViewDTO(BaseModel):
    center_node_id: str
    current_coord: RiftCoordinateDTO
    heading: RiftAbsoluteDirection | None = None
    visible_nodes: list[RiftMapViewNodeDTO] = Field(default_factory=list)
    visible_edges: list[RiftMapViewEdgeDTO] = Field(default_factory=list)


class RiftDebugMapCellDTO(BaseModel):
    node_id: str | None = None
    coord: RiftCoordinateDTO
    title: str | None = None
    state: RiftDebugCellState = "open"
    visited: bool = False
    discovered: bool = False


class RiftDebugMapEdgeDTO(BaseModel):
    from_node_id: str
    to_node_id: str
    from_coord: RiftCoordinateDTO
    to_coord: RiftCoordinateDTO
    state: Literal["open", "blocked_temporary", "blocked_permanent", "locked", "void"]


class RiftDebugMapDTO(BaseModel):
    width: int = 5
    height: int = 5
    cells: list[RiftDebugMapCellDTO] = Field(default_factory=list)
    passage_edges: list[RiftDebugMapEdgeDTO] = Field(default_factory=list)


class RiftObjectiveDTO(BaseModel):
    type: str
    title: str
    description: str = ""
    progress_label: str | None = None
    is_complete: bool = False


class RiftHudDTO(BaseModel):
    title: str
    subtitle: str | None = None
    tier: int = 0
    danger_label: str | None = None
    objective: RiftObjectiveDTO | None = None


class RiftHeartMethodDTO(BaseModel):
    method: RiftHeartMethod
    label: str
    enabled: bool = False
    locked_reason: str | None = None


class RiftHeartRewardDTO(BaseModel):
    lost_value: int = 0
    symbiote_xp: int = 0
    resource_value: int = 0
    resource_template_id: str = "currency_dust"


class RiftHeartDTO(BaseModel):
    node_id: str
    status: Literal["intact", "shattered", "absorbed", "dismantled"] = "intact"
    tier: int = 1
    base_value: int = 100
    is_current_node: bool = False
    methods: list[RiftHeartMethodDTO] = Field(default_factory=list)
    resolved_method: RiftHeartMethod | None = None
    reward: RiftHeartRewardDTO | None = None
    can_exit: bool = False


class RiftExitActionDTO(BaseModel):
    action: RiftExitAction
    label: str
    style: RiftActionStyle = "primary"
    is_active: bool = True


class RiftExitDTO(BaseModel):
    mode: RiftExitMode = "heart_exit_only"
    completion_exit: RiftCompletionExit = "from_heart"
    entrance_seals_on_entry: bool = True
    can_leave: bool = False
    can_complete: bool = False
    reason: str | None = None
    entrance_node_id: str | None = None
    exit_node_id: str | None = None
    target_state: str = "exploration"
    location_id: str | None = None
    close_rift_on_exit: bool = True
    actions: list[RiftExitActionDTO] = Field(default_factory=list)


class RiftScreenDTO(BaseModel):
    meta: RiftScreenMetaDTO
    hud: RiftHudDTO
    current_node: RiftCurrentNodeDTO
    surroundings: list[RiftSurroundingLineDTO] = Field(default_factory=list)
    movement: list[RiftMovementActionDTO] = Field(default_factory=list)
    radar: RiftRadarDTO
    map_view: RiftMapViewDTO
    node_entry_event: RiftNodeEntryEventPreviewDTO = Field(default_factory=RiftNodeEntryEventPreviewDTO)
    heart: RiftHeartDTO | None = None
    exit: RiftExitDTO = Field(default_factory=RiftExitDTO)
    last_travel: RiftTravelResultDTO | None = None
    debug_map: RiftDebugMapDTO | None = None
    messages: list[str] = Field(default_factory=list)


class RiftTravelTickResponseDTO(BaseModel):
    travel: RiftTravelStateDTO
    combat_prompt: RiftCombatPromptDTO | None = None
    screen: RiftScreenDTO | None = None


class RiftCombatResolveResponseDTO(BaseModel):
    result: Literal["victory"]
    message: str
    screen: RiftScreenDTO


class RiftNodeEventResolveResponseDTO(BaseModel):
    result: Literal["victory"]
    message: str
    granted_flags: list[str] = Field(default_factory=list)
    screen: RiftScreenDTO


class RiftActionResponseDTO(BaseModel):
    action_type: str
    result: Literal["success", "failure", "victory"]
    message: str
    screen: RiftScreenDTO
    details: dict[str, Any] = Field(default_factory=dict)
    granted_flags: list[str] = Field(default_factory=list)


class RiftExitResponseDTO(BaseModel):
    result: Literal["success"] = "success"
    action: RiftExitAction
    target_state: str
    location_id: str | None = None
    rift_session_id: str
    rift_instance_id: str
    exit_reason: Literal["left", "completed"]
    close_rift_on_exit: bool = True
    details: dict[str, Any] = Field(default_factory=dict)
