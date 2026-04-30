# TurnBasedMMORPG — Agent Notes

## Project Skills

Before architecture or implementation work, read the relevant project skill files in `docs/agent-skills/`.

Use:

- `docs/agent-skills/turnbasedmmorpg-project/SKILL.md` for repository-wide rules, source-tree ownership, donor-code migration, shared contracts, and handoff prompts.
- `docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md` for frontend routes, services, view models, templates, static assets, middleware placement, and backend API clients.
- `docs/agent-skills/turnbasedmmorpg-backend/SKILL.md` for backend feature layout, APIs, DTOs, models, repositories, services, workers, runtime code, and data ownership.
- `docs/agent-skills/turnbasedmmorpg-redis-streams/SKILL.md` for Redis Streams, `GameStreamRouter`, `GameEventProducer`, event handlers, publishing, and `correlation_id` reply flows.
- `docs/agent-skills/turnbasedmmorpg-feature-slice/SKILL.md` when a task spans backend, frontend, shared contracts, templates, tests, or events.
- `docs/agent-skills/turnbasedmmorpg-quality-gate/SKILL.md` before declaring code complete, before commits/PRs, or when choosing between full and targeted local validation.

Rule of thumb: if a task changes structure or crosses feature boundaries, read the project skill plus the specific frontend/backend/event skill before editing code. After code edits, use the quality-gate skill and report the verification command that ran.

## Event Bus (Redis Streams)

Before implementing any cross-feature communication, background task, or anything that involves
one feature triggering work in another, read `docs/agent-skills/turnbasedmmorpg-redis-streams/SKILL.md`.

**When to apply:**
- A feature needs to notify another feature that something happened
- A feature needs another feature to do work and return a result
- A background worker needs to be triggered (e.g. `actor_state` building a Redis snapshot)
- Any `app.state.events.publish(...)` call

## Graphify

Knowledge graph outputs for this project are stored in `graphify-out/`.
When exploring the codebase architecture visually, check there first before generating a new graph.
