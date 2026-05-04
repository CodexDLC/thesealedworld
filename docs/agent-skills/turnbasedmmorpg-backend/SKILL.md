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
- A feature owns its data, repositories, services, events, runtime code, and workers.
- Other features must not import a feature's internal services or repositories directly.
- Runtime gameplay features normally use Redis snapshots, Redis Streams events, and workers, not direct game DB access.
- `core` exposes infrastructure primitives, not game domain behavior.
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

Do not create empty folders just to satisfy the skeleton.
