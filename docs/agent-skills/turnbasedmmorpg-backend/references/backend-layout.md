# Backend Layout

## Target Skeleton

```text
src/backend/
  app.py
  manage.py
  core/
  config/
  features/
    auth/
    account/
    site/
    chat/
    world/
    game_lobby/
    actor_state/
    combat/
    inventory/
    exploration/
    scenario/
    game_menu/
    arena/
```

Feature folders should use only the layers they need:

```text
api/
dto/
models/
repositories/
integrations/
services/
dependencies/
events/
workers/
runtime/
```

## Layer Responsibilities

Use `api/` for FastAPI routers and HTTP boundary code.

Use `dto/` for backend DTOs owned by the feature, unless a DTO is a shared frontend/backend API contract.

Use `models/` for SQLAlchemy ORM models owned by the feature.

Use `repositories/` for persistence and cache access owned by the feature. Split into `db/` and `redis/` only when useful.

Use `integrations/` for facades that encapsulate low-level infrastructure managers (DB, Redis, sessions) behind a single cohesive interface.

Use `services/` for feature use cases and application/domain logic.

Use `dependencies/` for FastAPI dependency providers and local wiring.

Use `events/` for Redis Streams event handlers, publishers, subscribers, and stream-facing adapters.

Use `workers/` for ARQ or background jobs.

Use `runtime/` for engines, processors, assemblers, and other internal gameplay runtime code.

## Data Ownership

DB-owner features:

- `auth`: users, credentials, refresh tokens, auth dependencies.
- `site`: public or pre-game website content, when needed.
- `chat`: rooms, messages, moderation, history.
- `world`: persistent/generated world data and world cache bootstrap.
- `game_lobby`: character list/create/delete/enter flow before active runtime.
- `actor_state`: durable game actor/player state and DB-to-Redis lifecycle.

Runtime gameplay features:

- `combat`
- `inventory`
- `exploration`
- `scenario`
- `game_menu`
- `arena`

Runtime gameplay features should normally operate on Redis snapshots/events and avoid direct game database access.

## Identity Terms

Use terms consistently:

- `User` or `Account`: site account and authorization identity.
- `Character`: persistent game character owned by a user.
- `Actor`: active runtime form of a selected character, usually hydrated into Redis.

Login/register must not create actor state. Actor state appears only after a user enters the game with a selected character.
