from __future__ import annotations

import hashlib
from typing import Any, cast

from src.backend.features.rift.dto.runtime import RiftZoneRuntimeDTO, coord_key
from src.backend.features.rift.dto.screen import (
    RiftAbsoluteDirection,
    RiftCombatPromptActionDTO,
    RiftCombatPromptDTO,
    RiftCombatPromptEnemyDTO,
    RiftCombatResolveResponseDTO,
    RiftCoordinateDTO,
    RiftCurrentNodeDTO,
    RiftDebugCellState,
    RiftDebugMapCellDTO,
    RiftDebugMapDTO,
    RiftDebugMapEdgeDTO,
    RiftExitActionDTO,
    RiftExitDTO,
    RiftHeartDTO,
    RiftHeartMethod,
    RiftHeartMethodDTO,
    RiftHeartRewardDTO,
    RiftHudDTO,
    RiftMapNodeState,
    RiftMapViewDTO,
    RiftMapViewEdgeDTO,
    RiftMapViewNodeDTO,
    RiftMovementActionDTO,
    RiftNodeEntryEventPreviewDTO,
    RiftNodeEventResolveResponseDTO,
    RiftObjectiveDTO,
    RiftPassageState,
    RiftRadarArmDTO,
    RiftRadarDTO,
    RiftScreenDTO,
    RiftScreenMetaDTO,
    RiftSurroundingLineDTO,
    RiftTransitionEventType,
    RiftTravelPreviewDTO,
    RiftTravelResultDTO,
    RiftTravelStateDTO,
    RiftTravelTickResponseDTO,
)
from src.backend.features.rift.runtime.geometry import (
    ORDERED_DIRECTIONS,
    direction_between,
    neighbor_coord,
    relative_direction,
)
from src.backend.features.rift.runtime.tunables import current_tunables

_COLOR_BY_STATE = {
    "open": "green",
    "void": "black",
    "blocked_permanent": "amber",
    "blocked_temporary": "amber",
    "locked": "amber",
    "unknown": "gray",
}

_SCRIPTED_COMBAT_NODE_KEYS = {
    "boss",
    "crystal_guard",
    "objective_gate",
    "story_combat",
    "key_combat",
    "crystal_chamber",
}


def _screen_passage_state(value: str) -> RiftPassageState:
    return cast("RiftPassageState", value)


def _screen_transition_event(value: str) -> RiftTransitionEventType:
    return cast("RiftTransitionEventType", value)


def _screen_map_node_state(value: str) -> RiftMapNodeState:
    return cast("RiftMapNodeState", value)


_ATTRIBUTE_LABELS = {
    "strength": "Сила",
    "agility": "Ловкость",
    "intellect": "Интеллект",
    "intelligence": "Интеллект",
    "dexterity": "Ловкость",
}

_ATTRIBUTE_ALIASES = {
    "dexterity": "agility",
    "intelligence": "intellect",
}


def build_rift_screen(runtime: RiftZoneRuntimeDTO) -> RiftScreenDTO:
    current = runtime.nodes[runtime.current_node_id]
    heading = _resolve_heading(runtime)
    return RiftScreenDTO(
        meta=RiftScreenMetaDTO(
            rift_instance_id=runtime.rift_instance_id,
            zone_instance_id=runtime.zone_instance_id,
            zone_canvas_key=runtime.zone_canvas_key,
            current_zone_key=runtime.current_zone_key,
            zone_depth=runtime.zone_depth,
            zone_chain_order=runtime.zone_chain_order,
            zone_chain_total=len(runtime.zone_chain_order) or 1,
            debug=runtime.debug,
        ),
        hud=_build_hud(runtime),
        current_node=RiftCurrentNodeDTO(
            node_id=current.node_id,
            coord=current.coord,
            title=current.title,
            description=current.description,
            visited=True,
            tags=current.tags,
        ),
        surroundings=_build_surroundings(runtime, heading=heading),
        movement=_build_movement(runtime, heading=heading),
        radar=_build_radar(runtime, heading=heading),
        map_view=_build_map_view(runtime, heading=heading),
        node_entry_event=_build_node_entry_event(runtime),
        heart=_build_heart(runtime),
        exit=_build_exit(runtime),
        last_travel=RiftTravelResultDTO.model_validate(runtime.last_travel) if runtime.last_travel else None,
        debug_map=_build_debug_map(runtime) if runtime.debug else None,
    )


def start_travel_runtime(
    runtime: RiftZoneRuntimeDTO, target_node_id: str
) -> tuple[RiftZoneRuntimeDTO, RiftTravelTickResponseDTO]:
    current, target, direction = _validated_open_target(runtime, target_node_id)
    preview = _build_travel_preview(runtime, target_node_id)
    checks_total = max(
        preview.event_check_count,
        _travel_tick_count(duration_ms=preview.duration_ms, tick_interval_ms=preview.tick_interval_ms),
    )
    travel_id = _travel_id(runtime, from_node_id=current.node_id, to_node_id=target.node_id)
    active_travel = {
        "travel_id": travel_id,
        "status": "moving",
        "event_scope": "transition",
        "tick_result": "none",
        "from_node_id": current.node_id,
        "to_node_id": target.node_id,
        "kind": preview.kind,
        "duration_ms": preview.duration_ms,
        "tick_interval_ms": preview.tick_interval_ms,
        "checks_done": 0,
        "checks_total": checks_total,
        "remaining_ms": preview.duration_ms,
        "possible_events": preview.possible_events,
        "can_trigger_event": preview.can_trigger_event,
        "event_chance": preview.event_chance,
        "suppressed_by_target_node_event": preview.suppressed_by_target_node_event,
        "target_node_event_key": preview.target_node_event_key,
        "direction": direction,
    }
    updated = runtime.model_copy(update={"active_travel": active_travel, "last_travel": None})
    return updated, RiftTravelTickResponseDTO(travel=RiftTravelStateDTO.model_validate(active_travel))


def tick_travel_runtime(
    runtime: RiftZoneRuntimeDTO,
    *,
    travel_id: str,
    force_event: str | None = None,
) -> tuple[RiftZoneRuntimeDTO, RiftTravelTickResponseDTO]:
    active_travel = dict(runtime.active_travel or {})
    if not active_travel:
        raise ValueError("Rift travel is not active")
    if active_travel.get("travel_id") != travel_id:
        raise ValueError("Rift travel id does not match active travel")
    if active_travel.get("status") == "interrupted":
        return runtime, RiftTravelTickResponseDTO(
            travel=RiftTravelStateDTO.model_validate(active_travel),
            combat_prompt=_transition_combat_prompt(runtime, active_travel=active_travel),
        )
    if active_travel.get("status") != "moving":
        return runtime, RiftTravelTickResponseDTO(travel=RiftTravelStateDTO.model_validate(active_travel))

    checks_total = int(active_travel.get("checks_total") or 0)
    if checks_total <= 0:
        checks_total = _travel_tick_count(
            duration_ms=int(active_travel.get("duration_ms") or 0),
            tick_interval_ms=int(active_travel.get("tick_interval_ms") or 1000),
        )
        active_travel["checks_total"] = checks_total
    checks_done = int(active_travel.get("checks_done") or 0)
    next_check = checks_done + 1
    tick_result = _resolve_transition_tick_event(
        runtime, active_travel=active_travel, next_check=next_check, force_event=force_event
    )
    active_travel["checks_done"] = next_check
    active_travel["tick_result"] = tick_result
    active_travel["remaining_ms"] = max(
        0,
        int(active_travel.get("duration_ms") or 0) - next_check * int(active_travel.get("tick_interval_ms") or 1000),
    )

    if tick_result == "combat":
        active_travel["status"] = "interrupted"
        updated = runtime.model_copy(update={"active_travel": active_travel})
        return updated, RiftTravelTickResponseDTO(
            travel=RiftTravelStateDTO.model_validate(active_travel),
            combat_prompt=_transition_combat_prompt(updated, active_travel=active_travel),
        )

    if next_check >= checks_total:
        updated = _complete_travel(runtime, active_travel=active_travel)
        completed_travel = {
            **active_travel,
            "status": "completed",
            "tick_result": "none",
            "remaining_ms": 0,
        }
        node_entry_prompt = _node_entry_combat_prompt(updated)
        return updated, RiftTravelTickResponseDTO(
            travel=RiftTravelStateDTO.model_validate(completed_travel),
            combat_prompt=node_entry_prompt,
            screen=None if node_entry_prompt is not None else build_rift_screen(updated),
        )

    updated = runtime.model_copy(update={"active_travel": active_travel})
    return updated, RiftTravelTickResponseDTO(travel=RiftTravelStateDTO.model_validate(active_travel))


def resolve_transition_combat_runtime(
    runtime: RiftZoneRuntimeDTO,
    *,
    travel_id: str,
    result: str = "victory",
) -> tuple[RiftZoneRuntimeDTO, RiftCombatResolveResponseDTO]:
    if result != "victory":
        raise ValueError("Only victory result is supported by the rift dev combat placeholder")
    active_travel = dict(runtime.active_travel or {})
    if not active_travel:
        raise ValueError("Rift travel is not active")
    if active_travel.get("travel_id") != travel_id:
        raise ValueError("Rift travel id does not match active travel")
    if active_travel.get("status") != "interrupted" or active_travel.get("tick_result") != "combat":
        raise ValueError("Rift travel is not interrupted by transition combat")

    updated = _complete_travel(
        runtime,
        active_travel=active_travel,
        event_triggered=True,
        event_type="combat",
        resolved=True,
        result=result,
        suppress_random_node_combat=current_tunables().transition_suppress_ordinary_after_combat,
    )
    return updated, RiftCombatResolveResponseDTO(
        result="victory",
        message="Transition combat placeholder resolved. Travel completed into the target node.",
        screen=build_rift_screen(updated),
    )


def resolve_node_entry_event_runtime(
    runtime: RiftZoneRuntimeDTO,
    *,
    event_key: str | None = None,
    result: str = "victory",
) -> tuple[RiftZoneRuntimeDTO, RiftNodeEventResolveResponseDTO]:
    if result != "victory":
        raise ValueError("Only victory result is supported by the rift dev node event placeholder")
    current_event = dict(runtime.node_events.get(runtime.current_node_id) or {})
    if not current_event:
        raise ValueError("Current rift node has no entry event")
    if event_key and current_event.get("event_key") != event_key:
        raise ValueError("Rift node event key does not match current node event")
    if current_event.get("event_type") != "combat":
        raise ValueError("Only combat node events are supported by the dev resolver")

    granted_flags = [str(flag) for flag in current_event.get("grants_flags", []) if flag]
    node_events = dict(runtime.node_events)
    node_events[runtime.current_node_id] = {**current_event, "state": "cleared", "resolved_result": result}
    node_states = dict(runtime.node_states)
    current_state = dict(node_states.get(runtime.current_node_id) or {})
    node_states[runtime.current_node_id] = {
        **current_state,
        "entry_event_state": "cleared",
        "ordinary_event_state": "cleared"
        if current_event.get("source") == "ordinary_roll"
        else current_state.get("ordinary_event_state"),
        "event_key": current_event.get("event_key"),
    }
    runtime_flags = set(runtime.runtime_flags)
    runtime_flags.update(granted_flags)
    gate_states = _apply_granted_flags_to_gate_states(runtime.gate_states, runtime_flags)
    updated = runtime.model_copy(
        update={
            "runtime_flags": runtime_flags,
            "node_events": node_events,
            "node_states": node_states,
            "gate_states": gate_states,
        }
    )
    transition = dict(current_event.get("transition") or {})
    if transition.get("type") == "next_zone":
        updated = _activate_next_zone(updated, next_zone_key=str(transition.get("next_zone_key") or ""))
    return updated, RiftNodeEventResolveResponseDTO(
        result="victory",
        message=_node_event_resolve_message(current_event),
        granted_flags=granted_flags,
        screen=build_rift_screen(updated),
    )


def resolve_heart_runtime(
    runtime: RiftZoneRuntimeDTO,
    *,
    method: str = "shatter",
) -> tuple[RiftZoneRuntimeDTO, dict[str, Any]]:
    heart = _normalized_heart_state(runtime)
    if runtime.current_node_id != heart["node_id"]:
        raise ValueError("Rift heart can only be resolved from the heart node")
    if not _is_heart_node(runtime.nodes.get(str(heart["node_id"]))):
        raise ValueError("Rift heart node metadata is invalid")
    if heart["status"] != "intact":
        raise ValueError("Rift heart is already resolved")
    if method != "shatter":
        raise ValueError("Only shatter is available in the rift heart MVP")

    reward = _heart_reward(tier=int(heart["tier"]), base_value=int(heart["base_value"]), method=method)
    updated_heart = {
        **heart,
        "status": "shattered",
        "resolved_method": method,
        "reward": reward,
        "can_exit": True,
        "completion": {
            "status": "completed",
            "reason": "heart_shattered",
        },
    }
    updated = runtime.model_copy(update={"heart_state": updated_heart})
    return updated, updated_heart


def _validated_open_target(
    runtime: RiftZoneRuntimeDTO,
    target_node_id: str,
):
    if target_node_id not in runtime.nodes:
        raise ValueError(f"Unknown rift target node: {target_node_id}")
    if target_node_id in runtime.void_node_ids:
        raise ValueError("Target rift node is void")

    current = runtime.nodes[runtime.current_node_id]
    target = runtime.nodes[target_node_id]
    direction = direction_between(current.coord, target.coord)
    if direction is None:
        raise ValueError("Target rift node is not adjacent")
    edge = _edge_for(runtime, direction)
    if edge is None or edge.to_node_id != target_node_id or _effective_edge_state(runtime, edge) != "open":
        raise ValueError("Target rift passage is not open")
    if _is_heart_node(target) and not _heart_access_unlocked(runtime, target_node_id):
        raise ValueError("Rift heart is locked by its guard")
    return current, target, direction


def _build_hud(runtime: RiftZoneRuntimeDTO) -> RiftHudDTO:
    screen = dict(runtime.setting.get("screen") or {})
    raw_objective = dict(screen.get("objective") or {})
    heart = _normalized_heart_state(runtime)
    heart_resolved = heart.get("status") != "intact"
    objective = RiftObjectiveDTO(
        type=str(raw_objective.get("type") or "reach_exit"),
        title=str(raw_objective.get("title") or "Найти выход"),
        description=str(raw_objective.get("description") or ""),
        progress_label="Сердце разрушено" if heart_resolved else raw_objective.get("progress_label"),
        is_complete=heart_resolved,
    )
    return RiftHudDTO(
        title=str(screen.get("title") or dict(runtime.setting.get("profile") or {}).get("title") or "Rift"),
        subtitle=screen.get("subtitle"),
        tier=max(1, int(screen.get("tier") or 1)),
        danger_label=screen.get("danger_label"),
        objective=objective,
    )


def _build_heart(runtime: RiftZoneRuntimeDTO) -> RiftHeartDTO:
    heart = _normalized_heart_state(runtime)
    return RiftHeartDTO(
        node_id=str(heart["node_id"]),
        status=heart.get("status", "intact"),
        tier=int(heart["tier"]),
        base_value=int(heart["base_value"]),
        is_current_node=runtime.current_node_id == heart["node_id"],
        methods=[
            RiftHeartMethodDTO(
                method=cast("RiftHeartMethod", str(method["method"])),
                label=str(method["label"]),
                enabled=bool(method.get("enabled")),
                locked_reason=method.get("locked_reason"),
            )
            for method in heart.get("methods", [])
            if isinstance(method, dict)
        ],
        resolved_method=heart.get("resolved_method"),
        reward=RiftHeartRewardDTO.model_validate(heart["reward"]) if isinstance(heart.get("reward"), dict) else None,
        can_exit=bool(heart.get("can_exit")),
    )


def _build_exit(runtime: RiftZoneRuntimeDTO) -> RiftExitDTO:
    policy = _normalized_exit_policy(runtime)
    mode = str(policy.get("mode") or "heart_exit_only")
    completion_exit = str(policy.get("completion_exit") or "from_heart")
    heart = _normalized_heart_state(runtime)
    completion_available = _completion_available(runtime, heart)
    entrance_node_id = str(policy.get("entrance_node_id") or runtime.start_node_id)
    exit_node_id = str(policy.get("exit_node_id") or entrance_node_id)
    can_leave = mode == "entrance_return_only" and runtime.current_node_id == entrance_node_id
    at_completion_exit = completion_exit == "from_heart" or runtime.current_node_id == exit_node_id
    can_complete = mode == "heart_exit_only" and completion_available and at_completion_exit
    reason = None
    if mode == "entrance_return_only" and not can_leave:
        reason = "not_at_entrance"
    elif mode == "heart_exit_only" and completion_available and not at_completion_exit:
        reason = "return_to_exit_required"
    elif mode == "heart_exit_only" and not can_complete:
        reason = "heart_required"

    actions: list[RiftExitActionDTO] = []
    if can_leave:
        actions.append(RiftExitActionDTO(action="leave_rift", label="Выйти из разлома", style="secondary"))
    if can_complete:
        actions.append(RiftExitActionDTO(action="complete_rift", label="Выбраться из разлома", style="primary"))
    return RiftExitDTO(
        mode=mode,  # type: ignore[arg-type]
        completion_exit=completion_exit,  # type: ignore[arg-type]
        entrance_seals_on_entry=bool(policy.get("entrance_seals_on_entry", mode == "heart_exit_only")),
        can_leave=can_leave,
        can_complete=can_complete,
        reason=reason,
        entrance_node_id=entrance_node_id,
        exit_node_id=exit_node_id,
        target_state=str(policy.get("target_state") or "exploration"),
        location_id=str(policy.get("location_id") or "") or None,
        close_rift_on_exit=bool(policy.get("close_rift_on_exit", True)),
        actions=actions,
    )


def _build_surroundings(
    runtime: RiftZoneRuntimeDTO, *, heading: RiftAbsoluteDirection | None
) -> list[RiftSurroundingLineDTO]:
    result: list[RiftSurroundingLineDTO] = []
    templates = _templates(runtime)
    for direction in ORDERED_DIRECTIONS:
        neighbor = _neighbor_for(runtime, direction)
        rel = relative_direction(heading=heading, direction=direction)
        if neighbor is None:
            neighbor_coord_value = _neighbor_coord_for(runtime, direction)
            if not _is_void_coord(runtime, neighbor_coord_value):
                continue
            surface = _void_surface(runtime, coord=neighbor_coord_value, direction=direction)
            text = str(templates.get("void_surrounding") or "{relative_capitalized} {void_suffix}.").format(
                relative_capitalized=_relative_label(runtime, rel, capitalize=True),
                void_suffix=surface["narrative_line"],
            )
            result.append(
                RiftSurroundingLineDTO(
                    absolute_direction=direction,
                    relative_direction=rel,
                    state="void",
                    target_node_id=None,
                    text=text,
                    tone="blocked",
                )
            )
            continue
        state = "void" if neighbor.node_id in runtime.void_node_ids else "open"
        state = _passage_state_for(runtime, direction, neighbor.node_id)
        view = neighbor.approach_view
        if state == "open":
            text = str(templates.get("open_surrounding") or "{relative_capitalized} {open_suffix}.").format(
                relative_capitalized=_relative_label(runtime, rel, capitalize=True),
                open_suffix=view.get("open_suffix") or f"видно {neighbor.title}",
            )
            tone = "open"
        else:
            text = str(templates.get("void_surrounding") or "{relative_capitalized} {void_suffix}.").format(
                relative_capitalized=_relative_label(runtime, rel, capitalize=True),
                void_suffix=view.get("void_suffix") or f"проход к {neighbor.title} пропал",
            )
            tone = "blocked"
        result.append(
            RiftSurroundingLineDTO(
                absolute_direction=direction,
                relative_direction=rel,
                state=_screen_passage_state(state),
                target_node_id=neighbor.node_id,
                text=text,
                tone=cast("Any", tone),
            )
        )
    return result


def _build_movement(
    runtime: RiftZoneRuntimeDTO, *, heading: RiftAbsoluteDirection | None
) -> list[RiftMovementActionDTO]:
    result: list[RiftMovementActionDTO] = []
    templates = _templates(runtime)
    for direction in ORDERED_DIRECTIONS:
        neighbor = _neighbor_for(runtime, direction)
        rel = relative_direction(heading=heading, direction=direction)
        if neighbor is None:
            continue
        state = "void" if neighbor.node_id in runtime.void_node_ids else "open"
        state = _passage_state_for(runtime, direction, neighbor.node_id)
        if state not in {"open", "blocked_temporary", "locked"}:
            continue
        target_coord = RiftCoordinateDTO(x=neighbor.x, y=neighbor.y)
        if state == "open":
            transition = neighbor.transition_text
            template_key = "back_button" if rel == "back" else "open_button"
            label = str(templates.get(template_key) or "{verb} {relative} {enter_target}").format(
                verb=transition.get("verb") or "Пойти",
                relative=_relative_label(runtime, rel),
                enter_target=transition.get("enter_target") or f"к {neighbor.title}",
            )
            result.append(
                RiftMovementActionDTO(
                    id=f"move:{neighbor.node_id}",
                    label=_clean_spaces(label),
                    action="move",
                    style="primary" if rel != "back" else "secondary",
                    is_active=True,
                    target_node_id=neighbor.node_id,
                    target_coord=target_coord,
                    absolute_direction=direction,
                    relative_direction=rel,
                    state=_screen_passage_state(state),
                    travel=_build_travel_preview(runtime, neighbor.node_id),
                    debug_text_parts={"template": template_key},
                )
            )
            continue
        blocker = _passage_blocker(runtime, direction=direction)
        label = _blocked_passage_label(runtime, blocker=blocker, rel=rel)
        blocker_check = _blocker_check_result(runtime, blocker=blocker)
        is_interactive_blocker = state == "blocked_temporary" and bool(blocker_check.get("can_pass", True))
        blocker_debug = _blocker_debug_parts(blocker, check_result=blocker_check)
        result.append(
            RiftMovementActionDTO(
                id=f"{state}:{neighbor.node_id}",
                label=_clean_spaces(label),
                action="inspect_blocker" if state == "blocked_temporary" else "none",
                style="primary" if is_interactive_blocker else "disabled",
                is_active=is_interactive_blocker,
                target_node_id=neighbor.node_id,
                target_coord=target_coord,
                absolute_direction=direction,
                relative_direction=rel,
                state=_screen_passage_state(state),
                tooltip=_blocker_tooltip(blocker_debug),
                debug_text_parts=blocker_debug,
            )
        )
    return result


def _build_radar(runtime: RiftZoneRuntimeDTO, *, heading: RiftAbsoluteDirection | None) -> RiftRadarDTO:
    arms: list[RiftRadarArmDTO] = []
    for direction in ORDERED_DIRECTIONS:
        neighbor = _neighbor_for(runtime, direction)
        rel = relative_direction(heading=heading, direction=direction)
        if neighbor is None:
            neighbor_coord_value = _neighbor_coord_for(runtime, direction)
            state = "void" if _is_void_coord(runtime, neighbor_coord_value) else "unknown"
            arms.append(
                RiftRadarArmDTO(
                    absolute_direction=direction,
                    relative_direction=rel,
                    state=_screen_passage_state(state),
                    target_coord=neighbor_coord_value,
                    color_hint=_COLOR_BY_STATE[state],
                )
            )
            continue
        state = _passage_state_for(runtime, direction, neighbor.node_id)
        arms.append(
            RiftRadarArmDTO(
                absolute_direction=direction,
                relative_direction=rel,
                state=_screen_passage_state(state),
                target_node_id=neighbor.node_id,
                target_coord=neighbor.coord,
                is_available=state == "open",
                is_visited=neighbor.node_id in runtime.visited_node_ids,
                color_hint=_COLOR_BY_STATE.get(state, "gray"),
            )
        )
    return RiftRadarDTO(center_node_id=runtime.current_node_id, heading=heading, arms=arms)


def _build_travel_preview(runtime: RiftZoneRuntimeDTO, target_node_id: str) -> RiftTravelPreviewDTO:
    rules = _transition_combat_rules(runtime)
    tick_interval_ms = int(rules.get("tick_interval_ms") or 1000)
    if target_node_id in runtime.visited_node_ids:
        return RiftTravelPreviewDTO(
            kind="return",
            duration_ms=int(rules.get("return_duration_ms") or 1000),
            tick_interval_ms=tick_interval_ms,
            event_check_count=0,
            possible_events=["none"],
            can_trigger_event=False,
            event_chance=0.0,
        )
    target_node_event = _ready_node_entry_combat_event(runtime, target_node_id)
    target_node_event_key = str(target_node_event.get("event_key") or "") if target_node_event else ""
    if not target_node_event_key:
        target_node_event_key = _scripted_combat_event_key(runtime, target_node_id) or ""
    if target_node_event_key:
        return RiftTravelPreviewDTO(
            kind="exploration",
            duration_ms=int(rules.get("exploration_duration_ms") or 3000),
            tick_interval_ms=tick_interval_ms,
            event_check_count=0,
            possible_events=["none"],
            can_trigger_event=False,
            event_chance=0.0,
            suppressed_by_target_node_event=True,
            target_node_event_key=target_node_event_key,
        )
    return RiftTravelPreviewDTO(
        kind="exploration",
        duration_ms=int(rules.get("exploration_duration_ms") or 3000),
        tick_interval_ms=tick_interval_ms,
        event_check_count=_transition_event_check_count(rules),
        possible_events=["none", "combat"],
        can_trigger_event=True,
        event_chance=float(rules.get("base_chance_per_tick") or 0.0),
    )


def _complete_travel(
    runtime: RiftZoneRuntimeDTO,
    *,
    active_travel: dict[str, Any],
    event_triggered: bool = False,
    event_type: str = "none",
    resolved: bool = False,
    result: str | None = None,
    suppress_random_node_combat: bool = False,
) -> RiftZoneRuntimeDTO:
    from_node_id = str(active_travel["from_node_id"])
    to_node_id = str(active_travel["to_node_id"])
    current = runtime.nodes[from_node_id]
    target = runtime.nodes[to_node_id]
    direction = direction_between(current.coord, target.coord)
    visited = set(runtime.visited_node_ids)
    was_visited = to_node_id in visited
    visited.add(to_node_id)
    last_travel = RiftTravelResultDTO(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        kind=active_travel.get("kind", "exploration"),
        duration_ms=int(active_travel.get("duration_ms") or 0),
        event_scope="transition",
        event_triggered=event_triggered,
        event_type=_screen_transition_event(event_type),
    )
    last_travel_payload = last_travel.model_dump(mode="json")
    last_travel_payload["resolved"] = resolved
    last_travel_payload["result"] = result
    last_travel_payload["suppress_random_node_combat"] = suppress_random_node_combat
    updated = runtime.model_copy(
        update={
            "previous_node_id": from_node_id,
            "current_node_id": to_node_id,
            "heading": direction,
            "visited_node_ids": visited,
            "active_travel": None,
            "last_travel": last_travel_payload,
        }
    )
    return _resolve_ordinary_node_entry(updated, was_visited=was_visited)


def _resolve_ordinary_node_entry(runtime: RiftZoneRuntimeDTO, *, was_visited: bool) -> RiftZoneRuntimeDTO:
    node_id = runtime.current_node_id
    if node_id in runtime.node_events:
        return runtime
    if _scripted_combat_event_key(runtime, node_id):
        return runtime
    rules = _ordinary_node_combat_rules(runtime)
    if not rules.get("enabled", True):
        return runtime

    node_states = dict(runtime.node_states)
    state = dict(node_states.get(node_id) or {})
    if was_visited and rules.get("first_visit_only", True):
        node_states[node_id] = {
            **state,
            "ordinary_event_state": "visited",
            "ordinary_event_type": "none",
        }
        return runtime.model_copy(update={"node_states": node_states})

    suppress_combat = bool(dict(runtime.last_travel or {}).get("suppress_random_node_combat"))
    has_combat = _roll_ordinary_node_combat(runtime, combat_allowed=not suppress_combat)
    if not has_combat:
        node_states[node_id] = {
            **state,
            "ordinary_event_state": "suppressed" if suppress_combat else "resolved",
            "ordinary_event_type": "none",
            "ordinary_event_source": "ordinary_roll",
        }
        return runtime.model_copy(update={"node_states": node_states})

    event = _ordinary_node_combat_payload(runtime)
    node_events = dict(runtime.node_events)
    node_events[node_id] = event
    node_states[node_id] = {
        **state,
        "ordinary_event_state": "ready",
        "ordinary_event_type": "combat",
        "ordinary_event_source": "ordinary_roll",
        "event_key": event["event_key"],
        "entry_event_state": "ready",
    }
    return runtime.model_copy(update={"node_events": node_events, "node_states": node_states})


def _ordinary_node_combat_rules(runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
    _ = runtime
    tunables = current_tunables()
    return {
        "enabled": tunables.ordinary_node_combat_enabled,
        "first_visit_only": tunables.ordinary_node_first_visit_only,
        "combat_chance": tunables.ordinary_node_combat_chance,
        "possible_events": ["none", "combat"],
    }


def _roll_ordinary_node_combat(runtime: RiftZoneRuntimeDTO, *, combat_allowed: bool) -> bool:
    rules = _ordinary_node_combat_rules(runtime)
    roll = _ordinary_event_roll(runtime)
    combat_chance = max(0.0, min(1.0, float(rules.get("combat_chance") or 0.0))) if combat_allowed else 0.0
    return roll < combat_chance


def _ordinary_node_combat_payload(runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
    current = runtime.nodes[runtime.current_node_id]
    return {
        "event_key": "ordinary_combat",
        "event_type": "combat",
        "state": "ready",
        "source": "ordinary_roll",
        "is_required": False,
        "title": f"Стычка: {current.title}",
        "description": "Пока вы осматриваетесь, рядом поднимается шум. Местная мелкая группа выходит из укрытий и перекрывает путь.",
        "combat": {
            "status": "placeholder",
            "budget_policy": "ordinary_node_plus_gear_score",
        },
    }


def _resolve_transition_tick_event(
    runtime: RiftZoneRuntimeDTO,
    *,
    active_travel: dict[str, Any],
    next_check: int,
    force_event: str | None,
) -> RiftTransitionEventType:
    possible_events = set(active_travel.get("possible_events") or ["none"])
    if force_event in possible_events:
        return _screen_transition_event(str(force_event))
    if "combat" not in possible_events or not active_travel.get("can_trigger_event"):
        return "none"
    roll = _travel_event_roll(runtime, active_travel=active_travel, next_check=next_check)
    return "combat" if roll < float(active_travel.get("event_chance") or 0.0) else "none"


def _ready_node_entry_combat_event(runtime: RiftZoneRuntimeDTO, node_id: str) -> dict[str, Any]:
    event = dict(runtime.node_events.get(node_id) or {})
    if event.get("event_type") != "combat":
        return {}
    if event.get("state") != "ready":
        return {}
    return event


def _scripted_combat_event_key(runtime: RiftZoneRuntimeDTO, target_node_id: str) -> str | None:
    node = runtime.nodes.get(target_node_id)
    if node is None:
        return None
    for key in [*node.role_fit, *node.tags]:
        if key in _SCRIPTED_COMBAT_NODE_KEYS:
            return key
    if target_node_id == runtime.finish_node_id and "crystal_chamber" in node.role_fit:
        return "crystal_chamber"
    return None


def _node_entry_combat_prompt(runtime: RiftZoneRuntimeDTO) -> RiftCombatPromptDTO | None:
    event = _ready_node_entry_combat_event(runtime, runtime.current_node_id)
    if not event:
        return None
    is_ordinary = event.get("source") == "ordinary_roll" or event.get("event_key") == "ordinary_combat"
    encounter_kind = str(event.get("encounter_kind") or ("ordinary_node" if is_ordinary else "key_guard"))
    return RiftCombatPromptDTO(
        source="rift_transition",
        title=str(event.get("title") or ("Стычка" if is_ordinary else "Охрана узла")),
        description=str(event.get("description") or "Путь удерживает местная группа."),
        enemies=[
            RiftCombatPromptEnemyDTO(
                name="???",
                tier=0,
                threat_rating=None,
                hp_percent=None,
                image=None,
                visual={},
                description="Охрана удерживает проход и не отступит без боя.",
            )
        ],
        actions=[
            RiftCombatPromptActionDTO(
                id="attack",
                label="В бой!",
                action="attack",
                style="danger",
                is_active=True,
            )
        ],
        metadata={
            "rift_instance_id": runtime.rift_instance_id,
            "to_node_id": runtime.current_node_id,
            "event_scope": "node_entry",
            "event_key": event.get("event_key"),
            "encounter_kind": encounter_kind,
            "opening_context": _transition_opening_context_contract(runtime),
            "combat": {
                "status": "placeholder",
                "combat_id": None,
            },
        },
    )


def _transition_combat_prompt(runtime: RiftZoneRuntimeDTO, *, active_travel: dict[str, Any]) -> RiftCombatPromptDTO:
    descriptor = _transition_combat_descriptor(runtime, active_travel=active_travel)
    opening_context = _transition_opening_context_contract(runtime)
    return RiftCombatPromptDTO(
        source="rift_transition",
        title=descriptor["title"],
        description=descriptor["description"],
        enemies=[
            RiftCombatPromptEnemyDTO(
                name="???",
                tier=0,
                threat_rating=None,
                hp_percent=None,
                image=None,
                visual={},
                description=descriptor["enemy_description"],
            )
        ],
        actions=[
            RiftCombatPromptActionDTO(
                id="attack",
                label="В бой!",
                action="attack",
                style="danger",
                is_active=True,
            )
        ],
        metadata={
            "travel_id": active_travel.get("travel_id"),
            "rift_instance_id": runtime.rift_instance_id,
            "from_node_id": active_travel.get("from_node_id"),
            "to_node_id": active_travel.get("to_node_id"),
            "event_scope": "transition",
            "encounter_descriptor_key": descriptor["key"],
            "opening_context": opening_context,
            "combat": {
                "status": "placeholder",
                "combat_id": None,
            },
        },
    )


def _transition_combat_rules(runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
    _ = runtime
    tunables = current_tunables()
    return {
        "base_chance_per_tick": tunables.transition_base_chance_per_tick,
        "tick_interval_ms": tunables.transition_tick_interval_ms,
        "exploration_duration_ms": tunables.transition_exploration_duration_ms,
        "return_duration_ms": tunables.transition_return_duration_ms,
        "opening_context": dict(tunables.transition_opening_context),
    }


def _transition_event_check_count(rules: dict[str, Any]) -> int:
    duration_ms = int(rules.get("exploration_duration_ms") or 3000)
    tick_interval_ms = int(rules.get("tick_interval_ms") or 1000)
    if duration_ms <= 0 or tick_interval_ms <= 0:
        return 0
    return max(0, duration_ms // tick_interval_ms)


def _travel_tick_count(*, duration_ms: int, tick_interval_ms: int) -> int:
    if duration_ms <= 0 or tick_interval_ms <= 0:
        return 1
    return max(1, duration_ms // tick_interval_ms)


def _transition_opening_context_contract(runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
    rules = _transition_combat_rules(runtime)
    opening_context = dict(rules.get("opening_context") or {})
    if not opening_context:
        return {
            "status": "not_configured",
            "default_result": "neutral_opening",
            "possible_results": ["neutral_opening"],
            "skill_hooks": [],
            "resolved": False,
        }
    return {
        **opening_context,
        "resolved": False,
    }


def _transition_combat_descriptor(runtime: RiftZoneRuntimeDTO, *, active_travel: dict[str, Any]) -> dict[str, str]:
    vocabulary = dict(runtime.setting.get("encounter_vocabulary") or {})
    descriptors = [
        dict(item)
        for item in vocabulary.get("transition_combat", [])
        if isinstance(item, dict) and item.get("title") and item.get("description")
    ]
    if not descriptors:
        return {
            "key": "generic_transition_contact",
            "title": "Переход прерван",
            "description": "Пока вы пробираетесь дальше, путь пересекает враждебная группа. Бой нельзя обойти.",
            "enemy_description": "Враждебные силуэты перекрывают линию движения.",
        }
    descriptor = descriptors[
        _stable_index(runtime, f"transition-combat:{active_travel.get('travel_id')}", len(descriptors))
    ]
    return {
        "key": str(descriptor.get("key") or "transition_combat"),
        "title": str(descriptor["title"]),
        "description": str(descriptor["description"]),
        "enemy_description": str(descriptor.get("enemy_description") or "Враждебная группа перекрывает путь дальше."),
    }


def _build_map_view(runtime: RiftZoneRuntimeDTO, *, heading: RiftAbsoluteDirection | None) -> RiftMapViewDTO:
    current = runtime.nodes[runtime.current_node_id]
    visible_nodes: dict[str, RiftMapViewNodeDTO] = {
        current.node_id: RiftMapViewNodeDTO(
            node_id=current.node_id,
            coord=current.coord,
            title=current.title,
            state="current",
            visited=True,
            discovered=True,
        )
    }
    visible_edges: list[RiftMapViewEdgeDTO] = []

    for direction in ORDERED_DIRECTIONS:
        neighbor = _neighbor_for(runtime, direction)
        rel = relative_direction(heading=heading, direction=direction)
        if neighbor is None:
            continue

        state = _passage_state_for(runtime, direction, neighbor.node_id)
        if state not in {"open", "blocked_temporary"}:
            continue
        visible_nodes[neighbor.node_id] = RiftMapViewNodeDTO(
            node_id=neighbor.node_id,
            coord=neighbor.coord,
            title=neighbor.title,
            state=_screen_map_node_state(state),
            visited=neighbor.node_id in runtime.visited_node_ids,
            discovered=True,
        )
        visible_edges.append(
            RiftMapViewEdgeDTO(
                from_node_id=current.node_id,
                to_node_id=neighbor.node_id,
                absolute_direction=direction,
                relative_direction=rel,
                state=_screen_passage_state(state),
            )
        )

    return RiftMapViewDTO(
        center_node_id=current.node_id,
        current_coord=current.coord,
        heading=heading,
        visible_nodes=list(visible_nodes.values()),
        visible_edges=visible_edges,
    )


def _build_debug_map(runtime: RiftZoneRuntimeDTO) -> RiftDebugMapDTO:
    cells = []
    void_coord_keys = _void_coord_keys(runtime)
    for y in range(runtime.debug_map_height):
        for x in range(runtime.debug_map_width):
            node_id = runtime.cells_by_coord.get(coord_key(x, y))
            node = runtime.nodes.get(node_id) if node_id else None
            if node is None:
                state = "void" if coord_key(x, y) in void_coord_keys else "unknown"
                cells.append(
                    RiftDebugMapCellDTO(
                        node_id=None,
                        coord=RiftCoordinateDTO(x=x, y=y),
                        title=None,
                        state=cast("RiftDebugCellState", state),
                        visited=False,
                        discovered=state == "void",
                    )
                )
                continue
            state = "current" if node.node_id == runtime.current_node_id else "open"
            cells.append(
                RiftDebugMapCellDTO(
                    node_id=node.node_id,
                    coord=node.coord,
                    title=node.title,
                    state=cast("RiftDebugCellState", state),
                    visited=node.node_id in runtime.visited_node_ids,
                    discovered=True,
                )
            )
    return RiftDebugMapDTO(
        width=runtime.debug_map_width,
        height=runtime.debug_map_height,
        cells=cells,
        passage_edges=_build_debug_map_edges(runtime),
    )


def _build_debug_map_edges(runtime: RiftZoneRuntimeDTO) -> list[RiftDebugMapEdgeDTO]:
    result: list[RiftDebugMapEdgeDTO] = []
    seen_pairs: set[tuple[str, str]] = set()
    for edge in runtime.passage_edges.values():
        from_node = runtime.nodes.get(edge.from_node_id)
        to_node = runtime.nodes.get(edge.to_node_id)
        if from_node is None or to_node is None:
            continue
        pair = cast("tuple[str, str]", tuple(sorted((edge.from_node_id, edge.to_node_id))))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        result.append(
            RiftDebugMapEdgeDTO(
                from_node_id=edge.from_node_id,
                to_node_id=edge.to_node_id,
                from_coord=from_node.coord,
                to_coord=to_node.coord,
                state=cast("Any", _effective_edge_state(runtime, edge)),
            )
        )
    return result


def _neighbor_for(runtime: RiftZoneRuntimeDTO, direction: RiftAbsoluteDirection):
    coord = _neighbor_coord_for(runtime, direction)
    node_id = runtime.cells_by_coord.get(coord_key(coord.x, coord.y))
    return runtime.nodes.get(node_id) if node_id else None


def _neighbor_coord_for(runtime: RiftZoneRuntimeDTO, direction: RiftAbsoluteDirection) -> RiftCoordinateDTO:
    current = runtime.nodes[runtime.current_node_id]
    return neighbor_coord(current.coord, direction)


def _edge_for(runtime: RiftZoneRuntimeDTO, direction: RiftAbsoluteDirection):
    return runtime.passage_edges.get(_edge_key(runtime.current_node_id, direction))


def _passage_state_for(runtime: RiftZoneRuntimeDTO, direction: RiftAbsoluteDirection, neighbor_node_id: str) -> str:
    if neighbor_node_id in runtime.void_node_ids:
        return "void"
    edge = _edge_for(runtime, direction)
    if edge and edge.to_node_id == neighbor_node_id:
        if _is_heart_node(runtime.nodes.get(neighbor_node_id)) and not _heart_access_unlocked(
            runtime, neighbor_node_id
        ):
            return _effective_edge_state(runtime, edge) if edge.state == "locked" else "blocked_permanent"
        return _effective_edge_state(runtime, edge)
    return "blocked_permanent"


def _passage_blocker(runtime: RiftZoneRuntimeDTO, *, direction: RiftAbsoluteDirection) -> dict[str, Any] | None:
    edge = _edge_for(runtime, direction)
    if edge is None:
        return None
    blocker_key = edge.blocker_key
    if not blocker_key:
        return None
    vocabulary = dict(runtime.setting.get("blocker_vocabulary") or {})
    for item in [*vocabulary.get("soft_blocker", []), *vocabulary.get("locked_blocker", [])]:
        if isinstance(item, dict) and item.get("key") == blocker_key:
            blocker = dict(item)
            blocker["requirement"] = dict(edge.requirement or {})
            return blocker
    return {"key": blocker_key, "requirement": dict(edge.requirement or {})}


def _blocked_passage_label(runtime: RiftZoneRuntimeDTO, *, blocker: dict[str, Any] | None, rel: str | None) -> str:
    action_label = _blocker_action_label(blocker)
    if action_label:
        return action_label
    label = str(_templates(runtime).get("void_button") or "{relative_capitalized} прохода нет").format(
        relative_capitalized=_relative_label(runtime, rel, capitalize=True),
    )
    return label


def _blocker_debug_parts(
    blocker: dict[str, Any] | None,
    *,
    check_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not blocker:
        return {}
    requirement = dict(blocker.get("requirement") or {})
    check = dict(requirement.get("check") or {})
    checks = [dict(item) for item in requirement.get("checks", []) if isinstance(item, dict)]
    resolved_checks = [check] if check else checks
    requirements = [str(item["key"]) for item in resolved_checks if item.get("key")]
    interaction = dict(blocker.get("interaction") or {})
    if resolved_checks:
        interaction["resolved_checks"] = resolved_checks
    return {
        "blocker_key": blocker.get("key"),
        "requirements": requirements or blocker.get("requires", []),
        "requirement_label": _blocker_requirement_label(blocker),
        "requirement": requirement,
        "interaction": interaction,
        "check_result": check_result or {},
    }


def _blocker_requirement_label(blocker: dict[str, Any] | None) -> str | None:
    if not blocker:
        return None
    requirement = dict(blocker.get("requirement") or {})
    check = dict(requirement.get("check") or {})
    key = str(check.get("key") or "")
    dc = check.get("dc")
    if not key or dc is None:
        return None
    return f"{_ATTRIBUTE_LABELS.get(key, key)} {dc}"


def _blocker_action_label(blocker: dict[str, Any] | None) -> str | None:
    if not blocker:
        return None
    requirement = dict(blocker.get("requirement") or {})
    check = dict(requirement.get("check") or {})
    if check.get("label"):
        return str(check["label"])
    if blocker.get("button_label"):
        return str(blocker["button_label"])
    return None


def _blocker_check_result(runtime: RiftZoneRuntimeDTO, *, blocker: dict[str, Any] | None) -> dict[str, Any]:
    if not blocker:
        return {"current_known": False, "can_pass": True}
    requirement = dict(blocker.get("requirement") or {})
    check = dict(requirement.get("check") or {})
    key = str(check.get("key") or "")
    dc = int(check.get("dc") or 0)
    if not key or dc <= 0:
        return {"current_known": False, "can_pass": True}
    attributes = _runtime_attributes(runtime)
    if key not in attributes:
        return {
            "key": key,
            "attribute_label": _ATTRIBUTE_LABELS.get(key, key),
            "dc": dc,
            "current_known": False,
            "current_value": None,
            "shortfall": None,
            "can_pass": True,
        }
    current_value = int(attributes.get(key) or 0)
    shortfall = max(dc - current_value, 0)
    return {
        "key": key,
        "attribute_label": _ATTRIBUTE_LABELS.get(key, key),
        "dc": dc,
        "current_known": True,
        "current_value": current_value,
        "shortfall": shortfall,
        "can_pass": current_value >= dc,
    }


def _runtime_attributes(runtime: RiftZoneRuntimeDTO) -> dict[str, int]:
    character = dict(dict(runtime.dev_character_snapshot or {}).get("character") or {})
    attributes = dict(character.get("attributes") or {})
    normalized = {str(key): int(value) for key, value in attributes.items()}
    for legacy_key, canonical_key in _ATTRIBUTE_ALIASES.items():
        if legacy_key not in normalized and canonical_key in normalized:
            normalized[legacy_key] = normalized[canonical_key]
        if canonical_key not in normalized and legacy_key in normalized:
            normalized[canonical_key] = normalized[legacy_key]
    return normalized


def _blocker_tooltip(debug_parts: dict[str, Any]) -> str | None:
    requirement_label = str(debug_parts.get("requirement_label") or "")
    if not requirement_label:
        return None
    result = dict(debug_parts.get("check_result") or {})
    if result.get("current_known") is True:
        current_value = int(result.get("current_value") or 0)
        if result.get("can_pass") is True:
            return f"Требуется: {requirement_label}. У тебя: {current_value}. Можно пройти."
        shortfall = int(result.get("shortfall") or 0)
        return f"Требуется: {requirement_label}. У тебя: {current_value}. Не хватает: {shortfall}."
    return f"Требуется: {requirement_label}. Текущее значение будет проверено при действии."


def _build_node_entry_event(runtime: RiftZoneRuntimeDTO) -> RiftNodeEntryEventPreviewDTO:
    event = dict(runtime.node_events.get(runtime.current_node_id) or {})
    if not event:
        return RiftNodeEntryEventPreviewDTO()
    return RiftNodeEntryEventPreviewDTO(
        state=event.get("state", "ready"),
        event_type=event.get("event_type", "none"),
        event_key=event.get("event_key"),
        title=event.get("title"),
        description=event.get("description"),
        is_required=bool(event.get("is_required")),
        grants_flags=[str(flag) for flag in event.get("grants_flags", []) if flag],
        metadata={
            "source": event.get("source"),
            "unlocks": event.get("unlocks", []),
            "combat": event.get("combat", {}),
            "loot": event.get("loot", {}),
        },
    )


def _normalized_heart_state(runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
    screen = dict(runtime.setting.get("screen") or {})
    raw_heart = dict(runtime.setting.get("heart") or {})
    value_by_tier = dict(raw_heart.get("value_by_tier") or {})
    tier = max(1, int(raw_heart.get("tier") or screen.get("tier") or 1))
    base_value = int(raw_heart.get("base_value") or value_by_tier.get(str(tier)) or value_by_tier.get(tier) or 100)
    existing = dict(runtime.heart_state or {})
    return {
        "heart_id": existing.get("heart_id")
        or raw_heart.get("heart_id")
        or f"{runtime.setting.get('setting_key', 'rift')}:heart",
        "node_id": existing.get("node_id") or raw_heart.get("node_id") or runtime.finish_node_id,
        "tier": max(1, int(existing.get("tier") or tier)),
        "base_value": max(1, int(existing.get("base_value") or base_value)),
        "status": str(existing.get("status") or "intact"),
        "methods": existing.get("methods") or _default_heart_methods(),
        "resolved_method": existing.get("resolved_method"),
        "reward": existing.get("reward"),
        "can_exit": bool(existing.get("can_exit")),
        "completion": existing.get("completion") or {"status": "active"},
    }


def _is_heart_node(node: Any) -> bool:
    if node is None:
        return False
    tags = {str(tag) for tag in getattr(node, "tags", [])}
    role_fit = {str(role) for role in getattr(node, "role_fit", [])}
    return "rift_heart" in tags and "objective" in tags and "crystal_chamber" in role_fit


def _heart_access_unlocked(runtime: RiftZoneRuntimeDTO, heart_node_id: str) -> bool:
    gate_states = [
        dict(state) for state in runtime.gate_states.values() if str(state.get("to_node_id") or "") == heart_node_id
    ]
    if not gate_states:
        return True
    for state in gate_states:
        if state.get("state") == "open":
            return True
        requirement = dict(state.get("requirement") or {})
        if requirement.get("type") == "rift_flag" and str(requirement.get("flag") or "") in runtime.runtime_flags:
            return True
    return False


def _normalized_exit_policy(runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
    setting_policy = dict(runtime.setting.get("exit_policy") or {})
    mode = str(setting_policy.get("mode") or "heart_exit_only")
    if mode not in {"entrance_return_only", "heart_exit_only"}:
        mode = "heart_exit_only"
    completion_exit = str(setting_policy.get("completion_exit") or "from_heart")
    if completion_exit not in {"from_heart", "return_to_exit"}:
        completion_exit = "from_heart"
    entrance_node_id = str(setting_policy.get("entrance_node_id") or runtime.start_node_id)
    return {
        "mode": mode,
        "completion_exit": completion_exit,
        "entrance_seals_on_entry": bool(setting_policy.get("entrance_seals_on_entry", mode == "heart_exit_only")),
        "entrance_node_id": entrance_node_id,
        "exit_node_id": str(setting_policy.get("exit_node_id") or entrance_node_id),
        "target_state": setting_policy.get("target_state") or "exploration",
        "location_id": setting_policy.get("location_id"),
        "close_rift_on_exit": bool(setting_policy.get("close_rift_on_exit", True)),
    }


def _completion_available(runtime: RiftZoneRuntimeDTO, heart: dict[str, Any] | None = None) -> bool:
    resolved_heart = heart or _normalized_heart_state(runtime)
    completion = dict(resolved_heart.get("completion") or {})
    return (
        bool(resolved_heart.get("can_exit"))
        or str(completion.get("status") or "") == "completed"
        or str(resolved_heart.get("status") or "intact") != "intact"
    )


def _default_heart_methods() -> list[dict[str, Any]]:
    return [
        {"method": "shatter", "label": "Разбить сердце", "enabled": True},
        {"method": "absorb", "label": "Поглотить энергию", "enabled": False, "locked_reason": "not_unlocked"},
        {"method": "dismantle", "label": "Демонтировать", "enabled": False, "locked_reason": "artifact_craft_required"},
    ]


def _heart_reward(*, tier: int, base_value: int, method: str) -> dict[str, Any]:
    if method == "shatter":
        return {
            "lost_value": base_value // 2,
            "symbiote_xp": base_value // 4,
            "resource_value": base_value - (base_value // 2) - (base_value // 4),
            "resource_template_id": "currency_dust",
        }
    if method == "absorb":
        return {
            "lost_value": 0,
            "symbiote_xp": base_value,
            "resource_value": 0,
            "resource_template_id": "currency_dust",
        }
    if method == "dismantle":
        return {
            "lost_value": 0,
            "symbiote_xp": 0,
            "resource_value": base_value,
            "resource_template_id": _crystal_resource_for_tier(tier),
        }
    raise ValueError(f"Unsupported rift heart method: {method}")


def _crystal_resource_for_tier(tier: int) -> str:
    return {
        1: "currency_fragment",
        2: "currency_shard",
        3: "currency_crystal",
        4: "currency_orb",
        5: "currency_prism",
        6: "currency_core",
        7: "currency_star",
    }.get(max(1, min(7, tier)), "currency_fragment")


def _effective_edge_state(runtime: RiftZoneRuntimeDTO, edge) -> str:
    if edge.state in {"locked", "blocked_temporary"} and _edge_requirement_satisfied(
        runtime, dict(edge.requirement or {})
    ):
        return "open"
    return edge.state


def _edge_requirement_satisfied(runtime: RiftZoneRuntimeDTO, requirement: dict[str, Any]) -> bool:
    if not requirement:
        return False
    if requirement.get("type") == "rift_flag":
        return str(requirement.get("flag") or "") in runtime.runtime_flags
    return False


def _apply_granted_flags_to_gate_states(
    gate_states: dict[str, dict[str, Any]],
    runtime_flags: set[str],
) -> dict[str, dict[str, Any]]:
    updated: dict[str, dict[str, Any]] = {}
    for gate_key, state in gate_states.items():
        requirement = dict(state.get("requirement") or {})
        is_open = requirement.get("type") == "rift_flag" and str(requirement.get("flag") or "") in runtime_flags
        updated[gate_key] = {
            **state,
            "state": "open" if is_open else state.get("state", "locked"),
        }
    return updated


def _activate_next_zone(runtime: RiftZoneRuntimeDTO, *, next_zone_key: str) -> RiftZoneRuntimeDTO:
    if not next_zone_key:
        raise ValueError("Next zone transition does not define next_zone_key")
    chain = dict(runtime.zone_chain)
    if next_zone_key not in chain:
        raise ValueError(f"Next rift zone is not prepared: {next_zone_key}")
    current_snapshot = runtime.model_copy(update={"zone_chain": {}}).model_dump(mode="json")
    chain[runtime.current_zone_key] = current_snapshot
    next_runtime = RiftZoneRuntimeDTO.model_validate(chain[next_zone_key])
    return next_runtime.model_copy(
        update={
            "rift_instance_id": runtime.rift_instance_id,
            "zone_chain_order": runtime.zone_chain_order,
            "zone_chain": chain,
            "current_zone_key": next_zone_key,
            "current_node_id": next_runtime.start_node_id,
            "previous_node_id": None,
            "heading": next_runtime.heading,
            "visited_node_ids": {next_runtime.start_node_id},
            "active_travel": None,
            "last_travel": {
                "from_node_id": runtime.current_node_id,
                "to_node_id": next_runtime.start_node_id,
                "kind": "exploration",
                "duration_ms": 0,
                "event_scope": "transition",
                "event_triggered": True,
                "event_type": "combat",
                "title": "Переход на следующий уровень",
                "description": "После зачистки охраны рифт переносит вас в следующую зону.",
                "resolved": True,
                "result": "victory",
                "suppress_random_node_combat": True,
                "zone_transition": {
                    "from_zone_key": runtime.current_zone_key,
                    "to_zone_key": next_zone_key,
                },
            },
        }
    )


def _node_event_resolve_message(event: dict[str, Any]) -> str:
    transition = dict(event.get("transition") or {})
    if transition.get("type") == "next_zone":
        return "Node guard combat resolved. Active rift zone switched to the next prepared zone."
    if event.get("source") == "ordinary_roll":
        return "Ordinary node combat placeholder resolved."
    return "Node combat placeholder resolved. Granted rift flags were applied to locked passages."


def _is_void_coord(runtime: RiftZoneRuntimeDTO, coord: RiftCoordinateDTO) -> bool:
    return coord_key(coord.x, coord.y) in _void_coord_keys(runtime)


def _void_coord_keys(runtime: RiftZoneRuntimeDTO) -> set[str]:
    return {coord_key(coord.x, coord.y) for coord in runtime.void_coords}


def _void_surface(
    runtime: RiftZoneRuntimeDTO,
    *,
    coord: RiftCoordinateDTO,
    direction: RiftAbsoluteDirection,
) -> dict[str, str]:
    descriptors = _void_surface_descriptors(runtime)
    if not descriptors:
        return {
            "narrative_line": "проход обрывается в пустоту",
            "button_label": "Прохода нет",
        }
    descriptor = descriptors[_stable_index(runtime, f"void-surface:{coord.x}:{coord.y}:{direction}", len(descriptors))]
    narrative_lines = [str(line) for line in descriptor.get("narrative_lines", []) if line]
    button_labels = [str(label) for label in descriptor.get("button_labels", []) if label]
    narrative_line = (
        narrative_lines[_stable_index(runtime, f"void-line:{coord.x}:{coord.y}:{direction}", len(narrative_lines))]
        if narrative_lines
        else "проход обрывается в пустоту"
    )
    button_label = (
        button_labels[_stable_index(runtime, f"void-button:{coord.x}:{coord.y}:{direction}", len(button_labels))]
        if button_labels
        else "Прохода нет"
    )
    return {
        "narrative_line": narrative_line,
        "button_label": button_label,
    }


def _void_surface_descriptors(runtime: RiftZoneRuntimeDTO) -> list[dict[str, Any]]:
    vocabulary = dict(runtime.setting.get("blocker_vocabulary") or {})
    return [dict(item) for item in vocabulary.get("void_surface_descriptors", []) if isinstance(item, dict)]


def _stable_index(runtime: RiftZoneRuntimeDTO, key: str, size: int) -> int:
    if size <= 0:
        return 0
    raw = f"{runtime.rift_instance_id}:{runtime.zone_instance_id}:{key}"
    digest = hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
    return int(digest[:8], 16) % size


def _edge_key(node_id: str, direction: RiftAbsoluteDirection) -> str:
    return f"{node_id}:{direction}"


def _resolve_heading(runtime: RiftZoneRuntimeDTO) -> RiftAbsoluteDirection | None:
    if runtime.previous_node_id and runtime.previous_node_id in runtime.nodes:
        previous = runtime.nodes[runtime.previous_node_id]
        current = runtime.nodes[runtime.current_node_id]
        return direction_between(previous.coord, current.coord)
    return runtime.heading


def _relative_label(runtime: RiftZoneRuntimeDTO, rel: str | None, *, capitalize: bool = False) -> str:
    labels = dict(_templates(runtime).get("relative_direction_labels") or {})
    value = str(labels.get(rel or "") or rel or "")
    return value[:1].upper() + value[1:] if capitalize and value else value


def _templates(runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
    return dict(runtime.setting.get("text_templates") or {})


def _clean_spaces(value: str) -> str:
    return " ".join(value.split())


def _travel_id(runtime: RiftZoneRuntimeDTO, *, from_node_id: str, to_node_id: str) -> str:
    raw = f"{runtime.rift_instance_id}:{from_node_id}:{to_node_id}:{len(runtime.visited_node_ids)}"
    return f"trv_{hashlib.md5(raw.encode('utf-8'), usedforsecurity=False).hexdigest()[:12]}"


def _travel_event_roll(runtime: RiftZoneRuntimeDTO, *, active_travel: dict[str, Any], next_check: int) -> float:
    raw = (
        f"{runtime.rift_instance_id}:{active_travel.get('travel_id')}:"
        f"{active_travel.get('from_node_id')}:{active_travel.get('to_node_id')}:{next_check}"
    )
    digest = hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _ordinary_event_roll(runtime: RiftZoneRuntimeDTO) -> float:
    raw = (
        f"{runtime.rift_instance_id}:{runtime.zone_instance_id}:"
        f"{runtime.current_node_id}:ordinary-node-entry:{len(runtime.visited_node_ids)}"
    )
    digest = hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF
