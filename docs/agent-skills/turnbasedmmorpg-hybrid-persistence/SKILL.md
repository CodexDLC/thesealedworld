---
name: turnbasedmmorpg-hybrid-persistence
description: Hybrid PostgreSQL and MongoDB persistence guidance for TurnBasedMMORPG. Use when adding, moving, or redesigning storage for analytics, combat logs, chat history, generated content, audit/event history, monster dynamic documents, or any heavy/flexible JSON-like data.
---

# TurnBasedMMORPG Hybrid Persistence

Use this skill before changing persistence boundaries between PostgreSQL and
MongoDB.

## Core Rule

PostgreSQL remains the source of truth. MongoDB stores heavy, flexible,
document-shaped data that must evolve without repeated SQL migrations.

Do not make MongoDB the authority for game-critical facts such as account
ownership, character ownership, inventory, currency, rewards, combat result,
progression, permissions, or membership.

## PostgreSQL Owns

Keep stable facts, relationships, and fast indexes in PostgreSQL:

- Entity ids and ownership.
- Access control and memberships.
- Short list/search fields.
- Foreign-key-like relationships.
- Lifecycle status.
- Processing status for Mongo writes.
- Timestamps used for ordering.
- Pointers to Mongo documents.
- Small summaries needed by pages, dashboards, and workers.

Examples:

```text
combat_id
status
battle_type
location_id
winner_team
participant_char_ids
started_at
finished_at
mongo_document_id
mongo_status
mongo_stored_at
schema_version
```

## MongoDB Owns

Put heavy, flexible, nested, or high-variance payloads in MongoDB:

- Combat full analytics documents.
- Combat runtime/debug traces.
- Chat message bodies and long history.
- Generated content payloads.
- Simulation result documents.
- Dynamic monster configuration documents.
- Audit/event bodies when the event stream is large or schema-changing.

Mongo documents must include:

```text
schema_version
document_kind
stable foreign id from PostgreSQL, such as combat_id or thread_id
created_at / updated_at where relevant
```

## Avoid Repeated Metadata

Do not copy the same metadata into every nested event or message when it can
live once at document or thread level.

Use semantic local keys inside Mongo documents. Keep full participant metadata
once, then refer to it from nested events by compact keys.

Correct combat shape:

```json
{
  "combat_id": "combat_1",
  "document_kind": "combat_battle_log",
  "schema_version": 1,
  "meta": {
    "battle_type": "rift",
    "location_id": "forest_01"
  },
  "participants": {
    "p1": {
      "actor_id": "123",
      "type": "player",
      "team": "players"
    },
    "m1": {
      "actor_id": "wolf_7",
      "type": "monster",
      "team": "enemies"
    }
  },
  "events": [
    {
      "t": 1,
      "seq": 1,
      "s": "p1",
      "d": "m1",
      "a": "slash",
      "o": "hit",
      "dmg": 10
    }
  ]
}
```

Avoid this shape:

```json
{
  "events": [
    {
      "combat_id": "combat_1",
      "battle_type": "rift",
      "location_id": "forest_01",
      "source_actor_id": "123",
      "source_actor_type": "player",
      "source_actor_team": "players",
      "target_actor_id": "wolf_7",
      "target_actor_type": "monster",
      "target_actor_team": "enemies",
      "damage": 10
    }
  ]
}
```

## Document Size Rule

Use one Mongo document for bounded domain artifacts:

- One combat finalization document.
- One generated monster profile document.
- One simulation run result document.

Use separate Mongo documents for unbounded streams:

- Chat messages.
- Long audit logs.
- World activity feeds.
- Very long event streams.

Do not store an indefinitely growing message list as one array inside a single
thread document. MongoDB documents have a hard size limit, and growing arrays
become hard to query and update.

## Chat Pattern

PostgreSQL should own the thread record and membership indexes.

MongoDB should own message bodies and flexible message metadata.

PostgreSQL example:

```text
chat_thread_id
thread_type
created_at
last_message_at
membership rows
mongo_status
```

Mongo examples:

```json
{
  "thread_id": "thread_1",
  "document_kind": "chat_thread_meta",
  "schema_version": 1,
  "settings": {
    "private": true
  }
}
```

```json
{
  "thread_id": "thread_1",
  "message_id": "msg_100",
  "document_kind": "chat_message",
  "schema_version": 1,
  "sender_id": "user_1",
  "created_at": "2026-06-04T10:00:00Z",
  "body": "message text",
  "attachments": []
}
```

## Combat Analytics Direction

For combat analytics, move heavy JSONB payloads out of PostgreSQL and into
MongoDB:

- `combat_finalizations.finalization`
- `combat_finalizations.analytics`
- large `report` payloads
- large `reward_hooks` payloads when they are not needed for game truth
- runtime/debug traces

Keep or add PostgreSQL columns for:

- fast filtering and list pages
- combat result truth
- reward processing truth
- Mongo document reference and write status
- small summaries required by UI or workers

`combat_exchange_facts` and `combat_balance_rollups` may remain PostgreSQL
read models when they serve fast dashboard queries. Treat them as derived
analytics projections, not as primary raw analytics storage.

## Write Flow

Prefer this flow:

1. Write the official fact to PostgreSQL.
2. Write or enqueue the Mongo document.
3. Record Mongo write status in PostgreSQL.
4. Let retry/backfill repair failed Mongo writes.

If MongoDB is temporarily unavailable, game-critical state must not be lost.
The PostgreSQL row should expose enough status for a retry worker or admin
repair command.

## Repository Boundaries

Put low-level Mongo access under:

```text
src/backend/infrastructure/<domain>/repositories/
```

or shared Mongo connection code under:

```text
src/backend/infrastructure/mongo/
```

Feature services must use feature `integrations/` for semantic operations when
crossing infrastructure boundaries. Do not let runtime services build Mongo
queries or collection names directly.

## Versioning

Every Mongo document needs `schema_version`. Readers must handle known versions
explicitly. Do not add broad fallback behavior that silently hides invalid or
unknown document shapes.
