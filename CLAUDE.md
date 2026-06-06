# TurnBasedMMORPG — Agent Notes

## Project Skills

Before architecture or implementation work, read the relevant project skill files in `docs/agent-skills/`. Do not infer project architecture from folder absence alone; the skills are the source of truth for intended boundaries.

Use:

- `docs/agent-skills/turnbasedmmorpg-project/SKILL.md` for repository-wide rules, source-tree ownership, donor-code migration, shared contracts, and handoff prompts.
- `docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md` for frontend routes, services, view models, templates, static assets, middleware placement, and backend API clients.
- `docs/agent-skills/turnbasedmmorpg-studio/SKILL.md` for `src/studio/*` (local-only analytical cabinet on port 9100): source-switcher contract, read-only-on-prod policy, module migration rules, what belongs in studio vs prod cabinet.
- `docs/agent-skills/turnbasedmmorpg-design-system/SKILL.md` for frontend design-system usage, shared class reuse order, shell/include drift checks, and rules for adding CSS only after existing project styles are exhausted.
- `docs/agent-skills/turnbasedmmorpg-backend/SKILL.md` for backend feature layout, APIs, DTOs, models, repositories, services, workers, runtime code, and data ownership.
- `docs/agent-skills/turnbasedmmorpg-redis-streams/SKILL.md` for Redis Streams, `GameStreamRouter`, `GameEventProducer`, event handlers, publishing, and `correlation_id` reply flows.
- `docs/agent-skills/turnbasedmmorpg-feature-slice/SKILL.md` when a task spans backend, frontend, shared contracts, templates, tests, or events.
- `docs/agent-skills/turnbasedmmorpg-quality-gate/SKILL.md` before declaring code complete, before commits/PRs, or when choosing between full and targeted local validation.
- `docs/agent-skills/turnbasedmmorpg-release-flow/SKILL.md` before deciding which branch a change goes into, what version number to bump to, whether work needs a player-progress wipe, or how to phrase the matching announcement. This is the source of truth that the changelog and deployment skills follow.
- `docs/agent-skills/turnbasedmmorpg-combat-triggers/SKILL.md` before any work with combat triggers: adding a new trigger, weapon trigger, changing log_builder trigger rendering, event_texts, or merge rules.
- `docs/agent-skills/turnbasedmmorpg-logging-quality/SKILL.md` when writing or reviewing code with logger calls, adding new features with logging, or before commits. References `docs/logging-rules.md`.

Rule of thumb: if a task changes structure or crosses feature boundaries, read the project skill plus the specific frontend/backend/event skill before editing code. After code edits, use the quality-gate skill and report the verification command that ran.

For backend work involving repositories, Redis managers, Redis schemas, sessions, or infrastructure modules, read `turnbasedmmorpg-backend` before editing. Feature code should go through feature `integrations/`; domain infrastructure lives under `src/backend/infrastructure/<domain>/` and may contain `schemas/`, `models/`, `repositories/`, `managers/`, and adapters.

For frontend visual work, also read:

- `docs/design-system/README.md` for the canonical text summary of the design system, class reuse order, and shared-layer audit notes.
- `docs/design-system/Design System.html` as the canonical visual reference. Do not treat `/system/design` as the source of truth.

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
When answering architecture, ownership, dependency, or "where is this implemented?" questions, use Graphify as project context:

- Check `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.json`, and `graphify-out/wiki/` before doing broad manual scans.
- Use Graphify query/path/explain workflows when relationships across files or features matter.
- If skills, architecture docs, or significant source files changed since the last graph build, update Graphify before relying on it.
- After changing docs or architecture rules, run a Graphify update and regenerate the wiki when practical.
