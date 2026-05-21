# Frontend

`src/frontend/` — server-side site-web FastAPI service. Он рендерит публичный
сайт, account/auth flow, cabinet/admin surfaces, library и game-facing browser
views.

В текущей архитектуре имя `frontend` историческое: по ownership это site-web
service, а не только browser code.

## Ownership

Frontend/site владеет:

- public site pages;
- auth pages и user/account flow;
- cabinet/admin rendering;
- library pages;
- Jinja/HTMX templates и site/game-facing browser views;
- frontend routes, forms, services, view models и static assets;
- typed backend API clients under `src/frontend/integrations/backend_api/`;
- site-owned database models/repositories;
- Alembic миграциями для `site` schema;
- graceful unavailable state для game-backed страниц, когда backend/game
  недоступен.

Frontend/site не владеет:

- gameplay rules;
- combat/scenario/exploration runtime;
- game workers;
- game/chat schemas;
- прямым импортом backend internals.

## Current Feature Shape

Site-owned features живут в:

```text
src/frontend/features/
```

Game-facing browser orchestration живет в:

```text
src/frontend/game_features/
```

HTTP-клиенты к game backend живут в:

```text
src/frontend/integrations/backend_api/
```

## Site Database

Frontend Alembic и database infrastructure находятся в:

```text
src/frontend/alembic/
src/frontend/alembic.ini
src/frontend/core/database/
```

Site models принадлежат `site` schema. Backend/game models не импортируются в
frontend database layer.

## Разделы

- [Дизайн веб-интерфейса](interface_design/)
- [Game Features](game_features/)
- [Site Features](site_features/)
- [Integrations](integrations.md)
- [Middleware](middleware.md)
