# Player Realtime Gateway

Status: post-MVP improvement note.

MVP starts without this refactor. The current browser WebSocket is owned by
`chat/ws` and may continue to carry rare system/combat messages during MVP.
After MVP, the WebSocket transport should become a separate system-level
runtime surface instead of being semantically owned by chat.

## Goal

Use one browser WebSocket connection per active player session, but make it a
general player realtime gateway:

```text
src/backend/realtime/
  api/
  dto/
  events/
  integrations/
  services/
```

Target names:

- container/process: `realtime`
- backend module: `src/backend/realtime`
- endpoint: `/ws/realtime`
- connection manager: `RealtimeConnectionManager`

Chat then becomes one producer/consumer on that gateway, not the owner of all
player realtime delivery.

## Why This Is Post-MVP

The first playable slice can use HTTP/HTMX flows and the existing chat WebSocket
for rare system notifications. The refactor becomes important when gameplay
needs interactive player-facing events that should not be rendered as chat
history.

Examples:

- mass announcements should open a modal, banner, or toast instead of appearing
  as regular chat messages;
- trade requests should open a consent prompt and then a shared trade window for
  both characters;
- attacks outside a safe city should show a direct "you were attacked" modal or
  combat-entry prompt;
- arena, party, duel, group, and future social invitations should open their own
  UI flows;
- combat/session readiness events should notify the UI to fetch or patch the
  relevant gameplay fragment.

## Ownership Boundary

`realtime` owns:

- WebSocket authentication and lifecycle;
- active socket registry by `user_id`, `character_id`, and topic;
- subscription and unsubscription mechanics;
- fan-out to connected sockets;
- typed WebSocket envelope delivery;
- Redis Streams handlers that receive delivery requests from feature modules.

`chat` owns:

- chat messages, channels, DM sessions, moderation, history, and archiving;
- chat-specific DTOs and persistence;
- publishing chat delivery requests into realtime after migration.

Gameplay features own their domain state and decisions. They should not import
or call realtime internals directly. They publish semantic events through their
feature `integrations/` layer and Redis Streams.

## Event Flow

Use Redis Streams for cross-feature delivery requests:

```text
feature service/runtime
  -> feature integrations/stream_client.py
  -> Redis Streams event
  -> src/backend/realtime/events
  -> RealtimeConnectionManager
  -> browser /ws/realtime
```

Redis Stream payloads should stay flat and string-safe. Complex values should be
JSON strings:

```text
type = realtime.deliver
recipient_character_ids = [1,2] as JSON string
event_type = trade.requested
payload_json = {...} as JSON string
presentation = modal
priority = normal
```

Browser WebSocket messages may use a typed envelope:

```json
{
  "type": "trade.requested",
  "presentation": "modal",
  "payload": {
    "trade_id": "trade-123",
    "from_character_id": 12
  }
}
```

## Presentation Rules

Do not force every server event into chat.

Suggested presentation types:

- `chat`: append to a chat channel or dynamic chat tab;
- `toast`: small non-blocking notification;
- `modal`: direct blocking/confirmation prompt;
- `window`: open or update a gameplay window such as trade;
- `refresh`: tell the frontend to fetch or patch an existing HTTP/HTMX
  fragment.

Important events must also be backed by fetchable state. WebSocket delivery can
wake up the UI, but reconnecting clients should be able to recover the current
trade, combat, invitation, or modal state through normal APIs.

## Migration Path

1. Keep MVP on current HTTP/HTMX flows plus the existing `chat/ws` path.
2. Add `src/backend/realtime` with `/ws/realtime` and a
   `RealtimeConnectionManager`.
3. Move generic connection registry, user/character socket mapping, and fan-out
   behavior out of chat-specific services.
4. Add realtime Redis Streams handlers for `realtime.deliver` style events.
5. Migrate chat to publish `chat.message` delivery requests through realtime.
6. Update the browser shell to maintain one `/ws/realtime` connection and route
   incoming envelopes by `type` and `presentation`.
7. Deprecate `/ws/chat` after chat messages, combat logs, system messages, and
   gameplay prompts all use the realtime gateway.

## Non-Goals

- Do not replace feature DTOs with WebSocket-only DTOs.
- Do not make WebSocket delivery the only source of truth for critical state.
- Do not let gameplay features call a socket manager directly.
- Do not keep both `/ws/chat` and `/ws/realtime` as permanent parallel systems
  after migration.
