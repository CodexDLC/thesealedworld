# 06. Hybrid Runtime Persistence

Status: implemented as Redis live runtime, MongoDB restore snapshots, and
PostgreSQL membership indexes.

## Storage Boundary

- Redis owns live Rift runtime while participants are active.
- MongoDB owns durable Rift runtime snapshots for cold restore.
- PostgreSQL owns static catalog indexes and the minimal participant-to-rift
  membership index.

PostgreSQL must not store Redis backup payloads. The previous
`rift_instance_states` and `rift_run_states` JSONB backup model is obsolete.

## Redis Runtime Keys

- `game:rift:instance:<rift_instance_id>`
  - shared generated instance document: zone, graph, nodes, node events, node
    state, gates, heart, runtime flags, chain state.
- `game:rift:session:<rift_session_id>`
  - per-fighter runtime session: participant ref, current node, visited and
    discovered nodes, active travel, last travel, active encounter.
- `game:rift:presence:<rift_instance_id>:node:<node_id>`
- `game:rift:presence:<rift_instance_id>:travel:<travel_id>`
- `game:rift:presence:<rift_instance_id>:encounter:<encounter_id>`
  - live derived presence indexes.
- `game:rift:restore-lock:<rift_instance_id>`
  - restore idempotency lock with double-check before Mongo restore.

## Mongo Snapshot

Use one bounded Mongo document per `rift_instance_id`:

```json
{
  "document_kind": "rift_runtime_snapshot",
  "schema_version": 1,
  "rift_instance_id": "rift_001",
  "snapshot_version": 1,
  "captured_at": "...",
  "instance": {},
  "sessions": {},
  "presence": {}
}
```

Presence can be restored from the snapshot or rebuilt from
`sessions.*.current_node_id`. Rift runtime does not store online/offline state;
online checks use `game:ac:<char_id>`.

## PostgreSQL Tables

Static catalog tables are hybrid:

- `rift_settings`
  - keeps `setting_key`, `setting_hash`, title, biome, tags, generation version,
    `mongo_setting_doc_id`, `mongo_status`, `mongo_stored_at`;
  - Mongo setting documents hold profile, generation rules, and text
    vocabulary.
- `rift_node_pool_records`
  - keeps node ids, setting key, hashes, role, title, preview description, tags,
    role fit, `mongo_node_doc_id`, `mongo_status`, `mongo_stored_at`;
  - Mongo node documents hold approach text, transition text, and generation
    metadata.

Dynamic SQL uses one index table:

- `rift_memberships`
  - one row per participant session in a Rift;
  - fields: `rift_instance_id`, `rift_session_id`, `participant_ref`,
    `setting_key`, `status`, `mongo_snapshot_id`, `snapshot_version`, source
    refs, optional `current_node_id`, optional `active_encounter_id`,
    timestamps;
  - stores no Redis backup payloads.

`rift_portal_keys` is no longer a required durable SQL table. Portal live data
can stay in Redis and source/entry refs are indexed through `rift_memberships`.

## Flush Flow

1. Runtime mutates Redis.
2. Dirty session flush resolves the owning `rift_instance_id`.
3. Integration reads the Redis instance, all sessions for that instance, and
   presence.
4. Integration writes one Mongo `rift_runtime_snapshot`.
5. PostgreSQL `rift_memberships` rows are updated with `mongo_snapshot_id`,
   `snapshot_version`, and short index summaries.
6. Dirty marker is cleared in Redis.

## Restore Flow

1. A player attempts to enter/resume Rift.
2. PostgreSQL `rift_memberships` finds active/resumable membership by
   `participant_ref`.
3. Redis `game:rift:instance:<rift_instance_id>` is checked first.
4. If Redis exists, Mongo is not read.
5. If Redis is missing, acquire `game:rift:restore-lock:<rift_instance_id>`.
6. Under the lock, check Redis again.
7. If still missing, load Mongo snapshot and restore the whole instance,
   sessions, and presence.
8. Return the player's screen from restored Redis runtime.
