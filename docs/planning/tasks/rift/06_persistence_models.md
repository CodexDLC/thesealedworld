# 06. Infrastructure Runtime Storage

Status: implemented for Redis runtime storage.

## Goal

Move rift Redis key ownership out of the feature package into the shared infrastructure layer, then use the observed runtime documents as input for later database model design.

## Implemented Redis Managers

- `src/backend/infrastructure/rift/managers/instance.py`
  - owns `game:rift:instance:<rift_instance_id>`;
  - stores the active rift/zone runtime document: canvas, active nodes, placements, passage edges, blockers, node events, gate/heart state, chain snapshots.
- `src/backend/infrastructure/rift/managers/session.py`
  - owns `game:rift:session:<rift_session_id>`;
  - stores per-owner navigation state inside a rift: current node, previous node, heading, visited/discovered nodes, active travel, last travel and active encounter ref.
- `src/backend/infrastructure/rift/managers/presence.py`
  - owns presence set key families:
    - `game:rift:presence:<rift_instance_id>:node:<node_id>`;
    - `game:rift:presence:<rift_instance_id>:travel:<travel_id>`;
    - `game:rift:presence:<rift_instance_id>:encounter:<encounter_id>`.

## Scope

- Keep Redis as active runtime storage.
- Keep rift feature code behind `RiftRuntimeIntegration`; services/API do not assemble Redis keys.
- Keep one manager per key-space/type.
- Do not add SQLAlchemy models or migrations in this stage.
- Do not connect AS, combat, monster group generation or loot in this stage.

## Observed Runtime Documents

### Rift Instance

Active Redis document currently includes:

- identity: `rift_instance_id`, `zone_instance_id`, `zone_canvas_key`, `scale_preset_key`, `assembly_preset_key`;
- setting/preset snapshots: `setting`, `scale_preset`, `assembly_preset`;
- generated zone data: `placements`, `nodes`, `cells_by_coord`, `passage_edges`, `void_node_ids`, `void_coords`;
- navigation anchors: `start_node_id`, `finish_node_id`, `current_zone_key`, `zone_depth`, `zone_chain_order`;
- shared state: `node_events`, `node_states`, `gate_states`, `heart_state`, `runtime_flags`;
- multi-zone backup: `zone_chain`;
- debug/dev fields: `debug_map_width`, `debug_map_height`, `debug`, `dev_character_snapshot`.

### Rift Run Session

Session document is intentionally smaller than the instance:

- identity/owner: `rift_session_id`, `owner_type`, `owner_id`, `rift_instance_id`, `zone_instance_id`;
- navigation: `current_node_id`, `previous_node_id`, `heading`;
- map memory: `visited_node_ids`, `discovered_node_ids`;
- transient flow: `active_travel`, `last_travel`, `active_encounter_id`.

### Rift Presence

Presence is not a single JSON document. It is indexed as Redis sets:

- node occupants;
- travel participants;
- encounter participants.

## Persistence Model Contract

The first persistence shape uses four models. No contribution/rating table exists yet.

- `rift_setting`
  - stable setting/world DNA, biome tags, text vocabularies, blocker/void descriptors and generation rules;
  - table: `rift_settings`.
- `rift_node_pool_record`
  - reusable location/room descriptions without coordinates, generated text, tags, role fit and node hash;
  - table: `rift_node_pool_records`.
- `rift_instance_state`
  - cold-restore backup for shared rift state;
  - table: `rift_instance_states`;
  - uses top-level JSON blocks, not one giant `state_json`:
    - `zones_json`;
    - `graph_json`;
    - `nodes_state_json`;
    - `objectives_json`;
    - `runtime_flags_json`;
    - `state_meta_json`.
- `rift_run_state`
  - cold-restore backup for a solo/party visit inside the rift;
  - table: `rift_run_states`;
  - stores position and critical refs:
    - `participant_scope`;
    - `participant_ref`;
    - `current_zone_key`;
    - `current_node_id`;
    - `previous_node_id`;
    - `heading`;
    - `visited_node_ids`;
    - `discovered_node_ids`;
    - `active_encounter_id`;
    - `entry_context_json`;
    - `run_state_json`.

`active_travel` is intentionally not a first-class DB column. On cold restore, incomplete travel should collapse back to `current_node_id`; only active encounter references remain critical.

Later, when rift clearing/depletion/rating is designed, add a separate contribution table instead of overloading ownership:

- `rift_contribution`
  - `rift_instance_id`;
  - `participant_ref`;
  - depletion/contribution points;
  - percent/rank/reward hooks;
  - timestamps.

## Repository And Integration Boundary

Implemented repositories:

- `RiftSettingRepository`
- `RiftNodePoolRepository`
- `RiftInstanceStateRepository`
- `RiftRunStateRepository`

Current runtime/state mappers:

- `RiftInstanceStateMapper`
  - maps `RiftZoneRuntimeDTO` into `rift_instance_states` fields and JSON blocks.
- `RiftRunStateMapper`
  - maps run/session payloads into `rift_run_states`;
  - intentionally treats `active_travel` as transient restore data.

Feature services still do not call repositories directly. The feature-facing boundary is `RiftRuntimeIntegration`.

Internal persistence modes:

- `redis_only`
  - write only active runtime Redis.
- `db_only`
  - write only SQL backup state.
- `redis_and_db`
  - write Redis first, then SQL backup.

DB modes require explicitly configured repositories. If they are not configured, integration fails loudly instead of silently skipping backup.

Current dev flow still uses Redis-only behavior unless a caller explicitly chooses another mode.

## Contract Questions Before Coding

- Which records are global, player-owned, group-owned or world-owned?
- Which parts remain JSON blobs and which become normalized columns?
- How are generated hashes used for settings, pools and monster families?
- Does multi-zone backup stay in one `rift_instance_state` row or become one row per zone after scale testing?
- Which participant scopes are first-class in DB for run state: solo and party only for now.
- How exactly does contribution/depletion become rating later?

## Exit Criteria

- Rift Redis managers live in infrastructure.
- Feature code depends on `RiftRuntimeIntegration`, not direct Redis key assembly.
- Boundary tests assert the old feature-local Redis package is gone.
- Potential DB model list is documented, but migrations wait for explicit approval.
