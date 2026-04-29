# Event Bus — Redis Streams

## Overview

Features communicate through a shared Redis Stream. No direct cross-feature method calls.
One stream, one consumer group, one processor loop — all handlers registered via router decorators.

```
Publisher (any feature)
  └─► Redis Stream: game_events
        └─► StreamProcessor (polling loop)
              └─► StreamDispatcher
                    ├─► auth handlers
                    ├─► combat handlers
                    ├─► actor_state handlers
                    └─► ... (all features)
```

## Core classes (project-level wrappers)

| Class | Location | Role |
|---|---|---|
| `GameStreamRouter` | `src/backend/core/bus/router.py` | Decorator for registering handlers. Extends `StreamRouter` with `group` and `reply` params. |
| `GameEventProducer` | `src/backend/core/bus/producer.py` | Publishes events. Wraps `StreamProducer.add_event()` and adds `correlation_id` support. |

Import from:
```python
from src.backend.core.bus import GameStreamRouter, GameEventProducer
```

At runtime, `app.state.events` is a `GameEventProducer` instance (set in lifespan).

## Where handlers live

Every feature that listens to the bus has:

```
src/backend/features/<feature>/
  events/
    __init__.py   ← router = GameStreamRouter(); handlers defined here
```

If a feature does not listen — the file stays empty. That is fine.

All routers are included in `src/backend/core/lifespan.py` via `dispatcher.include_router(router)`.
**When you add a new handler, you only touch `events/__init__.py`. No changes to lifespan needed.**

## Event envelope

Every message on the stream is a flat dict:

```python
{
    "type": "feature.action",          # required — used for routing
    "correlation_id": "uuid4",         # optional — for request/reply
    # ... flat payload fields
}
```

`GameEventProducer.publish()` builds this automatically. Do not nest dicts — Redis stores all values as strings (`_sanitize` in `StreamProducer`). Keep payload fields flat or serialize complex structures to JSON strings explicitly.

## Naming convention

`<feature>.<action>` — lowercase, dot-separated:

```
actor_state.snapshot_requested
actor_state.snapshot_ready
combat.started
combat.round_resolved
inventory.item_added
```

---

## Patterns

### Pattern 1 — Fire and forget

Publish an event, no reply expected.

```python
# Publisher (e.g. in a service or API handler)
await request.app.state.events.publish(
    event_type="combat.started",
    data={"combat_id": combat_id, "attacker_id": attacker_id},
)

# Handler in src/backend/features/combat/events/__init__.py
from src.backend.core.bus import GameStreamRouter

router = GameStreamRouter()

@router.on("combat.started")
async def on_combat_started(payload: dict) -> None:
    combat_id = payload["combat_id"]
    # do work
```

---

### Pattern 2 — Task + Report (used by actor_state)

Publisher puts a task in the stream and **waits** for a report event on a reply stream.
Worker picks up the task, does work, publishes result back.

```
Publisher                              Worker (actor_state handler)
   │                                        │
   ├─► publish "actor_state.snapshot_requested"
   │     {correlation_id: "uuid", actor_id: "..."}
   │                                        │
   │                              picks up event
   │                              loads DB → writes Redis snapshot
   │                                        │
   │                              publish "actor_state.snapshot_ready"
   │                                {correlation_id: "uuid", snapshot_key: "..."}
   │                                        │
   │◄── XREAD BLOCK on reply stream ────────┘
   │    matched by correlation_id
   │
   continues execution
```

**Publisher side:**
```python
mid, cid = await request.app.state.events.publish_with_correlation(
    event_type="actor_state.snapshot_requested",
    data={"actor_id": actor_id},
)

# Wait for reply — blocking read on a dedicated reply key
reply = await redis.blpop(f"reply:{cid}", timeout=10)
if reply is None:
    raise TimeoutError("actor_state did not respond")
snapshot_key = reply[1]
```

**Worker side (actor_state):**
```python
@router.on("actor_state.snapshot_requested")
async def on_snapshot_requested(payload: dict) -> None:
    cid = payload.get("correlation_id")
    actor_id = payload["actor_id"]

    snapshot_key = await build_snapshot(actor_id)   # load DB → write Redis

    if cid:
        await redis.lpush(f"reply:{cid}", snapshot_key)
        await redis.expire(f"reply:{cid}", 30)
```

> Use `BLPOP` / `LPUSH` for point-to-point replies (simpler than a reply stream).
> Set a short TTL on the reply key to avoid leaks.

---

### Pattern 3 — Request / Reply via correlation_id (full stream round-trip)

When the reply itself needs to be consumed by multiple subscribers or logged.

```python
# Publisher
mid, cid = await app.state.events.publish_with_correlation(
    event_type="inventory.calculate_requested",
    data={"actor_id": actor_id, "item_ids": "1,2,3"},
)

# Handler publishes result back to the same stream
@router.on("inventory.calculate_requested")
async def on_calculate(payload: dict) -> None:
    result = await calculate(payload["item_ids"])
    await app.state.events.publish(
        event_type="inventory.calculate_result",
        data={"result": str(result)},
        correlation_id=payload.get("correlation_id"),
    )
```

---

## Future: splitting features into separate containers

Each handler can be tagged with a `group`:

```python
@router.on("combat.started", group="combat_service")
async def on_combat_started(payload: dict) -> None:
    ...
```

When the feature moves to its own container:
1. Its router is moved to the new service
2. A new `StreamProcessor` is created with `consumer_group_name="combat_service"`
3. The monolith dispatcher stops including that router

No handler logic changes — only configuration.

---

## Checklist: adding a new handler

1. Open `src/backend/features/<your_feature>/events/__init__.py`
2. Add `@router.on("feature.event_name")` with your handler function
3. Payload fields are flat strings — deserialize if needed
4. Done. Lifespan already includes this router.

## Checklist: publishing an event

1. Get producer: `producer = request.app.state.events`
2. Call `await producer.publish(event_type, data)` — flat dict, no nested objects
3. Need a reply? Use `publish_with_correlation()` and read from `reply:{cid}` via `BLPOP`
