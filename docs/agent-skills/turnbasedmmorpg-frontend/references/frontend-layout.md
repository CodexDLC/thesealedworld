# Frontend Layout

## Target Skeleton

```text
src/frontend/
  app.py
  manage.py
  config/
  core/
  integrations/
    backend_api/
  features/
    <feature_name>/
      routes/
      services/
      view_models/
      forms/
      dependencies/
  game_features/
    <feature_name>/
      routes/
      services/
      view_models/
      forms/
      dependencies/
  templates/
  static/
```

Create folders only when they are needed, but keep folder names consistent.

## Feature Folders

Use `src/frontend/game_features/` for gameplay surfaces such as game session, game menu, scenario, exploration, arena, combat, character status, and game catalog UI.

Use `src/frontend/features/` for public site, auth, account/cabinet, library, and other web-portal surfaces.

Use `routes/` for FastAPI routers that serve pages, forms, and HTMX fragments.

Use `services/` for frontend orchestration that calls backend API clients and assembles view data.

Use `view_models/` for data shaped for Jinja templates.

Use `forms/` for browser form parsing and validation.

Use `dependencies/` for FastAPI dependency providers and feature-local wiring.

Frontend feature internals should not import internals from another frontend feature. Promote only truly generic code to `core`.

## Game Session Context

Gameplay domains are rendered through the game session shell:

```text
src/frontend/templates/game/session.html
src/frontend/game_features/session/services/session_context_builder.py
src/frontend/game_features/session/services/response_director.py
```

Domain templates under `src/frontend/templates/game/domains/<domain>/` receive context assembled by the session layer. They should not fetch backend data directly or import backend feature internals.

For combat, add or update a typed backend client in `src/frontend/integrations/backend_api/`, then assemble combat-specific view models in `src/frontend/game_features/combat/` before passing them into `game/domains/combat/*` templates.

## Templates

Use:

```text
src/frontend/templates/site/
```

for public site pages, account/cabinet pages, auth entry surfaces, news, library, and game lobby pages rendered as site UI.

Use:

```text
src/frontend/templates/game/
```

for the game shell, game layouts, viewport, scene, status panels, sidebars, scenario UI, lobby-in-game screens, and game fragments.

Use:

```text
src/frontend/templates/shared/
```

only for reusable layout parts shared by site and game, such as meta, scripts, styles, minimal wrappers, or truly common fragments.

Use:

```text
src/frontend/templates/system/
```

for internal design system and preview pages.

Use:

```text
src/frontend/templates/errors/
```

for error pages.

## Static Assets

Use:

```text
src/frontend/static/css/core/
src/frontend/static/css/layout/
src/frontend/static/css/components/
src/frontend/static/css/includes/
src/frontend/static/css/pages/
src/frontend/static/css/pages/game/
src/frontend/static/css/vendor/
```

Use `pages/game/` for game-specific layout, viewport, scenario, combat, field, chat, and status styles.

Use frontend-owned image folders for runtime icons, for example:

```text
src/frontend/static/images/ui/game-menu-icons/
src/frontend/static/images/ui/scenario-choice-icons/
src/frontend/static/images/ui/combat-icons/
```

If an icon is only available in `tools/icon-reserve/game-icons-net/`, copy and adapt it into a frontend-owned static folder and map semantic keys to that file.

Use:

```text
src/frontend/static/js/core/
src/frontend/static/js/vendor/
```

for source modules and vendored browser libraries. Treat top-level bundles like `site.js` and `game.js` as bundle surfaces; edit source modules when a compiler is active.

## Backend API Clients

Place typed frontend HTTP clients in:

```text
src/frontend/integrations/backend_api/
```

Frontend services call those clients instead of constructing raw HTTP calls everywhere.

Do not hide backend business behavior in API clients. They should map frontend calls to backend HTTP routes.
