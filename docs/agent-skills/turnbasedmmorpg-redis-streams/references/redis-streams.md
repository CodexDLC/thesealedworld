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
character.combat_snapshots_requested
character.combat_snapshots_ready
character.gear_score_recalculate_requested
combat.started
combat.round_resolved
inventory.item_added
```

## Fire and Forget

Outbound stream client in `features/<feature>/integrations/stream_client.py`:

```python
class CombatStreamClient:
    def __init__(self, events: GameEventProducer) -> None:
        self.events = events

    async def notify_combat_started(self, *, combat_id: str, attacker_id: int) -> None:
        await self.events.publish(
            event_type="combat.started",
            data={"combat_id": combat_id, "attacker_id": attacker_id},
        )
```

Inbound handler in `features/<feature>/events/__init__.py`:

```python
from src.backend.core.bus import GameStreamRouter

router = GameStreamRouter()

@router.on("combat.started")
async def on_combat_started(payload: dict) -> None:
    combat_id = payload["combat_id"]
```

Feature services/runtime services should call semantic integration methods, not `GameEventProducer.publish()` directly.

## Task and Report

Use request/reply when a caller needs a reply. The request/reply mechanics belong in the feature integration layer.

Use `BLPOP` / `LPUSH` on `reply:{correlation_id}` for point-to-point replies. Set a short TTL on reply keys.

Outbound stream client:

```python
class CharacterCombatSnapshotStreamClient:
    def __init__(self, events: GameEventProducer) -> None:
        self.events = events

    async def request_combat_snapshot(self, *, char_id: int) -> str:
        response = await self.events.request(
            "character.combat_snapshots_requested",
            {"session_id": "combat-1", "player_ids": "[1]", "monster_ids": "[]"},
            timeout=10,
        )
        if not isinstance(response, dict) or not response.get("snapshot_key"):
            raise TimeoutError("character did not respond with a combat snapshot")
        return str(response["snapshot_key"])
```

Handler:

```python
@router.on("character.combat_snapshots_requested")
async def on_combat_snapshot_requested(payload: dict) -> None:
    cid = payload.get("correlation_id")
    player_ids = payload["player_ids"]

    snapshot_keys = await build_combat_snapshots(player_ids)

    if cid:
        await redis.lpush(f"reply:{cid}", snapshot_keys)
        await redis.expire(f"reply:{cid}", 30)
```

If a handler needs to publish a reply or error, prefer delegating the reply mapping and transport details to an integration helper. Handlers should stay focused on inbound payload validation and dispatch.

`character.combat_snapshots_requested` prepares temporary combat actor projections from `game:ac:<char_id>` and monster runtime sources. It must not be used as the live character session itself. The live selected-character runtime document is `game:ac:<char_id>`; snapshot keys such as `game:actor:snapshot:*` are derived transport/cache objects for combat sessions.

## Checklist: Handler

1. Open `src/backend/features/<feature>/events/__init__.py`.
2. Ensure `router = GameStreamRouter()` exists.
3. Add `@router.on("feature.event_name")`.
4. Keep payload flat and string-safe.
5. Add tests for routing or handler behavior when meaningful.

## Checklist: Publisher

1. Add or update a feature stream client under `src/backend/features/<feature>/integrations/`.
2. Inject `GameEventProducer` into that stream client or into the feature integration facade that owns it.
3. Expose semantic methods such as `notify_combat_started()` or `request_actor_snapshot()`.
4. Keep event names, payload mapping, correlation ids, timeouts, retries, reply parsing, and transport-error mapping inside the integration layer.
5. Services/runtime services must call the semantic integration method, not raw stream producer methods.
