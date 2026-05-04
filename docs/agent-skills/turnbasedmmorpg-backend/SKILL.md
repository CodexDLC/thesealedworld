---
name: turnbasedmmorpg-backend
description: Backend architecture guidance for TurnBasedMMORPG. Use when adding or changing backend FastAPI features, APIs, services, repositories, DTOs, SQLAlchemy models, workers, runtime engines, feature dependencies, or backend data ownership boundaries.
---

# TurnBasedMMORPG Backend

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-backend/references/backend-layout.md`

For Redis Streams events, also use `turnbasedmmorpg-redis-streams`.

## Core Rules

- Backend is a FastAPI monolith with explicit feature ownership.
- A feature owns its DTOs, API/services, events, runtime code, workers, and feature-specific orchestration.
- Low-level DB repositories, Redis managers, Redis schemas, and infrastructure adapters live under `src/backend/infrastructure/` when they are infrastructure primitives rather than feature business logic.
- Other features must not import a feature's internal services/runtime code directly.
- Runtime gameplay features normally use active character sessions (`game:ac:<char_id>`), temporary actor snapshots, Redis Streams events, and workers, not direct game DB access.
- Keep active character sessions and temporary actor snapshots separate:
  - `game:ac:<char_id>` is the live runtime state of a selected character.
  - `game:actor:snapshot:*` is an on-demand temporary projection for combat, inventory, builds, or future feature sessions.
- `core` exposes infrastructure primitives, not game domain behavior.
- `infrastructure` exposes low-level persistence/cache/session managers and schemas. It may contain Redis managers and DB repositories used by feature services through explicit wiring.
- `temp/` is donor code, not target architecture.

## Feature Vocabulary

Use these folder names when a layer exists:

```text
api/
dto/
models/
repositories/
integrations/  # Facades that encapsulate multiple low-level infrastructure managers (DB, Redis)
services/
dependencies/
events/
workers/
runtime/
```

Layer note:

- Use `infrastructure/` for low-level Redis managers/schemas and DB repositories.
- Use feature `services/` and `runtime/` for high-level internal logic that uses those managers.
- Use feature `integrations/` for a feature-owned facade over multiple infrastructure managers or cross-feature boundaries.
- Use feature `repositories/` only when the data access is truly feature-local and not part of the shared infrastructure layer.

Do not create empty folders just to satisfy the skeleton.
