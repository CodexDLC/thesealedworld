# Service Split Finalization

## Table of Contents

1. Goal
2. Final Service Shape
3. Database Schemas
4. Runtime Availability Model
5. Working Documents
6. Migration Order
7. Open Decisions

## Goal

Finalize the split between the site service and the game backend while keeping one repository and one codebase.

The primary product goal is operational: the site must keep working when the game backend is restarted, stopped for maintenance, or temporarily unavailable. In that state, public pages, auth, cabinet, and library surfaces should remain available, while game entry points show a clear maintenance or unavailable state.

## Final Service Shape

### Frontend / Site Service

`src/frontend` becomes the server-side site service. It remains a FastAPI application that renders HTML templates and owns the web portal layer.

Responsibilities:

- Public site pages.
- Auth and user/account layer.
- Cabinet.
- Library.
- Site-owned templates, forms, view models, and static assets.
- Client-facing FastAPI routes that render Jinja/HTMX responses.
- Browser-side JavaScript for client interaction where appropriate.
- Backend API clients under `src/frontend/integrations/backend_api/`.
- Game unavailable and maintenance states when the game backend is down.
- Site database schema migrations.

The service may be renamed later from `frontend` to `site`, but that should be a separate refactor. For now, the architectural meaning is `frontend == site-web`.

### Backend / Game Service

`src/backend` becomes the game backend. It owns game rules, runtime state, game APIs, workers, and Redis-backed active character sessions.

Responsibilities:

- Game lobby API.
- Character and active character lifecycle.
- Game session.
- Scenario.
- Combat.
- Exploration.
- Inventory.
- Arena.
- World/game catalog runtime.
- Redis active character state and game streams.
- Chat as a backend-owned module after absorbing the old `src/chat` tree.
- Game and chat database schema migrations.

The backend does not render the public site. The site service reaches game behavior through typed backend API clients.

### Chat

Chat should be moved into the backend codebase instead of remaining a fully separate source tree with its own duplicated app, config, and database layer.

Target shape:

```text
src/backend/chat/
  api/
  ws/
  services/
  repositories/
  models/
  dto/
  workers/
```

The chat process may still run as a separate container when useful, but it should import and use the backend codebase, backend settings, backend database/session infrastructure, and backend Alembic model registration.

## Database Schemas

Use one physical Postgres database with separated schemas:

```text
site
  auth_users
  auth_refresh_tokens
  cabinet_*
  library_*
  site-owned data

game
  characters
  character_attributes
  skills
  inventory
  world
  scenario
  combat
  arena
  game-owned data

chat
  chat_messages
  chat_sessions
  chat-owned persistence
```

Frontend/site Alembic owns only the `site` schema.

Backend/game Alembic owns the `game` and `chat` schemas.

To preserve service independence, avoid cross-schema foreign keys at the first pass unless explicitly chosen later. Store `game.characters.user_id` as a UUID and enforce ownership in the game API:

```text
current_user.id == character.user_id
```

This keeps site and game migrations independent while still making a later physical database split possible.

## Runtime Availability Model

The site service should start and operate independently from the game backend.

Expected behavior when the game backend is down:

- Public site works.
- Auth works.
- Cabinet works for site-owned data.
- Library works for site-owned or cached/static data.
- Game entry, lobby, ranking, or game-backed panels display unavailable or maintenance state.
- Frontend API clients fail gracefully and do not break full site rendering.

Redis may be used for short-lived health/cache state, but Postgres remains the source of truth for site users and site-owned data.

## Working Documents

- [Frontend Site Workplan](service_split_frontend_site.md)
- [Backend Game Workplan](service_split_backend_game.md)

## Migration Order

1. Freeze the target boundaries in these documents.
2. Add site Alembic ownership for the `site` schema. Done.
3. Move or re-home site-owned auth/user models into frontend/site ownership. Done.
4. Remove site auth models from backend Alembic model imports. Done.
5. Keep frontend/backend communication through `src/frontend/integrations/backend_api/`. Done for game APIs; auth no longer proxies to backend.
6. Move chat code into backend ownership. Done.
7. Register chat models in backend Alembic under the `chat` schema. Done.
8. Update Docker containers so chat may run as a backend-code process instead of a separate source service.
9. Add maintenance/unavailable rendering for game-backed frontend surfaces.
10. Reset/rebuild the database after migration boundaries are clean.

## Progress Notes

- Frontend site-owned code has been moved from the legacy `src/frontend/site_features/` namespace into `src/frontend/features/`.
- Frontend `auth`, `cabinet`, `library`, and `public_site` now have separate feature folders.
- Library routes were split from public site routes while keeping game catalog access behind `src/frontend/integrations/backend_api/`.
- Redis key namespaces now use top-level service ownership: site-owned auth cache uses `site:auth:user:{user_id}`, game actor snapshots use `game:combat:snapshot:{actor_id}`, and frontend-owned optional page cache key lives under `src/frontend/core/redis/`.
- The auth user Redis cache manager has moved out of backend `features_site` ownership into `src/frontend/features/auth/integrations/user_cache.py`.
- Chat source code moved from `src/chat` to `src/backend/chat`; backend Alembic owns the `chat` schema.
- Frontend/site owns `site.auth_users` and `site.auth_refresh_tokens`; backend Alembic no longer imports site auth models.
- Backend `characters.user_id` remains a UUID ownership column without a cross-schema FK to site auth.
- Frontend/site now owns auth models, repositories, DTOs, persistence, token/security runtime, API routes, and local auth middleware resolution.
- Frontend/site database infrastructure exists under `src/frontend/core/database/`; frontend Alembic exists under `src/frontend/alembic/` plus `src/frontend/alembic.ini`.
- Backend no longer imports `src.backend.features_site.auth`; game routes use `src.backend.core.auth.AuthenticatedUser` as the token-derived identity.
- The old frontend `BackendAuthApi` was removed because `/auth` is no longer a backend-game API.
- Frontend game calls now have a distinct game-token layer: `tbmmorpg_game_access_token` / `tbmmorpg_game_refresh_token`.
- Frontend game calls attach the configured internal service key header to backend API requests.
- Frontend game lobby calls backend `/game-lobby/bootstrap` with site user context and `/game-lobby/select` to receive game tokens.
- Backend now has `game_access` / `game_refresh` encode-decode helpers, internal service-key dependency, lobby bootstrap, character select, and game refresh endpoints.
- Backend game action routes enforce game-token `character_id` scope when a game token is used; transitional site token support remains for incremental rollout.
- Game lobby owner operations now use one internal site-to-game contract: `/game-lobby/create`, `/game-lobby/release-selected`, and `/game-lobby/delete-character` accept shared lobby request DTOs plus `X-Internal-Service-Key`. Character creation returns game tokens in the scenario payload, and character deletion validates the confirmation name on the backend.
- Current verification is green: `.\.venv\Scripts\pytest.exe tests\frontend --no-cov` and `.\.venv\Scripts\pytest.exe tests\backend --no-cov`.

## Open Decisions

- Whether to physically rename `src/frontend` to `src/site`.
- Whether `game.characters.user_id` should later gain a cross-schema FK to `site.auth_users.id`.
- Whether rankings/library pages should read only through game backend APIs, use site-owned projections, or cache public snapshots.
- Exact payment service integration contract.
