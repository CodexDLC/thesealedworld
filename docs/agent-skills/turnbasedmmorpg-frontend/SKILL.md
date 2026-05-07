---
name: turnbasedmmorpg-frontend
description: Frontend architecture guidance for TurnBasedMMORPG. Use when adding or changing frontend features, FastAPI frontend routes, Jinja templates, HTMX fragments, Alpine/client state, frontend middleware, static CSS/JS/images, or backend API integration clients.
---

# TurnBasedMMORPG Frontend

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-frontend/references/frontend-layout.md`

If backend API contracts are involved, also use `turnbasedmmorpg-backend`.

If the task changes game shell CSS, responsive layout, side panels, header/footer, game menu, chat/HUD placement, or domain viewport sizing, also use `turnbasedmmorpg-game-css-shell`.

## Core Rules

- Frontend renders UI and calls backend APIs.
- Frontend must not access databases or import backend feature internals.
- Put gameplay page and fragment routes in `src/frontend/game_features/<feature>/routes/`.
- Put site/account/public page routes in `src/frontend/site_features/<feature>/routes/`.
- Put frontend orchestration in `src/frontend/game_features/<feature>/services/` or `src/frontend/site_features/<feature>/services/`.
- Put template-shaped data in `src/frontend/game_features/<feature>/view_models/` or `src/frontend/site_features/<feature>/view_models/`.
- Put backend HTTP clients in `src/frontend/integrations/backend_api/`.
- Put generic frontend infrastructure in `src/frontend/core/`.
- Game session screens are assembled through `src/frontend/game_features/session/services/session_context_builder.py`.
- Domain transitions such as scenario to combat must be resolved by the session context/response director layer, not by templates importing backend internals.

## Combat Frontend Rules

- Treat current backend combat DTOs as a starting reference for the browser contract, not as a finished UI shape.
- It is allowed to expand and split combat dashboard data into focused frontend view models for viewport, left sidebar, right sidebar, action bar, log feed, actor cards, effects, feints, and target state.
- Missing backend fields must render as explicit `NO_DATA`/empty states in view models and templates instead of inventing values.
- Keep frontend-facing combat contracts in shared DTOs only when both backend and frontend need the same stable shape.
- The first combat screen should be built by requesting the combat view through a typed backend API client and then assembling the `COMBAT` session context.
- Combat actions and log polling may return smaller fragments than the full `CoreResponseDTO` page payload when the UI updates only one block.
- Header/game-menu behavior may be domain-specific: combat can close, disable, or replace header tabs/windows if the battle UI needs focus or prevents unrelated panels during a turn.
- If backend/catalog data references icons that do not exist in frontend static assets, copy and adapt SVGs from `tools/icon-reserve/game-icons-net/` into a frontend-owned icon folder and map semantic icon keys to those files. Do not reference reserve paths directly from templates or JSON.

## Middleware Rule

Put global frontend middleware in `src/frontend/core/middleware.py`.

Put feature-specific request helpers, dependencies, or middleware-like behavior inside the owning feature:

```text
src/frontend/game_features/<feature>/dependencies/
src/frontend/game_features/<feature>/middleware/
src/frontend/site_features/<feature>/dependencies/
src/frontend/site_features/<feature>/middleware/
```

Do not place lobby-only, scenario-only, game-menu-only, or cabinet-only behavior in core middleware.
