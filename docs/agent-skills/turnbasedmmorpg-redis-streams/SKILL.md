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

## Thin Handler Rule (mandatory)

**Handlers are transport wrappers only.** A handler must do exactly three things:

1. Extract fields from the payload.
2. Call one service or integration method.
3. Return or publish the reply.

A handler must **never**:

- Contain business logic, conditionals, or orchestration.
- Construct service objects with manual dependency wiring.
- Format ack/error responses with status fields.
- Catch and re-publish errors with fallback events.
- Exceed ~10 lines of non-boilerplate code.

### Reference: Telegram Bot (the correct pattern)

The `tg_bot` codebase already follows this rule. Use it as the reference when writing or reviewing backend handlers.

`src/tg_bot/features/redis/announcements/handlers/handlers.py`:

```python
@redis_router.message("news.published")
async def handle_news_published(message_data, container):
    orchestrator = container.get_feature("redis_announcements")
    await orchestrator.process_news(message_data)
```

Three lines. Payload in, get orchestrator, call method. The handler knows nothing about Telegram, news formatting, or error recovery. All of that lives in the orchestrator.

### Backend handlers must follow the same shape

```python
# CORRECT — thin handler
@router.on("character.combat_commitments_requested", group="character", reply=True)
async def on_combat_commitments_requested(payload: dict[str, Any]) -> None:
    service = get_character_commitment_service()
    await service.handle_combat_commitments(payload)
```

```python
# WRONG — fat handler (this is what we must stop doing)
@router.on("character.combat_commitments_requested", group="character", reply=True)
async def on_combat_commitments_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    try:
        player_ids = [int(v) for v in json.loads(payload.get("player_ids", []))]
        result = await CharacterCombatCommitmentIntegration(
            character_sessions=_app.state.character_sessions,
            commitment_manager=_app.state.actor_commitments,
        ).prepare_commitments(player_ids=player_ids, ...)
        ack = {"status": "ok", "commitments": result.commitments}
        await _app.state.events.publish("character.combat_commitments_ready", ack)
    except Exception:
        ack = {"status": "error", ...}
        await _app.state.events.publish("character.combat_commitments_failed", ack)
    if cid:
        await _app.state.events.publish_reply(cid, ack, ttl=30)
```

If a handler looks like the second example, the code review must reject it. Move the logic into a service or orchestrator method and make the handler thin.
