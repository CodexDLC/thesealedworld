# Known issue: scripted rift nodes do not auto-launch combat

## Symptom

Walking onto a node whose `role_fit`/`tags` contain a key from
`_SCRIPTED_COMBAT_NODE_KEYS` (see `src/backend/features/rift/runtime/navigation/screen_builder.py`)
does NOT emit a `node_entry` combat prompt. The travel completes, the player
sees the node, but no boss/key-combat fight starts on its own.

`_SCRIPTED_COMBAT_NODE_KEYS` currently includes:
`boss`, `crystal_guard`, `objective_gate`, `story_combat`, `key_combat`,
`crystal_chamber`.

## Why

`_resolve_ordinary_node_entry` returns early for any node that matches
`_scripted_combat_event_key(...)`. That means no entry is inserted into
`runtime.node_events`, and `_node_entry_combat_prompt` only fires when
`node_events[current_node_id]` is `ready`. So nothing triggers.

The only scripted node_events seeded today are
`guard_combat` (`NodeEventSeeder.build_node_event_state`) on the gate-guarding
node, and `next_zone_guard` on the finish node of a non-terminal zone. Both are
generated automatically and DO appear in `node_events`. All other scripted
tag-bearing nodes are no-ops.

## Scope

Design-side debt, not a regression introduced by `6f6394ba` / `569966fa`.

## Fix outline (deferred)

Extend `NodeEventSeeder` (or add a sibling pass in `zone_instance.py`) to:
- enumerate all nodes whose `role_fit`/`tags` overlap `_SCRIPTED_COMBAT_NODE_KEYS`
- emit a `node_events` entry per node with a scripted `event_key` (e.g.
  `key_combat_<node_id>`), `state=ready`, and an appropriate `grants_flags`/
  `unlocks` payload
- update `apply_combat_result` to accept the corresponding `event_scope`
  (currently only `transition` and `node_entry` are emitted by the encounter
  pipeline; the dead branch handling `boss`/`heart_guard`/`boss_solo`/
  `boss_with_minions` was removed in this cleanup pass)

## Related code

- `src/backend/features/rift/runtime/navigation/screen_builder.py`
  - `_SCRIPTED_COMBAT_NODE_KEYS`
  - `_scripted_combat_event_key`
  - `_resolve_ordinary_node_entry`
  - `_node_entry_combat_prompt`
- `src/backend/features/rift/runtime/generation/events.py`
  - `NodeEventSeeder.build_node_event_state`
  - `NodeEventSeeder.add_next_zone_transition_event`
- `src/backend/features/rift/integrations/runtime.py`
  - `apply_combat_result`
