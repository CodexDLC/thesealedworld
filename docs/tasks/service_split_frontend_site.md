# Frontend Site Workplan

## Purpose

Define the future responsibility of `src/frontend` as the site-web FastAPI service.

This service should keep the public site alive while the game backend is restarted or unavailable.

## Ownership

`src/frontend` owns:

- User-facing website.
- Auth pages and user/account flow.
- Cabinet.
- Library.
- Site templates under `src/frontend/templates/site/`.
- Shared/minimal template wrappers needed for site rendering.
- Frontend routes, forms, services, view models, and static files.
- Typed game backend clients under `src/frontend/integrations/backend_api/`.
- Site-owned database models and repositories.
- Site Alembic migrations for the `site` schema.

Repositories for site-owned database access should live inside the owning frontend `features/<feature>/` folder. Do not add a broad shared repository layer unless the number of models and cross-feature reuse justify it.

Example target shape:

```text
src/frontend/features/auth/
  routes/
  forms/
  services/
  repositories/
  models/
  dto/
  dependencies/

src/frontend/features/library/
  routes/
  services/
  repositories/
  models/
  view_models/

src/frontend/features/cabinet/
  routes/
  services/
  repositories/
  view_models/
```

## Database And Alembic

Add a frontend/site Alembic layer for the `site` schema.

Target:

```text
src/frontend/alembic/
src/frontend/alembic.ini
src/frontend/core/database/
```

The site database layer should expose site-owned session dependencies only. It should not import backend game models.

Site models should explicitly belong to the `site` schema:

```python
__table_args__ = {"schema": "site"}
```

Initial site-owned tables likely include:

- `site.auth_users`
- `site.auth_refresh_tokens`
- cabinet/site analytics tables if persisted
- library/content tables if persisted

## Auth

Auth may live in the frontend container because this is a server-side FastAPI service, not browser-only logic.

Allowed:

- Hashing passwords server-side.
- Issuing/refreshing tokens server-side.
- Storing refresh tokens in the `site` schema.
- Managing secure cookies.
- Resolving the current user for site rendering.

Not allowed:

- Relying only on browser-side validation.
- Putting signing secrets in browser JavaScript.
- Letting the browser prove character ownership without backend verification.

The game backend should accept the authenticated user identity through token/cookie flow and still verify character ownership against game data.

## Game Backend Integration

All game calls from the site service must go through typed clients:

```text
src/frontend/integrations/backend_api/
```

The site service must not import backend feature internals.

Game-backed surfaces should degrade cleanly:

- Game lobby unavailable.
- Server maintenance message.
- Rankings unavailable or stale snapshot, depending on the chosen future strategy.
- No full-site failure when backend HTTP calls fail.

## Library And Game Data

Some library/cabinet/ranking pages may need game data. This is intentionally deferred.

Candidate strategies:

- Read live data through game backend APIs.
- Maintain site-owned public projections/snapshots.
- Cache public game data in Redis with a maintenance fallback.

Do not solve this before the service boundary and Alembic split are stable.

## Current Frontend Shape

Site-owned frontend code now uses the target `features/` namespace:

- `src/frontend/features/auth`
- `src/frontend/features/cabinet`
- `src/frontend/features/library`
- `src/frontend/features/public_site`

Game-facing frontend orchestration remains in:

- `src/frontend/game_features/game_lobby`
- `src/frontend/integrations/backend_api`

Backend-owned auth code has been removed from the game backend:

- `src/backend/features_site/auth` is no longer a live ownership boundary.

## Completed Frontend Moves

- Moved frontend auth from `src/frontend/site_features/auth` to `src/frontend/features/auth`.
- Moved frontend cabinet from `src/frontend/site_features/cabinet` to `src/frontend/features/cabinet`.
- Split the former `src/frontend/site_features/site` into `src/frontend/features/public_site` and `src/frontend/features/library`.
- Updated frontend runtime imports and frontend tests to use `src.frontend.features.*`.
- Removed the empty `src/frontend/site_features` legacy tree.
- Kept game requests behind `src/frontend/integrations/backend_api/`.
- Added frontend-owned Redis site key namespace support under `src/frontend/core/redis/`.
- Moved the optional site page cache key out of backend Redis key definitions.
- Moved the auth user Redis cache manager into `src/frontend/features/auth/integrations/user_cache.py`.
- Reserved `site:*` for site-owned Redis data and `game:*` for game backend runtime data.
- Added frontend-owned database base/session/model import layer under `src/frontend/core/database/`.
- Added frontend Alembic shell under `src/frontend/alembic/` and `src/frontend/alembic.ini`.
- Moved auth models, DTOs, repositories, persistence, token/security runtime, and API router into `src/frontend/features/auth/`.
- Removed the frontend `BackendAuthApi`; auth now uses local site auth instead of proxying to the game backend.
- Removed backend auth model/repository/service/API ownership from `src/backend/features_site/auth`.
- Updated backend game routes to depend on `src.backend.core.auth.AuthenticatedUser` identity only.
- Added frontend game-token state under `src/frontend/game_features/session/token_state.py`.
- Game UI calls now prefer `tbmmorpg_game_access_token` and fall back to site access only as a transitional compatibility path.
- Game lobby enter/start responses can set `tbmmorpg_game_access_token` and `tbmmorpg_game_refresh_token` when backend starts returning game tokens.
- Backend API clients now attach the configured internal service header/key to outbound game-backend requests.
- Game lobby now uses backend service endpoints `/game-lobby/bootstrap` and `/game-lobby/select` for site-user bootstrap and character selection/game-token issuance.
- Game lobby create, release, and delete now also use typed internal backend API requests instead of bearer-token lobby calls. Create reads game tokens from the create response, delete clears stale active-character/game-token cookies, and visible lobby/site navigation labels are localized.

## Required Moves

1. Remove the transitional site-token fallback from game-token access after backend game-token issuance is live.
2. Add graceful game unavailable behavior for game-backed frontend surfaces.
3. Decide whether library/ranking data remains live through game APIs or gets site-owned snapshots.
4. Add first real site Alembic revision after the database reset strategy is confirmed.
5. Keep game requests behind backend API clients.

## Verification Targets

- Auth route tests.
- Frontend middleware tests.
- Site rendering tests.
- Alembic metadata import smoke test for `site` schema.
- Game backend unavailable rendering tests for lobby/game entry.

Current verification:

- `.\.venv\Scripts\pytest.exe tests\frontend --no-cov`
- `.\.venv\Scripts\pytest.exe tests\backend --no-cov`
