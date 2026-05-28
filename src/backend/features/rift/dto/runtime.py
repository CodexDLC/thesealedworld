from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.backend.features.rift.dto.screen import RiftAbsoluteDirection, RiftCoordinateDTO

RiftRuntimeCellState = Literal["open", "void"]
RiftRuntimePassageState = Literal["open", "blocked_temporary", "blocked_permanent", "locked", "void"]


class RiftTravelStartRequestDTO(BaseModel):
    target_node_id: str


class RiftTravelTickRequestDTO(BaseModel):
    travel_id: str
    force_event: Literal["none", "combat"] | None = None


class RiftActionRequestDTO(BaseModel):
    action_type: Literal["resolve_transition_combat", "resolve_node_event", "resolve_blocker", "resolve_heart"]
    action_id: str | None = None
    target_node_id: str | None = None
    direction: RiftAbsoluteDirection | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RiftStartRequestDTO(BaseModel):
    seed: str | None = None
    scale_preset_key: str | None = None
    assembly_preset_key: str | None = None
    void_cells: int | None = Field(default=None, ge=0)
    debug: bool = True


class RiftRebuildRequestDTO(BaseModel):
    seed: str | None = None
    scale_preset_key: str | None = None
    assembly_preset_key: str | None = None
    void_cells: int | None = Field(default=None, ge=0)


class RiftPoolGeneratedTextDTO(BaseModel):
    title: str
    description: str
    approach_view: dict[str, str] = Field(default_factory=dict)
    transition_text: dict[str, str] = Field(default_factory=dict)


class RiftPoolNodeDTO(BaseModel):
    pool_node_id: str
    node_hex: str
    source: str = "manual"
    axis_schema_version: int = 1
    pool_order: int = 0
    axes: dict[str, str] = Field(default_factory=dict)
    role_fit: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    generated_text: RiftPoolGeneratedTextDTO


class RiftZonePlacementDTO(BaseModel):
    cell_id: str
    x: int
    y: int
    pool_node_id: str


class RiftZoneCellDTO(BaseModel):
    node_id: str
    x: int
    y: int
    pool_node_id: str
    node_hex: str
    title: str
    description: str
    approach_view: dict[str, str] = Field(default_factory=dict)
    transition_text: dict[str, str] = Field(default_factory=dict)
    role_fit: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @property
    def coord(self) -> RiftCoordinateDTO:
        return RiftCoordinateDTO(x=self.x, y=self.y)


class RiftPassageEdgeDTO(BaseModel):
    from_node_id: str
    to_node_id: str
    absolute_direction: RiftAbsoluteDirection
    state: RiftRuntimePassageState
    blocker_key: str | None = None
    requirement: dict[str, Any] = Field(default_factory=dict)


class RiftZoneRuntimeDTO(BaseModel):
    rift_instance_id: str
    zone_instance_id: str
    zone_canvas_key: str
    scale_preset_key: str
    assembly_preset_key: str
    setting: dict[str, Any]
    scale_preset: dict[str, Any] = Field(default_factory=dict)
    assembly_preset: dict[str, Any] = Field(default_factory=dict)
    placements: list[RiftZonePlacementDTO] = Field(default_factory=list)
    nodes: dict[str, RiftZoneCellDTO]
    cells_by_coord: dict[str, str]
    passage_edges: dict[str, RiftPassageEdgeDTO] = Field(default_factory=dict)
    void_node_ids: set[str] = Field(default_factory=set)
    void_coords: list[RiftCoordinateDTO] = Field(default_factory=list)
    debug_map_width: int = 5
    debug_map_height: int = 5
    start_node_id: str
    finish_node_id: str
    current_node_id: str
    current_zone_key: str = "z01"
    zone_depth: int = 1
    zone_chain_order: list[str] = Field(default_factory=list)
    zone_chain: dict[str, dict[str, Any]] = Field(default_factory=dict)
    previous_node_id: str | None = None
    heading: RiftAbsoluteDirection | None = None
    visited_node_ids: set[str] = Field(default_factory=set)
    active_travel: dict[str, Any] | None = None
    last_travel: dict[str, Any] | None = None
    runtime_flags: set[str] = Field(default_factory=set)
    node_events: dict[str, dict[str, Any]] = Field(default_factory=dict)
    node_states: dict[str, dict[str, Any]] = Field(default_factory=dict)
    gate_states: dict[str, dict[str, Any]] = Field(default_factory=dict)
    heart_state: dict[str, Any] = Field(default_factory=dict)
    population_context: dict[str, Any] = Field(default_factory=dict)
    dev_character_snapshot: dict[str, Any] = Field(default_factory=dict)
    debug: bool = True

    def node_by_coord(self, coord: RiftCoordinateDTO) -> RiftZoneCellDTO | None:
        node_id = self.cells_by_coord.get(coord_key(coord.x, coord.y))
        return self.nodes.get(node_id) if node_id else None


def coord_key(x: int, y: int) -> str:
    return f"{x}:{y}"


def coord_from_key(value: str) -> RiftCoordinateDTO:
    raw_x, raw_y = value.split(":", 1)
    return RiftCoordinateDTO(x=int(raw_x), y=int(raw_y))
