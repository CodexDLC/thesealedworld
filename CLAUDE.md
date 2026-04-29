# TurnBasedMMORPG — Agent Notes

## Event Bus (Redis Streams)

Before implementing any cross-feature communication, background task, or anything that involves
one feature triggering work in another — read:

**`docs/architecture/event-bus.md`**

This covers: architecture overview, `GameStreamRouter`, `GameEventProducer`, all three patterns
(fire-and-forget, task+report, request-reply), naming conventions, and step-by-step checklists.

**When to apply:**
- A feature needs to notify another feature that something happened
- A feature needs another feature to do work and return a result
- A background worker needs to be triggered (e.g. `actor_state` building a Redis snapshot)
- Any `app.state.events.publish(...)` call

## Graphify

Knowledge graph outputs for this project are stored in `graphify-out/`.
When exploring the codebase architecture visually, check there first before generating a new graph.
