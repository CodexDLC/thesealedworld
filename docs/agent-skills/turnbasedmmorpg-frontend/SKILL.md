---
name: turnbasedmmorpg-frontend
description: Frontend architecture guidance for TurnBasedMMORPG. Use when adding or changing frontend features, FastAPI frontend routes, Jinja templates, HTMX fragments, Alpine/client state, frontend middleware, static CSS/JS/images, or backend API integration clients.
---

# TurnBasedMMORPG Frontend

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-frontend/references/frontend-layout.md`

If backend API contracts are involved, also use `turnbasedmmorpg-backend`.

## Core Rules

- Frontend renders UI and calls backend APIs.
- Frontend must not access databases or import backend feature internals.
- Put page and fragment routes in `src/frontend/features/<feature>/routes/`.
- Put frontend orchestration in `src/frontend/features/<feature>/services/`.
- Put template-shaped data in `src/frontend/features/<feature>/view_models/`.
- Put backend HTTP clients in `src/frontend/integrations/backend_api/`.
- Put generic frontend infrastructure in `src/frontend/core/`.

## Middleware Rule

Put global frontend middleware in `src/frontend/core/middleware.py`.

Put feature-specific request helpers, dependencies, or middleware-like behavior inside the owning feature:

```text
src/frontend/features/<feature>/dependencies/
src/frontend/features/<feature>/middleware/
```

Do not place lobby-only, scenario-only, game-menu-only, or cabinet-only behavior in core middleware.
