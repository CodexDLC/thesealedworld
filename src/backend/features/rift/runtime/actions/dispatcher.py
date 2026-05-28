from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.rift.dto.screen import RiftActionResponseDTO
from src.backend.features.rift.runtime.geometry import direction_between
from src.backend.features.rift.runtime.navigation.screen_builder import (
    build_rift_screen,
    resolve_heart_runtime,
    resolve_node_entry_event_runtime,
    resolve_transition_combat_runtime,
)

if TYPE_CHECKING:
    from src.backend.features.rift.dto.runtime import RiftActionRequestDTO, RiftZoneRuntimeDTO

_OPPOSITE_DIRECTION = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
}

_ATTRIBUTE_ALIASES = {
    "dexterity": "agility",
    "intelligence": "intellect",
}


def resolve_rift_action_runtime(
    runtime: RiftZoneRuntimeDTO,
    request: RiftActionRequestDTO,
) -> tuple[RiftZoneRuntimeDTO, RiftActionResponseDTO]:
    handlers = {
        "resolve_transition_combat": _resolve_transition_combat_action,
        "resolve_node_event": _resolve_node_event_action,
        "resolve_blocker": _resolve_blocker_action,
        "resolve_heart": _resolve_heart_action,
    }
    handler = handlers.get(request.action_type)
    if handler is None:
        raise ValueError(f"Unsupported rift action type: {request.action_type}")
    return handler(runtime, request)


def _resolve_transition_combat_action(
    runtime: RiftZoneRuntimeDTO,
    request: RiftActionRequestDTO,
) -> tuple[RiftZoneRuntimeDTO, RiftActionResponseDTO]:
    payload = dict(request.payload or {})
    updated, response = resolve_transition_combat_runtime(
        runtime,
        travel_id=str(payload.get("travel_id") or request.action_id or ""),
        result=str(payload.get("result") or "victory"),
    )
    return updated, RiftActionResponseDTO(
        action_type=request.action_type,
        result="victory",
        message=response.message,
        screen=response.screen,
        details={"travel_id": payload.get("travel_id") or request.action_id},
    )


def _resolve_node_event_action(
    runtime: RiftZoneRuntimeDTO,
    request: RiftActionRequestDTO,
) -> tuple[RiftZoneRuntimeDTO, RiftActionResponseDTO]:
    payload = dict(request.payload or {})
    updated, response = resolve_node_entry_event_runtime(
        runtime,
        event_key=payload.get("event_key") or request.action_id,
        result=str(payload.get("result") or "victory"),
    )
    return updated, RiftActionResponseDTO(
        action_type=request.action_type,
        result="victory",
        message=response.message,
        granted_flags=response.granted_flags,
        screen=response.screen,
        details={"event_key": payload.get("event_key") or request.action_id},
    )


def _resolve_heart_action(
    runtime: RiftZoneRuntimeDTO,
    request: RiftActionRequestDTO,
) -> tuple[RiftZoneRuntimeDTO, RiftActionResponseDTO]:
    payload = dict(request.payload or {})
    method = str(payload.get("method") or request.action_id or "shatter")
    updated, heart = resolve_heart_runtime(runtime, method=method)
    return updated, RiftActionResponseDTO(
        action_type=request.action_type,
        result="success",
        message="Rift heart shattered. The rift can now be closed.",
        screen=build_rift_screen(updated),
        details={
            "method": method,
            "heart": heart,
        },
    )


def _resolve_blocker_action(
    runtime: RiftZoneRuntimeDTO,
    request: RiftActionRequestDTO,
) -> tuple[RiftZoneRuntimeDTO, RiftActionResponseDTO]:
    direction = request.direction
    if direction is None:
        raise ValueError("Rift blocker action requires direction")
    edge = runtime.passage_edges.get(f"{runtime.current_node_id}:{direction}")
    if edge is None or edge.state != "blocked_temporary":
        raise ValueError("Current rift passage is not a temporary blocker")
    if request.target_node_id and edge.to_node_id != request.target_node_id:
        raise ValueError("Rift blocker target does not match current passage")

    requirement = dict(edge.requirement or {})
    check = dict(requirement.get("check") or {})
    attribute_key = str(check.get("key") or "")
    dc = int(check.get("dc") or 0)
    if not attribute_key or dc <= 0:
        raise ValueError("Temporary blocker does not define an attribute check")

    attributes = _action_attributes(runtime, payload=dict(request.payload or {}))
    attribute_value = int(attributes.get(attribute_key) or 0)
    success = attribute_value >= dc
    if not success:
        screen = build_rift_screen(runtime)
        return runtime, RiftActionResponseDTO(
            action_type=request.action_type,
            result="failure",
            message=f"Check failed: {attribute_key} {attribute_value}/{dc}.",
            screen=screen,
            details={
                "target_node_id": edge.to_node_id,
                "direction": direction,
                "check": check,
                "attribute_value": attribute_value,
            },
        )

    passage_edges = dict(runtime.passage_edges)
    reverse_direction = _OPPOSITE_DIRECTION[direction]
    for edge_key in [f"{edge.from_node_id}:{direction}", f"{edge.to_node_id}:{reverse_direction}"]:
        current_edge = passage_edges.get(edge_key)
        if current_edge is not None:
            passage_edges[edge_key] = current_edge.model_copy(
                update={
                    "state": "open",
                    "blocker_key": None,
                    "requirement": {},
                }
            )
    visited = set(runtime.visited_node_ids)
    visited.add(edge.to_node_id)
    current = runtime.nodes[edge.from_node_id]
    target = runtime.nodes[edge.to_node_id]
    traversal_direction = direction_between(current.coord, target.coord)
    last_travel = {
        "from_node_id": edge.from_node_id,
        "to_node_id": edge.to_node_id,
        "kind": "exploration",
        "duration_ms": 0,
        "event_scope": "transition",
        "event_triggered": False,
        "event_type": "none",
        "title": None,
        "description": None,
        "resolved": True,
        "result": "blocker_passed",
        "suppress_random_node_combat": True,
    }
    updated = runtime.model_copy(
        update={
            "passage_edges": passage_edges,
            "previous_node_id": edge.from_node_id,
            "current_node_id": edge.to_node_id,
            "heading": traversal_direction,
            "visited_node_ids": visited,
            "active_travel": None,
            "last_travel": last_travel,
        }
    )
    return updated, RiftActionResponseDTO(
        action_type=request.action_type,
        result="success",
        message=f"Temporary blocker passed: {attribute_key} {attribute_value}/{dc}.",
        screen=build_rift_screen(updated),
        details={
            "target_node_id": edge.to_node_id,
            "direction": direction,
            "check": check,
            "attribute_value": attribute_value,
            "entered_node_id": edge.to_node_id,
        },
    )


def _action_attributes(runtime: RiftZoneRuntimeDTO, *, payload: dict[str, Any]) -> dict[str, int]:
    raw_attributes = dict(payload.get("attributes") or {})
    if raw_attributes:
        return _with_attribute_aliases({str(key): int(value) for key, value in raw_attributes.items()})
    character = dict(dict(runtime.dev_character_snapshot or {}).get("character") or {})
    return _with_attribute_aliases(
        {str(key): int(value) for key, value in dict(character.get("attributes") or {}).items()}
    )


def _with_attribute_aliases(attributes: dict[str, int]) -> dict[str, int]:
    normalized = dict(attributes)
    for legacy_key, canonical_key in _ATTRIBUTE_ALIASES.items():
        if legacy_key not in normalized and canonical_key in normalized:
            normalized[legacy_key] = normalized[canonical_key]
        if canonical_key not in normalized and legacy_key in normalized:
            normalized[canonical_key] = normalized[legacy_key]
    return normalized
