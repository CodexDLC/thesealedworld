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
