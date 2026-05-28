# 01. Travel Tick Runtime

Status: implemented in dev prototype.

## Goal

Replace instant movement with a real transition state that can be advanced by ticks.

## Scope

- Add active travel state to rift runtime.
- Add API operations to start, tick and complete travel.
- Keep transition events limited to `none` and `combat`.
- Do not resolve node entry events here.
- Do not add loot, resources, traps or chests to transition ticks.

## Accepted Responsibility

This stage owns only the movement-through-time layer.

- Starting travel between open adjacent rift nodes.
- Keeping `active_travel` in runtime state.
- Advancing travel by ticks.
- Completing travel into `to_node_id` when no transition combat interrupts it.
- Using faster return travel for already visited nodes.
- Keeping transition events separate from node-entry events.

It does not own room events, loot, traps, resources, boss logic, monster group generation, or final persistence models.

## Draft Runtime Fields

- `active_travel.travel_id`
- `from_node_id`
- `to_node_id`
- `started_at`
- `duration_ms`
- `tick_interval_ms`
- `event_check_count`
- `checks_done`
- `status`: `moving`, `interrupted`, `completed`
- `possible_events`: `["none", "combat"]`

## Contract Questions Before Coding

- Resolved: frontend starts travel through `travel/start`, then advances through `travel/tick`.
- Resolved: the final tick can complete travel and return a new rift screen.
- Resolved: interrupted transition combat is completed through the combat placeholder/resolve flow before entering `to_node_id`.

## Exit Criteria

- Movement no longer changes `current_node_id` immediately for exploration travel.
- Backend owns timer/tick state.
- Frontend can render transition progress from backend state.
