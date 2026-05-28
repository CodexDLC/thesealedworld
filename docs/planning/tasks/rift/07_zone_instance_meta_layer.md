# 07. Zone Instance Meta Layer

Status: planned.

## Goal

Separate reusable setting/node-pool data from concrete generated zone instances.

## Intended Split

- `rift_setting`: world/biome/descriptor DNA.
- `node_pool`: reusable described mini-locations without coordinates.
- `rift_instance` / `zone_instance`: concrete canvas, coordinates, active placements, graph, blockers, node roles, node entry event slots and shared rift state.
- `rift_run_session`: per-owner navigation state inside a rift instance.
- `rift_presence`: indexes of who is currently in nodes, travel, or encounters.

## Accepted Runtime Ownership

Active character state remains the source for character/combat data, but not for internal rift navigation.

- `game:ac:<char_id>` can keep HP, energy, stamina, attributes, skills, inventory/equipment refs and combat session refs.
- When entering a rift, active character state should remember the external world return context and active rift session reference.
- Internal rift movement state belongs to `rift_run_session`, not directly to `game:ac:<char_id>`.

Suggested active character rift reference:

```json
{
  "location": {
    "current": "rift:<rift_instance_id>",
    "prev": "<world_location_id>",
    "domain": "rift"
  },
  "rift_ref": {
    "rift_instance_id": "<rift_instance_id>",
    "rift_session_id": "<rift_session_id>",
    "entry_world_location_id": "<world_location_id>"
  }
}
```

Suggested rift run session:

```json
{
  "rift_session_id": "<rift_session_id>",
  "owner_type": "solo",
  "owner_id": "char:<char_id>",
  "rift_instance_id": "<rift_instance_id>",
  "zone_instance_id": "<zone_instance_id>",
  "current_node_id": "<node_id>",
  "previous_node_id": null,
  "visited_node_ids": ["<node_id>"],
  "discovered_node_ids": ["<node_id>"],
  "active_travel_id": null,
  "active_encounter_id": null
}
```

Solo play is treated as a run session with one owner. Party play can later use `owner_type: party` as the source of truth for group movement, or per-character sessions if the design allows party members to split.

## Redis Key Ownership

One Redis manager owns one Redis key-space/type. Do not grow one broad `RiftRedisManager` that mutates every rift key.

Prototype low-level stores now live under `src/backend/infrastructure/rift/managers/`. The feature accesses them through `RiftRuntimeIntegration`, without direct Redis key construction:

- `RiftInstanceStore`
  - owns rift/zone instance documents;
  - owns map, zones, nodes, edges, blockers, heart/gate state and pre-assigned entry event slots;
  - example key family: `game:rift:instance:<rift_instance_id>`.
- `RiftRunSessionStore`
  - owns per-owner navigation/session documents;
  - owns current node, visited/discovered nodes, active travel refs and active encounter refs;
  - example key family: `game:rift:session:<rift_session_id>`.
- `RiftPresenceStore`
  - owns presence indexes;
  - owns node occupants, travel participants and encounter participants;
  - example key families: `game:rift:presence:<rift_instance_id>:node:<node_id>`, `...:travel:<travel_id>`, `...:encounter:<encounter_id>`.

Feature code should access these through rift feature integrations/services with semantic methods. Services/runtime code must not assemble Redis keys or JSON paths directly.

## Scope

- Define owner types:
  - dev/test
  - player
  - group
  - world/public
- Define zone instance backup format.
- Define how multi-level rifts chain zones.
- Define how active character state points into and exits from a rift session.
- Define manager boundaries for rift instance, run session and presence key-spaces.

## Contract Questions Before Coding

- Should zone instance contain full node text snapshot or references to pool nodes?
- How do long-lived rifts refresh events without regenerating the whole zone?
- How does a world map service point to a rift key or instance?
- Is party movement initially party-session locked, or can party members split into per-character rift sessions?
- Which rift owner types need shared presence in the first implementation: solo, party, public/world?

## Exit Criteria

- Zone instance contract is clear enough to support both short-lived and long-lived rifts.
