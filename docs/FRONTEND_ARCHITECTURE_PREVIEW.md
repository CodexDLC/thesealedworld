# Frontend Architecture Preview

## Goal

Frontend is a server-rendered web gateway for the game and site UI. It uses FastAPI, Jinja templates, HTMX-style fragments, Alpine-style client state, static assets, and typed clients to call the backend API.

Frontend should not own database access or game domain persistence. Its job is to route browser requests, call backend APIs, assemble view models, and render pages or fragments.

The main rule is separation of concerns:

- backend features own game behavior, persistence, runtime state, and API contracts
- frontend features own routes, page/fragment orchestration, forms, and view models
- shared code contains only stable contracts that are genuinely used by both backend and frontend

## Target Skeleton

```text
src/frontend/
  app.py
  manage.py
  config/
  core/
  integrations/
    backend_api/
      __init__.py
      base.py
      auth.py
      site.py
      actor_state.py
      game_menu.py
      inventory.py
      combat.py
      exploration.py
      scenario.py
      chat.py
  features/
    <feature_name>/
      routes/
      services/
      view_models/
      forms/
      dependencies/
  templates/
  static/
```

This is a target shape, not a requirement to create empty folders everywhere. A feature should add folders only when it actually needs them, but the allowed folder names should stay consistent.

## Application Root

`app.py` is the composition root for the frontend app.

Responsibilities:

- create the FastAPI app
- mount static files
- register global middleware
- register error handlers
- include feature routers
- initialize shared app state such as templates and HTTP clients

Top-level page routes may temporarily live in `app.py` during prototyping, but the target structure is to move real routes into `src/frontend/features/*/routes/`.

`manage.py` is a development entrypoint for running the frontend server and compiling static assets.

## Core

`src/frontend/core/` contains frontend infrastructure that is not owned by a specific web feature.

Expected responsibilities:

- `renderer.py`: Jinja rendering, global context injection, HTMX-aware rendering rules
- `api.py`: base HTTP client primitives
- `static.py`: static asset compilation helpers

`core` should not contain game-specific page orchestration, backend API area clients, or template-specific view models.

## Backend API Integrations

`src/frontend/integrations/backend_api/` is a flat typed-client layer for backend API calls.

It is intentionally similar to a repository layer from the point of view of frontend services: frontend code calls class methods instead of building HTTP requests directly. Under the hood these classes call backend HTTP API routes, not the database.

Example:

```text
src/frontend/integrations/backend_api/
  base.py
  auth.py
  actor_state.py
  inventory.py
  chat.py
```

Example responsibilities:

- `auth.py`: login, logout, session/current-user API calls
- `site.py`: public site content API calls
- `actor_state.py`: current actor status/snapshot API calls
- `game_menu.py`: menu state and menu actions
- `inventory.py`: inventory reads and item actions
- `combat.py`: combat state and combat actions
- `chat.py`: chat history, channels, send-message API calls

`__init__.py` may gather public client classes for convenient imports.

Allowed:

- `integrations/backend_api/* -> frontend/core/api`
- `integrations/backend_api/* -> shared/api_contracts`
- `frontend/features/* -> integrations/backend_api`

Avoid:

- database access from `integrations/backend_api`
- importing `src/backend/features/*`
- putting page-specific view assembly in API clients
- hiding business behavior in API clients that belongs to backend services

## Frontend Features

`src/frontend/features/*` is the web feature layer. Each feature uses the same folder vocabulary, but files inside those folders should be named for the feature's real use cases.

Example:

```text
src/frontend/features/game/
  routes/
    pages.py
    fragments.py
  services/
    game_shell_service.py
    status_panel_service.py
    menu_panel_service.py
  view_models/
    game_shell.py
    status_panel.py
    menu_panel.py
  forms/
  dependencies/
```

Folder responsibilities:

- `routes/`: FastAPI routers for pages, forms, and HTMX fragments
- `services/`: frontend orchestration services that call backend API clients and assemble view data
- `view_models/`: models shaped for templates, not for backend persistence
- `forms/`: frontend input parsing and validation for submitted forms
- `dependencies/`: FastAPI dependencies and wiring local to the feature

Frontend feature services may call multiple backend API clients in parallel when a page or fragment needs multiple data sources. For example, a game shell may load status, menu, inventory, and chat state together before rendering.

Frontend features should not import each other's internal services directly. Shared UI orchestration should be promoted to `core` only if it is truly generic, or kept behind backend API contracts when it is domain data.

## Templates

`src/frontend/templates/` stores Jinja templates.

Current target groups:

- `site/`: public site pages and site base layout
- `auth/`: login and account entry screens
- `game/`: game shell, game layouts, panels, and fragment templates
- `includes/`: common partials such as header, footer, meta, scripts, and minimal HTMX layout
- `errors/`: error pages
- `system/`: design system and internal UI preview pages

Templates are physically stored under `templates/`, but they are logically owned by frontend features. A route in `features/game/routes/` may render `templates/game/index.html`; a route in `features/site/routes/` may render `templates/site/index.html`.

Template-specific models belong in `features/*/view_models/`, not in `shared`.

## Static Assets

`src/frontend/static/` stores CSS, JavaScript, images, and vendored browser libraries.

Expected CSS groups:

- `css/core/`: tokens, reset, animations
- `css/layout/`: containers, ambient layout, responsive rules
- `css/components/`: reusable UI components
- `css/includes/`: header, footer, navigation, shared includes
- `css/pages/`: page-specific styles
- `css/pages/game/`: game-specific page and panel styles
- `css/vendor/`: vendored CSS

Expected JS groups:

- `js/core/`: source modules shared by frontend bundles
- `js/vendor/`: vendored browser libraries
- top-level bundle files such as `site.js` and `game.js`

Generated bundle files should be clearly treated as generated output. Source files should be edited instead of compiled files whenever the static compiler is in use.

## Shared API Contracts

Shared code should stay narrow.

Target:

```text
src/shared/
  api_contracts/
    auth.py
    site.py
    actor_state.py
    game_menu.py
    inventory.py
    combat.py
    exploration.py
    scenario.py
    chat.py
  enums/
```

`shared/api_contracts` contains only request and response DTOs for backend API routes that are used by both backend and frontend.

Allowed examples:

- request models accepted by backend API routes and sent by frontend API clients
- response models returned by backend API routes and parsed by frontend API clients
- stable enums used in those API contracts

Avoid:

- frontend view models
- backend service DTOs
- database models
- Redis snapshot internals unless they are intentionally exposed by an API route
- temporary helper schemas used only on one side

Backend-internal DTOs belong under `src/backend/features/*/dto/`.

Frontend-only view models belong under `src/frontend/features/*/view_models/`.

## Site Feature

The site may eventually run as a separate frontend container from the game UI. That does not mean the site frontend should own database access.

Target ownership:

```text
src/backend/features/site/
  api/
  dto/
  models/
  repositories/
  services/

src/frontend/features/site/
  routes/
  services/
  view_models/
  forms/
  dependencies/
```

Request flow:

```text
browser
  -> frontend/features/site/routes
  -> frontend/features/site/services
  -> integrations/backend_api/site.py
  -> backend/features/site/api
  -> backend/features/site/services
  -> backend/features/site/repositories
  -> DB
```

The same rule applies to game UI containers. Frontend containers render UI and call backend APIs; backend features own persistence and domain behavior.

## Dependency Rules

Allowed:

- `frontend/app.py -> frontend/features/*/routes`
- `frontend/features/* -> frontend/core`
- `frontend/features/* -> frontend/integrations/backend_api`
- `frontend/features/* -> shared/api_contracts` when typing request/response data is useful
- `frontend/integrations/backend_api -> frontend/core/api`
- `frontend/integrations/backend_api -> shared/api_contracts`

Avoid:

- `frontend/* -> backend/features/*`
- frontend database sessions, repositories, or migrations
- cross-feature imports between frontend feature internals
- putting frontend view models in `shared`
- putting backend domain behavior in frontend services

## Prompt Handoff Workflow

When starting a new chat for a focused implementation task, the prompt should be narrow and explicit. It should tell the next agent exactly which files to inspect, which files may be changed, what structure is being targeted, and which architectural rules must be preserved.

Prompt shape:

```text
We are working in C:\install\projects\pets\TurnBasedMMORPG.

Read these docs first:
- docs/BACKEND_ARCHITECTURE_PREVIEW.md
- docs/FRONTEND_ARCHITECTURE_PREVIEW.md

Task:
<specific task>

Relevant current files:
- <exact file path>
- <exact file path>

Target structure:
<small tree or exact files to create/move/edit>

Rules:
- Do not import src.backend.features from frontend.
- Frontend features call backend through src/frontend/integrations/backend_api.
- Shared DTOs belong only in src/shared/api_contracts when used by both backend and frontend.
- Frontend view models stay in src/frontend/features/<feature>/view_models.
- Keep changes scoped to the listed files unless you find a hard blocker.

Verification:
<exact command or manual check>
```

This project should use those handoff prompts to keep new chats focused on one implementation slice at a time.
