# Backend Game Workplan

## Purpose

Define the future responsibility of `src/backend` as the game backend and absorb chat into backend ownership.

The backend should own game logic and runtime behavior only. Site auth, public site pages, cabinet, and library ownership move to the frontend/site service.

## Ownership

`src/backend` owns:

- Game lobby.
- Character lifecycle and ownership checks.
- Active character sessions.
- Game session.
- Scenario.
- Combat.
- Exploration.
- Inventory.
- Arena.
- World and game catalog runtime.
- Game workers.
- Redis streams and runtime state.
- Chat after migration.
- Backend Alembic migrations for `game` and `chat` schemas.

Backend should not own:

- Public site rendering.
- Site auth pages.
- Site cabinet rendering.
- Library pages unless they are game API endpoints.
- Site schema migrations.

## Database And Alembic

Backend Alembic should own only game and chat models.

Target schemas:

```text
game
chat
```

Game models should explicitly belong to the `game` schema.

Chat models should explicitly belong to the `chat` schema.

Remove site auth models from backend model imports once frontend/site owns them.

Current file to split:

```text
src/backend/core/database/model_imports.py
```

The backend database/session layer should no longer create or migrate `site` schema models.

Current decision:

- Site auth models are owned by `src/frontend/features/auth/models`.
- Backend model imports do not include site auth models.
- `characters.user_id` is a UUID ownership column without a cross-schema FK to `site.auth_users`.
- Game requests use backend-owned token identity; site auth tokens are only a temporary compatibility path while frontend/site switches to game tokens.

## Character Ownership

To keep migrations independent, store account ownership as UUID without requiring a cross-schema FK at the first pass:

```text
game.characters.user_id UUID not null index
```

Every game API that accepts `character_id` must verify:

```text
current_user.id == character.user_id
```

Do not trust client-provided character ownership.

## Game Auth Boundary

Frontend/site calls backend/game as an internal service.

Current contract:

- Site-to-game requests must send `X-Internal-Service-Key`.
- Backend setting names are `site_to_game_service_key` and optional override `frontend_internal_service_key`.
- `POST /game-lobby/bootstrap` accepts a signed/internal user context and returns lobby characters filtered by `user_id`.
- `POST /game-lobby/select` validates character ownership, enters the character, and issues `game_access` plus `game_refresh`.
- `POST /game-lobby/create`, `/game-lobby/release-selected`, and `/game-lobby/delete-character` use the same internal service boundary for site-owned lobby actions. Create issues game tokens in the scenario payload; delete checks character ownership and the submitted confirmation name before cleanup.
- `POST /game-lobby/refresh-token` rotates a valid `game_refresh` into a fresh token pair.

Game token claims:

```text
token_type = "game_access" | "game_refresh"
sub = user_uuid
character_id = game character id
session_id = game session id
exp
iat
```

Backend route dependencies resolve `AuthenticatedUser` from `game_access` and enforce `character_id` scope for game action routes. Transitional site token support remains only to keep the split incremental.

## Chat Absorption

Move the old `src/chat` tree into backend ownership at `src/backend/chat`.

Target shape:

```text
src/backend/chat/
  api/
  ws/
  dto/
  services/
  repositories/
  models/
  events/
  integrations/
```

The chat process may still be launched as a separate container, but it should use the backend app/codebase patterns.

Current chat files to study:

- `src/backend/chat/app.py`
- `src/backend/chat/api/router.py`
- `src/backend/chat/api/ws.py`
- `src/backend/chat/models`
- `src/backend/chat/repositories`
- `src/backend/chat/services`
- `src/backend/chat/workers`

Migration direction:

1. Move chat models to backend ownership.
2. Register chat models in backend Alembic under `chat` schema.
3. Move REST and WebSocket routes under backend chat API.
4. Reuse backend settings, Redis, DB/session, logging, and lifespan infrastructure.
5. Update the chat container to run a backend chat entrypoint or backend app with chat-only routing if needed.
6. Remove duplicate chat app/config/database layers after the backend-owned route is stable.

## Backend API Boundary

The site service should interact with game through HTTP clients only.

Backend game APIs should return data contracts suitable for frontend rendering, but they should not render site templates.

Existing frontend client location:

```text
src/frontend/integrations/backend_api/
```

Maintain and expand this boundary instead of importing backend internals from frontend.

## Runtime Availability

Backend may be restarted independently from the site service.

When backend is down, frontend/site handles the unavailable state. Backend does not need to preserve site availability.

Backend health should remain simple and usable for frontend checks:

```text
GET /health
```

## Required Moves

1. Remove site auth ownership from backend after frontend/site is ready.
2. Keep game features under `src/backend/features`.
3. Move chat into `src/backend/chat`.
4. Register only game/chat models in backend Alembic.
5. Ensure `game.characters.user_id` is checked in API/service paths.
6. Add backend-owned game token issuance and route-level character scope checks.
7. Update Docker chat service to build from backend codebase.
8. Keep workers aligned with backend settings and Redis streams.

## Verification Targets

- Backend app route registration tests.
- Game lobby ownership tests.
- Character ownership tests.
- Chat REST tests.
- Chat WebSocket tests.
- Backend Alembic metadata import smoke test for `game` and `chat` schemas.
