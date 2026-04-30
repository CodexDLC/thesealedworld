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
4. Implement backend service/repository/runtime changes inside the owning feature.
5. Add or update the frontend backend API client.
6. Add frontend routes, services, view models, forms, and templates inside the owning frontend feature.
7. Add Redis Streams events only for cross-feature backend communication.
8. Add focused tests for the changed backend, shared contracts, and frontend integration points.
9. Run the strongest practical quality gate through `tools/dev/check.py` or documented targeted fallback checks.

## Keep Boundaries

Do not skip the backend API client by importing backend services from frontend.

Do not move feature-specific behavior into global core modules.

Do not create shared DTOs for one-side-only convenience.
