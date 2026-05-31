from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.rift.dto import RiftPassageEdgeDTO, RiftZoneCellDTO, RiftZoneRuntimeDTO

_SCRIPTED_COMBAT_NODE_KEYS = {
    "boss",
    "crystal_guard",
    "objective_gate",
    "story_combat",
    "key_combat",
    "crystal_chamber",
}


class NodeEventSeeder:
    """Seeds mandatory runtime events and their related gate state."""

    def build_node_event_state(
        self,
        *,
        nodes: dict[str, RiftZoneCellDTO],
        passage_edges: dict[str, RiftPassageEdgeDTO],
        start_node_id: str,
        finish_node_id: str,
        seed: str,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        gate = _select_guarded_gate(
            nodes=nodes,
            passage_edges=passage_edges,
            start_node_id=start_node_id,
            finish_node_id=finish_node_id,
            seed=seed,
        )
        node_events: dict[str, dict[str, Any]] = {}
        node_states: dict[str, dict[str, Any]] = {}
        gate_states: dict[str, dict[str, Any]] = {}
        if gate is not None:
            guard_node_id, locked_node_id = gate
            gate_key = f"guarded_node:{locked_node_id}"
            unlock_flag = f"rift_flag:{gate_key}:cleared"
            requirement = {
                "type": "rift_flag",
                "flag": unlock_flag,
                "source_node_id": guard_node_id,
                "source_event_key": "guard_combat",
                "status": "locked_until_flag",
            }
            _set_edge_lock(
                passage_edges,
                from_node_id=guard_node_id,
                to_node_id=locked_node_id,
                blocker_key="guarded_service_bulkhead",
                requirement=requirement,
            )
            _block_finish_bypass_edges(
                passage_edges,
                finish_node_id=locked_node_id,
                guard_node_id=guard_node_id,
            )
            node_events[guard_node_id] = {
                "event_key": "guard_combat",
                "event_type": "combat",
                "state": "ready",
                "is_required": True,
                "title": "Охрана узла",
                "description": "Местная группа удерживает проход. После победы заблокированный участок рядом должен открыться.",
                "grants_flags": [unlock_flag],
                "unlocks": [
                    {
                        "kind": "passage",
                        "gate_key": gate_key,
                        "target_node_id": locked_node_id,
                    }
                ],
                "combat": {
                    "status": "placeholder",
                    "budget_policy": "guard_node_plus_gear_score",
                },
            }
            node_states[guard_node_id] = {
                "entry_event_state": "ready",
                "event_key": "guard_combat",
            }
            node_states[locked_node_id] = {
                "access_state": "locked",
                "locked_by": gate_key,
            }
            gate_states[gate_key] = {
                "state": "locked",
                "from_node_id": guard_node_id,
                "to_node_id": locked_node_id,
                "requirement": requirement,
            }
        _seed_scripted_node_events(nodes=nodes, node_events=node_events, node_states=node_states)
        return node_events, node_states, gate_states

    def add_next_zone_transition_event(
        self,
        runtime: RiftZoneRuntimeDTO,
        *,
        next_zone_key: str,
        next_zone_depth: int,
    ) -> RiftZoneRuntimeDTO:
        event_key = "next_zone_guard"
        node_events = dict(runtime.node_events)
        node_events[runtime.finish_node_id] = {
            "event_key": event_key,
            "event_type": "combat",
            "state": "ready",
            "is_required": True,
            "title": "Охрана перехода",
            "description": "Переход на следующий уровень удерживает местная группа. Достаточно встать на эту ноду и зачистить бой, чтобы рифт перебросил вас дальше.",
            "grants_flags": [f"rift_flag:zone:{runtime.current_zone_key}:next_zone_guard_cleared"],
            "unlocks": [
                {
                    "kind": "zone_transition",
                    "next_zone_key": next_zone_key,
                    "next_zone_depth": next_zone_depth,
                }
            ],
            "transition": {
                "type": "next_zone",
                "next_zone_key": next_zone_key,
                "next_zone_depth": next_zone_depth,
            },
            "combat": {
                "status": "placeholder",
                "budget_policy": "next_zone_guard_plus_gear_score",
            },
        }
        node_states = dict(runtime.node_states)
        node_states[runtime.finish_node_id] = {
            **dict(node_states.get(runtime.finish_node_id) or {}),
            "entry_event_state": "ready",
            "event_key": event_key,
            "node_role": "next_zone_gate",
        }
        nodes = dict(runtime.nodes)
        finish_node = nodes[runtime.finish_node_id]
        nodes[runtime.finish_node_id] = finish_node.model_copy(
            update={
                "role_fit": sorted({*finish_node.role_fit, "objective_gate"}),
                "tags": sorted({*finish_node.tags, "next_zone_gate"}),
            }
        )
        return runtime.model_copy(update={"nodes": nodes, "node_events": node_events, "node_states": node_states})


def _seed_scripted_node_events(
    *,
    nodes: dict[str, RiftZoneCellDTO],
    node_events: dict[str, dict[str, Any]],
    node_states: dict[str, dict[str, Any]],
) -> None:
    for node_id in sorted(nodes):
        if node_id in node_events:
            continue
        node = nodes[node_id]
        event_key = _scripted_combat_event_key(node)
        if not event_key:
            continue
        encounter_kind = _scripted_node_encounter_kind(node, event_key=event_key)
        node_events[node_id] = _scripted_node_event_payload(node, event_key=event_key, encounter_kind=encounter_kind)
        state = dict(node_states.get(node_id) or {})
        node_states[node_id] = {
            **state,
            "entry_event_state": "ready",
            "event_key": event_key,
            "node_role": "scripted_combat",
        }


def _scripted_combat_event_key(node: RiftZoneCellDTO) -> str | None:
    for key in [*node.role_fit, *node.tags]:
        if key in _SCRIPTED_COMBAT_NODE_KEYS:
            return str(key)
    return None


def _scripted_node_encounter_kind(node: RiftZoneCellDTO, *, event_key: str) -> str:
    marks = {str(item) for item in [*node.role_fit, *node.tags]}
    if event_key == "crystal_chamber" or {"rift_heart", "crystal_chamber"} <= marks:
        return "heart_guard"
    if event_key == "boss" or "boss" in marks:
        return "boss_with_minions"
    return "key_guard"


def _scripted_node_event_payload(
    node: RiftZoneCellDTO,
    *,
    event_key: str,
    encounter_kind: str,
) -> dict[str, Any]:
    title_by_key = {
        "boss": "Бой с главарем",
        "crystal_chamber": "Страж сердца",
        "crystal_guard": "Кристальная охрана",
        "objective_gate": "Охрана цели",
        "story_combat": "Сюжетная схватка",
        "key_combat": "Ключевая схватка",
    }
    return {
        "event_key": event_key,
        "event_type": "combat",
        "state": "ready",
        "source": "scripted_node",
        "is_required": True,
        "title": f"{title_by_key.get(event_key, 'Охрана узла')}: {node.title}",
        "description": "Путь дальше держит обязательная враждебная группа. Этот бой нельзя обойти.",
        "encounter_kind": encounter_kind,
        "combat": {
            "status": "placeholder",
            "budget_policy": f"{encounter_kind}_plus_gear_score",
        },
    }


def _select_guarded_gate(
    *,
    nodes: dict[str, RiftZoneCellDTO],
    passage_edges: dict[str, RiftPassageEdgeDTO],
    start_node_id: str,
    finish_node_id: str,
    seed: str,
) -> tuple[str, str] | None:
    adjacency = _open_edge_adjacency(passage_edges)
    _ = seed
    parent = _shortest_path_parent(adjacency, start_node_id=start_node_id, finish_node_id=finish_node_id)
    guard_node_id = parent.get(finish_node_id)
    if guard_node_id and guard_node_id in nodes and finish_node_id in nodes:
        return guard_node_id, finish_node_id
    return None


def _open_edge_adjacency(passage_edges: dict[str, RiftPassageEdgeDTO]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {}
    for edge in passage_edges.values():
        if edge.state != "open":
            continue
        adjacency.setdefault(edge.from_node_id, set()).add(edge.to_node_id)
        adjacency.setdefault(edge.to_node_id, set()).add(edge.from_node_id)
    return adjacency


def _shortest_path_parent(
    adjacency: dict[str, set[str]],
    *,
    start_node_id: str,
    finish_node_id: str,
) -> dict[str, str | None]:
    queue: deque[str] = deque([start_node_id])
    parent: dict[str, str | None] = {start_node_id: None}
    while queue:
        node_id = queue.popleft()
        if node_id == finish_node_id:
            break
        for neighbor_id in sorted(adjacency.get(node_id, set())):
            if neighbor_id not in parent:
                parent[neighbor_id] = node_id
                queue.append(neighbor_id)
    return parent


def _set_edge_lock(
    passage_edges: dict[str, RiftPassageEdgeDTO],
    *,
    from_node_id: str,
    to_node_id: str,
    blocker_key: str,
    requirement: dict[str, Any],
) -> None:
    for edge_key, edge in list(passage_edges.items()):
        if {edge.from_node_id, edge.to_node_id} != {from_node_id, to_node_id}:
            continue
        passage_edges[edge_key] = edge.model_copy(
            update={
                "state": "locked",
                "blocker_key": blocker_key,
                "requirement": requirement,
            }
        )


def _block_finish_bypass_edges(
    passage_edges: dict[str, RiftPassageEdgeDTO],
    *,
    finish_node_id: str,
    guard_node_id: str,
) -> None:
    for edge_key, edge in list(passage_edges.items()):
        if finish_node_id not in {edge.from_node_id, edge.to_node_id}:
            continue
        if {edge.from_node_id, edge.to_node_id} == {guard_node_id, finish_node_id}:
            continue
        passage_edges[edge_key] = edge.model_copy(
            update={
                "state": "blocked_permanent",
                "blocker_key": "heart_guard_required",
                "requirement": {},
            }
        )
