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

Inbound handler in `features/<feature>/events/__init__.py` — **must be thin**:

```python
from src.backend.core.bus import GameStreamRouter

router = GameStreamRouter()

@router.on("combat.started")
async def on_combat_started(payload: dict) -> None:
    service = get_combat_notification_service()
    await service.handle_combat_started(payload)
```

The handler extracts nothing, builds nothing, catches nothing. It delegates to a service. This is the only acceptable handler shape.

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

Handler — **must be thin**, even for request/reply:

```python
@router.on("character.combat_snapshots_requested")
async def on_combat_snapshot_requested(payload: dict) -> None:
    service = get_character_snapshot_service()
    await service.handle_combat_snapshot_request(payload)
```

The service method internally parses `player_ids`, builds snapshots, and publishes the reply. The handler does not touch `correlation_id`, `redis.lpush`, payload parsing, or error formatting.

**Never put reply mechanics, error recovery, or payload parsing in a handler.** All of that belongs in the service or integration layer.

`character.combat_snapshots_requested` prepares temporary combat actor projections from `game:ac:<char_id>` and monster runtime sources. It must not be used as the live character session itself. The live selected-character runtime document is `game:ac:<char_id>`; snapshot keys such as `game:actor:snapshot:*` are derived transport/cache objects for combat sessions.

## Checklist: Handler

1. Open `src/backend/features/<feature>/events/__init__.py`.
2. Ensure `router = GameStreamRouter()` exists.
3. Add `@router.on("feature.event_name")`.
4. Keep payload flat and string-safe.
5. **Verify the handler is thin**: get service/orchestrator, call one method, done. If the handler body exceeds ~10 lines of non-boilerplate code, it is too fat — move logic to a service.
6. **Compare against the tg_bot reference** (`src/tg_bot/features/redis/announcements/handlers/handlers.py`): the handler should look structurally identical — 3 lines max.
7. Add tests for routing or handler behavior when meaningful.

## Checklist: Publisher

1. Add or update a feature stream client under `src/backend/features/<feature>/integrations/`.
2. Inject `GameEventProducer` into that stream client or into the feature integration facade that owns it.
3. Expose semantic methods such as `notify_combat_started()` or `request_actor_snapshot()`.
4. Keep event names, payload mapping, correlation ids, timeouts, retries, reply parsing, and transport-error mapping inside the integration layer.
5. Services/runtime services must call the semantic integration method, not raw stream producer methods.
