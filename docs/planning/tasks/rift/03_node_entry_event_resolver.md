# 03. Node Entry Event Resolver

Status: dev scaffold implemented.

## Goal

Resolve combat that happens after the player actually enters a node.

This stage owns the rift-side combat-entry contract and dev placeholders only. It does not connect loot service, rewards, party joining, or final multiplayer ownership rules.

## Stage Boundary

This stage starts after travel has completed and `current_node_id` has already changed to the destination node.

It must respect transition-combat output:

- if `last_travel.suppress_random_node_combat` is true, ordinary node-entry combat is skipped for that entry;
- scripted/key node combat can still exist, but transition combat must already have been suppressed before travel;
- non-combat ordinary node events are allowed to survive transition-combat suppression later, but they are only placeholders in this stage.

## Event Classes

Node-entry combat is split into two classes.

Scripted/objective events are pre-assigned during zone assembly because they change progression, topology, or objective state:

- `next_zone_gate` / `zone_exit`;
- `gate_guard`;
- future `rift_heart`;
- future `heart_guard`;
- future key/objective nodes that open required progress.

Ordinary node combat is not pre-assigned as a fixed room slot. A normal node can roll/check combat when the player or group enters it:

- `none`;
- `combat`.

Loot, buffs, chests, and small interactions are not node-entry events before combat. If they are added later, they belong to a post-combat reward/event phase after node combat resolves.

## Current Dev Implementation

Implemented now:

- scripted guard node event state in `node_events`;
- `node_entry_event` screen contract;
- dev resolve route for node combat placeholders;
- two-level zone chain transition through `next_zone_guard`;
- ordinary node-entry combat roll after travel completion;
- ordinary node state in `node_states`;
- transition-combat suppression for ordinary node combat.

Current ordinary roll is intentionally small:

- first visit only;
- `combat` or `none`;
- no pre-combat loot/chest/buff node-entry event;
- no real monster service or loot service is called.

## Runtime Rules

On travel completion:

1. Mark the destination node as current.
2. Store `last_travel`.
3. If the node already has a scripted event, expose that event.
4. If the node is a scripted combat target, do not roll ordinary events.
5. If the node was already visited and the rule is first-visit-only, do not roll ordinary events.
6. If transition combat happened, skip ordinary `combat`.
7. Otherwise roll ordinary node combat by rift rules.

Ordinary node state is stored under `node_states[node_id]`, for example:

```json
{
  "ordinary_event_state": "ready",
  "ordinary_event_type": "combat",
  "ordinary_event_source": "ordinary_roll",
  "event_key": "ordinary_combat",
  "entry_event_state": "ready"
}
```

If transition combat suppresses the ordinary combat roll:

```json
{
  "ordinary_event_state": "suppressed",
  "ordinary_event_type": "none",
  "ordinary_event_source": "ordinary_roll"
}
```

## Rift Heart And Guards

Future final rift heart rules:

- `rift_heart` is only one object: the heart/crystal/core of the rift.
- It exists only on the last zone of the rift.
- If the rift has one zone, it is placed in that zone.
- If the rift has multiple zones, previous zones use `next_zone_gate` or another transition objective instead of `rift_heart`.
- Access to `rift_heart` must be from one side through a guard node.
- `rift_heart` itself is not combat. It owns the final interaction/decision event.
- While `rift_heart` is alive/active, the rift is not closed.

Guard rules:

- `heart_guard` is a scripted combat node.
- It can be an enhanced fight by gear score/tier budget, not always the family boss.
- Small rifts can use veteran/elite packs or elite-plus-minions.
- Larger/final rifts can use champion/boss-like groups or a real family boss.
- Transition combat must be suppressed when moving into a guard/scripted-combat node.

## Future Runtime Integration Phase

The following work is explicitly outside stage 03:

- creating a real combat instance;
- asking monster service for group composition;
- resolving combat turns;
- applying rewards, loot, or post-combat bonus events;
- party auto-join or group pull rules;
- public/shared rift ownership;
- contribution leaderboards for larger rift campaigns.

Those belong to the later runtime-server integration phase.

## Exit Criteria

- Entering an ordinary node can produce a backend-owned combat prompt/result.
- Scripted combat and ordinary combat rolls are separate in code and payloads.
- Transition `combat` and node-entry `combat` are separate in payloads and state.
- Transition-combat can suppress ordinary node combat.
- Frontend receives enough data to launch current combat placeholders without knowing the final combat implementation.
