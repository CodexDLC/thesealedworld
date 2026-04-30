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
  templates/
  static/
```

Create folders only when they are needed, but keep folder names consistent.

## Feature Folders

Use `routes/` for FastAPI routers that serve pages, forms, and HTMX fragments.

Use `services/` for frontend orchestration that calls backend API clients and assembles view data.

Use `view_models/` for data shaped for Jinja templates.

Use `forms/` for browser form parsing and validation.

Use `dependencies/` for FastAPI dependency providers and feature-local wiring.

Frontend feature internals should not import internals from another frontend feature. Promote only truly generic code to `core`.

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

Use `pages/game/` for game-specific layout, viewport, scenario, field, chat, and status styles.

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
