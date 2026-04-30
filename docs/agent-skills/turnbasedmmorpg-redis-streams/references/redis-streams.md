# Redis Streams Rules

## Event Envelope

Messages are flat dictionaries:

```python
{
    "type": "feature.action",
    "correlation_id": "uuid4",
    "field": "value",
}
```

Do not nest dictionaries. Redis stores values as strings. Serialize complex values to JSON strings explicitly.

## Naming

Use lowercase dot-separated names:

```text
actor_state.snapshot_requested
actor_state.snapshot_ready
combat.started
combat.round_resolved
inventory.item_added
```

## Fire and Forget

Publisher:

```python
await request.app.state.events.publish(
    event_type="combat.started",
    data={"combat_id": combat_id, "attacker_id": attacker_id},
)
```

Handler:

```python
from src.backend.core.bus import GameStreamRouter

router = GameStreamRouter()

@router.on("combat.started")
async def on_combat_started(payload: dict) -> None:
    combat_id = payload["combat_id"]
```

## Task and Report

Use `publish_with_correlation()` when a caller needs a reply.

Use `BLPOP` / `LPUSH` on `reply:{correlation_id}` for point-to-point replies. Set a short TTL on reply keys.

Publisher:

```python
mid, cid = await request.app.state.events.publish_with_correlation(
    event_type="actor_state.snapshot_requested",
    data={"actor_id": actor_id},
)

reply = await redis.blpop(f"reply:{cid}", timeout=10)
if reply is None:
    raise TimeoutError("actor_state did not respond")
```

Handler:

```python
@router.on("actor_state.snapshot_requested")
async def on_snapshot_requested(payload: dict) -> None:
    cid = payload.get("correlation_id")
    actor_id = payload["actor_id"]

    snapshot_key = await build_snapshot(actor_id)

    if cid:
        await redis.lpush(f"reply:{cid}", snapshot_key)
        await redis.expire(f"reply:{cid}", 30)
```

## Checklist: Handler

1. Open `src/backend/features/<feature>/events/__init__.py`.
2. Ensure `router = GameStreamRouter()` exists.
3. Add `@router.on("feature.event_name")`.
4. Keep payload flat and string-safe.
5. Add tests for routing or handler behavior when meaningful.

## Checklist: Publisher

1. Get producer from `request.app.state.events` or inject `GameEventProducer`.
2. Call `publish()` for fire-and-forget.
3. Call `publish_with_correlation()` when a reply is required.
4. Use short timeouts and explicit error handling for reply waits.
