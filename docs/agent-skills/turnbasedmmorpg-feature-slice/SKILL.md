---
name: turnbasedmmorpg-feature-slice
description: End-to-end feature slice guidance for TurnBasedMMORPG. Use when adding a feature that spans backend APIs/services/DTOs, frontend routes/services/view models/templates, shared contracts, tests, and optional Redis Streams events.
---

# TurnBasedMMORPG Feature Slice

## First Reads

Use these skills together:

- `turnbasedmmorpg-project`
- `turnbasedmmorpg-backend`
- `turnbasedmmorpg-frontend`
- `turnbasedmmorpg-redis-streams` when events or workers are involved
- `turnbasedmmorpg-quality-gate` before declaring the slice complete

## Slice Order

1. Identify the owning backend feature.
2. Define backend API request/response contracts.
3. Put shared contracts in `src/shared` only if frontend and backend both use them.
4. Implement backend integrations before services when the feature needs infrastructure, Redis Streams, session managers, repositories, or cross-feature flows.
5. Implement backend service/repository/runtime changes inside the owning feature. Services/runtime code should call semantic integration methods for infrastructure work.
6. Add or update the frontend backend API client.
7. Add frontend routes, services, view models, forms, and templates inside the owning frontend feature.
8. Add Redis Streams events only for cross-feature backend communication. **Handlers must be thin** — get service, call method, done. No business logic in handlers. See `turnbasedmmorpg-redis-streams` skill for the mandatory thin handler rule and the tg_bot reference pattern.
9. Add focused tests for the changed backend, shared contracts, and frontend integration points.
10. Run the strongest practical quality gate through `tools/dev/check.py` or documented targeted fallback checks.

## Keep Boundaries

Do not skip the backend API client by importing backend services from frontend.

Do not move feature-specific behavior into global core modules.

Do not create shared DTOs for one-side-only convenience.

Do not wire feature services directly to low-level `src/backend/infrastructure/<domain>/` modules when an integration boundary is part of the feature slice.
