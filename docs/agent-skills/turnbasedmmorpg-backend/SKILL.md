---
name: turnbasedmmorpg-backend
description: Backend architecture guidance for TurnBasedMMORPG. Use when adding or changing backend FastAPI features, APIs, services, repositories, DTOs, SQLAlchemy models, workers, runtime engines, feature dependencies, or backend data ownership boundaries.
---

# TurnBasedMMORPG Backend

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-backend/references/backend-layout.md`

For service split, chat absorption, backend Alembic, game schema, site/game boundary, or frontend independence work, also read:

- `docs/ru/backend/index.md`
- `docs/ru/frontend/index.md`
- `docs/ru/frontend/integrations.md`
- `docs/ru/management/deployment-contract.md`

For Redis Streams events, also use `turnbasedmmorpg-redis-streams`.

## Core Rules

- Backend is a FastAPI monolith with explicit feature ownership.
- Treat `src/backend` as the game backend: gameplay APIs, runtime state, workers, Redis streams, game schema, and backend-owned chat belong here.
- Site auth, user/account, cabinet, library, public site rendering, and site Alembic belong to the frontend/site service, not backend.
- Chat should be absorbed into backend ownership as a backend feature/module; a separate chat container may still run, but it should use the backend codebase instead of a duplicated app/config/database layer.
- Backend Alembic should own only game and chat schemas after site auth is moved out.
- Game APIs that receive `character_id` must verify `current_user.id == character.user_id`; do not rely on client-provided ownership.
- A feature owns its DTOs, API/services, integrations, events, runtime code, workers, and feature-specific orchestration.
- Feature `integrations/` is the normal boundary for feature code that works with infrastructure. Services, runtime code, API handlers, and workers should use semantic integration methods instead of reaching into low-level infrastructure directly.
- Low-level domain infrastructure lives under `src/backend/infrastructure/<domain>/`. A domain infrastructure package may contain `schemas/`, `models/`, `repositories/`, `managers/`, and adapters when those modules are persistence, cache, session, Redis, or transport details rather than feature business logic.
- Other features must not import a feature's internal services/runtime code directly.
- Runtime gameplay features normally use active character sessions (`game:ac:<char_id>`), temporary actor snapshots, Redis Streams events, and workers, not direct game DB access.
- Keep active character sessions and temporary actor snapshots separate:
  - `game:ac:<char_id>` is the live runtime state of a selected character.
  - `game:actor:snapshot:*` is an on-demand temporary projection for combat, inventory, builds, or future feature sessions.
- `core` exposes infrastructure primitives, not game domain behavior.
- `infrastructure` exposes domain-grouped low-level persistence/cache/session managers, schemas, models, repositories, and adapters. Feature code works with those modules through feature integrations unless the file is itself dependency wiring.
- `temp/` is donor code, not target architecture.

## Feature Vocabulary

Use these folder names for feature layers. Create a layer when the feature has that responsibility; in particular, create `integrations/` whenever the feature needs infrastructure access or outbound cross-feature communication:

```text
api/
dto/
models/
repositories/
integrations/  # Feature-owned boundary to infrastructure managers, repositories, Redis Streams clients, sessions, and cross-feature flows
services/
dependencies/
events/
workers/
runtime/
```

Layer note:

- Use `infrastructure/<domain>/` for low-level Redis managers, Redis schemas, SQLAlchemy models, DB repositories, session managers, and adapters owned by that infrastructure domain.
- Use feature `integrations/` as the main feature-facing layer for infrastructure access. It exposes semantic feature operations over infrastructure managers, repositories, sessions, Redis Streams clients, or cross-feature boundaries.
- Use feature `services/` and `runtime/` for high-level internal logic that calls integrations, not low-level Redis/DB/session modules directly.
- Put outbound Redis Streams clients in feature `integrations/`, not in `services/` or `runtime/`.
- Keep inbound Redis Streams handlers in feature `events/`.
- Feature `services/` and `runtime/` must call semantic integration methods such as `request_actor_snapshot()` or `publish_round_resolved()`, not `GameEventProducer.publish()` / `request()` directly.
- Do not create feature persistence gateway layers that merely mirror CRUD methods from infrastructure repositories/managers. Feature integrations may depend directly on infrastructure repositories/managers, but they must expose semantic feature operations to services.
- Use feature `repositories/` only when the data access is truly feature-local and not part of the shared infrastructure layer.

When implementing a feature that needs infrastructure access, create the feature `integrations/` layer as part of the slice. Do not skip it and wire services directly to infrastructure.

Do not create empty folders just to satisfy the skeleton. For a not-yet-implemented feature, a missing `integrations/` folder means the layer has not been built yet; it does not mean services should bypass integrations once infrastructure access is added.

## Stable Documentation Rule

When backend/game ownership, service boundaries, schemas, or deployment behavior
change, update the stable documentation in `docs/ru/` and the relevant changelog.
Planning task files are temporary and should be removed after implementation.
