---
name: turnbasedmmorpg-frontend
description: Frontend architecture guidance for TurnBasedMMORPG. Use when adding or changing frontend features, FastAPI frontend routes, Jinja templates, HTMX fragments, Alpine/client state, frontend middleware, static CSS/JS/images, or backend API integration clients.
---

# TurnBasedMMORPG Frontend

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-frontend/references/frontend-layout.md`

For service split, auth/user, cabinet, library, frontend database, frontend Alembic, game-backend availability, or site/game boundary work, also read:

- `docs/tasks/service_split_finalization.md`
- `docs/tasks/service_split_frontend_site.md`

If backend API contracts are involved, also use `turnbasedmmorpg-backend`.

If the task changes game shell CSS, responsive layout, side panels, header/footer, game menu, chat/HUD placement, or domain viewport sizing, also use `turnbasedmmorpg-game-css-shell`.

If the task changes UI design, choose the surface-specific design skill before editing:

- Public website, landing, library, auth pages: `turnbasedmmorpg-site-design`.
- Cabinet/admin/operational dashboards: `turnbasedmmorpg-cabinet-design`.
- Gameplay HUD, `design_prototype`, exploration/combat/scenario/loot/status/inventory: `turnbasedmmorpg-game-interface-design`.

## Core Rules

- Frontend renders UI and calls backend APIs.
- Frontend must not access databases or import backend feature internals.
- During the service split, treat `src/frontend` as the server-side site service: user layer, auth, cabinet, library, public site, templates, site-owned repositories, and site Alembic belong here.
- Site-owned feature folders live under `src/frontend/features/<feature>/`.
- Site-owned repositories may live inside the owning frontend feature folder; do not add a broad shared repository layer until real model count or reuse justifies it.
- Game data access must go through typed clients under `src/frontend/integrations/backend_api/`.
- Game backend downtime must be rendered as unavailable or maintenance UI instead of breaking the site.
- Put gameplay page and fragment routes in `src/frontend/game_features/<feature>/routes/`.
- Put site/account/public page routes in `src/frontend/features/<feature>/routes/`.
- Put frontend orchestration in `src/frontend/game_features/<feature>/services/` or `src/frontend/features/<feature>/services/`.
- Put template-shaped data in `src/frontend/game_features/<feature>/view_models/` or `src/frontend/features/<feature>/view_models/`.
- Put backend HTTP clients in `src/frontend/integrations/backend_api/`.
- Put generic frontend infrastructure in `src/frontend/core/`.
- Game session screens are assembled through `src/frontend/game_features/session/services/session_context_builder.py`.
- Domain transitions such as scenario to combat must be resolved by the session context/response director layer, not by templates importing backend internals.
- Frontend architecture guidance is not enough for UI work. Public site design, cabinet design, and gameplay interface design are separate surfaces with separate rules. Do not use one surface's layout language as the default for another.

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
src/frontend/features/<feature>/dependencies/
src/frontend/features/<feature>/middleware/
```

Do not place lobby-only, scenario-only, game-menu-only, or cabinet-only behavior in core middleware.

## Service Split Closure Rule

Before closing a frontend/site service split task, update the relevant task document with the actual decision, file moves, deferred work, and any deviation from the planned architecture:

- `docs/tasks/service_split_finalization.md`
- `docs/tasks/service_split_frontend_site.md`
