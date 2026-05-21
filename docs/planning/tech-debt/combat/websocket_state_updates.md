# Combat WebSocket State Updates

Status: post-MVP improvement note.

The MVP combat screen uses normal HTTP/HTMX refreshes. `ACTION_LOCKED` and
`TARGET_QUEUE_EMPTY` may poll the current snapshot, and player actions return a
fresh dashboard or result payload.

Generic post-MVP player realtime delivery is tracked separately in
`docs/planning/tech-debt/realtime/player_realtime_gateway.md`. Combat state
notifications should eventually ride that single player realtime connection
instead of creating a second browser WebSocket.

Future combat and arena WebSocket work should focus on state that changes
without a direct player request:

- opponent responded to the player's exchange;
- pair became ready to resolve;
- pair resolved and produced a new exchange summary;
- target queue changed;
- player action became locked;
- combat finished;
- arena queue, invite, and combat-start state changed;
- combat/system chat events were emitted.

The WebSocket contract should not replace the combat DTOs. It should push small
state-change notifications that cause the frontend to fetch or patch the same
dashboard fragments used by the HTTP flow.
