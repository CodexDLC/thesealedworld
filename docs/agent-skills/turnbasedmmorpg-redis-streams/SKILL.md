---
name: turnbasedmmorpg-redis-streams
description: Redis Streams event bus guidance for TurnBasedMMORPG. Use when implementing cross-feature backend communication, background task triggers, GameStreamRouter handlers, GameEventProducer publishing, correlation_id request/reply flows, or any app.state.events.publish call.
---

# TurnBasedMMORPG Redis Streams

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-redis-streams/references/redis-streams.md`

## Core Rule

Use Redis Streams for backend cross-feature communication. Do not call another backend feature's internal service directly when the interaction crosses feature ownership.

Keep Redis Streams transport out of feature `services/` and `runtime/`.

- Inbound handlers live in feature `events/`.
- Outbound stream clients live in feature `integrations/`, usually as a dedicated module such as `stream_client.py`.
- Feature services/runtime services call semantic integration methods, not `GameEventProducer.publish()`, `GameEventProducer.request()`, `publish_with_correlation()`, or raw reply queue operations.
- Redis Streams request/reply, correlation ids, timeouts, retries, reply parsing, and transport-error mapping belong to the integration layer.

Import wrappers from:

```python
from src.backend.core.bus import GameStreamRouter, GameEventProducer
```

## Handler Location

Handlers live in:

```text
src/backend/features/<feature>/events/__init__.py
```

Add handlers through `@router.on("feature.action")`.

Do not change lifespan when adding a handler unless router discovery itself is the task.

Handlers should validate and map incoming payloads, then call the feature service or integration facade. Keep handler code thin; do not put feature use-case logic or low-level Redis reply queue mechanics in handlers when an integration helper can own it.
